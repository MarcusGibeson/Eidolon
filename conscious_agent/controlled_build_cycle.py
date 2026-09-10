from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from file_tools import active_project_root, safe_project_path
from operational_readiness import (
    build_controlled_self_build,
    build_doctor_report,
    build_patch_integrity_report,
    build_project_snapshot,
    build_task_review,
)
from paths import DATA_DIR, ROOT_DIR, path_reference, resolve_path_reference
from settings_manager import load_settings
from stable_loop_guardrails import stable_loop_guardrail_summary
from task_queue import list_tasks

CONTROLLED_BUILD_VERSION = RUNTIME_VERSION
WORKSPACE_DIR = DATA_DIR / "patch_workspace"
REPORTS_DIR = DATA_DIR / "controlled_build_reports"
BACKUPS_DIR = DATA_DIR / "controlled_build_backups"
CURRENT_PLAN = WORKSPACE_DIR / "current_plan.json"
PROPOSED_CHANGES = WORKSPACE_DIR / "proposed_changes.json"
DIFF_DIR = WORKSPACE_DIR / "file_diffs"
VALIDATION_REPORT = WORKSPACE_DIR / "validation_report.json"
LATEST_APPLY_REPORT = WORKSPACE_DIR / "latest_apply_report.json"
LATEST_DRY_RUN_APPLY_REPORT = WORKSPACE_DIR / "latest_dry_run_apply_report.json"
LATEST_ROLLBACK_REPORT = WORKSPACE_DIR / "latest_rollback_report.json"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    for path in [WORKSPACE_DIR, REPORTS_DIR, BACKUPS_DIR, DIFF_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _read_json(path: Path, default: Any) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return data


def _write_json(path: Path, data: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")



def latest_apply_report_integrity(archive_stale: bool = False) -> dict[str, Any]:
    """Return safety status for the latest real apply pointer.

    v10.0 moved dry-run reports to latest_dry_run_apply_report.json, but older
    packages could still contain a stale dry-run report at latest_apply_report.json.
    Treat that as unusable for rollback and optionally archive it.
    """
    report = _read_json(LATEST_APPLY_REPORT, {})
    if not report:
        return {"status": "missing", "ok": True, "message": "No latest real apply report exists."}
    status = report.get("status")
    applied_rows = [row for row in report.get("applied", []) if isinstance(row, dict) and row.get("status") == "applied" and row.get("action") != "metadata_only"]
    if status != "applied" or not applied_rows:
        archive_path = None
        if archive_stale:
            stale_dir = WORKSPACE_DIR / "stale_apply_reports"
            stale_dir.mkdir(parents=True, exist_ok=True)
            suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = stale_dir / f"latest_apply_report_{suffix}_{_slug(str(status or 'unknown'))}.json"
            archive_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
            try:
                LATEST_APPLY_REPORT.unlink()
            except OSError:
                pass
        return {
            "status": "stale",
            "ok": False,
            "latest_apply_status": status,
            "applied_row_count": len(applied_rows),
            "archived_to": path_reference(archive_path) if archive_path else None,
            "message": "latest_apply_report.json is not a real applied patch pointer and cannot be used for rollback.",
        }
    return {
        "status": "valid",
        "ok": True,
        "latest_apply_status": status,
        "applied_row_count": len(applied_rows),
        "message": f"Latest apply report has {len(applied_rows)} applied file row(s).",
    }


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return cleaned[:50] or "controlled-build"


def _status_from(counts: Counter[str]) -> str:
    if counts.get("fail", 0):
        return "fail"
    if counts.get("warn", 0):
        return "warn"
    return "pass"


def _priority_value(task: dict[str, Any]) -> int:
    raw = str(task.get("priority", "medium")).lower()
    mapping = {"critical": 40, "high": 30, "medium": 20, "low": 10}
    if raw.isdigit():
        return int(raw)
    return mapping.get(raw, 20)


def _task_risk(task: dict[str, Any]) -> str:
    text = json.dumps(task, default=str).lower()
    explicit = str(task.get("risk", task.get("risk_level", ""))).lower()
    if explicit in {"low", "medium", "high"}:
        return explicit
    high_terms = ["delete", "rollback", "apply patch", "secret", "token", "password", "subprocess", "shell", "approval"]
    medium_terms = ["main.py", "dashboard.py", "api_server.py", "command_runner.py", "settings", "safety"]
    if any(term in text for term in high_terms):
        return "high"
    if any(term in text for term in medium_terms):
        return "medium"
    return "low"


def _safe_task(task: dict[str, Any]) -> bool:
    status = str(task.get("status", "planned")).lower()
    if status in {"done", "completed", "cancelled", "blocked", "failed"}:
        return False
    if _task_risk(task) == "high":
        return False
    if bool(task.get("requires_approval")):
        return False
    return True


def _synthetic_task(project_id: str) -> dict[str, Any]:
    return {
        "id": "synthetic_v9_safe_readme_task",
        "title": "Controlled build README/workspace safety probe",
        "description": "No queued task was safe to select, so v9.0 selected a synthetic README/workspace probe. It stages changes before touching source files.",
        "status": "planned",
        "priority": "low",
        "risk": "low",
        "project": project_id,
        "synthetic": True,
    }


def build_controlled_task_selection(project_id: str = "eidolon") -> dict[str, Any]:
    tasks = list_tasks(project=project_id, include_cancelled=False)
    candidates: list[dict[str, Any]] = []
    for task in tasks:
        risk = _task_risk(task)
        safe = _safe_task(task)
        candidates.append({
            "id": task.get("id", ""),
            "title": task.get("title", task.get("name", "[untitled]")),
            "status": task.get("status", "unknown"),
            "priority": task.get("priority", "medium"),
            "priority_score": _priority_value(task),
            "risk": risk,
            "requires_approval": bool(task.get("requires_approval")),
            "safe_to_select": safe,
            "source": "task_queue",
            "raw": task,
        })
    selectable = [item for item in candidates if item["safe_to_select"]]
    selectable.sort(key=lambda item: (item["risk"] != "low", -item["priority_score"], str(item["title"]).lower()))
    selected = selectable[0] if selectable else {
        "id": _synthetic_task(project_id)["id"],
        "title": _synthetic_task(project_id)["title"],
        "status": "planned",
        "priority": "low",
        "priority_score": 10,
        "risk": "low",
        "requires_approval": False,
        "safe_to_select": True,
        "source": "synthetic",
        "raw": _synthetic_task(project_id),
    }
    warnings = []
    if not selectable:
        warnings.append("No safe queued task was available, so a synthetic README/workspace safety probe was selected.")
    return {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if warnings else "pass",
        "ok": True,
        "selected_task": selected,
        "candidate_count": len(candidates),
        "safe_candidate_count": len(selectable),
        "warnings": warnings,
        "recommendations": [
            "Use --plan-patch after selection to create a bounded patch plan.",
            "Avoid high-risk or approval-required tasks until the supervised loop has clean verification history.",
        ],
        "next_commands": [
            "python conscious_agent/main.py --controlled-self-build --plan-patch",
            "python conscious_agent/main.py --patch-workspace-status",
        ],
        "message": f"Selected {selected['id']} ({selected['risk']} risk) from {selected['source']}.",
    }


def controlled_task_selection_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_controlled_task_selection()
    selected = report.get("selected_task") or {}
    lines = [
        "# Eidolon v8.1 Controlled Self-Build Task Selection",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at')}",
        f"Status: {str(report.get('status')).upper()}",
        f"Message: {report.get('message')}",
        "",
        "## Selected task",
        f"- ID: {selected.get('id')}",
        f"- Title: {selected.get('title')}",
        f"- Source: {selected.get('source')}",
        f"- Risk: {selected.get('risk')}",
        f"- Priority: {selected.get('priority')}",
        f"- Requires approval: {selected.get('requires_approval')}",
        "",
        "## Warnings",
    ]
    lines.extend([f"- {item}" for item in report.get("warnings", [])] or ["- None."])
    lines.extend(["", "## Next commands"])
    lines.extend([f"- {item}" for item in report.get("next_commands", [])])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def build_patch_plan(project_id: str = "eidolon", target_version: str = "15.0", save: bool = True) -> dict[str, Any]:
    selection = build_controlled_task_selection(project_id=project_id)
    selected = selection.get("selected_task") or {}
    task_id = str(selected.get("id") or "synthetic")
    risk = str(selected.get("risk") or "low")
    files = ["README_NEXT_STEPS.md"]
    if selected.get("source") != "synthetic":
        title = str(selected.get("title", "")).lower()
        if "dashboard" in title:
            files.append("conscious_agent/dashboard.py")
        if "api" in title:
            files.append("conscious_agent/api_server.py")
        if "command" in title or "cli" in title:
            files.append("conscious_agent/main.py")
    seen: set[str] = set()
    files = [item for item in files if not (item in seen or seen.add(item))]
    plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(task_id)}"
    approval_required = risk != "low" or any(path.startswith("conscious_agent/") for path in files if path != "README_NEXT_STEPS.md")
    plan = {
        "version": CONTROLLED_BUILD_VERSION,
        "plan_id": plan_id,
        "created_at": _now(),
        "project_id": project_id,
        "target_version": target_version,
        "status": "planned",
        "ok": True,
        "task": selected,
        "files_to_change": files,
        "expected_tests": [
            "python -m py_compile conscious_agent/*.py tools/smoke_check.py",
            "python conscious_agent/main.py --doctor",
            "python conscious_agent/main.py --readme-gate",
            "python tools/smoke_check.py",
        ],
        "readme_sections_required": [f"Eidolon v{target_version}", "Verification performed for v15.0"],
        "rollback_strategy": "Create per-file backups under data/controlled_build_backups before writing staged changes.",
        "risk": risk,
        "approval_required": approval_required,
        "readme_update_required": True,
        "stage_policy": "Generate proposed changes in data/patch_workspace first. Do not write source files until apply-staged-patch is explicitly approved.",
        "message": f"Patch plan {plan_id} created for {task_id}.",
    }
    if save:
        _write_json(CURRENT_PLAN, plan)
    return plan


def patch_plan_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_patch_plan(save=False)
    lines = [
        "# Eidolon v8.2 Controlled Patch Planner",
        "",
        f"Plan ID: {report.get('plan_id')}",
        f"Target version: {report.get('target_version')}",
        f"Task: {(report.get('task') or {}).get('id')} - {(report.get('task') or {}).get('title')}",
        f"Risk: {report.get('risk')}",
        f"Approval required: {report.get('approval_required')}",
        f"README update required: {report.get('readme_update_required')}",
        "",
        "## Files expected to change",
    ]
    lines.extend([f"- {item}" for item in report.get("files_to_change", [])] or ["- None."])
    lines.extend(["", "## Expected tests"])
    lines.extend([f"- {item}" for item in report.get("expected_tests", [])])
    lines.extend(["", "## Rollback strategy", str(report.get("rollback_strategy", ""))])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def _read_file_for_change(relative_path: str) -> tuple[bool, str, str]:
    try:
        path = safe_project_path(relative_path)
    except PermissionError as error:
        return False, "", str(error)
    if not path.exists():
        return True, "", ""
    if not path.is_file():
        return False, "", f"Target path is not a file: {relative_path}"
    try:
        return True, path.read_text(encoding="utf-8"), ""
    except UnicodeDecodeError:
        return False, "", f"Target file is not UTF-8 text: {relative_path}"
    except OSError as error:
        return False, "", str(error)


def _make_readme_probe(original: str, plan: dict[str, Any]) -> str:
    marker = "<!-- EIDOLON_CONTROLLED_BUILD_STAGE_MARKER -->"
    stamp = plan.get("plan_id", "unknown")
    note = (
        f"\n\n{marker}\n"
        f"Staged controlled-build probe for {stamp}. This line is only written if the operator explicitly applies the staged patch.\n"
    )
    if marker in original:
        return original
    return original.rstrip() + note


def stage_controlled_patch(project_id: str = "eidolon", create_plan_if_missing: bool = True, save: bool = True) -> dict[str, Any]:
    if save:
        _ensure_dirs()
    plan = _read_json(CURRENT_PLAN, None)
    if not isinstance(plan, dict) and create_plan_if_missing:
        plan = build_patch_plan(project_id=project_id, save=save)
    if not isinstance(plan, dict):
        return {"version": CONTROLLED_BUILD_VERSION, "status": "fail", "ok": False, "message": "No patch plan exists. Run --plan-patch first."}

    changes: list[dict[str, Any]] = []
    errors: list[str] = []
    for relative_path in plan.get("files_to_change", []):
        ok, original, error = _read_file_for_change(relative_path)
        if not ok:
            errors.append(error)
            continue
        proposed = original
        action = "modify" if original else "add"
        if relative_path == "README_NEXT_STEPS.md":
            proposed = _make_readme_probe(original, plan)
        else:
            # For source files, v9.0 stages metadata only unless a future generator supplies a real proposed_content.
            action = "metadata_only"
        if action == "metadata_only":
            changes.append({
                "path": relative_path,
                "action": action,
                "status": "info",
                "original_sha256": _sha256(original),
                "proposed_sha256": _sha256(original),
                "message": "No source rewrite was generated; this file remains a planned impact surface only.",
            })
            continue
        diff_text = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        ))
        diff_file = DIFF_DIR / (relative_path.replace("/", "__").replace("\\", "__") + ".diff")
        if save:
            diff_file.parent.mkdir(parents=True, exist_ok=True)
            diff_file.write_text(diff_text, encoding="utf-8")
        changes.append({
            "path": relative_path,
            "action": action,
            "status": "staged",
            "original_sha256": _sha256(original),
            "proposed_sha256": _sha256(proposed),
            "original_content": original,
            "proposed_content": proposed,
            "diff_path": path_reference(diff_file) if save else None,
            "diff_summary": {
                "added_lines": sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")),
                "removed_lines": sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---")),
            },
        })
    report = {
        "version": CONTROLLED_BUILD_VERSION,
        "created_at": _now(),
        "project_id": project_id,
        "status": "fail" if errors else "pass",
        "ok": not errors,
        "plan_id": plan.get("plan_id"),
        "changes": changes,
        "errors": errors,
        "message": f"Staged {sum(1 for c in changes if c.get('status') == 'staged')} writable change(s) and {sum(1 for c in changes if c.get('action') == 'metadata_only')} metadata-only impact surface(s).",
        "next_commands": [
            "python conscious_agent/main.py --controlled-self-build --preview-diff",
            "python conscious_agent/main.py --patch-workspace-status",
        ],
    }
    if save:
        _write_json(PROPOSED_CHANGES, report)
    else:
        report["preview_only"] = True
    return report


