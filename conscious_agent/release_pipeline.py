from __future__ import annotations

from release_metadata import RUNTIME_VERSION

import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic
from patch_drafting import (
    APPROVAL_STATE,
    CURRENT_DIFF,
    DRAFT_REQUEST,
    CURRENT_DRAFT,
    build_draft_diff,
    build_draft_test_impact,
    build_draft_verification_bundle,
    build_patch_draft_request,
    build_draft_patch,
    validate_approval_binding,
)
from workspace_execution import build_project_boundary_check
from workspace_orchestration import _timeline_event

RELEASE_PIPELINE_VERSION = RUNTIME_VERSION
CODE_PATCH_DIR = DATA_DIR / "code_patches"
BACKUPS_DIR = CODE_PATCH_DIR / "backups"
CODE_EDIT_PROPOSAL = CODE_PATCH_DIR / "code_edit_proposal.json"
SAFE_REWRITE_PREVIEW = CODE_PATCH_DIR / "safe_rewrite_preview.json"
GENERATED_CODE_PATCH = CODE_PATCH_DIR / "generated_code_patch.json"
TEST_SUGGESTIONS = CODE_PATCH_DIR / "test_suggestions.json"
INLINE_REVIEW_NOTES = CODE_PATCH_DIR / "inline_review_notes.json"
APPROVED_CODE_APPLY = CODE_PATCH_DIR / "latest_approved_code_apply_report.json"
APPROVED_CODE_DRY_RUN = CODE_PATCH_DIR / "latest_approved_code_apply_dry_run_report.json"
RELEASE_PACKAGE = CODE_PATCH_DIR / "release_package.json"
RELEASE_READINESS = CODE_PATCH_DIR / "release_readiness.json"
RELEASE_LOOP_REPORT = CODE_PATCH_DIR / "human_approved_release_loop.json"
README_FILE = ROOT_DIR / "README_NEXT_STEPS.md"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    CODE_PATCH_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    expected_type = type(default) if isinstance(default, (dict, list)) else None
    return load_json_file(path, default, expected_type=expected_type)


def _write_json(path: Path, value: Any) -> None:
    _ensure_dirs()
    expected_type = type(value) if isinstance(value, (dict, list)) else None
    write_json_atomic(path, value, expected_type=expected_type, default=str)


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str))


def _current_release_version() -> str:
    settings = _read_json(DATA_DIR / "settings.json", {})
    return str(settings.get("version") or settings.get("settings_version") or settings.get("last_updated_for") or RELEASE_PIPELINE_VERSION).lstrip("v")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_")
    return cleaned[:70] or "release_patch"


def _safe_path(relative_path: str) -> Path:
    if not relative_path or relative_path.startswith(("/", "\\")) or ".." in Path(relative_path).parts:
        raise PermissionError(f"Unsafe relative path: {relative_path}")
    target = (ROOT_DIR / relative_path).resolve()
    target.relative_to(ROOT_DIR.resolve())
    return target


def _read_text(relative_path: str) -> tuple[str, str | None]:
    try:
        path = _safe_path(relative_path)
        if not path.exists():
            return "", None
        return path.read_text(encoding="utf-8"), None
    except Exception as error:
        return "", str(error)


def _status_from(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("status", "pass")).lower() for row in rows}
    if statuses & {"blocked", "fail", "failed"}:
        return "blocked"
    if "warn" in statuses:
        return "warn"
    return "pass"


def _current_diff(project_id: str = "eidolon", *, save: bool = False) -> dict[str, Any]:
    diff = _read_json(CURRENT_DIFF, {})
    if not isinstance(diff, dict) or not diff.get("rows"):
        diff = build_draft_diff(project_id=project_id, save=save)
    return diff if isinstance(diff, dict) else {}


