from __future__ import annotations

"""v1256.0-v1256.2 persistent development-session foundations.

This layer consolidates the *current* v1254/v1255 development lineage into a
restart-safe session record.  It persists references, digests, bounded attempt
and verification evidence, blockers, completion markers, and next-step state.
It never starts or retries provider work, runs commands/tests, applies a
candidate, rolls a project back, or reuses prior authority.
"""

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from isolated_coding_execution_foundations import (
    _valid as _valid_foundation_record,
    check_coding_source_freshness,
    load_coding_project_inspection,
    load_coding_work_plan,
    load_coding_work_request,
)
from isolated_coding_execution import load_isolated_coding_execution, load_isolated_coding_review
from controlled_application_rollback_foundations import load_controlled_application, inspect_controlled_application_conflicts
from controlled_application_rollback import (
    load_controlled_application_execution,
    load_controlled_rollback,
    load_controlled_rollback_result,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1256.2"
REQUEST_RE = re.compile(r"^devc_[a-f0-9]{24}$")
SESSION_RE = re.compile(r"^devs_[a-f0-9]{24}$")
MAX_ATTEMPTS = 16
MAX_BLOCKERS = 32
MAX_COMPLETED = 32

DENIED_AUTHORITY = {
    "automatic_resume_authorized": False,
    "duplicate_execution_authorized": False,
    "implementation_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "provider_contact_authorized": False,
    "dependency_installation_authorized": False,
    "selected_project_mutation_authorized": False,
    "source_application_authorized": False,
    "rollback_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}


def _session_dir(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "persistent_development_sessions"


def _session_index_dir(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "persistent_development_session_indexes"


def _session_path_for_request(request_id: str, runtime_root=None) -> Path:
    return _session_dir(runtime_root) / f"{request_id}.json"


def _index_path(session_id: str, runtime_root=None) -> Path:
    return _session_index_dir(runtime_root) / f"{session_id}.json"


def _workspace_record_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "coding_workspace_records" / f"{request_id}.json"


def _attempt_dir(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "isolated_coding_execution_attempts" / request_id


def _validate_request_id(request_id: str) -> str:
    value = str(request_id or "").lower()
    if not REQUEST_RE.fullmatch(value):
        raise ValueError("invalid_development_request_id")
    return value


def _validate_session_id(session_id: str) -> str:
    value = str(session_id or "").lower()
    if not SESSION_RE.fullmatch(value):
        raise ValueError("invalid_development_session_id")
    return value


def _sealed(record: Mapping[str, Any], field: str = "session_digest") -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str = "session_digest") -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _session_id(request_id: str, request_digest: str) -> str:
    return "devs_" + _digest({"request_id": request_id, "request_digest": request_digest, "purpose": "persistent_development_session"})[:24]


def _digest_list(value: Any) -> str:
    return _digest(list(value or []))


def _workspace_record(request_id: str, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_workspace_record_path(request_id, runtime_root))
    if row and _valid_foundation_record(row, "workspace_record_digest"):
        return row
    return {}


def _attempt_evidence(request_id: str, runtime_root=None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    root = _attempt_dir(request_id, runtime_root)
    if not root.is_dir():
        return rows
    for path in sorted(root.glob("attempt-*.json")):
        record = _read_json(path)
        if not record:
            continue
        digest = str(record.get("attempt_record_digest") or "")
        if not digest or digest != _digest({k: v for k, v in record.items() if k != "attempt_record_digest"}):
            continue
        verification = dict(record.get("verification") or {})
        diagnostic = _read_json(_store_root(runtime_root) / "diagnostic_repair_results" / request_id / f"attempt-{int(record.get('attempt_number') or 0)}.json")
        diagnostic_digest = str(diagnostic.get("diagnostic_result_digest") or "") if diagnostic else ""
        if diagnostic_digest and diagnostic_digest != _digest({k: v for k, v in diagnostic.items() if k != "diagnostic_result_digest"}):
            diagnostic = {}
            diagnostic_digest = ""
        rows.append({
            "attempt_number": int(record.get("attempt_number") or 0),
            "status": str(record.get("status") or ""),
            "attempt_digest": digest,
            "mode": str(record.get("mode") or ""),
            "change_count": int(record.get("change_count") or len(record.get("changes") or [])),
            "verification_digest": str(verification.get("verification_digest") or ""),
            "verification_status": str(verification.get("status") or ""),
            "tests_executed": bool(verification.get("tests_executed")),
            "passed": verification.get("passed") if isinstance(verification.get("passed"), bool) else None,
            "cleanup_confirmed": verification.get("cleanup_confirmed") if isinstance(verification.get("cleanup_confirmed"), bool) else None,
            "diagnostic_result_digest": diagnostic_digest,
            "diagnostic_repair_posture": str(diagnostic.get("repair_posture") or "") if diagnostic else "",
            "diagnostic_preferred_hypothesis": str(diagnostic.get("preferred_hypothesis_code") or "") if diagnostic else "",
        })
        if len(rows) >= MAX_ATTEMPTS:
            break
    return rows


def _artifact_refs(request_id: str, runtime_root=None) -> dict[str, str]:
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
    workspace = _workspace_record(request_id, runtime_root=runtime_root)
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    review = load_isolated_coding_review(request_id, runtime_root=runtime_root)
    application = load_controlled_application(request_id, runtime_root=runtime_root)
    application_execution = load_controlled_application_execution(request_id, runtime_root=runtime_root)
    rollback = load_controlled_rollback(request_id, runtime_root=runtime_root)
    rollback_result = load_controlled_rollback_result(request_id, runtime_root=runtime_root)
    return {
        "request_digest": str(request.get("record_digest") or ""),
        "request_contract_digest": str(request.get("request_digest") or ""),
        "inspection_digest": str(inspection.get("inspection_digest") or ""),
        "plan_digest": str(plan.get("plan_digest") or ""),
        "workspace_digest": str(workspace.get("workspace_record_digest") or ""),
        "execution_digest": str(execution.get("execution_record_digest") or ""),
        "review_digest": str(review.get("review_record_digest") or ""),
        "application_digest": str(application.get("application_record_digest") or ""),
        "application_execution_digest": str(application_execution.get("execution_record_digest") or application_execution.get("application_result_digest") or ""),
        "rollback_digest": str(rollback.get("rollback_record_digest") or ""),
        "rollback_result_digest": str(rollback_result.get("rollback_result_digest") or ""),
    }


def _derive_phase(request_id: str, runtime_root=None) -> tuple[str, list[str], list[str], str]:
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    inspection = load_coding_project_inspection(request_id, runtime_root=runtime_root)
    plan = load_coding_work_plan(request_id, runtime_root=runtime_root)
    workspace = _workspace_record(request_id, runtime_root=runtime_root)
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    review = load_isolated_coding_review(request_id, runtime_root=runtime_root)
    application = load_controlled_application(request_id, runtime_root=runtime_root)
    app_result = load_controlled_application_execution(request_id, runtime_root=runtime_root)
    rollback = load_controlled_rollback(request_id, runtime_root=runtime_root)
    rollback_result = load_controlled_rollback_result(request_id, runtime_root=runtime_root)

    blockers: list[str] = []
    completed: list[str] = []
    next_action = ""
    if not request:
        return "blocked", ["coding_work_request_missing_or_tampered"], completed, "restore_or_recreate_request"
    if request.get("cancelled"):
        return "cancelled", blockers, ["request_cancelled"], "none"
    completed.append("requirements_recorded")
    if inspection:
        completed.append("project_inspected")
    else:
        return "request_ready", blockers, completed, "inspect_project"
    if plan:
        completed.append("plan_recorded")
    else:
        return "inspection_ready", blockers, completed, "create_plan"
    if workspace:
        completed.append("isolated_workspace_materialized")
    else:
        freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
        if not freshness.get("ok"):
            blockers.append(str(freshness.get("status") or "source_not_fresh"))
            return "blocked", blockers, completed, "operator_reconcile_source"
        return "plan_ready", blockers, completed, "materialize_isolated_workspace"

    if execution:
        phase = str(execution.get("phase") or "")
        result = execution.get("result") if isinstance(execution.get("result"), Mapping) else execution
        status = str(result.get("status") or execution.get("status") or "")
        if phase == "prepared":
            freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
            if freshness.get("ok") is not True:
                blockers.append(str(freshness.get("status") or "stale_source_detected"))
                return "blocked", blockers, completed, "operator_reconcile_source"
            return "execution_authorization_required", blockers, completed, "authorize_existing_isolated_execution"
        if phase == "running":
            if float(execution.get("lease_expires_unix") or 0.0) <= time.time():
                return "execution_recovery_required", blockers, completed, "recover_existing_isolated_execution"
            return "execution_in_progress", blockers, completed, "wait_for_existing_execution"
        if status == "isolated_coding_execution_completed":
            completed.append("isolated_execution_completed")
        elif status:
            blockers.append(status)
            return "blocked", blockers, completed, "review_execution_failure"
    else:
        freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
        if freshness.get("ok") is not True:
            blockers.append(str(freshness.get("status") or "stale_source_detected"))
            return "blocked", blockers, completed, "operator_reconcile_source"
        return "workspace_ready", blockers, completed, "prepare_isolated_execution"

    if review:
        completed.append("operator_review_artifact_ready")
    if app_result and str(app_result.get("phase") or "") == "running":
        if float(app_result.get("lease_expires_unix") or 0.0) <= time.time():
            return "application_recovery_required", blockers, completed, "recover_existing_controlled_application"
        return "application_in_progress", blockers, completed, "wait_for_existing_application"
    if rollback_result and rollback_result.get("ok") is True:
        if app_result and app_result.get("ok") is True:
            completed.append("controlled_application_completed")
        completed.append("controlled_rollback_completed")
        return "rolled_back", blockers, completed, "none"
    if rollback:
        if app_result and app_result.get("ok") is True:
            completed.append("controlled_application_completed")
        return "rollback_authorization_required", blockers, completed, "authorize_existing_rollback"
    if app_result:
        status = str(app_result.get("status") or "")
        if status in {"controlled_application_completed", "controlled_application_completed_recovered"} or app_result.get("ok") is True:
            completed.append("controlled_application_completed")
            return "completed", blockers, completed, "none"
        if "verification_failed" in status or "failed" in status:
            blockers.append(status)
            return "blocked", blockers, completed, "review_application_failure"
    if application:
        conflicts = inspect_controlled_application_conflicts(request_id, runtime_root=runtime_root)
        if conflicts.get("ok") is not True:
            blockers.append(str(conflicts.get("status") or "controlled_application_conflict_detected"))
            return "blocked", blockers, completed, "operator_reconcile_application_conflict"
        return "application_authorization_required", blockers, completed, "authorize_existing_application"
    return "review_ready", blockers, completed, "prepare_controlled_application"


def build_persistent_development_session_snapshot(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _validate_request_id(request_id)
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    if not request:
        return {"ok": False, "status": "persistent_session_request_missing_or_tampered", "request_id": request_id, **DENIED_AUTHORITY}
    refs = _artifact_refs(request_id, runtime_root=runtime_root)
    phase, blockers, completed, next_action = _derive_phase(request_id, runtime_root=runtime_root)
    attempts = _attempt_evidence(request_id, runtime_root=runtime_root)
    snapshot = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "request_id": request_id,
        "request_contract_digest": str(request.get("request_digest") or ""),
        "requirements_digest": _digest_list(request.get("requirements")),
        "acceptance_criteria_digest": _digest_list(request.get("acceptance_criteria")),
        "constraints_digest": _digest_list(request.get("constraints")),
        "prohibited_actions_digest": _digest_list(request.get("prohibited_actions")),
        "expected_artifacts_digest": _digest_list(request.get("expected_artifacts")),
        "verification_requirements_digest": _digest_list(request.get("verification")),
        "artifact_refs": refs,
        "attempt_evidence": attempts,
        "attempt_count": len(attempts),
        "blockers": blockers[:MAX_BLOCKERS],
        "completed_work": completed[:MAX_COMPLETED],
        "phase": phase,
        "next_action": next_action,
        "content_minimized": True,
        "private_project_path_stored": False,
        "private_content_stored": False,
        "raw_provider_output_stored": False,
        "raw_test_output_stored": False,
        **DENIED_AUTHORITY,
    }
    snapshot["snapshot_digest"] = _digest(snapshot)
    return snapshot


def create_or_restore_persistent_development_session(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = _validate_request_id(request_id)
    with _proposal_lock(request_id, runtime_root):
        request = load_coding_work_request(request_id, runtime_root=runtime_root)
        if not request:
            return {"ok": False, "status": "persistent_session_request_missing_or_tampered", "request_id": request_id, **DENIED_AUTHORITY}
        session_id = _session_id(request_id, str(request.get("request_digest") or ""))
        path = _session_path_for_request(request_id, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing) or existing.get("session_id") != session_id:
                return {"ok": False, "status": "persistent_session_record_invalid", "request_id": request_id, "session_id": session_id, **DENIED_AUTHORITY}
            return {**existing, "operation_status": "restored"}
        snapshot = build_persistent_development_session_snapshot(request_id, runtime_root=runtime_root)
        if not snapshot.get("ok"):
            return snapshot
        record = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "persistent_development_session_ready",
            "session_id": session_id,
            "request_id": request_id,
            "request_contract_digest": str(request.get("request_digest") or ""),
            "generation": 1,
            "prior_session_digest": "",
            "snapshot": snapshot,
            "snapshot_digest": snapshot["snapshot_digest"],
            "phase": snapshot["phase"],
            "next_action": snapshot["next_action"],
            "attempt_count": snapshot["attempt_count"],
            "blocker_count": len(snapshot["blockers"]),
            "completed_work_count": len(snapshot["completed_work"]),
            "cancelled": snapshot["phase"] == "cancelled",
            "content_minimized": True,
            "restart_safe": True,
            "duplicate_request_idempotent": True,
            "authority_reuse_forbidden": True,
            **DENIED_AUTHORITY,
        }
        record = _sealed(record)
        _atomic_json(path, record)
        index = _sealed({
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "session_id": session_id,
            "request_id": request_id,
            "request_contract_digest": str(request.get("request_digest") or ""),
            "content_minimized": True,
        }, "index_digest")
        _atomic_json(_index_path(session_id, runtime_root), index)
        return {**record, "operation_status": "created"}


def load_persistent_development_session(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    session_id = _validate_session_id(session_id)
    index = _read_json(_index_path(session_id, runtime_root))
    if not index or not _valid(index, "index_digest") or index.get("session_id") != session_id:
        return {}
    request_id = str(index.get("request_id") or "")
    if not REQUEST_RE.fullmatch(request_id):
        return {}
    record = _read_json(_session_path_for_request(request_id, runtime_root))
    if not record or not _valid(record) or record.get("session_id") != session_id:
        return {}
    return record


def refresh_persistent_development_session(session_id: str, *, runtime_root=None) -> dict[str, Any]:
    session_id = _validate_session_id(session_id)
    current = load_persistent_development_session(session_id, runtime_root=runtime_root)
    if not current:
        return {"ok": False, "status": "persistent_session_missing_or_tampered", "session_id": session_id, **DENIED_AUTHORITY}
    request_id = str(current.get("request_id") or "")
    with _proposal_lock(request_id, runtime_root):
        current = load_persistent_development_session(session_id, runtime_root=runtime_root)
        snapshot = build_persistent_development_session_snapshot(request_id, runtime_root=runtime_root)
        if not snapshot.get("ok"):
            return snapshot
        if snapshot["snapshot_digest"] == current.get("snapshot_digest"):
            return {**current, "operation_status": "restored"}
        updated = dict(current)
        updated.pop("session_digest", None)
        updated.update({
            "status": "persistent_development_session_refreshed",
            "generation": int(current.get("generation") or 1) + 1,
            "prior_session_digest": str(current.get("session_digest") or ""),
            "snapshot": snapshot,
            "snapshot_digest": snapshot["snapshot_digest"],
            "phase": snapshot["phase"],
            "next_action": snapshot["next_action"],
            "attempt_count": snapshot["attempt_count"],
            "blocker_count": len(snapshot["blockers"]),
            "completed_work_count": len(snapshot["completed_work"]),
            "cancelled": snapshot["phase"] == "cancelled",
            **DENIED_AUTHORITY,
        })
        updated = _sealed(updated)
        _atomic_json(_session_path_for_request(request_id, runtime_root), updated)
        return {**updated, "operation_status": "updated"}


def public_persistent_development_session(record: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = dict(record.get("snapshot") or {})
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "session_id": str(record.get("session_id") or ""),
        "request_id": str(record.get("request_id") or ""),
        "generation": int(record.get("generation") or 0),
        "phase": str(record.get("phase") or ""),
        "next_action": str(record.get("next_action") or ""),
        "attempt_count": int(record.get("attempt_count") or 0),
        "blocker_count": int(record.get("blocker_count") or 0),
        "completed_work_count": int(record.get("completed_work_count") or 0),
        "blockers": list(snapshot.get("blockers") or []),
        "completed_work": list(snapshot.get("completed_work") or []),
        "attempt_evidence": list(snapshot.get("attempt_evidence") or []),
        "requirements_preserved": bool(snapshot.get("requirements_digest")),
        "plan_preserved": bool((snapshot.get("artifact_refs") or {}).get("plan_digest")),
        "verification_evidence_preserved": any(bool(row.get("verification_digest")) for row in snapshot.get("attempt_evidence") or []),
        "restart_safe": bool(record.get("restart_safe")),
        "content_minimized": True,
        "private_project_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **DENIED_AUTHORITY,
    }


__all__ = [
    "CONTRACT_VERSION", "DENIED_AUTHORITY", "build_persistent_development_session_snapshot",
    "create_or_restore_persistent_development_session", "load_persistent_development_session",
    "refresh_persistent_development_session", "public_persistent_development_session",
]
