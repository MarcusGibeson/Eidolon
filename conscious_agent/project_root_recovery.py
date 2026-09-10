from __future__ import annotations

"""Preview-then-confirm recovery for missing or moved project source roots.

The operator's project registries are mutable private runtime data.  This module
never guesses a replacement root and never writes one without an exact preview
token plus explicit confirmation.  Conversation sessions and drafts are untouched.
"""

import hashlib
import json
import secrets
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import DATA_DIR, ROOT_DIR
from project_identity import normalize_project_identity, project_source_binding, resolve_project_selection
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic

PROJECT_ROOT_RECOVERY_SCHEMA_VERSION = "1"
RECOVERY_DIR = DATA_DIR / "workspaces" / "project_root_recovery"
RECOVERY_RECEIPT_DIR = RECOVERY_DIR / "receipts"
RECOVERY_BACKUP_DIR = RECOVERY_DIR / "backups"
RECOVERY_PREVIEW_DIR = RECOVERY_DIR / "previews"
RECOVERY_PREVIEW_TTL_SECONDS = 1800.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load(path: Path, default: Any) -> Any:
    expected_type = type(default) if isinstance(default, (dict, list)) else None
    return load_json_file(path, default, expected_type=expected_type)


def _atomic_write(path: Path, value: Any) -> None:
    expected_type = type(value) if isinstance(value, (dict, list)) else None
    write_json_atomic(path, value, expected_type=expected_type, sort_keys=True)


def _backup(path: Path, project_id: str) -> str:
    if not path.is_file():
        return ""
    RECOVERY_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = RECOVERY_BACKUP_DIR / f"{project_id}-{path.name}-{stamp}.bak"
    shutil.copy2(path, target)
    return str(target)


def _candidate_record(project: dict[str, Any], candidate_root: str | Path) -> dict[str, Any]:
    path = Path(candidate_root).expanduser().resolve(strict=False)
    candidate = dict(project)
    candidate["root"] = str(path)
    candidate["path"] = str(path)
    candidate["source_root"] = str(path)
    return normalize_project_identity(candidate, base_root=ROOT_DIR)


