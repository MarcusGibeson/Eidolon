from __future__ import annotations

import difflib
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from task_queue import list_tasks
from workspace_orchestration import build_project_context, _timeline_event
from workspace_execution import build_project_boundary_check

PATCH_DRAFTING_VERSION = "15.0"
DRAFTS_DIR = DATA_DIR / "patch_drafts"
PROPOSED_FILES_DIR = DRAFTS_DIR / "proposed_files"
BACKUPS_DIR = DRAFTS_DIR / "backups"
DRAFT_REQUEST = DRAFTS_DIR / "draft_request.json"
CURRENT_DRAFT = DRAFTS_DIR / "current_draft.json"
CURRENT_DIFF = DRAFTS_DIR / "current_diff.json"
TEST_IMPACT = DRAFTS_DIR / "test_impact.json"
REVIEW_NOTES = DRAFTS_DIR / "review_notes.json"
APPROVAL_STATE = DRAFTS_DIR / "approval_state.json"
APPLY_REPORT = DRAFTS_DIR / "latest_approved_apply_report.json"
DRY_RUN_APPLY_REPORT = DRAFTS_DIR / "latest_approved_apply_dry_run_report.json"
ROLLBACK_REPORT = DRAFTS_DIR / "latest_approved_rollback_report.json"
DRAFT_QUALITY = DRAFTS_DIR / "draft_quality.json"
FILE_TARGETS = DRAFTS_DIR / "file_targets.json"
INTENT_BLOCKS = DRAFTS_DIR / "intent_blocks.json"
DRAFT_CONFLICTS = DRAFTS_DIR / "draft_conflicts.json"
VERIFICATION_BUNDLE = DRAFTS_DIR / "verification_bundle.json"
REVIEW_CHECKLIST = DRAFTS_DIR / "review_checklist.json"
EXECUTION_REPORT = DRAFTS_DIR / "approved_execution_report.json"
REVIEW_LOOP_REPORT = DRAFTS_DIR / "review_centered_patch_loop.json"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSED_FILES_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _artifact_snapshot() -> dict[str, Any]:
    """Capture the saved review artifacts that bind one approval to one exact draft.

    The snapshot intentionally uses saved files only. Preview builders can be useful,
    but approval must point at the exact request/draft/diff/test/review artifacts the
    human reviewed, not a freshly generated cousin wearing the same trench coat.
    """
    artifacts = {
        "request": DRAFT_REQUEST,
        "draft": CURRENT_DRAFT,
        "diff": CURRENT_DIFF,
        "test_impact": TEST_IMPACT,
        "quality": DRAFT_QUALITY,
        "checklist": REVIEW_CHECKLIST,
        "verification_bundle": VERIFICATION_BUNDLE,
    }
    snapshot: dict[str, Any] = {}
    for name, artifact_path in artifacts.items():
        value = _read_json(artifact_path, {})
        snapshot[name] = {
            "path": str(artifact_path.relative_to(ROOT_DIR)),
            "exists": artifact_path.exists(),
            "sha256": _file_sha256(artifact_path),
            "request_id": value.get("request_id") if isinstance(value, dict) else None,
            "draft_id": value.get("draft_id") if isinstance(value, dict) else None,
            "status": value.get("status") if isinstance(value, dict) else None,
            "ok": value.get("ok") if isinstance(value, dict) else None,
        }
    return snapshot


def build_draft_artifact_binding(project_id: str = "eidolon", save: bool = False) -> dict[str, Any]:
    """Verify that saved draft review artifacts all describe the same request/draft."""
    request = _read_json(DRAFT_REQUEST, {})
    draft = _read_json(CURRENT_DRAFT, {})
    diff = _read_json(CURRENT_DIFF, {})
    impact = _read_json(TEST_IMPACT, {})
    quality = _read_json(DRAFT_QUALITY, {})
    checklist = _read_json(REVIEW_CHECKLIST, {})
    bundle = _read_json(VERIFICATION_BUNDLE, {})

    request_id = request.get("request_id") if isinstance(request, dict) else None
    draft_id = draft.get("draft_id") if isinstance(draft, dict) else None
    rows: list[dict[str, Any]] = []

    def row(name: str, passed: bool, message: str, *, status_if_fail: str = "blocked") -> None:
        rows.append({"name": name, "status": "pass" if passed else status_if_fail, "message": message})

    row("request-exists", bool(request_id), f"request_id={request_id or 'missing'}")
    row("draft-exists", bool(draft_id), f"draft_id={draft_id or 'missing'}")
    row("draft-request-binding", bool(request_id and draft.get("request_id") == request_id), f"draft.request_id={draft.get('request_id') if isinstance(draft, dict) else None}; request_id={request_id}")

    required = [
        ("diff", diff),
        ("test-impact", impact),
        ("quality", quality),
        ("checklist", checklist),
        ("verification-bundle", bundle),
    ]
    for name, artifact in required:
        if not isinstance(artifact, dict) or not artifact:
            row(f"{name}-exists", False, f"Saved {name} artifact is missing.")
            continue
        artifact_draft_id = artifact.get("draft_id")
        artifact_request_id = artifact.get("request_id")
        if name == "verification-bundle":
            artifact_draft_id = artifact_draft_id or ((artifact.get("steps") or {}).get("draft") or {}).get("draft_id")
            artifact_request_id = artifact_request_id or ((artifact.get("steps") or {}).get("request") or {}).get("request_id")
        row(f"{name}-draft-binding", bool(draft_id and artifact_draft_id == draft_id), f"{name}.draft_id={artifact_draft_id}; draft_id={draft_id}")
        if artifact_request_id is not None or name in {"checklist", "verification-bundle"}:
            row(f"{name}-request-binding", bool(request_id and artifact_request_id == request_id), f"{name}.request_id={artifact_request_id}; request_id={request_id}")

    snapshot = _artifact_snapshot()
    for name, meta in snapshot.items():
        row(f"{name}-file-present", bool(meta.get("exists") and meta.get("sha256")), f"{meta.get('path')} sha256={meta.get('sha256') or 'missing'}")

    status = _status_from(rows)
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "request_id": request_id,
        "draft_id": draft_id,
        "status": status,
        "ok": status == "pass",
        "rows": rows,
        "snapshot": snapshot,
        "message": "Saved draft review artifacts must all bind to the same request_id and draft_id before approval/apply.",
    }
    if save:
        _write_json(DRAFTS_DIR / "artifact_binding.json", report)
    else:
        report["preview_only"] = True
    return report


