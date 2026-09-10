from __future__ import annotations

"""v1255.6-v1255.8 reliability, recovery inspection, and operator handoff."""

import time
from pathlib import Path
from typing import Any, Mapping

from controlled_application_rollback_foundations import (
    DENIED_AUTHORITY,
    inspect_controlled_application_conflicts,
    load_controlled_application,
    public_controlled_application,
    validate_private_backup_manifest,
)
from controlled_application_rollback import (
    _application_scope_states,
    _backup_manifest_path,
    _execution_path,
    _journal_path,
    _rollback_journal_path,
    _valid_journal,
    load_controlled_application_execution,
    load_controlled_rollback,
    load_controlled_rollback_result,
    public_controlled_application_result,
    public_controlled_rollback,
)
from isolated_coding_execution_foundations import _resolve_project_root, load_coding_work_request
from ordinary_chat_development_campaign import _digest, _read_json

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1255.8"


def inspect_controlled_application_health(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    application = load_controlled_application(request_id, runtime_root=runtime_root)
    execution = load_controlled_application_execution(request_id, runtime_root=runtime_root)
    rollback = load_controlled_rollback(request_id, runtime_root=runtime_root)
    rollback_result = load_controlled_rollback_result(request_id, runtime_root=runtime_root)
    backup = _read_json(_backup_manifest_path(request_id, runtime_root))
    apply_journal = _read_json(_journal_path(request_id, runtime_root))
    rollback_journal = _read_json(_rollback_journal_path(request_id, runtime_root))
    request = load_coding_work_request(request_id, runtime_root=runtime_root)
    errors: list[str] = []
    if not application:
        errors.append("application_packet_missing_or_invalid")
    if execution and str(execution.get("application_digest") or "") != str(application.get("application_digest") or ""):
        errors.append("execution_application_binding_invalid")
    backup_valid = bool(backup and validate_private_backup_manifest(backup, expected_application_digest=str(application.get("application_digest") or "")))
    if backup and not backup_valid:
        errors.append("backup_manifest_invalid")
    if apply_journal and not _valid_journal(apply_journal):
        errors.append("apply_journal_invalid")
    if rollback_journal and not _valid_journal(rollback_journal):
        errors.append("rollback_journal_invalid")

    path_states: list[str] = []
    target_state = "unavailable"
    if request and application:
        try:
            root = _resolve_project_root((request.get("target") or {}).get("private_path") or "")
            states = _application_scope_states(root, application)
            path_states = [str(row.get("state") or "") for row in states]
            if states and all(value == "baseline" for value in path_states):
                target_state = "baseline"
            elif states and all(value == "candidate" for value in path_states):
                target_state = "candidate"
            elif states and all(value in {"baseline", "candidate"} for value in path_states):
                target_state = "known_partial"
            else:
                target_state = "conflict"
        except Exception:
            target_state = "unavailable"
    if target_state == "conflict":
        errors.append("selected_project_conflict")

    phase = str(execution.get("phase") or "")
    lease_active = bool(phase == "running" and float(execution.get("lease_expires_unix") or 0.0) > time.time())
    lease_expired = bool(phase == "running" and not lease_active)
    if phase == "running" and not backup_valid and target_state != "baseline":
        errors.append("running_application_without_valid_backup")

    if rollback_result:
        recovery = "rollback_terminal"
    elif rollback:
        recovery = "rollback_exact_authorization_required" if target_state == "candidate" else "rollback_conflict_review_required"
    elif phase == "sealed":
        result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
        recovery = "rollback_available" if result.get("ok") and target_state == "candidate" else "application_terminal_review"
    elif lease_active:
        recovery = "application_in_progress_do_not_duplicate"
    elif lease_expired and target_state in {"baseline", "candidate", "known_partial"} and backup_valid:
        recovery = "same_exact_application_authorization_may_recover"
    elif application:
        recovery = "exact_application_authorization_required"
    else:
        recovery = "manual_review_required"

    row = {
        "ok": not errors,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "controlled_application_health_ok" if not errors else "controlled_application_health_attention_required",
        "request_id": request_id,
        "application_present": bool(application),
        "execution_present": bool(execution),
        "backup_present": bool(backup),
        "backup_valid": backup_valid,
        "rollback_present": bool(rollback),
        "rollback_result_present": bool(rollback_result),
        "target_state": target_state,
        "path_state_count": len(path_states),
        "lease_active": lease_active,
        "lease_expired": lease_expired,
        "recovery_disposition": recovery,
        "errors": errors,
        "read_only": True,
        "selected_project_modified_by_inspection": False,
        "provider_contacted_by_inspection": False,
        "tests_executed_by_inspection": False,
        "private_project_path_exposed": False,
        **DENIED_AUTHORITY,
    }
    row["health_digest"] = _digest(row)
    return row


def build_controlled_application_operator_handoff(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    application = load_controlled_application(request_id, runtime_root=runtime_root)
    execution = load_controlled_application_execution(request_id, runtime_root=runtime_root)
    rollback = load_controlled_rollback(request_id, runtime_root=runtime_root)
    rollback_result = load_controlled_rollback_result(request_id, runtime_root=runtime_root)
    health = inspect_controlled_application_health(request_id, runtime_root=runtime_root)
    if not application:
        return {"ok": False, "status": "controlled_application_handoff_unavailable", "request_id": request_id, **DENIED_AUTHORITY}
    public_execution = public_controlled_application_result(execution) if execution else {}
    public_rollback = public_controlled_rollback(rollback_result or rollback) if (rollback_result or rollback) else {}
    limitations = [
        "Application authority is exact, one-time, and separate from the v1254 isolated execution authorization.",
        "Only reviewed candidate paths may be changed; unrelated operator edits are preserved.",
        "Rollback after a successful application requires a separate exact authorization.",
        "Provider contact, dependency installation, promotion, release, permanent approval, and independent authority remain denied.",
    ]
    if health.get("target_state") == "conflict":
        limitations.append("An affected selected-project path no longer matches either the sealed baseline or candidate; automatic mutation is blocked.")
    row = {
        "ok": bool(health.get("ok")),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "controlled_application_operator_handoff_ready",
        "request_id": request_id,
        "application": public_controlled_application(application),
        "application_result": public_execution,
        "rollback": public_rollback,
        "health": {
            "status": health.get("status"),
            "target_state": health.get("target_state"),
            "backup_valid": health.get("backup_valid"),
            "recovery_disposition": health.get("recovery_disposition"),
            "health_digest": health.get("health_digest"),
        },
        "limitations": limitations,
        "operator_review_required": True,
        "private_project_path_exposed": False,
        "backup_content_exposed": False,
        "raw_test_output_exposed": False,
        **DENIED_AUTHORITY,
    }
    row["handoff_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "inspect_controlled_application_health", "build_controlled_application_operator_handoff"]