def _current_draft(project_id: str = "eidolon", *, save: bool = False) -> dict[str, Any]:
    draft = _read_json(CURRENT_DRAFT, {})
    if not isinstance(draft, dict) or not draft.get("draft_id"):
        request = _read_json(DRAFT_REQUEST, {})
        if not isinstance(request, dict) or not request.get("request_id"):
            build_patch_draft_request(project_id=project_id, target_version=_current_release_version(), save=save)
        draft = build_draft_patch(project_id=project_id, save=save)
    return draft if isinstance(draft, dict) else {}


def _proposal_from_diff_row(row: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    target = str(row.get("path", ""))
    change_type = "add" if row.get("action") == "add" else "modify"
    intent = "Update README release notes." if target == "README_NEXT_STEPS.md" else f"Apply approved draft change to {target}."
    expected_symbols: list[str] = []
    if target.endswith(".py"):
        stem = Path(target).stem
        expected_symbols = [stem]
    return {
        "target_file": target,
        "change_type": change_type,
        "intent": intent,
        "risk": draft.get("risk", "medium"),
        "expected_symbols": expected_symbols,
        "readme_required": target != "README_NEXT_STEPS.md",
        "tests_required": [],
        "source": "draft_diff",
        "original_sha256": row.get("original_sha256"),
        "proposed_sha256": row.get("proposed_sha256"),
        "has_proposed_content": row.get("proposed_content") is not None,
    }


def build_code_edit_proposal(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v14.1: create a structured proposal for real code/file edits."""
    draft = _current_draft(project_id=project_id, save=save)
    diff = _current_diff(project_id=project_id, save=save)
    proposals = []
    skipped = []
    for row in diff.get("rows", []) or []:
        if row.get("status") == "staged" and row.get("action") in {"modify", "add"}:
            proposals.append(_proposal_from_diff_row(row, draft))
        else:
            skipped.append({"path": row.get("path"), "status": row.get("status"), "reason": "Not a writable staged diff row."})
    if not proposals:
        proposals.append({
            "target_file": "README_NEXT_STEPS.md",
            "change_type": "modify",
            "intent": "Document release pipeline changes.",
            "risk": "low",
            "expected_symbols": [],
            "readme_required": True,
            "tests_required": ["python tools/smoke_check.py"],
            "source": "fallback",
            "has_proposed_content": False,
        })
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "draft_id": draft.get("draft_id"),
        "status": "pass" if proposals else "warn",
        "ok": True,
        "proposals": proposals,
        "skipped": skipped,
        "message": f"Prepared {len(proposals)} code edit proposal(s).",
    }
    if save:
        _write_json(CODE_EDIT_PROPOSAL, report)
    else:
        report["preview_only"] = True
    return report


def build_safe_rewrite_preview(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v14.2: verify hash/expected text and show rewrite diffs without writing source files."""
    proposal = _read_json(CODE_EDIT_PROPOSAL, {})
    if not isinstance(proposal, dict) or not proposal.get("proposals"):
        proposal = build_code_edit_proposal(project_id=project_id, save=save)
    diff = _current_diff(project_id=project_id, save=False)
    diff_rows = {str(row.get("path")): row for row in diff.get("rows", []) if isinstance(row, dict)}
    rows: list[dict[str, Any]] = []
    blocked: list[str] = []
    for item in proposal.get("proposals", []) or []:
        target = str(item.get("target_file", ""))
        original, error = _read_text(target)
        if error:
            rows.append({"path": target, "status": "blocked", "message": error})
            blocked.append(f"{target}: {error}")
            continue
        diff_row = diff_rows.get(target, {})
        expected_sha = item.get("original_sha256") or diff_row.get("original_sha256") or _sha256(original)
        proposed_content = diff_row.get("proposed_content")
        if proposed_content is None:
            proposed_content = original
        current_sha = _sha256(original)
        if expected_sha and current_sha != expected_sha:
            rows.append({
                "path": target,
                "status": "blocked",
                "message": "Current file hash does not match the proposal's expected original hash.",
                "current_sha256": current_sha,
                "expected_sha256": expected_sha,
            })
            blocked.append(f"{target}: hash mismatch")
            continue
        diff_text = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            str(proposed_content).splitlines(keepends=True),
            fromfile=f"a/{target}",
            tofile=f"b/{target}",
        ))
        rows.append({
            "path": target,
            "status": "ready",
            "change_type": item.get("change_type", "modify"),
            "expected_sha256": expected_sha,
            "current_sha256": current_sha,
            "proposed_sha256": _sha256(str(proposed_content)),
            "backup_required": True,
            "blind_overwrite": False,
            "diff_summary": {
                "added_lines": sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")),
                "removed_lines": sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---")),
            },
            "diff_preview": diff_text[-6000:],
            "proposed_content": str(proposed_content),
        })
    boundary = build_project_boundary_check(project_id=project_id, changes=rows)
    if boundary.get("ok") is False:
        blocked.append(boundary.get("message", "Boundary check failed."))
    status = "blocked" if blocked else "pass"
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": not blocked,
        "rows": rows,
        "boundary": boundary,
        "blocked_reasons": blocked,
        "message": f"Safe rewrite preview prepared for {len(rows)} file(s); no source files changed.",
    }
    if save:
        _write_json(SAFE_REWRITE_PREVIEW, report)
    else:
        report["preview_only"] = True
    return report