def patch_workspace_status() -> dict[str, Any]:
    _ensure_dirs()
    plan = _read_json(CURRENT_PLAN, {})
    proposed = _read_json(PROPOSED_CHANGES, {})
    validation = _read_json(VALIDATION_REPORT, {})
    apply_report = _read_json(LATEST_APPLY_REPORT, {})
    dry_apply_report = _read_json(LATEST_DRY_RUN_APPLY_REPORT, {})
    apply_integrity = latest_apply_report_integrity(archive_stale=False)
    warnings = []
    if apply_integrity.get("status") == "stale":
        warnings.append(apply_integrity.get("message", "latest_apply_report.json is stale."))
    diff_files = sorted(DIFF_DIR.glob("*.diff"))
    counts = Counter()
    for path in [CURRENT_PLAN, PROPOSED_CHANGES, VALIDATION_REPORT, LATEST_APPLY_REPORT, LATEST_DRY_RUN_APPLY_REPORT, LATEST_ROLLBACK_REPORT]:
        counts["present" if path.exists() else "missing"] += 1
    status = "pass" if CURRENT_PLAN.exists() and PROPOSED_CHANGES.exists() else "warn"
    ok = True
    if not apply_integrity.get("ok", True):
        status = "warn"
        ok = False
    return {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "status": status,
        "ok": ok,
        "workspace_dir": path_reference(WORKSPACE_DIR),
        "plan_id": plan.get("plan_id"),
        "proposed_change_count": len(proposed.get("changes", [])) if isinstance(proposed, dict) else 0,
        "diff_file_count": len(diff_files),
        "validation_status": validation.get("status"),
        "latest_apply_status": apply_report.get("status"),
        "latest_apply_integrity": apply_integrity,
        "latest_dry_run_apply_status": dry_apply_report.get("status"),
        "warnings": warnings,
        "files": {p.name: p.exists() for p in [CURRENT_PLAN, PROPOSED_CHANGES, VALIDATION_REPORT, LATEST_APPLY_REPORT, LATEST_DRY_RUN_APPLY_REPORT, LATEST_ROLLBACK_REPORT]},
        "counts": dict(counts),
        "next_commands": [
            "python conscious_agent/main.py --controlled-self-build --plan-patch",
            "python conscious_agent/main.py --controlled-self-build --stage-patch",
            "python conscious_agent/main.py --controlled-self-build --preview-diff",
        ],
        "message": "Patch workspace status generated.",
    }