def validate_approval_binding(approval: dict[str, Any] | None = None, project_id: str = "eidolon") -> dict[str, Any]:
    """Validate that the current saved artifacts still match the approved snapshot."""
    approval = approval if isinstance(approval, dict) else _read_json(APPROVAL_STATE, {})
    binding = build_draft_artifact_binding(project_id=project_id, save=False)
    snapshot = approval.get("artifact_snapshot") if isinstance(approval, dict) else None
    rows: list[dict[str, Any]] = []

    def row(name: str, passed: bool, message: str) -> None:
        rows.append({"name": name, "status": "pass" if passed else "blocked", "message": message})

    approved_draft_id = approval.get("draft_id") if isinstance(approval, dict) else None
    row("approval-exists", bool(approval and approval.get("approved") and approval.get("status") == "approved"), f"approval status={approval.get('status') if isinstance(approval, dict) else 'missing'}")
    row("approval-unconsumed", bool(approval and not approval.get("consumed")), f"consumed={approval.get('consumed') if isinstance(approval, dict) else None}")
    row("approval-draft-binding", bool(approved_draft_id and approved_draft_id == binding.get("draft_id")), f"approval.draft_id={approved_draft_id}; current draft_id={binding.get('draft_id')}")
    row("artifact-binding", bool(binding.get("ok")), binding.get("message", "Artifact binding report missing."))

    if not isinstance(snapshot, dict) or not snapshot:
        row("approval-snapshot", False, "Approval does not include an artifact snapshot; approve the current draft again.")
    else:
        current = _artifact_snapshot()
        for name, approved_meta in snapshot.items():
            current_meta = current.get(name, {})
            row(
                f"snapshot-{name}",
                bool(approved_meta.get("sha256") and current_meta.get("sha256") == approved_meta.get("sha256")),
                f"approved={approved_meta.get('sha256')}; current={current_meta.get('sha256')}",
            )
            if approved_meta.get("draft_id") is not None:
                row(
                    f"snapshot-{name}-draft",
                    current_meta.get("draft_id") == approved_meta.get("draft_id"),
                    f"approved={approved_meta.get('draft_id')}; current={current_meta.get('draft_id')}",
                )

    status = _status_from(rows)
    return {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": binding.get("draft_id"),
        "status": status,
        "ok": status == "pass",
        "rows": rows,
        "binding": binding,
        "message": "Approval binding validation requires approval, current artifacts, and approved snapshot hashes to match.",
    }


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return cleaned[:60] or "patch_draft"


def _safe_path(relative_path: str) -> Path:
    if not relative_path or relative_path.startswith(("/", "\\")) or ".." in Path(relative_path).parts:
        raise PermissionError(f"Unsafe relative path: {relative_path}")
    target = (ROOT_DIR / relative_path).resolve()
    target.relative_to(ROOT_DIR.resolve())
    return target


def _status_from(rows: list[dict[str, Any]]) -> str:
    counts = Counter(str(row.get("status", "pass")) for row in rows)
    if counts.get("fail") or counts.get("blocked"):
        return "blocked"
    if counts.get("warn"):
        return "warn"
    return "pass"


def _risk_value(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "blocked": 4}.get(str(value or "medium").lower(), 2)


def _selected_task(project_id: str, task: str | None = None, intent: str | None = None) -> dict[str, Any]:
    if task:
        return {"id": _slug(task), "title": task, "description": intent or task, "priority": "medium", "risk": "medium", "source": "operator"}
    tasks = list_tasks(project=project_id, include_cancelled=False)
    for item in tasks:
        status = str(item.get("status", "planned")).lower()
        risk = str(item.get("risk", item.get("risk_level", "medium"))).lower()
        if status not in {"done", "completed", "cancelled", "blocked", "failed"} and risk != "high":
            return {
                "id": item.get("id", "task"),
                "title": item.get("title", item.get("name", "Queued task")),
                "description": item.get("description", ""),
                "priority": item.get("priority", "medium"),
                "risk": risk,
                "source": "task_queue",
            }
    return {
        "id": "synthetic_patch_draft_request",
        "title": "Draft a safe README/documentation patch lane",
        "description": intent or "No safe queued task was available, so v14.0 created a bounded documentation-first draft request.",
        "priority": "low",
        "risk": "low",
        "source": "synthetic",
    }


def _likely_files(task: dict[str, Any], expected_files: list[str] | None = None) -> list[str]:
    files = [str(item).replace("\\", "/") for item in (expected_files or []) if str(item).strip()]
    text = json.dumps(task, default=str).lower()
    rules = [
        ("dashboard", "conscious_agent/dashboard.py"),
        ("api", "conscious_agent/api_server.py"),
        ("workspace", "conscious_agent/workspace_execution.py"),
        ("registry", "conscious_agent/workspace_orchestration.py"),
        ("draft", "conscious_agent/patch_drafting.py"),
        ("approval", "conscious_agent/patch_drafting.py"),
        ("test", "tools/smoke_check.py"),
        ("smoke", "tools/smoke_check.py"),
        ("readme", "README_NEXT_STEPS.md"),
    ]
    for needle, path in rules:
        if needle in text and path not in files:
            files.append(path)
    if "README_NEXT_STEPS.md" not in files:
        files.append("README_NEXT_STEPS.md")
    return files[:12]


def build_patch_draft_request(
    project_id: str = "eidolon",
    target_version: str = "15.0",
    task: str | None = None,
    intent: str | None = None,
    constraints: list[str] | None = None,
    expected_files: list[str] | None = None,
    risk_limit: str = "medium",
    save: bool = True,
) -> dict[str, Any]:
    selected = _selected_task(project_id, task=task, intent=intent)
    files = _likely_files(selected, expected_files=expected_files)
    request_id = f"draft_request_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(selected.get('id', 'task'))}"
    request = {
        "version": PATCH_DRAFTING_VERSION,
        "created_at": _now(),
        "request_id": request_id,
        "project_id": project_id,
        "target_version": target_version,
        "task": selected,
        "intent": intent or selected.get("description") or selected.get("title"),
        "constraints": constraints or [
            "Update README_NEXT_STEPS.md for every project change.",
            "Do not modify guardrails or command execution policy without explicit approval.",
            "Keep GET/preview API routes read-only.",
            "Run py_compile, doctor, stabilization checkpoint, and smoke check before packaging.",
        ],
        "expected_files": files,
        "risk_limit": risk_limit,
        "status": "pass",
        "ok": True,
        "message": f"Patch draft request {request_id} prepared for {project_id}.",
    }
    if save:
        _write_json(DRAFT_REQUEST, request)
    else:
        request["preview_only"] = True
    return request


def build_draft_patch(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    request = _read_json(DRAFT_REQUEST, {})
    if not isinstance(request, dict) or not request.get("request_id"):
        request = build_patch_draft_request(project_id=project_id, save=save)
    context = build_project_context(project_id=str(request.get("project_id") or project_id))
    proposed_files = []
    for path in request.get("expected_files", []) or ["README_NEXT_STEPS.md"]:
        path = str(path).replace("\\", "/")
        action = "modify" if path == "README_NEXT_STEPS.md" else "metadata_only"
        proposed_files.append({
            "path": path,
            "action": action,
            "status": "drafted" if action != "metadata_only" else "info",
            "reason": "README documentation update required." if path == "README_NEXT_STEPS.md" else "Impact surface only; no source rewrite generated in the draft interface.",
            "writable": action != "metadata_only",
        })
    risk = str((request.get("task") or {}).get("risk") or "medium").lower()
    if any("command_runner.py" in item.get("path", "") or "guardrail" in item.get("path", "") for item in proposed_files):
        risk = "high"
    draft = {
        "version": PATCH_DRAFTING_VERSION,
        "created_at": _now(),
        "draft_id": f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(str(request.get('request_id', 'request')))}",
        "project_id": request.get("project_id", project_id),
        "request_id": request.get("request_id"),
        "target_version": request.get("target_version", "15.0"),
        "task": request.get("task"),
        "intent": request.get("intent"),
        "risk": risk,
        "risk_limit": request.get("risk_limit", "medium"),
        "needs_review": True,
        "readme_update_planned": any(item["path"] == "README_NEXT_STEPS.md" for item in proposed_files),
        "proposed_files": proposed_files,
        "project_context_status": context.get("status"),
        "status": "pass",
        "ok": True,
        "message": f"Patch draft created with {len(proposed_files)} proposed file row(s).",
    }
    if save:
        _write_json(CURRENT_DRAFT, draft)
    else:
        draft["preview_only"] = True
    return draft


