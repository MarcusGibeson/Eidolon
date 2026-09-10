from __future__ import annotations

"""Content-free crash and orphan recovery for process-owned operations."""

import hashlib
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any

try:
    from json_storage import load_json_file
    from metadata_mutation_coordination import metadata_mutation_lock
    from process_ownership import TERMINAL_STATES, finalize_process_operation, inspect_process_operation, load_private_process_operation, ownership_path, write_process_result, process_is_alive, result_path, results_root, ownership_root
except ImportError:
    from json_storage import load_json_file
    from metadata_mutation_coordination import metadata_mutation_lock
    from process_ownership import (
        TERMINAL_STATES,
        finalize_process_operation,
        inspect_process_operation,
        load_private_process_operation,
        ownership_path,
        write_process_result,
        process_is_alive,
        result_path,
        results_root,
        ownership_root,
    )

SCHEMA_VERSION = "4"


_PUBLIC_RECOVERY_FIELDS = {
    "ok", "schema_version", "operation_id", "operation_kind", "generation", "status", "state",
    "owner_active", "owner_dead", "owner_liveness_unknown", "child_active",
    "child_identity_mismatch_or_dead", "child_liveness_unknown", "cancellation_requested",
    "cancellation_available", "force_termination_available", "bound_to_project",
    "bound_to_session", "bound_to_tab", "tab_revision", "may_mutate", "safe_retry",
    "uncertain_result", "accepted_at", "updated_at", "content_free", "context_matches",
    "read_only_reattached", "control_context_matches", "project_mismatch",
    "session_mismatch", "stale_tab", "replay_allowed", "result_bound", "applied",
    "recovery_required", "operator_confirmation_required", "orphan_terminated",
    "restart_restored", "result_after_cancel", "cancellation_phase", "retry_reason",
    "stale_request", "force_terminated", "duplicate",
}

def _content_free_recovery_row(row: dict[str, Any]) -> dict[str, Any]:
    public = {key: row[key] for key in _PUBLIC_RECOVERY_FIELDS if key in row}
    public["schema_version"] = SCHEMA_VERSION
    public["content_free"] = True
    public["private_process_details_returned"] = False
    public["command_returned"] = False
    public["environment_returned"] = False
    public["paths_returned"] = False
    return public


def _load_result(operation_id: str) -> dict[str, Any] | None:
    return load_json_file(result_path(operation_id), None, expected_type=dict)


def _result_matches(record: dict[str, Any], result: dict[str, Any] | None) -> bool:
    if not result:
        return False
    expected_nonce_digest = hashlib.sha256(str(record.get("owner_nonce") or "").encode("utf-8")).hexdigest()
    return bool(
        str(result.get("operation_id") or "") == str(record.get("operation_id") or "")
        and int(result.get("generation") or 0) == int(record.get("generation") or 0)
        and str(result.get("owner_nonce_digest") or "") == expected_nonce_digest
        and str(result.get("state") or "") in TERMINAL_STATES
    )