def preview_staged_diff(project_id: str = "eidolon", stage_if_missing: bool = True, save: bool = True) -> dict[str, Any]:
    proposed = _read_json(PROPOSED_CHANGES, None)
    if not isinstance(proposed, dict) and stage_if_missing:
        proposed = stage_controlled_patch(project_id=project_id, save=save)
    if not isinstance(proposed, dict):
        return {"version": CONTROLLED_BUILD_VERSION, "status": "fail", "ok": False, "message": "No proposed changes exist. Run --stage-patch first."}
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for change in proposed.get("changes", []):
        path = str(change.get("path", ""))
        action = str(change.get("action", ""))
        diff_text = ""
        diff_path = change.get("diff_path")
        if diff_path:
            file_path = resolve_path_reference(str(diff_path))
            if file_path.exists():
                diff_text = file_path.read_text(encoding="utf-8")
        if action == "metadata_only":
            warnings.append(f"{path} is metadata-only and will not be written by apply-staged-patch.")
        rows.append({
            "path": path,
            "action": action,
            "status": change.get("status", "unknown"),
            "diff_path": diff_path,
            "added_lines": (change.get("diff_summary") or {}).get("added_lines", 0),
            "removed_lines": (change.get("diff_summary") or {}).get("removed_lines", 0),
            "diff_preview": diff_text[:4000],
        })
    report = {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "warn" if warnings else "pass",
        "ok": True,
        "plan_id": proposed.get("plan_id"),
        "rows": rows,
        "warnings": warnings,
        "recommendations": [
            "Review every diff before applying staged changes.",
            "Run --apply-staged-patch only with explicit approval and rollback available.",
        ],
        "message": f"Previewed {len(rows)} staged change row(s).",
    }
    if save:
        _write_json(VALIDATION_REPORT, report)
    else:
        report["preview_only"] = True
    return report