def build_patch_draft_status(project_id: str = "eidolon") -> dict[str, Any]:
    request = _read_json(DRAFT_REQUEST, {})
    draft = _read_json(CURRENT_DRAFT, {})
    diff = _read_json(CURRENT_DIFF, {})
    impact = _read_json(TEST_IMPACT, {})
    notes = _read_json(REVIEW_NOTES, [])
    approval = _read_json(APPROVAL_STATE, {})
    apply_report = _read_json(APPLY_REPORT, {})
    blockers = []
    if draft and not diff:
        blockers.append("Draft exists but no diff has been generated.")
    if diff and not impact:
        blockers.append("Diff exists but no test impact report has been generated.")
    if approval.get("approved") and approval.get("consumed"):
        blockers.append("Approval has already been consumed; reopen or approve again before another apply.")
    status = "warn" if blockers else "pass"
    return {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": True,
        "workspace_dir": str(DRAFTS_DIR.relative_to(ROOT_DIR)),
        "request_id": request.get("request_id"),
        "draft_id": draft.get("draft_id"),
        "diff_status": diff.get("status"),
        "test_impact_status": impact.get("status"),
        "review_note_count": len(notes) if isinstance(notes, list) else 0,
        "approval_status": approval.get("status", "missing"),
        "approval_consumed": bool(approval.get("consumed")),
        "latest_apply_status": apply_report.get("status"),
        "proposed_file_count": len(draft.get("proposed_files", [])) if isinstance(draft, dict) else 0,
        "blockers": blockers,
        "message": "Patch draft workspace status assembled.",
    }


def build_patch_review_notes(note: str | None = None, project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    notes = _read_json(REVIEW_NOTES, [])
    if not isinstance(notes, list):
        notes = []
    added = None
    if note:
        added = {"created_at": _now(), "project_id": project_id, "note": note, "status": "open"}
        notes.append(added)
        if save:
            _write_json(REVIEW_NOTES, notes)
    return {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass",
        "ok": True,
        "added": added,
        "notes": notes[-25:],
        "message": f"Patch review notes loaded; {1 if added else 0} note(s) added.",
    }


def _read_text(relative_path: str) -> tuple[str, str | None]:
    try:
        path = _safe_path(relative_path)
        if not path.exists():
            return "", None
        return path.read_text(encoding="utf-8"), None
    except Exception as error:
        return "", str(error)


def _draft_readme_content(original: str, draft: dict[str, Any]) -> str:
    marker = f"<!-- EIDOLON_PATCH_DRAFT_{draft.get('draft_id', 'draft')} -->"
    if marker in original:
        return original
    section = (
        f"\n\n{marker}\n"
        f"## Patch Draft Prepared for {draft.get('target_version', 'v15.0')}\n\n"
        f"Draft ID: `{draft.get('draft_id')}`\n\n"
        f"Task: {(draft.get('task') or {}).get('title', 'Unspecified task')}\n\n"
        "This draft marker is written only by the approved draft apply command. "
        "It proves the approval pipeline can update documentation while preserving rollback metadata.\n"
    )
    return original.rstrip() + section


def build_draft_diff(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    draft = _read_json(CURRENT_DRAFT, {})
    if not isinstance(draft, dict) or not draft.get("draft_id"):
        draft = build_draft_patch(project_id=project_id, save=save)
    rows: list[dict[str, Any]] = []
    for item in draft.get("proposed_files", []) or []:
        relative_path = str(item.get("path", ""))
        original, error = _read_text(relative_path)
        if error:
            rows.append({"path": relative_path, "status": "blocked", "action": item.get("action"), "message": error})
            continue
        action = str(item.get("action") or "metadata_only")
        if action == "metadata_only":
            rows.append({
                "path": relative_path,
                "action": action,
                "status": "info",
                "original_sha256": _sha256(original),
                "proposed_sha256": _sha256(original),
                "message": "No source edit generated for this impact surface.",
            })
            continue
        proposed = _draft_readme_content(original, draft) if relative_path == "README_NEXT_STEPS.md" else original
        diff_text = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        ))
        draft_file = PROPOSED_FILES_DIR / (relative_path.replace("/", "__").replace("\\", "__") + ".draft")
        if save:
            draft_file.parent.mkdir(parents=True, exist_ok=True)
            draft_file.write_text(proposed, encoding="utf-8")
        rows.append({
            "path": relative_path,
            "action": "modify" if original else "add",
            "status": "staged",
            "draft_file": str(draft_file.relative_to(ROOT_DIR)) if save else None,
            "original_sha256": _sha256(original),
            "proposed_sha256": _sha256(proposed),
            "proposed_content": proposed,
            "diff_summary": {
                "added_lines": sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")),
                "removed_lines": sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---")),
            },
            "diff_preview": diff_text[-6000:],
        })
    boundary = build_project_boundary_check(project_id=str(draft.get("project_id") or project_id), changes=rows)
    blocked = [row.get("message", row.get("path")) for row in rows if row.get("status") == "blocked"]
    if boundary.get("ok") is False:
        blocked.append(boundary.get("message", "Project boundary check failed."))
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": draft.get("project_id", project_id),
        "draft_id": draft.get("draft_id"),
        "status": "blocked" if blocked else "pass",
        "ok": not blocked,
        "rows": rows,
        "boundary": boundary,
        "readme_update_planned": any(row.get("path") == "README_NEXT_STEPS.md" and row.get("status") == "staged" for row in rows),
        "blocked_reasons": blocked,
        "message": f"Draft diff generated for {len(rows)} file row(s).",
    }
    if save:
        _write_json(CURRENT_DIFF, report)
    else:
        report["preview_only"] = True
    return report


def build_draft_test_impact(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    diff = _read_json(CURRENT_DIFF, {})
    if not isinstance(diff, dict) or not diff.get("rows"):
        diff = build_draft_diff(project_id=project_id, save=save)
    commands: list[dict[str, Any]] = []
    files = [str(row.get("path", "")) for row in diff.get("rows", [])]
    def add(command: str, reason: str) -> None:
        if not any(item["command"] == command for item in commands):
            commands.append({"command": command, "reason": reason})
    add("python -m py_compile conscious_agent/*.py tools/smoke_check.py", "Every draft that may touch Python files must compile.")
    add("python conscious_agent/main.py --doctor", "Doctor mode summarizes environment, project, and readiness issues.")
    add("python conscious_agent/main.py --stabilization-checkpoint --stabilization-full", "Stabilization checkpoint verifies the whole loop after draft work.")
    add("python tools/smoke_check.py", "Smoke check covers critical CLI/report surfaces.")
    if any("dashboard.py" in path for path in files):
        add("PYTHONPATH=conscious_agent python -c \"import dashboard; print(dashboard.DASHBOARD_VERSION)\"", "Dashboard import catches route/template syntax errors.")
    if any("api_server.py" in path for path in files):
        add("python conscious_agent/main.py --readme-gate --readiness-json", "API route changes require README and safety-gate review.")
    if any("patch_drafting.py" in path for path in files):
        add("python conscious_agent/main.py --patch-draft-status", "Patch drafting changes must preserve the draft workspace report.")
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": diff.get("project_id", project_id),
        "draft_id": diff.get("draft_id"),
        "status": "pass" if diff.get("ok", True) else "blocked",
        "ok": bool(diff.get("ok", True)),
        "files": files,
        "commands": commands,
        "message": f"Draft test impact planned {len(commands)} verification command(s).",
    }
    if save:
        _write_json(TEST_IMPACT, report)
    else:
        report["preview_only"] = True
    return report