def _terminate_exact_child(record: dict[str, Any]) -> bool:
    pid = int(record.get("child_pid") or 0)
    identity = str(record.get("child_start_identity") or "")
    if pid <= 0 or not identity or process_is_alive(pid, identity) is not True:
        return False
    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
            return completed.returncode == 0 or process_is_alive(pid, identity) is False
        except Exception:
            return False
    group_id = int(record.get("child_process_group_id") or 0)
    try:
        if group_id > 0:
            os.killpg(group_id, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        return False
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if process_is_alive(pid, identity) is False:
            return True
        time.sleep(0.02)
    try:
        if group_id > 0:
            os.killpg(group_id, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        return False
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if process_is_alive(pid, identity) is False:
            return True
        time.sleep(0.02)
    return process_is_alive(pid, identity) is False


def reconcile_process_operation(operation_id: str, *, terminate_orphan: bool = False) -> dict[str, Any]:
    record = load_private_process_operation(operation_id)
    if not record:
        return {"ok": False, "status": "not_found", "operation_id": str(operation_id), "content_free": True}
    public = inspect_process_operation(operation_id)
    state = str(record.get("state") or "missing")
    if state in TERMINAL_STATES:
        return {**public, "ok": True, "status": state, "replay_allowed": False, "result_bound": bool(_result_matches(record, _load_result(operation_id)))}
    if public.get("owner_active"):
        live_status = "cancellation_requested" if record.get("cancellation_requested") is True else str(record.get("state") or "running")
        return {**public, "ok": True, "status": live_status, "replay_allowed": False, "safe_retry": False}
    result = _load_result(operation_id)
    if _result_matches(record, result):
        terminal = str(result.get("state") or "uncertain")
        nonce = str(record.get("owner_nonce") or "")
        finalized = finalize_process_operation(
            operation_id,
            int(record.get("generation") or 0),
            nonce,
            state=terminal,
        )
        return {
            **finalized,
            "ok": terminal != "uncertain",
            "status": terminal,
            "result_bound": True,
            "applied": bool(result.get("applied")),
            "replay_allowed": False,
            "safe_retry": terminal in {"failed", "cancelled", "interrupted"} and not bool(result.get("applied")),
        }
    child_alive = public.get("child_active") is True
    may_mutate = bool(record.get("may_mutate"))
    if child_alive:
        if terminate_orphan is not True:
            return {
                **public,
                "ok": False,
                "status": "orphan_running",
                "recovery_required": True,
                "operator_confirmation_required": True,
                "replay_allowed": False,
                "safe_retry": False,
            }
        terminated = _terminate_exact_child(record)
        if not terminated:
            return {**public, "ok": False, "status": "orphan_termination_uncertain", "replay_allowed": False, "safe_retry": False}
    terminal = "uncertain" if may_mutate else "interrupted"
    nonce = str(record.get("owner_nonce") or "")
    finalized = finalize_process_operation(
        operation_id,
        int(record.get("generation") or 0),
        nonce,
        state=terminal,
    )
    return {
        **finalized,
        "ok": False,
        "status": terminal,
        "result_bound": False,
        "replay_allowed": False,
        "safe_retry": terminal == "interrupted",
        "orphan_terminated": child_alive and terminate_orphan is True,
    }



def _request_context_matches(
    record: dict[str, Any], *, generation: int, project_id: str, session_id: str,
    tab_id: str, tab_revision: int,
) -> tuple[bool, str]:
    if int(record.get("generation") or 0) != int(generation):
        return False, "generation_mismatch"
    for field, expected in (("project_id", project_id), ("session_id", session_id), ("tab_id", tab_id)):
        stored = str(record.get(field) or "")
        if stored and stored != str(expected or ""):
            return False, f"{field}_mismatch"
    stored_revision = int(record.get("tab_revision") or 0)
    if stored_revision and stored_revision != int(tab_revision or 0):
        return False, "tab_revision_mismatch"
    return True, "match"


def cancel_process_operation_with_escalation(
    operation_id: str, *, generation: int, project_id: str = "", session_id: str = "",
    tab_id: str = "", tab_revision: int = 0, operator_confirmed: bool,
    force_termination_permitted: bool = False, cooperative_wait_seconds: float = 1.0,
) -> dict[str, Any]:
    """Request exact cancellation, wait boundedly, then escalate only if still exact and permitted."""
    try:
        from process_ownership import request_process_operation_cancellation_exact
    except ImportError:
        from process_ownership import request_process_operation_cancellation_exact
    requested = request_process_operation_cancellation_exact(
        operation_id, generation=generation, project_id=project_id, session_id=session_id,
        tab_id=tab_id, tab_revision=tab_revision, operator_confirmed=operator_confirmed,
    )
    if not requested.get("ok"):
        return _content_free_recovery_row(requested)
    deadline = time.monotonic() + max(0.0, min(float(cooperative_wait_seconds), 10.0))
    while time.monotonic() < deadline:
        state = reconcile_process_operation(operation_id, terminate_orphan=False)
        status = str(state.get("status") or "")
        if status in TERMINAL_STATES:
            record = load_private_process_operation(operation_id) or {}
            result = _load_result(operation_id) or {}
            after_cancel = bool(record.get("cancellation_requested_at") and result.get("persisted_at"))
            return _content_free_recovery_row({
                **state, "result_after_cancel": after_cancel,
                "cancellation_phase": "cooperative_complete",
                "safe_retry": bool(state.get("safe_retry")) and not bool(state.get("applied")),
            })
        time.sleep(0.02)
    if force_termination_permitted is not True:
        return _content_free_recovery_row({
            **inspect_process_operation_for_context(
                operation_id, project_id=project_id, session_id=session_id,
                tab_id=tab_id, tab_revision=tab_revision,
            ),
            "ok": False, "status": "cooperative_wait_expired",
            "cancellation_phase": "awaiting_force_permission", "safe_retry": False,
        })
    forced = force_cancel_process_operation(
        operation_id, generation=generation, project_id=project_id, session_id=session_id,
        tab_id=tab_id, tab_revision=tab_revision, operator_confirmed=operator_confirmed,
        force_termination_permitted=True,
    )
    return _content_free_recovery_row({**forced, "cancellation_phase": "force_escalated"})


def force_cancel_process_operation(
    operation_id: str, *, generation: int, project_id: str = "", session_id: str = "",
    tab_id: str = "", tab_revision: int = 0, operator_confirmed: bool,
    force_termination_permitted: bool,
) -> dict[str, Any]:
    if operator_confirmed is not True:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "confirmation_required"}
    if force_termination_permitted is not True:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "force_permission_required"}
    record = load_private_process_operation(operation_id)
    if not record:
        return {"ok": False, "status": "not_found", "operation_id": str(operation_id), "content_free": True}
    matched, reason = _request_context_matches(
        record, generation=generation, project_id=project_id, session_id=session_id,
        tab_id=tab_id, tab_revision=tab_revision,
    )
    if not matched:
        return {**inspect_process_operation(operation_id), "ok": False, "status": reason, "stale_request": True}
    if record.get("cancellation_requested") is not True:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "cooperative_cancellation_required"}
    expected_owner = hashlib.sha256(str(record.get("owner_nonce") or "").encode("utf-8")).hexdigest()
    expected_child = hashlib.sha256(str(record.get("child_start_identity") or "").encode("utf-8")).hexdigest()
    if str(record.get("cancellation_owner_nonce_digest") or "") != expected_owner or str(record.get("cancellation_child_identity_digest") or "") != expected_child:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "cancellation_identity_stale"}
    if str(record.get("state") or "") in TERMINAL_STATES:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "already_terminal"}
    child_alive = process_is_alive(int(record.get("child_pid") or 0), str(record.get("child_start_identity") or ""))
    if child_alive is None:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "child_liveness_unknown"}
    terminated = True if child_alive is False else _terminate_exact_child(record)
    if not terminated:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "force_termination_uncertain"}
    terminal = "uncertain" if bool(record.get("may_mutate")) else "cancelled"
    nonce = str(record.get("owner_nonce") or "")
    write_process_result(
        operation_id, generation=int(record.get("generation") or 0), owner_nonce=nonce,
        state=terminal, applied=False,
    )
    finalized = finalize_process_operation(
        operation_id, int(record.get("generation") or 0), nonce, state=terminal,
    )
    return {
        **finalized, "ok": terminal == "cancelled", "status": terminal,
        "force_terminated": child_alive is True, "safe_retry": terminal == "cancelled",
        "replay_allowed": False,
    }