def _backup_path(run_id: str, relative_path: str) -> Path:
    return BACKUPS_DIR / run_id / relative_path.replace("\\", "/")


def apply_staged_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = False) -> dict[str, Any]:
    proposed = _read_json(PROPOSED_CHANGES, None)
    validation = _read_json(VALIDATION_REPORT, None)
    if not isinstance(proposed, dict):
        return {"version": CONTROLLED_BUILD_VERSION, "status": "fail", "ok": False, "message": "No staged patch exists. Run --stage-patch first."}
    if not isinstance(validation, dict):
        validation = preview_staged_diff(project_id=project_id)
    if not approve and not dry_run:
        return {
            "version": CONTROLLED_BUILD_VERSION,
            "checked_at": _now(),
            "status": "blocked",
            "ok": False,
            "dry_run": dry_run,
            "message": "Applying staged patches requires --approve-controlled-self-build. The file goblin remains supervised.",
            "next_commands": ["python conscious_agent/main.py --controlled-self-build --apply-staged-patch --approve-controlled-self-build"],
        }
    run_id = f"apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(str(proposed.get('plan_id', 'staged')))}"
    applied: list[dict[str, Any]] = []
    errors: list[str] = []
    for change in proposed.get("changes", []):
        if change.get("action") == "metadata_only":
            applied.append({"path": change.get("path"), "action": "metadata_only", "status": "skipped", "message": "No proposed file content to write."})
            continue
        relative_path = str(change.get("path", ""))
        try:
            target = safe_project_path(relative_path)
        except PermissionError as error:
            errors.append(str(error))
            continue
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if _sha256(current) != change.get("original_sha256"):
            errors.append(f"{relative_path}: current file hash does not match staged original hash.")
            continue
        backup = _backup_path(run_id, relative_path)
        if not dry_run:
            backup.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                backup.write_text(current, encoding="utf-8")
            else:
                backup.write_text("", encoding="utf-8")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(change.get("proposed_content", "")), encoding="utf-8")
        applied.append({
            "path": relative_path,
            "action": change.get("action"),
            "status": "dry_run" if dry_run else "applied",
            "backup_path": path_reference(backup),
            "original_sha256": change.get("original_sha256"),
            "applied_sha256": change.get("proposed_sha256"),
        })
    report = {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "run_id": run_id,
        "plan_id": proposed.get("plan_id"),
        "status": "fail" if errors else "dry_run" if dry_run else "applied",
        "ok": not errors,
        "dry_run": dry_run,
        "approved": approve,
        "applied": applied,
        "errors": errors,
        "readme_updated": any(row.get("path") == "README_NEXT_STEPS.md" and row.get("status") in {"applied", "dry_run"} for row in applied),
        "rollback_available": not dry_run and any(row.get("status") == "applied" and row.get("backup_path") for row in applied),
        "next_commands": [
            "python conscious_agent/main.py --verify-latest-patch",
            "python conscious_agent/main.py --readme-gate",
            "python conscious_agent/main.py --rollback-latest-patch --approve-controlled-self-build",
        ],
        "message": f"Staged patch {run_id} {'validated' if dry_run else 'applied'} with {len(errors)} error(s).",
    }
    if dry_run:
        _write_json(LATEST_DRY_RUN_APPLY_REPORT, report)
    else:
        _write_json(LATEST_APPLY_REPORT, report)
    _write_json(REPORTS_DIR / f"{run_id}.json", report)
    return report