def build_approval_gate(project_id: str = "eidolon") -> dict[str, Any]:
    draft = _read_json(CURRENT_DRAFT, {})
    diff = _read_json(CURRENT_DIFF, {})
    impact = _read_json(TEST_IMPACT, {})
    notes = _read_json(REVIEW_NOTES, [])
    rows: list[dict[str, Any]] = []
    draft_id = draft.get("draft_id") if isinstance(draft, dict) else None
    rows.append({"name": "draft-exists", "status": "pass" if draft_id else "fail", "message": draft_id or "No current draft."})
    rows.append({"name": "diff-exists", "status": "pass" if diff.get("rows") else "fail", "message": diff.get("status", "No diff report.")})
    rows.append({"name": "diff-draft-binding", "status": "pass" if draft_id and diff.get("draft_id") == draft_id else "fail", "message": f"diff.draft_id={diff.get('draft_id')}; draft_id={draft_id}"})
    rows.append({"name": "test-impact-exists", "status": "pass" if impact.get("commands") else "fail", "message": f"{len(impact.get('commands', [])) if isinstance(impact, dict) else 0} command(s)."})
    rows.append({"name": "test-impact-draft-binding", "status": "pass" if draft_id and impact.get("draft_id") == draft_id else "fail", "message": f"impact.draft_id={impact.get('draft_id')}; draft_id={draft_id}"})
    rows.append({"name": "boundary-check", "status": "pass" if (diff.get("boundary") or {}).get("ok", False) else "fail", "message": (diff.get("boundary") or {}).get("message", "Boundary check missing.")})
    rows.append({"name": "readme-update", "status": "pass" if diff.get("readme_update_planned") else "fail", "message": "README update is required for project patches."})
    risk = str(draft.get("risk", "medium")).lower()
    limit = str(draft.get("risk_limit", "medium")).lower()
    rows.append({"name": "risk-limit", "status": "pass" if _risk_value(risk) <= _risk_value(limit) else "fail", "message": f"risk={risk}; limit={limit}"})
    if any("reject" in str(note.get("note", "")).lower() for note in notes if isinstance(note, dict)):
        rows.append({"name": "review-notes", "status": "warn", "message": "Review notes contain rejection language; inspect before approval."})
    status = _status_from(rows)
    return {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "request_id": draft.get("request_id") if isinstance(draft, dict) else None,
        "draft_id": draft_id,
        "status": status,
        "ok": status == "pass",
        "rows": rows,
        "message": "Approval gate requires draft, diff, test impact, boundary pass, README update, risk within limit, and matching draft ids.",
    }


def approve_draft(project_id: str = "eidolon", note: str | None = None, save: bool = True) -> dict[str, Any]:
    # Ensure the human approval binds to the full saved artifact set, not only
    # a draft id. Missing artifacts are generated from the saved request/draft
    # first, then their hashes are captured in the approval snapshot.
    if not _read_json(DRAFT_QUALITY, {}).get("draft_id"):
        build_draft_quality(project_id=project_id, save=True)
    if not _read_json(VERIFICATION_BUNDLE, {}).get("draft_id"):
        build_draft_verification_bundle(project_id=project_id, save=True)
    if not _read_json(REVIEW_CHECKLIST, {}).get("draft_id"):
        build_draft_review_checklist(project_id=project_id, save=True)
    gate = build_approval_gate(project_id=project_id)
    binding = build_draft_artifact_binding(project_id=project_id, save=True)
    approved = bool(gate.get("ok") and binding.get("ok"))
    state = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "request_id": gate.get("request_id"),
        "draft_id": gate.get("draft_id"),
        "status": "approved" if approved else "blocked",
        "approved": approved,
        "approved_at": _now() if approved else None,
        "approved_for": "apply_once" if approved else None,
        "risk_accepted": (_read_json(CURRENT_DRAFT, {}) or {}).get("risk", "medium"),
        "note": (note or "Approved for one apply only.") if approved else note,
        "consumed": False,
        "gate": gate,
        "artifact_binding": binding,
        "artifact_snapshot": binding.get("snapshot", {}),
        "ok": approved,
        "message": "Draft approved for one apply and bound to the saved review artifact snapshot." if approved else "Draft approval blocked by approval gate or artifact binding.",
    }
    if save:
        _write_json(APPROVAL_STATE, state)
    else:
        state["preview_only"] = True
    return state


def reject_draft(project_id: str = "eidolon", note: str | None = None, save: bool = True) -> dict[str, Any]:
    draft = _read_json(CURRENT_DRAFT, {})
    state = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": draft.get("draft_id"),
        "status": "rejected",
        "approved": False,
        "rejected_at": _now(),
        "note": note or "Rejected by operator.",
        "consumed": False,
        "ok": True,
        "message": "Draft rejected and cannot be applied until reopened and approved again.",
    }
    if save:
        _write_json(APPROVAL_STATE, state)
        if note:
            build_patch_review_notes(note=note, project_id=project_id, save=True)
    return state


def build_apply_approved_draft(project_id: str = "eidolon", dry_run: bool = False, save: bool = True) -> dict[str, Any]:
    approval = _read_json(APPROVAL_STATE, {})
    diff = _read_json(CURRENT_DIFF, {})
    if not approval.get("approved") or approval.get("consumed") or approval.get("status") != "approved":
        return {
            "version": PATCH_DRAFTING_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "blocked",
            "ok": False,
            "dry_run": dry_run,
            "approval_status": approval.get("status", "missing"),
            "message": "Applying an approved draft requires an unconsumed approved approval_state.json.",
        }
    if not isinstance(diff, dict) or not diff.get("rows"):
        return {"version": PATCH_DRAFTING_VERSION, "checked_at": _now(), "project_id": project_id, "status": "blocked", "ok": False, "message": "No draft diff exists."}
    if approval.get("draft_id") != diff.get("draft_id"):
        return {
            "version": PATCH_DRAFTING_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "blocked",
            "ok": False,
            "dry_run": dry_run,
            "approval_draft_id": approval.get("draft_id"),
            "diff_draft_id": diff.get("draft_id"),
            "message": "Approved draft id does not match the current diff draft id. Regenerate review artifacts and approve again.",
        }
    binding_validation = validate_approval_binding(approval=approval, project_id=project_id)
    if not binding_validation.get("ok"):
        return {
            "version": PATCH_DRAFTING_VERSION,
            "checked_at": _now(),
            "project_id": project_id,
            "status": "blocked",
            "ok": False,
            "dry_run": dry_run,
            "approval_draft_id": approval.get("draft_id"),
            "diff_draft_id": diff.get("draft_id"),
            "binding_validation": binding_validation,
            "message": "Approved draft artifact binding is stale or mismatched. Approve the current saved draft artifacts again before applying.",
        }
    run_id = f"approved_draft_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(str(diff.get('draft_id', 'draft')))}"
    applied: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in diff.get("rows", []):
        if row.get("status") != "staged" or row.get("action") == "metadata_only":
            applied.append({"path": row.get("path"), "action": row.get("action"), "status": "skipped", "message": "No writable proposed content."})
            continue
        relative_path = str(row.get("path", ""))
        try:
            target = _safe_path(relative_path)
        except Exception as error:
            errors.append(str(error))
            continue
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if _sha256(current) != row.get("original_sha256"):
            errors.append(f"{relative_path}: current file hash does not match draft original hash.")
            continue
        backup = BACKUPS_DIR / run_id / relative_path.replace("\\", "/")
        if not dry_run:
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text(current, encoding="utf-8")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(row.get("proposed_content", "")), encoding="utf-8")
        applied.append({
            "path": relative_path,
            "action": row.get("action"),
            "status": "dry_run" if dry_run else "applied",
            "backup_path": str(backup.relative_to(ROOT_DIR)),
            "original_sha256": row.get("original_sha256"),
            "applied_sha256": row.get("proposed_sha256"),
        })
    status = "failed" if errors else "dry_run" if dry_run else "applied"
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "run_id": run_id,
        "draft_id": diff.get("draft_id"),
        "status": status,
        "ok": not errors,
        "dry_run": dry_run,
        "applied": applied,
        "errors": errors,
        "approval_consumed": bool(not dry_run and not errors),
        "rollback_available": bool(not dry_run and any(row.get("status") == "applied" for row in applied)),
        "binding_validation": binding_validation,
        "message": f"Approved draft apply {status} with {len(errors)} error(s).",
    }
    if save:
        if dry_run:
            _write_json(DRY_RUN_APPLY_REPORT, report)
        else:
            _write_json(APPLY_REPORT, report)
        if not dry_run and not errors:
            approval["consumed"] = True
            approval["consumed_at"] = _now()
            approval["apply_run_id"] = run_id
            _write_json(APPROVAL_STATE, approval)
            _timeline_event("approved_patch_draft_apply", {"project_id": project_id, "draft_id": diff.get("draft_id"), "status": status}, save=True)
    return report