def inspect_process_operation_for_context(
    operation_id: str, *, project_id: str = "", session_id: str = "", tab_id: str = "", tab_revision: int = 0,
) -> dict[str, Any]:
    record = load_private_process_operation(operation_id)
    if not record:
        return {"ok": False, "status": "not_found", "operation_id": str(operation_id), "content_free": True}
    state = reconcile_process_operation(operation_id, terminate_orphan=False)
    project_match = not str(record.get("project_id") or "") or str(record.get("project_id") or "") == str(project_id or "")
    session_match = not str(record.get("session_id") or "") or str(record.get("session_id") or "") == str(session_id or "")
    tab_match = not str(record.get("tab_id") or "") or str(record.get("tab_id") or "") == str(tab_id or "")
    revision_match = not int(record.get("tab_revision") or 0) or int(record.get("tab_revision") or 0) == int(tab_revision or 0)
    context_match = project_match and session_match
    exact_control_match = context_match and tab_match and revision_match
    active = str(state.get("status") or "") in {"accepted", "starting", "running", "cancellation_requested", "orphan_running"}
    return {
        **state,
        "ok": state.get("ok", True),
        "context_matches": context_match,
        "read_only_reattached": context_match and active,
        "control_context_matches": exact_control_match,
        "cancellation_available": bool(active and exact_control_match and str(state.get("status") or "") not in TERMINAL_STATES),
        "force_termination_available": bool(exact_control_match and state.get("child_active") and (state.get("owner_dead") or str(state.get("status") or "") == "orphan_running") and record.get("cancellation_requested") is True),
        "project_mismatch": not project_match,
        "session_mismatch": not session_match,
        "stale_tab": context_match and not (tab_match and revision_match),
        "replay_allowed": False,
        "content_free": True,
    }