def _run_fixed_command(command: list[str], timeout: int = 45) -> dict[str, Any]:
    started = _now()
    try:
        result = subprocess.run(command, cwd=ROOT_DIR, text=True, capture_output=True, timeout=timeout)
        return {
            "command": " ".join(command),
            "started_at": started,
            "finished_at": _now(),
            "return_code": result.returncode,
            "ok": result.returncode == 0,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        }
    except Exception as error:
        return {
            "command": " ".join(command),
            "started_at": started,
            "finished_at": _now(),
            "return_code": None,
            "ok": False,
            "error": str(error),
        }


def verify_latest_patch(project_id: str = "eidolon") -> dict[str, Any]:
    apply_report = _read_json(LATEST_APPLY_REPORT, {})
    dry_run_apply_report = _read_json(LATEST_DRY_RUN_APPLY_REPORT, {})
    apply_integrity = latest_apply_report_integrity(archive_stale=False)
    commands = [
        [sys.executable, "-m", "py_compile", *[str(p.relative_to(ROOT_DIR)) for p in sorted((ROOT_DIR / "conscious_agent").glob("*.py"))], "tools/smoke_check.py"],
        [sys.executable, "conscious_agent/main.py", "--doctor"],
        [sys.executable, "conscious_agent/main.py", "--stabilization-checkpoint", "--stabilization-full"],
        [sys.executable, "conscious_agent/main.py", "--readme-gate"],
    ]
    rows = [_run_fixed_command(command, timeout=60) for command in commands]
    fail_count = sum(1 for row in rows if not row.get("ok"))
    integrity_ok = bool(apply_integrity.get("ok", True))
    status = "failed" if fail_count or not integrity_ok else "passed_with_warnings" if apply_report.get("status") in {"blocked", "fail"} else "passed"
    report = {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": fail_count == 0 and integrity_ok,
        "apply_report_status": apply_report.get("status"),
        "latest_apply_integrity": apply_integrity,
        "latest_dry_run_apply_status": dry_run_apply_report.get("status"),
        "rows": rows,
        "rollback_recommended": fail_count > 0 and bool(apply_report.get("rollback_available")),
        "message": f"Verification {status}; {fail_count} command(s) failed; latest apply integrity={apply_integrity.get('status')}." ,
    }
    _write_json(VALIDATION_REPORT, report)
    return report