def build_rollback_approved_draft(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    apply_report = _read_json(APPLY_REPORT, {})
    if apply_report.get("status") != "applied":
        return {"version": PATCH_DRAFTING_VERSION, "checked_at": _now(), "project_id": project_id, "status": "blocked", "ok": False, "dry_run": dry_run, "message": "No applied approved-draft report is available for rollback."}
    if not dry_run and not approve:
        return {"version": PATCH_DRAFTING_VERSION, "checked_at": _now(), "project_id": project_id, "status": "blocked", "ok": False, "dry_run": dry_run, "message": "Rollback writes require --approve-controlled-self-build."}
    restored: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in apply_report.get("applied", []):
        if row.get("status") != "applied":
            continue
        relative_path = str(row.get("path", ""))
        backup = ROOT_DIR / str(row.get("backup_path", ""))
        if not backup.exists():
            errors.append(f"Missing backup for {relative_path}: {row.get('backup_path')}")
            continue
        try:
            target = _safe_path(relative_path)
        except Exception as error:
            errors.append(str(error))
            continue
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if row.get("applied_sha256") and _sha256(current) != row.get("applied_sha256"):
            errors.append(f"{relative_path}: current file hash does not match applied hash; rollback would overwrite newer edits.")
            continue
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(backup, target)
        restored.append({"path": relative_path, "status": "dry_run" if dry_run else "restored", "backup_path": row.get("backup_path")})
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "failed" if errors else "dry_run" if dry_run else "rolled_back",
        "ok": not errors,
        "dry_run": dry_run,
        "restored": restored,
        "errors": errors,
        "message": f"Approved draft rollback checked {len(restored)} file(s) with {len(errors)} error(s).",
    }
    if save:
        _write_json(ROLLBACK_REPORT, report)
        if not dry_run and not errors:
            _timeline_event("approved_patch_draft_rollback", {"project_id": project_id, "status": report["status"]}, save=True)
    return report


def reopen_draft(project_id: str = "eidolon", note: str | None = None, save: bool = True) -> dict[str, Any]:
    approval = _read_json(APPROVAL_STATE, {})
    draft = _read_json(CURRENT_DRAFT, {})
    approval.update({
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": draft.get("draft_id"),
        "status": "reopened",
        "approved": False,
        "consumed": False,
        "reopened_at": _now(),
        "note": note or approval.get("note") or "Draft reopened for more review.",
        "ok": True,
        "message": "Draft reopened; approval cleared.",
    })
    if save:
        _write_json(APPROVAL_STATE, approval)
        if note:
            build_patch_review_notes(note=note, project_id=project_id, save=True)
    return approval


def build_human_approved_patch_loop(project_id: str = "eidolon", approve_apply: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    request = build_patch_draft_request(project_id=project_id, save=save)
    draft = build_draft_patch(project_id=project_id, save=save)
    diff = build_draft_diff(project_id=project_id, save=save)
    impact = build_draft_test_impact(project_id=project_id, save=save)
    gate = build_approval_gate(project_id=project_id)
    approval = _read_json(APPROVAL_STATE, {})
    apply_report = None
    if approval.get("approved") and approve_apply:
        apply_report = build_apply_approved_draft(project_id=project_id, dry_run=dry_run, save=save)
    status = "blocked" if any(step.get("ok") is False for step in [request, draft, diff, impact, gate]) else "applied" if apply_report and apply_report.get("status") == "applied" else "awaiting_approval"
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "dry_run": dry_run,
        "steps": {
            "request": request,
            "draft": draft,
            "diff": diff,
            "test_impact": impact,
            "approval_gate": gate,
            "approval_state": approval,
            "apply": apply_report,
        },
        "message": "Human-approved patch loop prepared one draft and stopped unless an unconsumed approval allowed one apply.",
    }
    if save:
        _timeline_event("human_approved_patch_loop", {"project_id": project_id, "status": status, "dry_run": dry_run}, save=True)
    return report



def build_draft_file_targets(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """Resolve likely and avoided files for the current draft without editing source files."""
    request = _read_json(DRAFT_REQUEST, {})
    draft = _read_json(CURRENT_DRAFT, {})
    task = request.get("task") if isinstance(request, dict) else {}
    if not isinstance(task, dict) or not task:
        task = draft.get("task", {}) if isinstance(draft, dict) else {}
    likely = _likely_files(task if isinstance(task, dict) else {"title": str(task)}, expected_files=(request.get("expected_files") if isinstance(request, dict) else None))
    for item in (draft.get("proposed_files", []) if isinstance(draft, dict) else []):
        path = str(item.get("path", "")).replace("\\", "/")
        if path and path not in likely:
            likely.append(path)
    avoid = [
        {"path": "conscious_agent/command_runner.py", "reason": "Command execution policy should change only when the task explicitly targets safety/whitelist behavior."},
        {"path": "conscious_agent/stable_loop_guardrails.py", "reason": "Guardrails are high-risk and should not be changed as incidental draft work."},
        {"path": "data/workspaces/projects.json", "reason": "Workspace registry writes belong to explicit registry commands, not draft review."},
        {"path": "data/patch_workspace/latest_apply_report.json", "reason": "Real apply pointers must not be rewritten by preview/draft reports."},
    ]
    rows = []
    text = json.dumps({"request": request, "draft": draft}, default=str).lower()
    for path in likely[:20]:
        risk = "high" if any(name in path for name in ["command_runner.py", "guardrail", "settings_manager.py"]) else "medium" if path.startswith("conscious_agent/") else "low"
        reason = "README update required for every project patch." if path == "README_NEXT_STEPS.md" else "Resolved from draft request, task text, proposed file metadata, and project review surfaces."
        rows.append({"path": path, "status": "target", "risk": risk, "reason": reason})
    if "api" in text and "conscious_agent/api_server.py" not in likely:
        rows.append({"path": "conscious_agent/api_server.py", "status": "candidate", "risk": "medium", "reason": "Task references API behavior."})
    if "dashboard" in text and "conscious_agent/dashboard.py" not in likely:
        rows.append({"path": "conscious_agent/dashboard.py", "status": "candidate", "risk": "medium", "reason": "Task references dashboard behavior."})
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": draft.get("draft_id") if isinstance(draft, dict) else None,
        "status": "pass" if rows else "warn",
        "ok": True,
        "rows": rows,
        "likely_files": [row["path"] for row in rows],
        "avoid": avoid,
        "message": f"Resolved {len(rows)} likely draft file target(s).",
    }
    if save:
        _write_json(FILE_TARGETS, report)
    else:
        report["preview_only"] = True
    return report


