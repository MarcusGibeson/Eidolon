from __future__ import annotations

"""v1255.0-v1255.2 foundations for controlled candidate application.

This layer consumes the sealed v1254 isolated-coding result and prepares a
content-bounded, digest-bound application packet.  Preparation is read-only
with respect to the selected project.  It detects conflicts only on paths the
candidate intends to change, records unrelated source drift without treating
it as permission to overwrite anything, and defines the private backup scope
required before the first selected-project mutation.

No preparation function grants application, rollback, installation, release,
permanent approval, or independent authority.
"""

import base64
import hashlib
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from isolated_coding_execution import (
    load_isolated_coding_execution,
    load_isolated_coding_review,
)
from isolated_coding_execution_foundations import (
    _file_digest,
    _is_link_like,
    _manifest_digest,
    _resolve_project_root,
    _safe_relative,
    _walk_project,
    _within,
    load_coding_project_inspection,
    load_coding_work_request,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1255.2"
MAX_APPLICATION_FILES = 64
MAX_APPLICATION_BYTES = 4 * 1024 * 1024
MAX_BACKUP_BYTES = 4 * 1024 * 1024

DENIED_AUTHORITY = {
    "application_execution_authorized": False,
    "rollback_execution_authorized": False,
    "selected_project_mutation_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "provider_contact_authorized": False,
    "dependency_installation_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "approval_granted": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}


def _application_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_application_requests" / f"{request_id}.json"


def _backup_scope_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "controlled_application_backup_scopes" / f"{request_id}.json"


def _workspace_record_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json"


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _request_id(value: str) -> str:
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"devc_[a-f0-9]{24}", text):
        raise ValueError("invalid_coding_work_request_id")
    return text


def _path_digest(relative: str) -> str:
    return hashlib.sha256(relative.encode("utf-8")).hexdigest()


def _candidate_workspace_root(workspace: Mapping[str, Any]) -> Path:
    raw = str(workspace.get("workspace_path") or "")
    if not raw:
        raise ValueError("candidate_workspace_missing")
    path = Path(raw)
    if _is_link_like(path):
        raise ValueError("candidate_workspace_link_or_junction_rejected")
    root = path.resolve(strict=True)
    if not root.is_dir() or _is_link_like(root):
        raise ValueError("candidate_workspace_invalid")
    return root


def _inventory_map(inspection: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in inspection.get("inventory") or []:
        relative = _safe_relative(str(row.get("relative_path") or ""))
        folded = relative.casefold()
        if folded in {key.casefold() for key in rows}:
            raise ValueError("baseline_casefold_collision")
        rows[relative] = {
            "relative_path": relative,
            "relative_path_digest": _path_digest(relative),
            "content_digest": str(row.get("content_digest") or ""),
            "size_bytes": int(row.get("size_bytes") or 0),
            "existed": True,
        }
    return rows


def _candidate_change_entries(
    *, review: Mapping[str, Any], inspection: Mapping[str, Any], workspace: Mapping[str, Any]
) -> list[dict[str, Any]]:
    changed = sorted({_safe_relative(str(value)) for value in review.get("changed_paths") or []}, key=str.casefold)
    if not changed:
        raise ValueError("review_has_no_candidate_changes")
    if len(changed) > MAX_APPLICATION_FILES:
        raise ValueError("candidate_file_limit_exceeded")
    if len({value.casefold() for value in changed}) != len(changed):
        raise ValueError("candidate_casefold_collision")

    baseline = _inventory_map(inspection)
    root = _candidate_workspace_root(workspace)
    entries: list[dict[str, Any]] = []
    total = 0
    for relative in changed:
        candidate = root / Path(*PurePosixPath(relative).parts)
        if not _within(root, candidate):
            raise ValueError("candidate_path_escape")
        baseline_row = baseline.get(relative)
        if candidate.exists():
            if _is_link_like(candidate) or not candidate.is_file():
                raise ValueError("candidate_path_link_or_nonfile_rejected")
            size = int(candidate.stat().st_size)
            total += size
            if total > MAX_APPLICATION_BYTES:
                raise ValueError("candidate_byte_limit_exceeded")
            operation = "modify" if baseline_row else "create"
            digest = _file_digest(candidate)
        else:
            if not baseline_row:
                raise ValueError("candidate_missing_for_new_path")
            size = 0
            operation = "delete"
            digest = ""
        entries.append({
            "relative_path": relative,
            "relative_path_digest": _path_digest(relative),
            "operation": operation,
            "candidate_content_digest": digest,
            "candidate_size_bytes": size,
            "baseline_existed": bool(baseline_row),
            "baseline_content_digest": str((baseline_row or {}).get("content_digest") or ""),
            "baseline_size_bytes": int((baseline_row or {}).get("size_bytes") or 0),
        })
    return entries


def _current_path_state(project_root: Path, entry: Mapping[str, Any]) -> dict[str, Any]:
    relative = _safe_relative(str(entry.get("relative_path") or ""))
    target = project_root / Path(*PurePosixPath(relative).parts)
    if not _within(project_root, target):
        return {"relative_path": relative, "relative_path_digest": _path_digest(relative), "state": "containment_conflict", "current_exists": False, "current_digest": ""}
    if target.exists() and (_is_link_like(target) or not target.is_file()):
        return {"relative_path": relative, "relative_path_digest": _path_digest(relative), "state": "link_or_nonfile_conflict", "current_exists": True, "current_digest": ""}
    current_exists = target.is_file()
    current_digest = _file_digest(target) if current_exists else ""
    baseline_exists = bool(entry.get("baseline_existed"))
    baseline_digest = str(entry.get("baseline_content_digest") or "")
    candidate_exists = str(entry.get("operation") or "") != "delete"
    candidate_digest = str(entry.get("candidate_content_digest") or "")
    if current_exists == baseline_exists and (not current_exists or current_digest == baseline_digest):
        state = "baseline"
    elif current_exists == candidate_exists and (not current_exists or current_digest == candidate_digest):
        state = "candidate"
    else:
        state = "conflict"
    return {
        "relative_path": relative,
        "relative_path_digest": _path_digest(relative),
        "state": state,
        "current_exists": current_exists,
        "current_content_digest": current_digest,
    }


def inspect_controlled_application_conflicts(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    review = load_isolated_coding_review(request_id, runtime_root=runtime_root)
    workspace = _read_json(_workspace_record_path(request_id, runtime_root))
    if not request or not inspection or not execution or not review or not workspace:
        return {"ok": False, "status": "controlled_application_lineage_missing", "request_id": request_id, **DENIED_AUTHORITY}
    result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
    if not result.get("ok") or result.get("test_passed") is not True:
        return {"ok": False, "status": "passing_isolated_candidate_required", "request_id": request_id, **DENIED_AUTHORITY}
    if str(result.get("review_digest") or "") != str(review.get("review_record_digest") or ""):
        return {"ok": False, "status": "isolated_review_lineage_mismatch", "request_id": request_id, **DENIED_AUTHORITY}
    try:
        project_root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
        changes = _candidate_change_entries(review=review, inspection=inspection, workspace=workspace)
        states = [_current_path_state(project_root, row) for row in changes]
        current_inventory, _ = _walk_project(project_root)
        current_manifest = _manifest_digest(current_inventory)
        current_casefold = {}
        for current_row in current_inventory:
            rel = str(current_row.get("relative_path") or "")
            current_casefold.setdefault(rel.casefold(), []).append(rel)
        casefold_conflicts = []
        for change in changes:
            relative = str(change.get("relative_path") or "")
            aliases = [value for value in current_casefold.get(relative.casefold(), []) if value != relative]
            if aliases:
                casefold_conflicts.append({
                    "relative_path_digest": _path_digest(relative),
                    "alias_path_digests": [_path_digest(value) for value in sorted(aliases, key=str.casefold)],
                })
    except (OSError, ValueError) as exc:
        return {"ok": False, "status": "controlled_application_boundary_rejected", "reason": str(exc), "request_id": request_id, **DENIED_AUTHORITY}

    conflicts = [row for row in states if row["state"] not in {"baseline", "candidate"}]
    if casefold_conflicts:
        conflicts.extend({
            "relative_path": "",
            "relative_path_digest": row["relative_path_digest"],
            "state": "windows_casefold_conflict",
        } for row in casefold_conflicts)
    already_applied = bool(states and all(row["state"] == "candidate" for row in states) and not casefold_conflicts)
    mixed_known = bool(states and not conflicts and not already_applied and any(row["state"] == "candidate" for row in states))
    source_changed = current_manifest != str(inspection.get("source_manifest_digest") or "")
    safe = not conflicts and not mixed_known
    row = {
        "ok": safe,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": (
            "controlled_application_candidate_already_present" if already_applied
            else "controlled_application_paths_clear" if safe
            else "controlled_application_partial_state_conflict" if mixed_known
            else "controlled_application_conflict_detected"
        ),
        "request_id": request_id,
        "change_count": len(changes),
        "changes": changes,
        "path_states": states,
        "conflict_count": len(conflicts),
        "conflict_path_digests": [row["relative_path_digest"] for row in conflicts],
        "windows_casefold_conflict_count": len(casefold_conflicts),
        "source_manifest_changed": source_changed,
        "unrelated_source_changes_allowed": bool(source_changed and safe and not already_applied),
        "candidate_already_present": already_applied,
        "mixed_known_state": mixed_known,
        "selected_project_modified_by_inspection": False,
        "content_minimized": True,
        **DENIED_AUTHORITY,
    }
    row["conflict_inspection_digest"] = _digest(row)
    return row


def _application_authorization_phrase(request_id: str, application_digest: str) -> str:
    return f"Authorize controlled application for request {request_id} packet {application_digest}."


def prepare_controlled_application(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    path = _application_path(request_id, runtime_root)
    with _proposal_lock(request_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "application_request_record_digest"):
                return {"ok": False, "status": "controlled_application_request_invalid", "request_id": request_id, **DENIED_AUTHORITY}
            # A prepared packet is immutable.  Re-evaluate conflicts separately at
            # execution time rather than silently rewriting its authority binding.
            return {**existing, "operation_status": "restored"}

        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
        execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
        review = load_isolated_coding_review(request_id, runtime_root=runtime_root)
        workspace = _read_json(_workspace_record_path(request_id, runtime_root))
        conflicts = inspect_controlled_application_conflicts(request_id, runtime_root=runtime_root)
        if not request or not inspection or not execution or not review or not workspace:
            return {"ok": False, "status": "controlled_application_lineage_missing", "request_id": request_id, **DENIED_AUTHORITY}
        if request.get("cancelled"):
            return {"ok": False, "status": "coding_work_request_cancelled", "request_id": request_id, **DENIED_AUTHORITY}
        if conflicts.get("ok") is not True or conflicts.get("candidate_already_present"):
            return {**conflicts, "ok": False}
        result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
        try:
            changes = _candidate_change_entries(review=review, inspection=inspection, workspace=workspace)
        except (OSError, ValueError) as exc:
            return {"ok": False, "status": "controlled_application_candidate_invalid", "reason": str(exc), "request_id": request_id, **DENIED_AUTHORITY}

        candidate_manifest_digest = _digest(changes)
        bindings = {
            "request_digest": request.get("request_digest", ""),
            "inspection_digest": inspection.get("inspection_digest", ""),
            "source_manifest_digest": inspection.get("source_manifest_digest", ""),
            "execution_digest": execution.get("execution_digest", ""),
            "execution_result_digest": result.get("execution_result_digest", ""),
            "review_record_digest": review.get("review_record_digest", ""),
            "diff_digest": review.get("diff_digest", ""),
            "workspace_manifest_digest": review.get("workspace_manifest_digest", ""),
            "candidate_manifest_digest": candidate_manifest_digest,
        }
        application_digest = _digest({"request_id": request_id, "bindings": bindings, "changes": changes})
        record = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "controlled_application_authorization_required",
            "phase": "prepared",
            "request_id": request_id,
            "application_digest": application_digest,
            "authorization_phrase": _application_authorization_phrase(request_id, application_digest),
            "bindings": bindings,
            "changes": changes,
            "change_count": len(changes),
            "candidate_manifest_digest": candidate_manifest_digest,
            "conflict_inspection_digest": conflicts.get("conflict_inspection_digest", ""),
            "source_manifest_changed": bool(conflicts.get("source_manifest_changed")),
            "unrelated_source_changes_allowed": bool(conflicts.get("unrelated_source_changes_allowed")),
            "backup_required_before_first_write": True,
            "rollback_required_on_partial_failure": True,
            "rollback_requires_separate_authorization_after_success": True,
            "post_apply_verification_required": True,
            "operator_review_required": True,
            "selected_project_modified": False,
            "runtime_records_external": True,
            **DENIED_AUTHORITY,
        }
        record = _sealed(record, "application_request_record_digest")
        _atomic_json(path, record)

        backup_scope = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "controlled_application_backup_scope_ready",
            "request_id": request_id,
            "application_digest": application_digest,
            "entry_count": len(changes),
            "entries": [
                {
                    "relative_path_digest": row["relative_path_digest"],
                    "baseline_existed": row["baseline_existed"],
                    "baseline_content_digest": row["baseline_content_digest"],
                    "candidate_content_digest": row["candidate_content_digest"],
                    "operation": row["operation"],
                }
                for row in changes
            ],
            "private_contents_captured": False,
            "capture_timing": "immediately_before_first_authorized_write",
            "selected_project_modified": False,
            **DENIED_AUTHORITY,
        }
        backup_scope = _sealed(backup_scope, "backup_scope_digest")
        _atomic_json(_backup_scope_path(request_id, runtime_root), backup_scope)
        return {**record, "operation_status": "created"}


def load_controlled_application(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    row = _read_json(_application_path(request_id, runtime_root))
    return row if row and _valid(row, "application_request_record_digest") else {}


def load_controlled_application_backup_scope(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _request_id(request_id)
    row = _read_json(_backup_scope_path(request_id, runtime_root))
    return row if row and _valid(row, "backup_scope_digest") else {}


def build_private_backup_manifest(
    request_id: str,
    application: Mapping[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    """Capture exactly the application scope; caller persists it externally.

    This helper is intentionally private-data bearing.  Public projections must
    never return ``entries[*].content_b64`` or the selected-project path.
    """
    entries: list[dict[str, Any]] = []
    total = 0
    for change in application.get("changes") or []:
        relative = _safe_relative(str(change.get("relative_path") or ""))
        target = project_root / Path(*PurePosixPath(relative).parts)
        if not _within(project_root, target):
            raise ValueError("backup_scope_escape")
        if target.exists() and (_is_link_like(target) or not target.is_file()):
            raise ValueError("backup_scope_link_or_nonfile_rejected")
        existed = target.is_file()
        content = target.read_bytes() if existed else b""
        total += len(content)
        if total > MAX_BACKUP_BYTES:
            raise ValueError("backup_byte_limit_exceeded")
        digest = hashlib.sha256(content).hexdigest() if existed else ""
        entries.append({
            "relative_path": relative,
            "relative_path_digest": _path_digest(relative),
            "existed": existed,
            "content_digest": digest,
            "size_bytes": len(content),
            "content_b64": base64.b64encode(content).decode("ascii") if existed else "",
        })
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "controlled_application_private_backup_ready",
        "request_id": request_id,
        "application_digest": str(application.get("application_digest") or ""),
        "entry_count": len(entries),
        "entries": entries,
        "total_bytes": total,
        "private_runtime_record": True,
        "selected_project_path_stored": False,
    }
    return _sealed(manifest, "backup_manifest_digest")


def validate_private_backup_manifest(manifest: Mapping[str, Any], *, expected_application_digest: str = "") -> bool:
    if not manifest or not _valid(manifest, "backup_manifest_digest"):
        return False
    if expected_application_digest and str(manifest.get("application_digest") or "") != expected_application_digest:
        return False
    entries = list(manifest.get("entries") or [])
    if len(entries) != int(manifest.get("entry_count") or -1) or len(entries) > MAX_APPLICATION_FILES:
        return False
    seen: set[str] = set()
    total = 0
    try:
        for row in entries:
            relative = _safe_relative(str(row.get("relative_path") or ""))
            if relative.casefold() in seen:
                return False
            seen.add(relative.casefold())
            if str(row.get("relative_path_digest") or "") != _path_digest(relative):
                return False
            existed = bool(row.get("existed"))
            if existed:
                content = base64.b64decode(str(row.get("content_b64") or ""), validate=True)
                total += len(content)
                if len(content) != int(row.get("size_bytes") or -1):
                    return False
                if hashlib.sha256(content).hexdigest() != str(row.get("content_digest") or ""):
                    return False
            elif row.get("content_b64") or row.get("content_digest") or int(row.get("size_bytes") or 0):
                return False
    except Exception:
        return False
    return total <= MAX_BACKUP_BYTES and total == int(manifest.get("total_bytes") or 0)


def public_controlled_application(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "phase": str(record.get("phase") or ""),
        "request_id": str(record.get("request_id") or ""),
        "application_digest": str(record.get("application_digest") or ""),
        "authorization_phrase": str(record.get("authorization_phrase") or "") if record.get("phase") == "prepared" else "",
        "change_count": int(record.get("change_count") or 0),
        "source_manifest_changed": bool(record.get("source_manifest_changed")),
        "unrelated_source_changes_allowed": bool(record.get("unrelated_source_changes_allowed")),
        "backup_required_before_first_write": bool(record.get("backup_required_before_first_write", True)),
        "post_apply_verification_required": bool(record.get("post_apply_verification_required", True)),
        "operator_review_required": True,
        "selected_project_modified": bool(record.get("selected_project_modified", False)),
        "private_project_path_exposed": False,
        "backup_content_exposed": False,
        "raw_test_output_exposed": False,
        **DENIED_AUTHORITY,
    }


__all__ = [
    "CONTRACT_VERSION",
    "DENIED_AUTHORITY",
    "prepare_controlled_application",
    "inspect_controlled_application_conflicts",
    "load_controlled_application",
    "load_controlled_application_backup_scope",
    "build_private_backup_manifest",
    "validate_private_backup_manifest",
    "public_controlled_application",
]