def _identity_requirements(project: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    markers = [str(value) for value in binding.get("source_identity_markers", []) if str(value)]
    if not markers:
        readme = str(project.get("readme_path") or "").strip()
        if readme:
            markers = [readme]
    evidence_sufficient = bool(markers or binding.get("source_version_file") or project.get("id") == "eidolon")
    missing = [marker for marker in markers if not (Path(str(binding.get("source_root") or "")) / marker).is_file()]
    return {
        "markers": markers,
        "missing_markers": missing,
        "evidence_sufficient": evidence_sufficient,
        "version_checked": bool(binding.get("source_version_file")),
        "expected_version": str(binding.get("expected_working_version") or ""),
        "observed_version": str(binding.get("observed_working_version") or ""),
        "version_mismatch": bool(binding.get("version_mismatch")),
    }


def preview_project_root_correction(selector: str, candidate_root: str | Path, *, _persist: bool = True) -> dict[str, Any]:
    import project_manager

    projects = project_manager.list_projects()
    selection = resolve_project_selection(projects, selector)
    report = selection.as_dict()
    report.update({
        "changed": False,
        "operator_confirmation_required": False,
        "runtime_registry_rewritten": False,
        "workspace_registry_rewritten": False,
        "provider_contacted": False,
    })
    if not selection.ok:
        report["message"] = "Select one stable project ID before previewing a source-root correction."
        return report
    project = selection.project or {}
    candidate = _candidate_record(project, candidate_root)
    binding = project_source_binding(candidate)
    requirements = _identity_requirements(candidate, binding)
    current_root = str(project.get("source_root") or project.get("root") or project.get("path") or "")
    candidate_resolved = str(binding.get("source_root") or "")
    same_root = bool(current_root and Path(current_root).resolve(strict=False) == Path(candidate_resolved).resolve(strict=False))
    safe = bool(
        binding.get("source_root_accessible")
        and requirements["evidence_sufficient"]
        and not requirements["missing_markers"]
        and not requirements["version_mismatch"]
    )
    token_payload = {
        "schema": PROJECT_ROOT_RECOVERY_SCHEMA_VERSION,
        "project_id": str(project.get("id") or ""),
        "current_root": str(Path(current_root).resolve(strict=False)) if current_root else "",
        "candidate_root": candidate_resolved,
        "markers": requirements["markers"],
        "expected_version": requirements["expected_version"],
        "observed_version": requirements["observed_version"],
        "safe_to_apply": safe,
    }
    preview_token = hashlib.sha256(_canonical(token_payload)).hexdigest()
    report.update({
        "ok": safe,
        "status": "ready" if safe else str(binding.get("status") or "blocked"),
        "project_id": str(project.get("id") or ""),
        "project_name": str(project.get("name") or ""),
        "current_source_root": token_payload["current_root"],
        "candidate_source_root": candidate_resolved,
        "same_root": same_root,
        "source_binding": binding,
        "identity_requirements": requirements,
        "safe_to_apply": safe,
        "preview_token": preview_token,
        "operator_confirmation_required": safe and not same_root,
        "message": (
            "The candidate source root matches the registered identity and awaits explicit confirmation."
            if safe and not same_root else
            "The candidate source root is already registered."
            if safe and same_root else
            "The candidate source root could not be identity-bound and was not accepted."
        ),
    })
    if _persist and safe and not same_root:
        try:
            from project_switching_continuity import project_switch_snapshot
            switch_revision = max(0, int(project_switch_snapshot().get("revision") or 0))
        except Exception:
            switch_revision = 0
        created_epoch = time.time()
        private_preview = {
            "type": "project_root_recovery_preview",
            "schema_version": PROJECT_ROOT_RECOVERY_SCHEMA_VERSION,
            "project_id": str(project.get("id") or ""),
            "current_source_root": token_payload["current_root"],
            "candidate_source_root": candidate_resolved,
            "preview_token": preview_token,
            "identity_digest": hashlib.sha256(_canonical(token_payload)).hexdigest(),
            "switch_revision": switch_revision,
            "created_at": _now(),
            "created_epoch": created_epoch,
            "expires_epoch": created_epoch + RECOVERY_PREVIEW_TTL_SECONDS,
            "local_private": True,
            "content_free": True,
        }
        _atomic_write(RECOVERY_PREVIEW_DIR / f"{private_preview['project_id']}.json", private_preview)
    return report


def pending_project_root_correction(project_id: str, *, now_epoch: float | None = None) -> dict[str, Any]:
    """Revalidate one private pending preview and return a content-free summary."""
    import project_manager
    project_token = str(project_id or "").strip().lower()
    path = RECOVERY_PREVIEW_DIR / f"{project_token}.json"
    record = _load(path, {})
    base = {
        "pending": False, "status": "none", "project_id": project_token, "valid": False,
        "expires_at": "", "identity_evidence_matches": False, "switch_revision_matches": False,
        "provider_contacted": False, "content_free": True, "local_private": True,
    }
    if not isinstance(record, dict) or record.get("type") != "project_root_recovery_preview":
        return base
    now = time.time() if now_epoch is None else float(now_epoch)
    expires = float(record.get("expires_epoch") or 0.0)
    base["expires_at"] = datetime.fromtimestamp(expires, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z") if expires else ""
    if not expires or now >= expires:
        base["status"] = "expired"
        return base
    project = project_manager.get_project(project_token) or {}
    if not project:
        base["status"] = "project_missing"
        return base
    try:
        from project_switching_continuity import project_switch_snapshot
        current_revision = max(0, int(project_switch_snapshot().get("revision") or 0))
    except Exception:
        current_revision = 0
    revision_matches = current_revision == max(0, int(record.get("switch_revision") or 0))
    base["switch_revision_matches"] = revision_matches
    current_root = str(project.get("source_root") or project.get("root") or project.get("path") or "")
    try:
        current_root = str(Path(current_root).expanduser().resolve(strict=False)) if current_root else ""
    except OSError:
        current_root = ""
    root_matches = current_root == str(record.get("current_source_root") or "")
    candidate = str(record.get("candidate_source_root") or "")
    preview = preview_project_root_correction(project_token, candidate, _persist=False) if candidate else {}
    identity_matches = bool(
        preview.get("ok")
        and secrets.compare_digest(str(preview.get("preview_token") or ""), str(record.get("preview_token") or ""))
        and str(preview.get("candidate_source_root") or "") == candidate
        and root_matches
    )
    base["identity_evidence_matches"] = identity_matches
    base["valid"] = bool(identity_matches and revision_matches)
    base["pending"] = bool(base["valid"])
    base["status"] = "pending" if base["valid"] else ("stale_revision" if not revision_matches else "stale_identity")
    return base


def discard_project_root_correction_preview(project_id: str) -> None:
    (RECOVERY_PREVIEW_DIR / f"{str(project_id or '').strip().lower()}.json").unlink(missing_ok=True)


def _replace_project_root(payload: dict[str, Any], project_id: str, candidate_root: str) -> bool:
    projects = payload.get("projects") if isinstance(payload.get("projects"), list) else []
    changed = False
    for row in projects:
        if not isinstance(row, dict) or str(row.get("id") or "") != project_id:
            continue
        row["root"] = candidate_root
        row["path"] = candidate_root
        row["source_root"] = candidate_root
        row["source_root_reference"] = candidate_root
        row["source_root_recovered_at"] = _now()
        changed = True
    return changed


def confirm_project_root_correction(
    selector: str,
    candidate_root: str | Path,
    *,
    preview_token: str,
    operator_confirmed: bool = False,
) -> dict[str, Any]:
    import project_manager
    import workspace_orchestration

    preview = preview_project_root_correction(selector, candidate_root)
    result = dict(preview)
    result.update({
        "changed": False,
        "operator_confirmed": bool(operator_confirmed),
        "runtime_registry_rewritten": False,
        "workspace_registry_rewritten": False,
        "backup_paths": [],
    })
    if not preview.get("ok"):
        return result
    if not operator_confirmed:
        result.update({
            "ok": False,
            "status": "confirmation_required",
            "message": "Explicit operator confirmation is required before changing a project source root.",
        })
        return result
    if not secrets.compare_digest(str(preview.get("preview_token") or ""), str(preview_token or "")):
        result.update({
            "ok": False,
            "status": "stale_preview",
            "message": "The source-root preview changed. Review the current candidate before confirming it.",
        })
        return result
    if preview.get("same_root"):
        result.update({"ok": True, "status": "already_current", "message": "The candidate source root is already registered."})
        return result

    project_id = str(preview.get("project_id") or "")
    candidate = str(preview.get("candidate_source_root") or "")
    runtime_path = project_manager.PROJECTS_FILE
    workspace_path = workspace_orchestration.PROJECTS_FILE
    runtime_before = runtime_path.read_bytes() if runtime_path.is_file() else None
    workspace_before = workspace_path.read_bytes() if workspace_path.is_file() else None
    runtime_data = project_manager.load_projects_data()
    workspace_data = _load(workspace_path, {}) if workspace_path.is_file() else {}
    if not _replace_project_root(runtime_data, project_id, candidate):
        result.update({"ok": False, "status": "project_missing", "message": "The runtime project disappeared before confirmation."})
        return result
    workspace_has_project = False
    if isinstance(workspace_data, dict) and isinstance(workspace_data.get("projects"), list):
        workspace_has_project = _replace_project_root(workspace_data, project_id, candidate)
    if workspace_path.is_file() and not workspace_has_project:
        result.update({
            "ok": False,
            "status": "registry_mismatch",
            "message": "Workspace and runtime project registries are not aligned; neither source-root record changed.",
        })
        return result

    backups = [path for path in (_backup(runtime_path, project_id), _backup(workspace_path, project_id)) if path]
    try:
        project_manager.save_projects_data(runtime_data)
        if workspace_path.is_file():
            _atomic_write(workspace_path, workspace_data)
    except Exception:
        if runtime_before is not None:
            runtime_path.write_bytes(runtime_before)
        elif runtime_path.exists():
            runtime_path.unlink()
        if workspace_before is not None:
            workspace_path.write_bytes(workspace_before)
        elif workspace_path.exists():
            workspace_path.unlink()
        raise

    receipt = {
        "type": "project_root_recovery_receipt",
        "schema_version": PROJECT_ROOT_RECOVERY_SCHEMA_VERSION,
        "project_id": project_id,
        "previous_source_root": str(preview.get("current_source_root") or ""),
        "candidate_source_root": candidate,
        "preview_token": str(preview_token or ""),
        "changed_at": _now(),
        "backup_count": len(backups),
        "local_private": True,
        "content_free": True,
    }
    receipt_path = RECOVERY_RECEIPT_DIR / f"{project_id}-{hashlib.sha256(str(preview_token).encode()).hexdigest()}.json"
    _atomic_write(receipt_path, receipt)
    discard_project_root_correction_preview(project_id)
    result.update({
        "ok": True,
        "status": "changed",
        "changed": True,
        "runtime_registry_rewritten": True,
        "workspace_registry_rewritten": workspace_path.is_file(),
        "backup_paths": backups,
        "receipt": {key: value for key, value in receipt.items() if key not in {"preview_token"}},
        "message": "The project source root was corrected after exact identity verification and explicit confirmation.",
    })
    return result


def root_recovery_record_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {"content", "message", "prompt", "conversation", "draft", "memory", "provider_payload", "credential", "secret"}
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