def build_generated_code_patch(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v14.3: assemble generated code patch artifacts from proposal + rewrite preview."""
    proposal = _read_json(CODE_EDIT_PROPOSAL, {})
    if not isinstance(proposal, dict) or not proposal.get("proposals"):
        proposal = build_code_edit_proposal(project_id=project_id, save=save)
    preview = _read_json(SAFE_REWRITE_PREVIEW, {})
    if not isinstance(preview, dict) or not preview.get("rows"):
        preview = build_safe_rewrite_preview(project_id=project_id, save=save)
    bundle = build_draft_verification_bundle(project_id=project_id, save=False)
    rows = []
    for row in preview.get("rows", []) or []:
        rows.append({
            "path": row.get("path"),
            "status": row.get("status"),
            "change_type": row.get("change_type"),
            "proposed_sha256": row.get("proposed_sha256"),
            "diff_summary": row.get("diff_summary"),
        })
    blocked = [row.get("path") for row in preview.get("rows", []) if row.get("status") == "blocked"]
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "blocked" if blocked or preview.get("ok") is False else "pass",
        "ok": not blocked and preview.get("ok") is not False,
        "proposal_id": proposal.get("checked_at"),
        "rows": rows,
        "risk_report": bundle.get("steps", {}).get("quality", {}),
        "review_checklist": bundle.get("steps", {}).get("review_checklist", {}),
        "message": "Generated code patch artifact assembled without applying source edits.",
    }
    if save:
        _write_json(GENERATED_CODE_PATCH, report)
    else:
        report["preview_only"] = True
    return report


def build_test_suggestions(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v14.4: suggest verification steps based on proposed file changes."""
    preview = _read_json(SAFE_REWRITE_PREVIEW, {})
    if not isinstance(preview, dict) or not preview.get("rows"):
        preview = build_safe_rewrite_preview(project_id=project_id, save=save)
    draft_impact = build_draft_test_impact(project_id=project_id, save=False)
    commands: list[dict[str, Any]] = []
    manual_checks: list[str] = []

    def add(command: str, reason: str) -> None:
        if not any(row.get("command") == command for row in commands):
            commands.append({"command": command, "reason": reason})

    add("python -m py_compile conscious_agent/*.py tools/smoke_check.py", "Compile every Python module before release.")
    add("PYTHONPATH=conscious_agent python -c \"import dashboard; print(dashboard.DASHBOARD_VERSION)\"", "Catch dashboard syntax/import issues before desktop launch.")
    add("python conscious_agent/main.py --doctor", "Doctor mode summarizes release blockers and environment warnings.")
    add("python conscious_agent/main.py --stabilization-checkpoint --stabilization-full", "Full stabilization checkpoint must remain healthy.")
    add("python tools/smoke_check.py", "Smoke check verifies critical CLI surfaces.")
    for item in draft_impact.get("commands", []) or []:
        add(str(item.get("command")), str(item.get("reason", "Draft test impact command.")))

    files = [str(row.get("path", "")) for row in preview.get("rows", [])]
    if any("api_server.py" in path for path in files):
        manual_checks.append("Verify GET endpoints are read-only and POST endpoints require explicit confirmations for writes.")
    if any("dashboard.py" in path for path in files):
        manual_checks.append("Open /patch-drafts and confirm approve/reject controls use POST only.")
    if any("release_pipeline.py" in path for path in files):
        manual_checks.append("Run release readiness and approved code patch dry-run after code patch generation changes.")
    manual_checks.append("Confirm README_NEXT_STEPS.md documents every version included in the patch.")
    manual_checks.append("Confirm dry-runs never overwrite real rollback/apply pointers.")
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if commands else "warn",
        "ok": True,
        "files": files,
        "commands": commands,
        "manual_checks": manual_checks,
        "message": f"Prepared {len(commands)} command suggestion(s) and {len(manual_checks)} manual check(s).",
    }
    if save:
        _write_json(TEST_SUGGESTIONS, report)
    else:
        report["preview_only"] = True
    return report