def rollback_latest_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = False) -> dict[str, Any]:
    apply_report = _read_json(LATEST_APPLY_REPORT, {})
    if not apply_report:
        return {"version": CONTROLLED_BUILD_VERSION, "status": "fail", "ok": False, "message": "No latest apply report exists."}
    integrity = latest_apply_report_integrity(archive_stale=False)
    if not integrity.get("ok"):
        return {
            "version": CONTROLLED_BUILD_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "fail",
            "ok": False,
            "dry_run": dry_run,
            "latest_apply_integrity": integrity,
            "message": "Rollback requires latest_apply_report.json to point at a real applied patch with at least one applied file row.",
        }
    if not approve and not dry_run:
        return {
            "version": CONTROLLED_BUILD_VERSION,
            "checked_at": _now(),
            "status": "blocked",
            "ok": False,
            "message": "Rollback requires --approve-controlled-self-build so a casual typo does not time-travel your files.",
        }
    restored: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in apply_report.get("applied", []):
        if row.get("status") != "applied" or row.get("action") == "metadata_only":
            continue
        relative_path = str(row.get("path", ""))
        backup_raw = str(row.get("backup_path", ""))
        backup = resolve_path_reference(backup_raw)
        if not backup.exists():
            errors.append(f"Missing backup for {relative_path}: {backup_raw}")
            continue
        try:
            target = safe_project_path(relative_path)
        except PermissionError as error:
            errors.append(str(error))
            continue
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        current_sha = _sha256(current)
        expected_sha = row.get("applied_sha256")
        if expected_sha and current_sha != expected_sha:
            errors.append(f"{relative_path}: current file hash does not match applied hash; rollback would overwrite newer edits.")
            continue
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(backup, target)
        restored.append({"path": relative_path, "backup_path": backup_raw, "status": "dry_run" if dry_run else "restored", "current_sha256": current_sha, "expected_applied_sha256": expected_sha})
    report = {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "fail" if errors else "dry_run" if dry_run else "rolled_back",
        "ok": not errors,
        "dry_run": dry_run,
        "source_apply_run_id": apply_report.get("run_id"),
        "restored": restored,
        "errors": errors,
        "message": f"Rollback {'previewed' if dry_run else 'completed'} for {len(restored)} file(s).",
    }
    _write_json(LATEST_ROLLBACK_REPORT, report)
    return report


def readme_gate(project_id: str = "eidolon") -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    text = README_FILE.read_text(encoding="utf-8") if README_FILE.exists() else ""
    required_versions = ["v8.1", "v8.2", "v8.3", "v8.4", "v8.5", "v8.6", "v8.7", "v8.8", "v8.9", "v9.0", "v9.1", "v9.2", "v9.3", "v9.4", "v9.5", "v9.6", "v9.7", "v9.8", "v9.9", "v10.0", "v10.1", "v10.2", "v10.3", "v10.4", "v10.5", "v10.6", "v10.7", "v10.8", "v10.9", "v11.0", "v11.1", "v11.2", "v11.3", "v11.4", "v11.5", "v11.6", "v11.7", "v11.8", "v11.9", "v12.0", "v12.1", "v12.2", "v12.3", "v12.4", "v12.5", "v12.6", "v12.7", "v12.8", "v12.9", "v13.0", "v13.1", "v13.2", "v13.3", "v13.4", "v13.5", "v13.6", "v13.7", "v13.8", "v13.9", "v14.0", "v14.1", "v14.2", "v14.3", "v14.4", "v14.5", "v14.6", "v14.7", "v14.8", "v14.9", "v15.0"]
    for version in required_versions:
        present = f"Eidolon {version}" in text or f"## {version}" in text
        rows.append({"name": f"readme-section-{version}", "status": "pass" if present else "fail", "message": "present" if present else "missing"})
    settings = load_settings()
    rows.append({"name": "settings-version", "status": "pass" if str(settings.get("settings_version")) == "15.0" else "warn", "message": f"settings_version={settings.get('settings_version')}"})
    apply_report = _read_json(LATEST_APPLY_REPORT, {})
    if apply_report.get("status") == "applied":
        changed_files = [row.get("path") for row in apply_report.get("applied", []) if row.get("status") == "applied"]
        readme_changed = "README_NEXT_STEPS.md" in changed_files
        rows.append({"name": "latest-applied-readme-update", "status": "pass" if readme_changed else "fail", "message": f"changed_files={changed_files}"})
    fail = sum(1 for row in rows if row["status"] == "fail")
    warn = sum(1 for row in rows if row["status"] == "warn")
    return {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": _status_from(Counter({"fail": fail, "warn": warn})),
        "ok": fail == 0,
        "rows": rows,
        "message": f"README gate checked {len(rows)} item(s): {fail} fail, {warn} warn.",
    }