def build_process_restart_state(
    *, project_id: str = "", session_id: str = "", tab_id: str = "", tab_revision: int = 0,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    invalid_record_count = 0
    root = ownership_root()
    if root.is_dir():
        for path in sorted(root.glob("*.json")):
            record = load_json_file(path, None, expected_type=dict)
            if not record or not record.get("operation_id"):
                invalid_record_count += 1
                continue
            rows.append(_content_free_recovery_row(inspect_process_operation_for_context(
                str(record["operation_id"]), project_id=project_id, session_id=session_id,
                tab_id=tab_id, tab_revision=tab_revision,
            )))
    visible_all = [row for row in rows if row.get("context_matches")]
    visible_all.sort(key=lambda row: str(row.get("updated_at") or row.get("accepted_at") or ""), reverse=True)
    history_limit = 50
    visible = visible_all[:history_limit]
    counts: dict[str, int] = {}
    for row in visible:
        status = str(row.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    overall = "healthy"
    if invalid_record_count or any(row.get("uncertain_result") or row.get("status") in {"uncertain", "orphan_termination_uncertain"} for row in visible):
        overall = "uncertain"
    elif any(row.get("status") == "orphan_running" for row in visible):
        overall = "recovery_required"
    elif any(row.get("read_only_reattached") for row in visible):
        overall = "busy"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": overall,
        "operation_count": len(visible),
        "total_matching_operation_count": len(visible_all),
        "history_limit": history_limit,
        "history_truncated": len(visible_all) > history_limit,
        "counts": counts,
        "rows": visible,
        "invalid_private_record_count": invalid_record_count,
        "restart_restored": True,
        "ownership_transferred": False,
        "replay_allowed": False,
        "content_free": True,
        "private_process_details_returned": False,
        "unified_recovery_contract": True,
        "ordinary_conversation_available": True,
    }

def build_unified_process_recovery_state(
    *, project_id: str = "", session_id: str = "", tab_id: str = "", tab_revision: int = 0,
) -> dict[str, Any]:
    return build_process_restart_state(
        project_id=project_id, session_id=session_id, tab_id=tab_id, tab_revision=tab_revision,
    )

def build_process_recovery_state() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    root = ownership_root()
    if root.is_dir():
        for path in sorted(root.glob("*.json")):
            record = load_json_file(path, None, expected_type=dict)
            if not record or not record.get("operation_id"):
                continue
            rows.append(reconcile_process_operation(str(record["operation_id"]), terminate_orphan=False))
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    overall = "healthy"
    if any(row.get("status") in {"uncertain", "orphan_termination_uncertain"} for row in rows):
        overall = "uncertain"
    elif any(row.get("status") == "orphan_running" for row in rows):
        overall = "recovery_required"
    elif any(row.get("status") == "running" for row in rows):
        overall = "busy"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": overall,
        "operation_count": len(rows),
        "counts": counts,
        "rows": rows,
        "content_free": True,
        "payload_returned": False,
        "command_returned": False,
        "private_process_details_returned": False,
    }


def reconcile_process_recovery_operation(operation_id: str, *, operator_confirmed: bool) -> dict[str, Any]:
    if operator_confirmed is not True:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "confirmation_required"}
    return reconcile_process_operation(operation_id, terminate_orphan=True)


def cleanup_process_recovery_operation(operation_id: str, *, operator_confirmed: bool) -> dict[str, Any]:
    if operator_confirmed is not True:
        return {**inspect_process_operation(operation_id), "ok": False, "status": "confirmation_required"}
    state = reconcile_process_operation(operation_id, terminate_orphan=False)
    if str(state.get("status") or "") not in TERMINAL_STATES:
        return {**state, "ok": False, "status": "not_terminal"}
    path = ownership_path(operation_id)
    result = result_path(operation_id)
    try:
        path.unlink(missing_ok=True)
        result.unlink(missing_ok=True)
    except OSError:
        return {**state, "ok": False, "status": "cleanup_failed"}
    return {
        "ok": True,
        "status": "cleaned",
        "operation_id": str(operation_id),
        "content_free": True,
        "replay_allowed": False,
    }