def build_inline_review_note(
    project_id: str = "eidolon",
    note: str | None = None,
    file_path: str | None = None,
    intent_block: str | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """v14.6: attach review notes to a file and/or intent block."""
    notes = _read_json(INLINE_REVIEW_NOTES, [])
    if not isinstance(notes, list):
        notes = []
    added = None
    if note:
        added = {
            "created_at": _now(),
            "project_id": project_id,
            "file": file_path,
            "intent_block": intent_block,
            "note": note,
            "status": "open",
        }
        notes.append(added)
        if save:
            _write_json(INLINE_REVIEW_NOTES, notes)
    return {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass",
        "ok": True,
        "added": added,
        "notes": notes[-50:],
        "message": f"Inline review notes loaded; {1 if added else 0} note(s) added.",
    }


def _approval_ok(project_id: str = "eidolon") -> tuple[bool, dict[str, Any], str | None]:
    approval = _read_json(APPROVAL_STATE, {})
    if not isinstance(approval, dict) or not approval.get("approved"):
        return False, approval if isinstance(approval, dict) else {}, "No approved draft exists."
    if approval.get("consumed"):
        return False, approval, "Approval has already been consumed."
    if approval.get("status") != "approved":
        return False, approval, f"Approval status is {approval.get('status')!r}, not 'approved'."
    binding = validate_approval_binding(approval=approval, project_id=project_id)
    if not binding.get("ok"):
        approval = dict(approval)
        approval["binding_validation"] = binding
        return False, approval, "Approval artifact binding is stale or mismatched; approve the current saved review bundle again."
    return True, approval, None


def build_apply_approved_code_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v14.7: apply generated code edits only after approval; dry-run is non-mutating."""
    ok, approval, reason = _approval_ok(project_id=project_id)
    if not ok:
        return {"version": RELEASE_PIPELINE_VERSION, "checked_at": _now(), "project_id": project_id, "status": "blocked", "ok": False, "dry_run": dry_run, "message": reason}
    preview = _read_json(SAFE_REWRITE_PREVIEW, {})
    if not isinstance(preview, dict) or not preview.get("rows"):
        preview = build_safe_rewrite_preview(project_id=project_id, save=save)
    generated = _read_json(GENERATED_CODE_PATCH, {})
    if not isinstance(generated, dict) or not generated.get("rows"):
        generated = build_generated_code_patch(project_id=project_id, save=save)
    if preview.get("ok") is False:
        return {"version": RELEASE_PIPELINE_VERSION, "checked_at": _now(), "project_id": project_id, "status": "blocked", "ok": False, "dry_run": dry_run, "message": "Safe rewrite preview is blocked; code patch cannot apply.", "preview": preview}
    if not dry_run and not approve:
        return {"version": RELEASE_PIPELINE_VERSION, "checked_at": _now(), "project_id": project_id, "status": "blocked", "ok": False, "dry_run": dry_run, "message": "Real code patch apply requires approve=True / --approve-controlled-self-build."}

    run_id = f"approved_code_patch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    applied: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in preview.get("rows", []) or []:
        if row.get("status") != "ready":
            applied.append({"path": row.get("path"), "status": "skipped", "message": row.get("message", "Not ready.")})
            continue
        relative_path = str(row.get("path"))
        try:
            target = _safe_path(relative_path)
        except Exception as error:
            errors.append(str(error))
            continue
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if _sha256(current) != row.get("expected_sha256"):
            errors.append(f"{relative_path}: current hash changed after preview; refusing rewrite.")
            continue
        backup = BACKUPS_DIR / run_id / relative_path.replace("\\", "/")
        if not dry_run:
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text(current, encoding="utf-8")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(row.get("proposed_content", "")), encoding="utf-8")
        applied.append({
            "path": relative_path,
            "status": "dry_run" if dry_run else "applied",
            "backup_path": str(backup.relative_to(ROOT_DIR)),
            "original_sha256": row.get("expected_sha256"),
            "applied_sha256": row.get("proposed_sha256"),
        })
    status = "failed" if errors else "dry_run" if dry_run else "applied"
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "run_id": run_id,
        "status": status,
        "ok": not errors,
        "dry_run": dry_run,
        "approval_consumed": bool(not dry_run and not errors),
        "applied": applied,
        "errors": errors,
        "rollback_available": bool(not dry_run and any(row.get("status") == "applied" for row in applied)),
        "message": f"Approved code patch {status}; dry-runs do not consume approval or overwrite real apply pointers.",
    }
    if save:
        _write_json(APPROVED_CODE_DRY_RUN if dry_run else APPROVED_CODE_APPLY, report)
        if not dry_run and not errors:
            approval["consumed"] = True
            approval["consumed_at"] = _now()
            approval["code_patch_run_id"] = run_id
            _write_json(APPROVAL_STATE, approval)
            _timeline_event("approved_code_patch_apply", {"project_id": project_id, "run_id": run_id, "status": status}, save=True)
    return report


def _compile_check() -> dict[str, Any]:
    files = sorted((ROOT_DIR / "conscious_agent").glob("*.py")) + [ROOT_DIR / "tools" / "smoke_check.py"]
    cmd = [sys.executable, "-m", "py_compile", *[str(path) for path in files]]
    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, text=True, capture_output=True, timeout=45)
        return {"name": "py-compile", "status": "pass" if result.returncode == 0 else "blocked", "returncode": result.returncode, "message": (result.stderr or result.stdout)[-1000:] if result.returncode else "Python compile passed."}
    except Exception as error:
        return {"name": "py-compile", "status": "blocked", "message": str(error)}


def build_release_readiness(project_id: str = "eidolon", save: bool = True) -> dict[str, Any]:
    """v14.9+: decide whether the current package is ready to ship."""
    rows: list[dict[str, Any]] = []
    rows.append(_compile_check())
    readme = README_FILE.read_text(encoding="utf-8") if README_FILE.exists() else ""
    settings = _read_json(DATA_DIR / "settings.json", {})
    projects = _read_json(DATA_DIR / "projects.json", {})
    expected_version = str(settings.get("version") or settings.get("settings_version") or settings.get("last_updated_for") or RELEASE_PIPELINE_VERSION).lstrip("v")
    expected_marker = f"v{expected_version}"
    rows.append({"name": "readme-current-version", "status": "pass" if expected_marker in readme else "warn", "message": f"README documents {expected_marker}." if expected_marker in readme else f"README does not yet mention {expected_marker}."})
    rows.append({"name": "settings-version", "status": "pass" if (str(settings.get("version") or settings.get("settings_version")) == expected_version and settings.get("last_updated_for") == expected_marker) else "warn", "message": f"settings version markers: version={settings.get('version') or settings.get('settings_version')} last_updated_for={settings.get('last_updated_for')} expected={expected_marker}"})
    rows.append({"name": "project-version", "status": "pass" if projects.get("last_updated_for") == expected_marker else "warn", "message": f"projects last_updated_for={projects.get('last_updated_for')} expected={expected_marker}"})
    approval = _read_json(APPROVAL_STATE, {})
    rows.append({"name": "approval-state", "status": "warn" if approval.get("approved") and not approval.get("consumed") else "pass", "message": "Unconsumed approval exists; acceptable for review but not final release." if approval.get("approved") and not approval.get("consumed") else "No dirty unconsumed approval blocking release."})
    apply_report = _read_json(APPROVED_CODE_APPLY, {})
    dry_run = _read_json(APPROVED_CODE_DRY_RUN, {})
    rows.append({"name": "dry-run-separation", "status": "pass" if dry_run.get("dry_run", True) is True else "blocked", "message": "Dry-run code patch reports are separate from real apply reports."})
    if apply_report:
        real_rows = [row for row in apply_report.get("applied", []) if row.get("status") == "applied"]
        rows.append({"name": "rollback-availability", "status": "pass" if apply_report.get("status") == "applied" and real_rows and apply_report.get("rollback_available") else "warn", "message": f"latest real code apply status={apply_report.get('status')} rollback={apply_report.get('rollback_available')}"})
    else:
        rows.append({"name": "rollback-availability", "status": "warn", "message": "No real approved code apply exists yet; rollback is not applicable."})
    suggestions = _read_json(TEST_SUGGESTIONS, {})
    rows.append({"name": "test-suggestions", "status": "pass" if suggestions.get("commands") else "warn", "message": f"{len(suggestions.get('commands', [])) if isinstance(suggestions, dict) else 0} test suggestion(s) recorded."})
    status = _status_from(rows)
    readiness = "FAILED" if status == "blocked" else "READY WITH WARNINGS" if status == "warn" else "READY"
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "release_readiness": readiness,
        "rows": rows,
        "known_warnings": [row.get("message") for row in rows if row.get("status") == "warn"],
        "message": f"Release readiness: {readiness}.",
    }
    if save:
        _write_json(RELEASE_READINESS, report)
    else:
        report["preview_only"] = True
    return report


def build_prepare_release_package(project_id: str = "eidolon", package_name: str | None = None, save: bool = True) -> dict[str, Any]:
    """v14.8: create package metadata after approval/release checks."""
    readiness = build_release_readiness(project_id=project_id, save=False)
    settings = _read_json(DATA_DIR / "settings.json", {})
    current_version = _current_release_version()
    apply_report = _read_json(APPROVED_CODE_APPLY, {})
    dry_run = _read_json(APPROVED_CODE_DRY_RUN, {})
    suggestions = _read_json(TEST_SUGGESTIONS, {})
    changed = [row.get("path") for row in apply_report.get("applied", []) if row.get("status") == "applied"] if isinstance(apply_report, dict) else []
    previewed = [row.get("path") for row in dry_run.get("applied", []) if row.get("status") == "dry_run"] if isinstance(dry_run, dict) else []
    name = package_name or f"Eidolon_v{current_version.replace('.', '_')}.zip"
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": "pass" if readiness.get("ok") else "blocked",
        "ok": bool(readiness.get("ok")),
        "package_name": name,
        "changed_files": changed,
        "previewed_files": previewed,
        "readme_sections_required": [f"v{current_version}"],
        "verification_commands": [row.get("command") for row in suggestions.get("commands", [])] if isinstance(suggestions, dict) else [],
        "known_warnings": readiness.get("known_warnings", []),
        "rollback_available": bool(apply_report.get("rollback_available")) if isinstance(apply_report, dict) else False,
        "zip_readiness": readiness.get("release_readiness"),
        "message": f"Release package metadata prepared for {name}.",
    }
    if save:
        _write_json(RELEASE_PACKAGE, report)
    else:
        report["preview_only"] = True
    return report


def build_human_approved_release_loop(project_id: str = "eidolon", approve_apply: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """v15.0: one approved patch through preview/apply/readiness/package, then stop."""
    existing_approval = _read_json(APPROVAL_STATE, {})
    approval_is_live = bool(isinstance(existing_approval, dict) and existing_approval.get("approved") and not existing_approval.get("consumed") and existing_approval.get("status") == "approved")
    if approval_is_live:
        request = _read_json(DRAFT_REQUEST, {})
        draft = _read_json(CURRENT_DRAFT, {})
    else:
        request = build_patch_draft_request(project_id=project_id, target_version=_current_release_version(), save=save)
        draft = build_draft_patch(project_id=project_id, save=save)
    proposal = build_code_edit_proposal(project_id=project_id, save=save)
    preview = build_safe_rewrite_preview(project_id=project_id, save=save)
    generated = build_generated_code_patch(project_id=project_id, save=save)
    tests = build_test_suggestions(project_id=project_id, save=save)
    approval_ok, approval, approval_reason = _approval_ok(project_id=project_id)
    apply_report = None
    if approval_ok and approve_apply:
        apply_report = build_apply_approved_code_patch(project_id=project_id, approve=approve_apply, dry_run=dry_run, save=save)
    readiness = build_release_readiness(project_id=project_id, save=save)
    package = build_prepare_release_package(project_id=project_id, save=save)
    blocked = [name for name, step in {"request": request, "draft": draft, "proposal": proposal, "preview": preview, "generated": generated, "tests": tests, "readiness": readiness, "package": package}.items() if isinstance(step, dict) and step.get("ok") is False]
    status = "blocked" if blocked else "applied" if apply_report and apply_report.get("status") == "applied" else "dry_run" if apply_report and apply_report.get("status") == "dry_run" else "awaiting_approval"
    report = {
        "version": RELEASE_PIPELINE_VERSION,
        "checked_at": _now(),
        "project_id": project_id,
        "status": status,
        "ok": status != "blocked",
        "dry_run": dry_run,
        "approval_ready": approval_ok,
        "approval_reason": approval_reason,
        "steps": {
            "request": request,
            "draft": draft,
            "code_edit_proposal": proposal,
            "safe_rewrite_preview": preview,
            "generated_code_patch": generated,
            "test_suggestions": tests,
            "approval_state": approval,
            "apply": apply_report,
            "release_readiness": readiness,
            "release_package": package,
        },
        "blocked_steps": blocked,
        "message": "Human-approved release loop prepared one release package path and stopped after one approval/apply decision.",
    }
    if save:
        _write_json(RELEASE_LOOP_REPORT, report)
        _timeline_event("human_approved_release_loop", {"project_id": project_id, "status": status, "dry_run": dry_run}, save=True)
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
    for key in ["blocked_reasons", "errors", "known_warnings"]:
        values = report.get(key) or []
        if values:
            lines.extend(["", f"## {key.replace('_', ' ').title()}"])
            lines.extend([f"- {item}" for item in values])
    rows = report.get("rows") or report.get("proposals") or report.get("commands") or report.get("manual_checks") or []
    if rows:
        lines.extend(["", "## Rows"])
        for row in rows[:35]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("path") or row.get("target_file") or row.get("command") or row.get("item") or "row"
                status = row.get("status") or row.get("change_type") or "info"
                message = row.get("message") or row.get("intent") or row.get("reason") or ""
                lines.append(f"- {str(status).upper()} {name}: {message}")
            else:
                lines.append(f"- {row}")
    if full:
        lines.extend(["", "## Raw report", json.dumps(report, indent=2, default=str)])
    return "\n".join(lines).strip()


def code_edit_proposal_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.1 Real Code Edit Proposal", report or build_code_edit_proposal(save=False), full)


def safe_rewrite_preview_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.2 Safe File Rewrite Preview", report or build_safe_rewrite_preview(save=False), full)


def generated_code_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.3 AI-Assisted Code Patch Generation", report or build_generated_code_patch(save=False), full)


def test_suggestions_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.4 Unit Test Suggestion Generator", report or build_test_suggestions(save=False), full)


def inline_review_note_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.6 Inline Patch Review Comments", report or build_inline_review_note(save=False), full)


def apply_approved_code_patch_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.7 Human-Approved Real Apply Pipeline", report or build_apply_approved_code_patch(dry_run=True, save=False), full)


def prepare_release_package_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v14.8 Commit / Package Preparation", report or build_prepare_release_package(save=False), full)


def release_readiness_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    report = report or build_release_readiness(save=False)
    text = _generic_text("Eidolon v14.9 Release Readiness Gate", report, full)
    text += f"\n\nRelease readiness: {report.get('release_readiness')}"
    return text


def human_approved_release_loop_text(report: dict[str, Any] | None = None, full: bool = False) -> str:
    return _generic_text("Eidolon v15.0 Human-Approved Release Loop", report or build_human_approved_release_loop(save=False), full)


def print_code_edit_proposal(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_code_edit_proposal(project_id=project_id, save=True)
    _json_print(report) if json_output else print(code_edit_proposal_text(report, full=full))


def print_safe_rewrite_preview(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_safe_rewrite_preview(project_id=project_id, save=True)
    _json_print(report) if json_output else print(safe_rewrite_preview_text(report, full=full))


def print_generated_code_patch(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_generated_code_patch(project_id=project_id, save=True)
    _json_print(report) if json_output else print(generated_code_patch_text(report, full=full))


def print_test_suggestions(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_test_suggestions(project_id=project_id, save=True)
    _json_print(report) if json_output else print(test_suggestions_text(report, full=full))


def print_inline_review_note(project_id: str = "eidolon", note: str | None = None, file_path: str | None = None, intent_block: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_inline_review_note(project_id=project_id, note=note, file_path=file_path, intent_block=intent_block, save=True)
    _json_print(report) if json_output else print(inline_review_note_text(report, full=full))


def print_apply_approved_code_patch(project_id: str = "eidolon", approve: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_apply_approved_code_patch(project_id=project_id, approve=approve, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(apply_approved_code_patch_text(report, full=full))


def print_prepare_release_package(project_id: str = "eidolon", package_name: str | None = None, full: bool = False, json_output: bool = False) -> None:
    report = build_prepare_release_package(project_id=project_id, package_name=package_name, save=True)
    _json_print(report) if json_output else print(prepare_release_package_text(report, full=full))


def print_release_readiness(project_id: str = "eidolon", full: bool = False, json_output: bool = False) -> None:
    report = build_release_readiness(project_id=project_id, save=True)
    _json_print(report) if json_output else print(release_readiness_text(report, full=full))


def print_human_approved_release_loop(project_id: str = "eidolon", approve_apply: bool = False, dry_run: bool = True, full: bool = False, json_output: bool = False) -> None:
    report = build_human_approved_release_loop(project_id=project_id, approve_apply=approve_apply, dry_run=dry_run, save=True)
    _json_print(report) if json_output else print(human_approved_release_loop_text(report, full=full))