def build_controlled_build_cycle(project_id: str = "eidolon", live: bool = False, approve: bool = False, dry_run: bool = True) -> dict[str, Any]:
    selection = build_controlled_task_selection(project_id=project_id)
    plan = build_patch_plan(project_id=project_id, save=True)
    staged = stage_controlled_patch(project_id=project_id)
    preview = preview_staged_diff(project_id=project_id, stage_if_missing=False)
    apply_report = apply_staged_patch(project_id=project_id, approve=approve, dry_run=True if dry_run or not live else False)
    verification = verify_latest_patch(project_id=project_id)
    integrity = build_patch_integrity_report()
    gate = readme_gate(project_id=project_id)
    rows = [selection, plan, staged, preview, apply_report, verification, integrity, gate]
    fail = sum(1 for row in rows if row.get("ok") is False or row.get("status") in {"fail", "blocked", "failed"})
    warn = sum(1 for row in rows if row.get("status") in {"warn", "passed_with_warnings", "dry_run"})
    report = {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "fail" if fail else "warn" if warn else "pass",
        "ok": fail == 0,
        "live": live,
        "approved": approve,
        "dry_run": dry_run or not live,
        "steps": {
            "selection": selection,
            "plan": plan,
            "stage": staged,
            "preview": preview,
            "apply": apply_report,
            "verification": verification,
            "integrity": integrity,
            "readme_gate": gate,
        },
        "message": f"Controlled build cycle completed with {fail} blocker(s) and {warn} warning/dry-run item(s).",
    }
    report_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    _write_json(REPORTS_DIR / f"{report_id}.json", report)
    return report


def build_supervised_dev_loop(project_id: str = "eidolon", live: bool = False, approve: bool = False, use_ai: bool = False) -> dict[str, Any]:
    doctor = build_doctor_report(project_id=project_id, full=False)
    guardrails = stable_loop_guardrail_summary(project_id=project_id)
    controlled_preview = build_controlled_self_build(project_id=project_id, max_steps=1, live=False, approve_live=False, use_ai=use_ai)
    blocked: list[str] = []
    if doctor.get("status") == "blocked":
        blocked.append("Doctor mode is blocked.")
    if live and not approve:
        blocked.append("Live supervised dev loop requires --approve-controlled-self-build.")
    if live and not guardrails.get("ok_for_live"):
        blocked.append("Stable-loop closure guardrails do not allow live advancement.")
    cycle = build_controlled_build_cycle(project_id=project_id, live=live and not blocked, approve=approve, dry_run=not live or bool(blocked))
    status = "blocked" if blocked else "completed_live" if live else "preview_complete"
    return {
        "version": CONTROLLED_BUILD_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked and cycle.get("ok", False),
        "live": live,
        "approved": approve,
        "use_ai": use_ai,
        "doctor_status": doctor.get("status"),
        "guardrails_ok_for_live": guardrails.get("ok_for_live"),
        "blocked_reasons": blocked,
        "controlled_self_build_preview": controlled_preview,
        "cycle": cycle,
        "message": "Supervised dev loop stopped after one bounded cycle.",
        "next_recommended_task": "Review the cycle report, then run --doctor before another supervised loop.",
    }


def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# {title}",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at', report.get('created_at', ''))}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ]
    for key in ["warnings", "errors", "recommendations", "next_commands", "blocked_reasons"]:
        values = report.get(key) or []
        if values or key in {"warnings", "errors", "blocked_reasons"}:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values] or ["- None."])
    rows = report.get("rows") or report.get("changes") or report.get("applied") or report.get("restored") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows:
            if isinstance(row, dict):
                name = row.get("name") or row.get("path") or row.get("id") or row.get("command") or "row"
                status = str(row.get("status", "info")).upper()
                message = row.get("message") or row.get("action") or row.get("return_code") or ""
                lines.append(f"- {status} {name}: {message}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def workspace_status_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v8.3 Patch Workspace Status", report or patch_workspace_status(), full=full)