def build_draft_intent_blocks(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    request = _read_json(DRAFT_REQUEST, {})
    draft = _read_json(CURRENT_DRAFT, {})
    targets = build_draft_file_targets(project_id=project_id, save=False)
    task_title = ((request.get("task") or {}).get("title") if isinstance(request, dict) else None) or ((draft.get("task") or {}).get("title") if isinstance(draft, dict) else None) or "Current patch draft"
    blocks: list[dict[str, Any]] = []
    def add(title: str, purpose: str, files: list[str], risk: str = "medium", tests: list[str] | None = None, readme: bool = False, approval: str = "Review before approval.") -> None:
        blocks.append({
            "id": f"intent_{len(blocks)+1}",
            "title": title,
            "purpose": purpose,
            "files": files,
            "risk": risk,
            "tests_required": tests or ["python -m py_compile conscious_agent/*.py tools/smoke_check.py"],
            "readme_impact": readme,
            "approval_notes": approval,
            "status": "planned",
        })
    add("Clarify requested change", f"Represent the task `{task_title}` as reviewable patch intent.", ["data/patch_drafts/draft_request.json"], "low", ["python conscious_agent/main.py --patch-draft-status"], False)
    likely = targets.get("likely_files", []) or ["README_NEXT_STEPS.md"]
    for path in likely[:8]:
        if path == "README_NEXT_STEPS.md":
            add("Update project documentation", "Document the version and verification commands for the patch.", [path], "low", ["python conscious_agent/main.py --readme-gate --readiness-json"], True, "README update is mandatory before approval.")
        elif path.endswith("api_server.py"):
            add("Review API surface", "Keep GET endpoints read-only and route mutations through POST-only handlers.", [path], "medium", ["python conscious_agent/main.py --draft-verification-bundle"], False, "Reject if any preview GET writes state.")
        elif path.endswith("dashboard.py"):
            add("Review dashboard surface", "Expose draft review information without mutating workspace state.", [path], "medium", ["PYTHONPATH=conscious_agent python -c \"import dashboard; print(dashboard.DASHBOARD_VERSION)\""], False)
        elif path.endswith("patch_drafting.py"):
            add("Update patch drafting logic", "Keep draft generation, review, approval, apply, and reporting bounded to one patch lane.", [path], "medium", ["python conscious_agent/main.py --draft-quality", "python conscious_agent/main.py --draft-conflicts"], False)
        else:
            add("Review impacted file", "Treat this file as an impact surface for the draft.", [path], "medium")
    status = "pass" if blocks else "warn"
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": draft.get("draft_id") if isinstance(draft, dict) else None,
        "status": status,
        "ok": True,
        "blocks": blocks,
        "message": f"Prepared {len(blocks)} draft intent block(s).",
    }
    if save:
        _write_json(INTENT_BLOCKS, report)
    else:
        report["preview_only"] = True
    return report


def build_draft_conflicts(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    approval = _read_json(APPROVAL_STATE, {})
    draft = _read_json(CURRENT_DRAFT, {})
    diff = _read_json(CURRENT_DIFF, {})
    apply_report = _read_json(APPLY_REPORT, {})
    dry_apply = _read_json(DRY_RUN_APPLY_REPORT, {})
    workspace_plan = _read_json(DATA_DIR / "patch_workspace" / "current_plan.json", {})
    workspace_diff = _read_json(DATA_DIR / "patch_workspace" / "current_diff.json", {})
    rows: list[dict[str, Any]] = []
    if approval.get("approved") and not approval.get("consumed"):
        rows.append({"name": "existing-approval", "status": "warn", "message": "An unconsumed approval exists; applying another draft requires explicit review."})
    if approval.get("consumed"):
        rows.append({"name": "consumed-approval", "status": "blocked", "message": "The current approval was already consumed; reopen or approve again."})
    if apply_report.get("status") and apply_report.get("status") != "applied":
        rows.append({"name": "stale-apply-report", "status": "warn", "message": f"Approved apply report status is {apply_report.get('status')}; rollback may be unavailable."})
    if dry_apply.get("status") == "dry_run":
        rows.append({"name": "dry-run-apply-report", "status": "pass", "message": "Dry-run apply report is separated from the real apply pointer."})
    if workspace_plan:
        rows.append({"name": "workspace-plan", "status": "warn", "message": "A controlled/workspace patch plan exists; verify it does not overlap with the draft."})
    if workspace_diff:
        rows.append({"name": "workspace-diff", "status": "warn", "message": "A controlled/workspace diff exists; verify staged work is not stale."})
    if draft.get("project_id") and draft.get("project_id") != project_id:
        rows.append({"name": "project-mismatch", "status": "blocked", "message": f"Draft project {draft.get('project_id')} does not match requested project {project_id}."})
    if diff.get("draft_id") and draft.get("draft_id") and diff.get("draft_id") != draft.get("draft_id"):
        rows.append({"name": "draft-diff-mismatch", "status": "warn", "message": "Current diff belongs to a different draft id; regenerate --draft-diff before approval."})
    if not rows:
        rows.append({"name": "conflict-scan", "status": "pass", "message": "No blocking draft/workspace conflicts detected."})
    status = _status_from(rows)
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": draft.get("draft_id") if isinstance(draft, dict) else None,
        "status": status,
        "ok": status != "blocked",
        "rows": rows,
        "message": "Draft conflict scan completed.",
    }
    if save:
        _write_json(DRAFT_CONFLICTS, report)
    else:
        report["preview_only"] = True
    return report


def build_draft_quality(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    request = _read_json(DRAFT_REQUEST, {})
    draft = _read_json(CURRENT_DRAFT, {})
    diff = _read_json(CURRENT_DIFF, {})
    impact = _read_json(TEST_IMPACT, {})
    targets = build_draft_file_targets(project_id=project_id, save=False)
    conflicts = build_draft_conflicts(project_id=project_id, save=False)
    rows: list[dict[str, Any]] = []
    def criterion(name: str, passed: bool, weight: int, message: str) -> None:
        rows.append({"name": name, "status": "pass" if passed else "warn", "weight": weight, "earned": weight if passed else 0, "message": message})
    criterion("request-complete", bool(request.get("request_id") and request.get("intent")), 15, "Draft request should include id and intent.")
    criterion("context-loaded", bool(draft.get("project_context_status")), 10, "Project context should be available.")
    criterion("file-targets", bool(targets.get("rows")), 15, "Likely file targets should be resolved.")
    criterion("intent-blocks", bool(_read_json(INTENT_BLOCKS, {}).get("blocks")) or bool(build_draft_intent_blocks(project_id=project_id, save=False).get("blocks")), 10, "Draft intent should be broken into reviewable blocks.")
    criterion("diff-ready", bool(diff.get("rows")), 15, "Draft diff should exist before approval.")
    criterion("test-impact", bool(impact.get("commands")), 10, "Test impact plan should exist.")
    criterion("readme-coverage", bool(diff.get("readme_update_planned") or any(row.get("path") == "README_NEXT_STEPS.md" for row in targets.get("rows", []))), 10, "README update must be planned.")
    criterion("boundary-safe", bool((diff.get("boundary") or {}).get("ok", True)), 10, "Boundary check should pass.")
    criterion("conflicts-clear", conflicts.get("status") != "blocked", 15, "Blocking conflicts must be absent.")
    total = sum(row["weight"] for row in rows) or 1
    earned = sum(row["earned"] for row in rows)
    score = int(round(100 * earned / total))
    status = "pass" if score >= 80 and conflicts.get("status") != "blocked" else "warn" if score >= 60 else "blocked"
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": draft.get("draft_id") if isinstance(draft, dict) else None,
        "status": status,
        "ok": status != "blocked",
        "score": score,
        "max_score": 100,
        "rows": rows,
        "strong": [row["name"] for row in rows if row["status"] == "pass"],
        "weak": [row["name"] for row in rows if row["status"] != "pass"],
        "message": f"Draft quality score is {score}%.",
    }
    if save:
        _write_json(DRAFT_QUALITY, report)
    else:
        report["preview_only"] = True
    return report