def staged_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v8.3 Patch Staging", report or stage_controlled_patch(), full=full)


def diff_preview_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or preview_staged_diff()
    lines = [
        "# Eidolon v8.4 File Diff Preview System",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at')}",
        f"Status: {str(report.get('status')).upper()}",
        f"Message: {report.get('message')}",
    ]
    for row in report.get("rows", []):
        lines.extend([
            "",
            f"## {row.get('path')} ({row.get('action')})",
            f"Status: {row.get('status')} | +{row.get('added_lines', 0)} / -{row.get('removed_lines', 0)}",
        ])
        if row.get("diff_preview"):
            lines.extend(["```diff", row.get("diff_preview", ""), "```"])
    if report.get("warnings"):
        lines.extend(["", "## Warnings"])
        lines.extend([f"- {item}" for item in report.get("warnings", [])])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def apply_staged_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v8.5 Apply Controlled Patch", report or apply_staged_patch(dry_run=True), full=full)


def verify_latest_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v8.6 Auto-Verify Applied Patch", report or verify_latest_patch(), full=full)


def rollback_latest_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v8.7 Rollback Latest Patch", report or rollback_latest_patch(dry_run=True), full=full)


def readme_gate_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v8.8 README Enforcement Gate", report or readme_gate(), full=full)


def controlled_build_cycle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_controlled_build_cycle(dry_run=True)
    lines = _generic_text("Eidolon v8.9 Full Controlled Build Cycle", report, full=False).splitlines()
    steps = report.get("steps") or {}
    if steps:
        lines.extend(["", "## Step statuses"])
        for name, step in steps.items():
            lines.append(f"- {name}: {str(step.get('status', 'unknown')).upper()} - {step.get('message', '')}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def supervised_dev_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_supervised_dev_loop(live=False)
    lines = _generic_text("Eidolon v9.0 Supervised Autonomous Development Loop", report, full=False).splitlines()
    cycle = report.get("cycle") or {}
    lines.extend([
        "",
        "## One-cycle result",
        f"- Cycle status: {str(cycle.get('status', 'unknown')).upper()}",
        f"- Live: {report.get('live')}",
        f"- Doctor status: {report.get('doctor_status')}",
        f"- Guardrails OK for live: {report.get('guardrails_ok_for_live')}",
        f"- Next recommended task: {report.get('next_recommended_task')}",
    ])
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


# CLI print helpers

def print_controlled_task_selection(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_controlled_task_selection(project_id=project_id)
    _json_print(report) if json_output else print(controlled_task_selection_text(report, full=full))


def print_patch_plan(project_id: str = "eidolon", target_version: str = "10.0", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_plan(project_id=project_id, target_version=target_version, save=True)
    _json_print(report) if json_output else print(patch_plan_text(report, full=full))


def print_patch_workspace_status(full: bool = False, json_output: bool = False) -> None:
    report = patch_workspace_status()
    _json_print(report) if json_output else print(workspace_status_text(report, full=full))


def print_stage_controlled_patch(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = stage_controlled_patch(project_id=project_id)
    _json_print(report) if json_output else print(staged_patch_text(report, full=full))


def print_preview_staged_diff(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = preview_staged_diff(project_id=project_id)
    _json_print(report) if json_output else print(diff_preview_text(report, full=full))


def print_apply_staged_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = apply_staged_patch(project_id=project_id, approve=approve, dry_run=dry_run)
    _json_print(report) if json_output else print(apply_staged_patch_text(report, full=full))


def print_verify_latest_patch(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = verify_latest_patch(project_id=project_id)
    _json_print(report) if json_output else print(verify_latest_patch_text(report, full=full))


def print_rollback_latest_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = rollback_latest_patch(project_id=project_id, approve=approve, dry_run=dry_run)
    _json_print(report) if json_output else print(rollback_latest_patch_text(report, full=full))


def print_readme_gate(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = readme_gate(project_id=project_id)
    _json_print(report) if json_output else print(readme_gate_text(report, full=full))


def print_controlled_build_cycle(project_id: str = "eidolon", live: bool = False, approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_controlled_build_cycle(project_id=project_id, live=live, approve=approve, dry_run=dry_run)
    _json_print(report) if json_output else print(controlled_build_cycle_text(report, full=full))


def print_supervised_dev_loop(project_id: str = "eidolon", live: bool = False, approve: bool = False, use_ai: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_supervised_dev_loop(project_id=project_id, live=live, approve=approve, use_ai=use_ai)
    _json_print(report) if json_output else print(supervised_dev_loop_text(report, full=full))