def build_draft_verification_bundle(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    status = build_patch_draft_status(project_id=project_id)
    request = _read_json(DRAFT_REQUEST, {})
    draft = _read_json(CURRENT_DRAFT, {})
    missing_saved = []
    if not isinstance(request, dict) or not request.get("request_id"):
        missing_saved.append("request")
        request = {"status": "blocked", "ok": False, "message": "No saved draft request exists."}
    if not isinstance(draft, dict) or not draft.get("draft_id"):
        missing_saved.append("draft")
        draft = {"status": "blocked", "ok": False, "message": "No saved current draft exists."}
    targets = build_draft_file_targets(project_id=project_id, save=False)
    intents = build_draft_intent_blocks(project_id=project_id, save=False)
    conflicts = build_draft_conflicts(project_id=project_id, save=False)
    diff = _read_json(CURRENT_DIFF, {})
    if not isinstance(diff, dict) or not diff.get("rows"):
        diff = build_draft_diff(project_id=project_id, save=False)
    impact = _read_json(TEST_IMPACT, {})
    if not isinstance(impact, dict) or not impact.get("commands"):
        impact = build_draft_test_impact(project_id=project_id, save=False)
    quality = _read_json(DRAFT_QUALITY, {})
    if not isinstance(quality, dict) or not quality.get("rows"):
        quality = build_draft_quality(project_id=project_id, save=False)
    gate = build_approval_gate(project_id=project_id)
    draft_id = draft.get("draft_id") if isinstance(draft, dict) else None
    request_id = request.get("request_id") if isinstance(request, dict) else None
    steps = {"status": status, "request": request, "draft": draft, "file_targets": targets, "intent_blocks": intents, "conflicts": conflicts, "diff": diff, "test_impact": impact, "quality": quality, "approval_gate": gate}
    blocked = [name for name, report in steps.items() if isinstance(report, dict) and report.get("ok") is False]
    blocked.extend([f"missing-{name}" for name in missing_saved])
    warns = [name for name, report in steps.items() if isinstance(report, dict) and report.get("status") == "warn"]
    mismatch = []
    if isinstance(draft, dict) and isinstance(request, dict) and request_id and draft.get("request_id") != request_id:
        mismatch.append("draft-request")
    for name, artifact in {"diff": diff, "test_impact": impact, "quality": quality}.items():
        if isinstance(artifact, dict) and artifact.get("draft_id") and draft_id and artifact.get("draft_id") != draft_id:
            mismatch.append(name)
    blocked.extend([f"mismatch-{name}" for name in mismatch])
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "request_id": request_id,
        "draft_id": draft_id,
        "status": "blocked" if blocked else "warn" if warns else "pass",
        "ok": not blocked,
        "steps": steps,
        "blocked_steps": blocked,
        "warning_steps": warns,
        "artifact_mismatches": mismatch,
        "recommended_next_action": "Fix blocked review artifacts before approval." if blocked else "Review checklist and approve once if the draft matches the task." if warns else "Draft is ready for human review.",
        "message": "Draft verification bundle assembled from saved request/draft artifacts, not freshly generated request ids.",
    }
    if save:
        _write_json(VERIFICATION_BUNDLE, report)
    else:
        report["preview_only"] = True
    return report


def build_draft_review_checklist(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    bundle = build_draft_verification_bundle(project_id=project_id, save=False)
    items = [
        {"item": "Do the intended files match the task?", "status": "open", "source": "file_targets"},
        {"item": "Are GET routes read-only and mutation routes POST-only?", "status": "open", "source": "api_safety"},
        {"item": "Is README_NEXT_STEPS.md included or explicitly unnecessary?", "status": "pass" if bundle.get("steps", {}).get("diff", {}).get("readme_update_planned") else "open", "source": "readme"},
        {"item": "Are rollback/apply reports separated for dry-run vs real apply?", "status": "open", "source": "rollback"},
        {"item": "Are test commands specific to touched files?", "status": "pass" if bundle.get("steps", {}).get("test_impact", {}).get("commands") else "open", "source": "tests"},
        {"item": "Is approval single-use and unconsumed?", "status": "open", "source": "approval"},
        {"item": "Is risk within the requested limit?", "status": "pass" if bundle.get("steps", {}).get("approval_gate", {}).get("ok") else "open", "source": "risk"},
        {"item": "Are blocking conflicts clear?", "status": "pass" if bundle.get("steps", {}).get("conflicts", {}).get("ok") else "blocked", "source": "conflicts"},
    ]
    blocked = [item for item in items if item.get("status") == "blocked"]
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "request_id": bundle.get("request_id") or ((bundle.get("steps") or {}).get("request") or {}).get("request_id"),
        "draft_id": bundle.get("draft_id") or ((bundle.get("steps") or {}).get("draft") or {}).get("draft_id"),
        "status": "blocked" if blocked else "pass",
        "ok": not blocked,
        "items": items,
        "message": f"Human review checklist prepared with {len(items)} item(s).",
    }
    if save:
        _write_json(REVIEW_CHECKLIST, report)
    else:
        report["preview_only"] = True
    return report


def build_approved_draft_execution_report(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    apply_report = _read_json(APPLY_REPORT, {})
    dry_apply = _read_json(DRY_RUN_APPLY_REPORT, {})
    rollback = _read_json(ROLLBACK_REPORT, {})
    approval = _read_json(APPROVAL_STATE, {})
    selected = apply_report if apply_report.get("status") == "applied" else dry_apply
    dry_run = bool(selected.get("dry_run"))
    rows = selected.get("applied", []) if isinstance(selected, dict) else []
    real_applied = [row for row in rows if row.get("status") == "applied"]
    status = "pass" if real_applied else "warn" if dry_run or selected else "warn"
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "dry_run": dry_run,
        "approval_used": bool(approval.get("consumed")),
        "apply_status": selected.get("status") if isinstance(selected, dict) else None,
        "files_changed": [row.get("path") for row in real_applied],
        "files_previewed": [row.get("path") for row in rows if row.get("status") == "dry_run"],
        "rollback_available": bool(not dry_run and real_applied and selected.get("rollback_available")),
        "rollback_status": rollback.get("status"),
        "message": "Approved draft execution report assembled; dry-run reports never imply rollback availability.",
    }
    if save:
        _write_json(EXECUTION_REPORT, report)
    else:
        report["preview_only"] = True
    return report


def build_review_centered_patch_loop(project_id: str = "eidolon", approve_apply: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    request = build_patch_draft_request(project_id=project_id, target_version="15.0", save=save)
    draft = build_draft_patch(project_id=project_id, save=save)
    targets = build_draft_file_targets(project_id=project_id, save=save)
    intents = build_draft_intent_blocks(project_id=project_id, save=save)
    diff = build_draft_diff(project_id=project_id, save=save)
    impact = build_draft_test_impact(project_id=project_id, save=save)
    conflicts = build_draft_conflicts(project_id=project_id, save=save)
    quality = build_draft_quality(project_id=project_id, save=save)
    bundle = build_draft_verification_bundle(project_id=project_id, save=save)
    checklist = build_draft_review_checklist(project_id=project_id, save=save)
    approval = _read_json(APPROVAL_STATE, {})
    apply_report = None
    execution = None
    if approval.get("approved") and not approval.get("consumed") and approve_apply:
        apply_report = build_apply_approved_draft(project_id=project_id, dry_run=dry_run, save=save)
        execution = build_approved_draft_execution_report(project_id=project_id, save=save)
    blocked = [name for name, step in {"request": request, "draft": draft, "targets": targets, "intents": intents, "conflicts": conflicts, "diff": diff, "impact": impact, "quality": quality, "bundle": bundle, "checklist": checklist}.items() if isinstance(step, dict) and step.get("ok") is False]
    status = "blocked" if blocked else "applied" if apply_report and apply_report.get("status") == "applied" else "awaiting_review"
    report = {
        "version": PATCH_DRAFTING_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "dry_run": dry_run,
        "steps": {
            "request": request,
            "draft": draft,
            "file_targets": targets,
            "intent_blocks": intents,
            "conflicts": conflicts,
            "diff": diff,
            "test_impact": impact,
            "quality": quality,
            "verification_bundle": bundle,
            "review_checklist": checklist,
            "approval_state": approval,
            "apply": apply_report,
            "execution_report": execution,
        },
        "blocked_steps": blocked,
        "message": "Review-centered patch loop prepared review artifacts and stopped unless an unconsumed approval allowed one apply.",
    }
    if save:
        _write_json(REVIEW_LOOP_REPORT, report)
        _timeline_event("review_centered_patch_loop", {"project_id": project_id, "status": status, "dry_run": dry_run}, save=True)
    return report

def _generic_text(title: str, report: dict[str, Any], full: bool = False) -> str:
    lines = [
        f"# {title}",
        "",
        f"Version: {report.get('version')}",
        f"Checked at: {report.get('checked_at', report.get('created_at', ''))}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Message: {report.get('message', '')}",
    ]
    for key in ["blockers", "blocked_reasons", "errors"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values])
    rows = report.get("rows") or report.get("proposed_files") or report.get("commands") or report.get("notes") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:30]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("path") or row.get("command") or row.get("note") or row.get("status") or "row"
                status = row.get("status") or row.get("action") or "info"
                message = row.get("message") or row.get("reason") or row.get("suggested_fix") or ""
                lines.append(f"- {str(status).upper()} {name}: {message}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def patch_draft_request_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.1 Patch Draft Request", report or build_patch_draft_request(save=False), full)


def draft_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.2 AI Patch Drafting Interface", report or build_draft_patch(save=False), full)


def patch_draft_status_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.3 Patch Draft Workspace", report or build_patch_draft_status(), full)


def patch_review_notes_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.4 Human Patch Review Notes", report or build_patch_review_notes(save=False), full)


def draft_diff_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.5 Draft Diff Generator", report or build_draft_diff(save=False), full)


def draft_test_impact_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.6 Draft Test Impact Planner", report or build_draft_test_impact(save=False), full)


def approval_gate_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.7 Approval Gate", report or build_approval_gate(), full)


def apply_approved_draft_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.8 Apply Approved Draft", report or build_apply_approved_draft(dry_run=True, save=False), full)


def draft_rollback_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v12.9 Draft Rollback and Reopen", report or build_rollback_approved_draft(dry_run=True, save=False), full)


def human_approved_patch_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.0 Human-Approved Autonomous Patch Loop", report or build_human_approved_patch_loop(save=False), full)



def draft_quality_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_draft_quality(save=False)
    text = _generic_text("Eidolon v13.1 Draft Quality Scoring", report, full)
    if "score" in report:
        text += f"\n\nDraft Quality: {report.get('score')}%"
    return text


def draft_file_targets_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v13.2 Draft File Target Resolver", report or build_draft_file_targets(save=False), full)


def draft_intent_blocks_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v13.3 Draft Change Intent Blocks", report or build_draft_intent_blocks(save=False), full)


def draft_conflicts_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v13.4 Draft Conflict Detector", report or build_draft_conflicts(save=False), full)


def draft_verification_bundle_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v13.7 Draft Verification Bundle", report or build_draft_verification_bundle(save=False), full)


def draft_review_checklist_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_draft_review_checklist(save=False)
    lines = [_generic_text("Eidolon v13.8 Human Review Checklist", report, full), "", "## Checklist"]
    for item in report.get("items", []):
        mark = "[x]" if item.get("status") == "pass" else "[!]" if item.get("status") == "blocked" else "[ ]"
        lines.append(f"- {mark} {item.get('item')}")
    return "\n".join(lines).strip()


def approved_draft_execution_report_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v13.9 Approved Draft Execution Report", report or build_approved_draft_execution_report(save=False), full)


def review_centered_patch_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.0 Review-Centered Patch Loop", report or build_review_centered_patch_loop(save=False), full)

def print_patch_draft_request(project_id: str = "eidolon", target_version: str = "15.0", task: str | None = None, intent: str | None = None, risk_limit: str = "medium", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_draft_request(project_id=project_id, target_version=target_version, task=task, intent=intent, risk_limit=risk_limit, save=True)
    _json_print(report) if json_output else print(patch_draft_request_text(report, full=full))


def print_draft_patch(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_patch(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_patch_text(report, full=full))


def print_patch_draft_status(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_patch_draft_status(project_id=project_id)
    _json_print(report) if json_output else print(patch_draft_status_text(report, full=full))


def print_patch_review_notes(project_id: str = "eidolon", note: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_patch_review_notes(project_id=project_id, note=note, save=True)
    _json_print(report) if json_output else print(patch_review_notes_text(report, full=full))


def print_draft_diff(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_diff(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_diff_text(report, full=full))


def print_draft_test_impact(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_test_impact(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_test_impact_text(report, full=full))


def print_approve_draft(project_id: str = "eidolon", note: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = approve_draft(project_id=project_id, note=note, save=True)
    _json_print(report) if json_output else print(approval_gate_text(report, full=full))


def print_reject_draft(project_id: str = "eidolon", note: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = reject_draft(project_id=project_id, note=note, save=True)
    _json_print(report) if json_output else print(approval_gate_text(report, full=full))


def print_apply_approved_draft(project_id: str = "eidolon", dry_run: bool = False, full: bool = False, json_output: bool = False) -> None:
    report = build_apply_approved_draft(project_id=project_id, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(apply_approved_draft_text(report, full=full))


def print_rollback_approved_draft(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_rollback_approved_draft(project_id=project_id, approve=approve, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(draft_rollback_text(report, full=full))


def print_reopen_draft(project_id: str = "eidolon", note: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = reopen_draft(project_id=project_id, note=note, save=True)
    _json_print(report) if json_output else print(approval_gate_text(report, full=full))


def print_human_approved_patch_loop(project_id: str = "eidolon", approve_apply: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_human_approved_patch_loop(project_id=project_id, approve_apply=approve_apply, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(human_approved_patch_loop_text(report, full=full))


def print_draft_quality(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_quality(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_quality_text(report, full=full))


def print_draft_file_targets(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_file_targets(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_file_targets_text(report, full=full))


def print_draft_intent_blocks(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_intent_blocks(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_intent_blocks_text(report, full=full))


def print_draft_conflicts(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_conflicts(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_conflicts_text(report, full=full))


def print_draft_verification_bundle(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_verification_bundle(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_verification_bundle_text(report, full=full))


def print_draft_review_checklist(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_draft_review_checklist(project_id=project_id, save=True)
    _json_print(report) if json_output else print(draft_review_checklist_text(report, full=full))


def print_approved_draft_execution_report(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_approved_draft_execution_report(project_id=project_id, save=True)
    _json_print(report) if json_output else print(approved_draft_execution_report_text(report, full=full))


def print_review_centered_patch_loop(project_id: str = "eidolon", approve_apply: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_review_centered_patch_loop(project_id=project_id, approve_apply=approve_apply, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(review_centered_patch_loop_text(report, full=full))
