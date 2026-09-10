from __future__ import annotations

"""Separately authorized execution pause, resume, cancel, and recovery.

v1228 derives one content-free control state from an active v1226 launch and its
v1227 monitoring stream. v1227 intervention requests may be converted into
single-use pause, cancel, or review-acknowledgment authorizations. A paused
session requires a fresh resume authorization. Missing or inconsistent runtime
state is reconciled into ``recovery_required`` and may only recover into a
paused state. No control in this module authorizes provider, command, test,
workspace-materialization, project-mutation, cognition, installation,
promotion, release, or model-management work.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from execution_session_authorization_bounded_launch import (
    _runtime_namespace_path,
    _validate_launch,
    load_bounded_development_execution_session,
    inspect_bounded_development_execution_session,
)
from live_execution_monitoring_operator_intervention import (
    _request_path as _v1227_request_path,
    _validate_request as _validate_v1227_request,
    inspect_live_execution_monitoring,
    load_live_execution_monitoring,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1228.8"
MAX_CONTROL_STATES = 100
MAX_TRANSITIONS_PER_SESSION = 100
MAX_TRANSITION_AUTHORIZATIONS = 200
MAX_RECOVERY_ATTEMPTS = 10

SESSION_STATES = {
    "active",
    "pause_pending_safe_boundary",
    "paused",
    "recovery_required",
    "cancelled",
}
TRANSITION_ACTIONS = {"acknowledge_review", "pause", "resume", "cancel", "recover"}
REQUEST_ACTION_MAP = {
    "operator_review": "acknowledge_review",
    "pause": "pause",
    "stop": "cancel",
}
SAFE_PAUSE_STAGES = {
    "launched_waiting_for_step_authorization",
    "step_authorization_review",
    "operator_review_required",
    "blocked",
    "completed_pending_review",
}
UNSAFE_ACTIVE_STAGES = {
    "provider_step_active",
    "command_step_active",
    "test_step_active",
    "verification_active",
}
TERMINAL_STATES = {"cancelled"}

AUTHORITY_FLAGS = {
    "session_control_authorized": True,
    "transition_authorization_required": True,
    "transition_authorization_consumed": False,
    "pause_applied": False,
    "resume_applied": False,
    "cancel_applied": False,
    "recovery_applied": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "background_execution_authorized": False,
    "cognition_write_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "old_authority_reusable": False,
}

_PREPARE_CONTROL = re.compile(
    r"^prepare execution session control for bounded development execution session "
    r"(?P<launch>launch_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show execution session controls[.!?]*$", re.I)
_SHOW_ONE = re.compile(
    r"^show execution session control for bounded development execution session "
    r"(?P<launch>launch_[a-f0-9]{24})[.!?]*$",
    re.I,
)
_PREPARE_REQUEST_ACTION = re.compile(
    r"^prepare bounded execution (?P<action>review acknowledgment|pause|cancel) authorization for intervention request "
    r"(?P<request>intervention_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_PREPARE_DIRECT_ACTION = re.compile(
    r"^prepare bounded execution (?P<action>resume|cancel|recovery) authorization for execution session control "
    r"(?P<control>control_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_APPLY = re.compile(
    r"^authorize bounded execution (?P<action>review acknowledgment|pause|resume|cancel|recovery) for execution session control "
    r"(?P<control>control_[a-f0-9]{24}) digest (?P<control_digest>[a-f0-9]{64}) authorization "
    r"(?P<authorization>transition_auth_[a-f0-9]{24}) digest (?P<authorization_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_RECONCILE = re.compile(
    r"^reconcile bounded execution session control (?P<control>control_[a-f0-9]{24}) digest "
    r"(?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_AUTHS = re.compile(r"^show execution session transition authorizations[.!?]*$", re.I)
_SHOW_TRANSITIONS = re.compile(r"^show execution session transitions[.!?]*$", re.I)


def _control_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "execution_session_control_states"


def _control_path(launch_id: str, runtime_root=None) -> Path:
    return _control_root(runtime_root) / f"{str(launch_id or '').lower()}.json"


def _snapshot_path(launch_id: str, generation: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "execution_session_control_snapshots" / str(launch_id or "").lower() / f"generation-{generation:06d}.json"


def _authorization_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "execution_session_transition_authorizations"


def _authorization_path(authorization_id: str, runtime_root=None) -> Path:
    return _authorization_root(runtime_root) / f"{str(authorization_id or '').lower()}.json"


def _consumption_path(authorization_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "execution_session_transition_authorization_consumptions" / f"{str(authorization_id or '').lower()}.json"


def _transition_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "execution_session_transitions"


def _transition_path(transition_id: str, runtime_root=None) -> Path:
    return _transition_root(runtime_root) / f"{str(transition_id or '').lower()}.json"


def _request_resolution_path(request_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "execution_session_intervention_request_resolutions" / f"{str(request_id or '').lower()}.json"


def _journal_path(authorization_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "execution_session_transition_journals" / f"{str(authorization_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _store_root(runtime_root) / "locks" / "execution-session-pause-resume-cancel-recovery.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 15.0
    while True:
        try:
            path.mkdir()
            (path / "owner").write_text(str(os.getpid()), encoding="ascii")
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 60:
                    shutil.rmtree(path, ignore_errors=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for execution-session control lock")
            time.sleep(0.02)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _sealed(record: Mapping[str, Any], field: str) -> dict[str, Any]:
    row = dict(record)
    row[field] = _digest({key: value for key, value in row.items() if key != field})
    return row


def _valid(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != field}))


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "runtime_records_external": True,
        "operator_control_required": True,
        "safe_boundary_pause_required": True,
        "fresh_resume_authorization_required": True,
        "recovery_defaults_to_paused": True,
        "intervention_request_preserved_as_evidence": True,
        "goal_alignment_preserved": True,
        "uncertainty_preserved": True,
        "eventual_outcome_reflection_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_materialized": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "project_name_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        "cognition_written": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, reason: str = "") -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason, **_base()}
    row["execution_session_control_result_digest"] = _digest(row)
    return row


def _control_digest(row: Mapping[str, Any]) -> str:
    return _digest({
        "control_id": str(row.get("control_id") or ""),
        "launch_id": str(row.get("launch_id") or ""),
        "launch_digest": str(row.get("launch_digest") or ""),
        "generation": int(row.get("generation") or 0),
        "session_state": str(row.get("session_state") or ""),
        "last_transition_digest": str(row.get("last_transition_digest") or ""),
        "pending_action": str(row.get("pending_action") or ""),
        "recovery_attempts": int(row.get("recovery_attempts") or 0),
    })


def _validate_control(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_session_control_record_digest")
        and str(row.get("control_id") or "").startswith("control_")
        and str(row.get("launch_id") or "").startswith("launch_")
        and str(row.get("session_state") or "") in SESSION_STATES
        and int(row.get("generation") or 0) >= 1
        and str(row.get("control_digest") or "") == _control_digest(row)
        and row.get("provider_execution_authorized") is False
        and row.get("project_mutation_authorized") is False
    )


def _authorization_digest(row: Mapping[str, Any]) -> str:
    return _digest({
        "authorization_id": str(row.get("authorization_id") or ""),
        "action": str(row.get("action") or ""),
        "control_id": str(row.get("control_id") or ""),
        "control_digest": str(row.get("control_digest") or ""),
        "launch_id": str(row.get("launch_id") or ""),
        "request_id": str(row.get("request_id") or ""),
        "request_digest": str(row.get("request_digest") or ""),
    })


def _validate_authorization(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_session_transition_authorization_record_digest")
        and str(row.get("authorization_id") or "").startswith("transition_auth_")
        and str(row.get("action") or "") in TRANSITION_ACTIONS
        and str(row.get("authorization_digest") or "") == _authorization_digest(row)
        and row.get("authorization_consumed") is False
    )


def _validate_consumption(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_session_transition_authorization_consumption_record_digest")
        and str(row.get("authorization_id") or "").startswith("transition_auth_")
        and str(row.get("transition_id") or "").startswith("transition_")
        and row.get("authorization_consumed") is True
        and int(row.get("consumption_count") or 0) == 1
    )


def _validate_transition(row: Mapping[str, Any]) -> bool:
    return (
        _valid(row, "execution_session_transition_record_digest")
        and str(row.get("transition_id") or "").startswith("transition_")
        and str(row.get("action") or "") in TRANSITION_ACTIONS
        and str(row.get("from_state") or "") in SESSION_STATES
        and str(row.get("to_state") or "") in SESSION_STATES
        and row.get("provider_contacted") is False
        and row.get("project_modified") is False
    )


def _raw_launch(launch_id: str, runtime_root=None) -> dict[str, Any]:
    launch = load_bounded_development_execution_session(str(launch_id or "").lower(), runtime_root=runtime_root)
    if not launch or not _validate_launch(launch):
        raise ValueError("bounded_execution_session_missing_or_invalid")
    return launch


def _namespace_valid(launch: Mapping[str, Any], runtime_root=None) -> bool:
    row = _read_json(_runtime_namespace_path(str(launch.get("launch_id") or ""), runtime_root) / "session.json")
    return bool(row and str(row.get("launch_digest") or "") == str(launch.get("launch_digest") or ""))


def _control_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _control_root(runtime_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("launch_*.json"))[: MAX_CONTROL_STATES + 1]:
        row = _read_json(path)
        if not row or not _validate_control(row) or path.stem != row.get("launch_id"):
            raise ValueError("execution_session_control_tampered_or_malformed")
        rows.append(row)
    if len(rows) > MAX_CONTROL_STATES:
        raise ValueError("execution_session_control_limit_exceeded")
    return rows


def _authorization_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _authorization_root(runtime_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("transition_auth_*.json"))[: MAX_TRANSITION_AUTHORIZATIONS + 1]:
        row = _read_json(path)
        if not row or not _validate_authorization(row) or path.stem != row.get("authorization_id"):
            raise ValueError("transition_authorization_tampered_or_malformed")
        rows.append(row)
    if len(rows) > MAX_TRANSITION_AUTHORIZATIONS:
        raise ValueError("transition_authorization_limit_exceeded")
    return rows


def _transition_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _transition_root(runtime_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("transition_*.json")):
        row = _read_json(path)
        if not row or not _validate_transition(row) or path.stem != row.get("transition_id"):
            raise ValueError("execution_session_transition_tampered_or_malformed")
        rows.append(row)
    return rows


def _state_record(
    launch: Mapping[str, Any],
    *,
    generation: int,
    session_state: str,
    last_transition_digest: str = "",
    pending_action: str = "",
    latest_request_id: str = "",
    recovery_attempts: int = 0,
    runtime_root=None,
) -> dict[str, Any]:
    control_id = "control_" + _digest({
        "launch_id": str(launch.get("launch_id") or ""),
        "launch_digest": str(launch.get("launch_digest") or ""),
    })[:24]
    row = {
        "ok": True,
        "status": "execution_session_control_ready",
        "control_id": control_id,
        "launch_id": str(launch.get("launch_id") or ""),
        "launch_digest": str(launch.get("launch_digest") or ""),
        "source_session_id": str(launch.get("source_session_id") or ""),
        "source_session_digest": str(launch.get("source_session_digest") or ""),
        "queue_item_id": str(launch.get("queue_item_id") or ""),
        "project_reference": str(launch.get("project_reference") or ""),
        "proposal_id": str(launch.get("proposal_id") or ""),
        "generation": int(generation),
        "session_state": session_state,
        "pending_action": pending_action,
        "latest_request_id": latest_request_id,
        "last_transition_digest": last_transition_digest,
        "recovery_attempts": int(recovery_attempts),
        "runtime_namespace_present": _namespace_valid(launch, runtime_root),
        "fresh_transition_authorization_required": True,
        "fresh_resume_authorization_required": True,
        **_base(),
    }
    row["control_digest"] = _control_digest(row)
    return _sealed(row, "execution_session_control_record_digest")


def prepare_execution_session_control(launch_id: str, *, expected_launch_digest: str, runtime_root=None) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            launch = inspect_bounded_development_execution_session(str(launch_id or "").lower(), runtime_root=runtime_root)
            if launch.get("ok") is not True:
                raise ValueError(str(launch.get("reason") or "bounded_launch_missing_or_stale"))
            if str(launch.get("launch_digest") or "") != str(expected_launch_digest or ""):
                raise ValueError("stale_bounded_launch_digest")
            existing = _read_json(_control_path(launch_id, runtime_root))
            if existing:
                if not _validate_control(existing):
                    raise ValueError("execution_session_control_tampered_or_malformed")
                return {**existing, "operation_status": "resumed"}
            monitor = inspect_live_execution_monitoring(str(launch_id or "").lower(), runtime_root=runtime_root)
            if monitor.get("ok") is not True:
                raise ValueError(str(monitor.get("reason") or "live_execution_monitoring_required"))
            row = _state_record(launch, generation=1, session_state="active", runtime_root=runtime_root)
            _atomic_json(_snapshot_path(launch_id, 1, runtime_root), row)
            _atomic_json(_control_path(launch_id, runtime_root), row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("execution_session_control_blocked", str(exc))


def load_execution_session_control(launch_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_control_path(str(launch_id or "").lower(), runtime_root))
    return row if row and _validate_control(row) else {}


def _detect_recovery_need(control: Mapping[str, Any], runtime_root=None) -> bool:
    state = str(control.get("session_state") or "")
    if state in TERMINAL_STATES or state == "recovery_required":
        return False
    launch = _raw_launch(str(control.get("launch_id") or ""), runtime_root)
    return not _namespace_valid(launch, runtime_root)


def inspect_execution_session_control(launch_id: str, *, runtime_root=None, reconcile_runtime: bool = True) -> dict[str, Any]:
    try:
        row = load_execution_session_control(launch_id, runtime_root=runtime_root)
        if not row:
            raise ValueError("execution_session_control_missing_or_invalid")
        launch = _raw_launch(str(row.get("launch_id") or ""), runtime_root)
        if str(launch.get("launch_digest") or "") != str(row.get("launch_digest") or ""):
            raise ValueError("execution_session_control_launch_binding_invalid")
        if reconcile_runtime and _detect_recovery_need(row, runtime_root):
            with _lock(runtime_root):
                current = load_execution_session_control(launch_id, runtime_root=runtime_root)
                if not current:
                    raise ValueError("execution_session_control_missing_or_invalid")
                if _detect_recovery_need(current, runtime_root):
                    current = _write_state_transition_without_authorization(
                        current,
                        action="recover",
                        to_state="recovery_required",
                        runtime_root=runtime_root,
                        status="execution_session_recovery_required",
                        recovery_detection_only=True,
                    )
                row = current
        return row
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("execution_session_control_expired", str(exc))


def get_effective_execution_session_state(launch_id: str, *, runtime_root=None) -> str:
    row = load_execution_session_control(launch_id, runtime_root=runtime_root)
    return str(row.get("session_state") or "active") if row else "active"


def _load_request(request_id: str, expected_digest: str, runtime_root=None) -> dict[str, Any]:
    request = _read_json(_v1227_request_path(str(request_id or "").lower(), runtime_root))
    if not request or not _validate_v1227_request(request):
        raise ValueError("intervention_request_missing_or_invalid")
    if str(request.get("request_digest") or "") != str(expected_digest or ""):
        raise ValueError("stale_intervention_request_digest")
    resolution = _read_json(_request_resolution_path(str(request_id or "").lower(), runtime_root))
    if resolution:
        if not _valid(resolution, "execution_session_intervention_request_resolution_record_digest"):
            raise ValueError("intervention_request_resolution_tampered")
        raise ValueError("intervention_request_already_resolved")
    return request


def _allowed_action(control: Mapping[str, Any], action: str, request: Mapping[str, Any] | None = None) -> None:
    state = str(control.get("session_state") or "")
    if action == "acknowledge_review":
        if not request or request.get("intervention_type") != "operator_review":
            raise ValueError("review_request_required")
    elif action == "pause":
        if state != "active" or not request or request.get("intervention_type") != "pause":
            raise ValueError("active_session_pause_request_required")
    elif action == "resume":
        if state != "paused" or request:
            raise ValueError("paused_session_required")
    elif action == "cancel":
        if state not in {"active", "paused", "pause_pending_safe_boundary", "recovery_required"}:
            raise ValueError("cancellable_session_required")
        if request and request.get("intervention_type") != "stop":
            raise ValueError("stop_request_required_for_request_cancel")
    elif action == "recover":
        if state != "recovery_required" or request:
            raise ValueError("recovery_required_state_required")
    else:
        raise ValueError("unsupported_transition_action")


def prepare_execution_session_transition_authorization(
    action: str,
    *,
    control_id: str = "",
    expected_control_digest: str = "",
    request_id: str = "",
    expected_request_digest: str = "",
    exact_phrase: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        action = str(action or "").strip().lower().replace(" ", "_")
        if action == "review_acknowledgment":
            action = "acknowledge_review"
        if action == "recovery":
            action = "recover"
        if action not in TRANSITION_ACTIONS:
            raise ValueError("unsupported_transition_action")
        with _lock(runtime_root):
            request = None
            if request_id:
                request = _load_request(request_id, expected_request_digest, runtime_root)
                mapped = REQUEST_ACTION_MAP.get(str(request.get("intervention_type") or ""))
                if mapped != action:
                    raise ValueError("intervention_request_action_mismatch")
                candidates = [row for row in _control_rows(runtime_root) if row.get("launch_id") == request.get("launch_id")]
                if len(candidates) != 1:
                    raise ValueError("execution_session_control_required_for_request")
                control = candidates[0]
            else:
                candidates = [row for row in _control_rows(runtime_root) if row.get("control_id") == str(control_id or "").lower()]
                if len(candidates) != 1:
                    raise ValueError("execution_session_control_missing_or_invalid")
                control = candidates[0]
                if str(control.get("control_digest") or "") != str(expected_control_digest or ""):
                    raise ValueError("stale_execution_session_control_digest")
            _allowed_action(control, action, request)
            seed = {
                "action": action,
                "control_id": str(control.get("control_id") or ""),
                "control_digest": str(control.get("control_digest") or ""),
                "request_id": str((request or {}).get("request_id") or ""),
                "request_digest": str((request or {}).get("request_digest") or ""),
            }
            authorization_id = "transition_auth_" + _digest(seed)[:24]
            path = _authorization_path(authorization_id, runtime_root)
            existing = _read_json(path)
            if existing:
                if not _validate_authorization(existing):
                    raise ValueError("transition_authorization_tampered_or_malformed")
                return {**existing, "operation_status": "replayed"}
            row = {
                "ok": True,
                "status": "execution_session_transition_authorization_ready",
                "authorization_id": authorization_id,
                "action": action,
                "control_id": str(control.get("control_id") or ""),
                "control_digest": str(control.get("control_digest") or ""),
                "launch_id": str(control.get("launch_id") or ""),
                "launch_digest": str(control.get("launch_digest") or ""),
                "request_id": str((request or {}).get("request_id") or ""),
                "request_digest": str((request or {}).get("request_digest") or ""),
                "authorization_consumed": False,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                **_base(),
            }
            row["authorization_digest"] = _authorization_digest(row)
            human_action = {
                "acknowledge_review": "review acknowledgment",
                "pause": "pause",
                "resume": "resume",
                "cancel": "cancel",
                "recover": "recovery",
            }[action]
            row["authorize_phrase"] = (
                f"Authorize bounded execution {human_action} for execution session control "
                f"{row['control_id']} digest {row['control_digest']} authorization "
                f"{authorization_id} digest {row['authorization_digest']}."
            )
            row = _sealed(row, "execution_session_transition_authorization_record_digest")
            _atomic_json(path, row)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("execution_session_transition_authorization_blocked", str(exc))


def load_execution_session_transition_authorization(authorization_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_authorization_path(str(authorization_id or "").lower(), runtime_root))
    return row if row and _validate_authorization(row) else {}


def _safe_monitor_stage(control: Mapping[str, Any], runtime_root=None) -> tuple[bool, str]:
    monitor = load_live_execution_monitoring(str(control.get("launch_id") or ""), runtime_root=runtime_root)
    if not monitor:
        raise ValueError("live_execution_monitor_missing_or_invalid")
    stage = str(monitor.get("current_stage") or "")
    return stage in SAFE_PAUSE_STAGES, stage


def _resolution_record(request_id: str, request_digest: str, action: str, transition_id: str) -> dict[str, Any]:
    row = {
        "ok": True,
        "status": "intervention_request_resolved",
        "request_id": request_id,
        "request_digest": request_digest,
        "action": action,
        "transition_id": transition_id,
        "request_state": "resolved_by_v1228",
        "content_free": True,
        "old_authority_reusable": False,
    }
    return _sealed(row, "execution_session_intervention_request_resolution_record_digest")


def _write_state_transition_without_authorization(
    control: Mapping[str, Any],
    *,
    action: str,
    to_state: str,
    runtime_root=None,
    status: str = "execution_session_transition_applied",
    recovery_detection_only: bool = False,
) -> dict[str, Any]:
    launch = _raw_launch(str(control.get("launch_id") or ""), runtime_root)
    generation = int(control.get("generation") or 0) + 1
    transition_id = "transition_" + _digest({
        "control_id": str(control.get("control_id") or ""),
        "generation": generation,
        "action": action,
        "from_state": str(control.get("session_state") or ""),
        "to_state": to_state,
    })[:24]
    transition_digest = _digest({
        "transition_id": transition_id,
        "control_id": str(control.get("control_id") or ""),
        "generation": generation,
        "action": action,
        "from_state": str(control.get("session_state") or ""),
        "to_state": to_state,
        "authorization_id": "",
    })
    transition = {
        "ok": True,
        "status": status,
        "transition_id": transition_id,
        "transition_digest": transition_digest,
        "control_id": str(control.get("control_id") or ""),
        "launch_id": str(control.get("launch_id") or ""),
        "generation": generation,
        "action": action,
        "from_state": str(control.get("session_state") or ""),
        "to_state": to_state,
        "authorization_id": "",
        "authorization_digest": "",
        "request_id": "",
        "request_digest": "",
        "recovery_detection_only": bool(recovery_detection_only),
        **_base(),
    }
    transition = _sealed(transition, "execution_session_transition_record_digest")
    updated = _state_record(
        launch,
        generation=generation,
        session_state=to_state,
        last_transition_digest=transition_digest,
        pending_action="recover" if to_state == "recovery_required" else "",
        latest_request_id=str(control.get("latest_request_id") or ""),
        recovery_attempts=int(control.get("recovery_attempts") or 0),
        runtime_root=runtime_root,
    )
    _atomic_json(_transition_path(transition_id, runtime_root), transition)
    _atomic_json(_snapshot_path(str(control.get("launch_id") or ""), generation, runtime_root), updated)
    _atomic_json(_control_path(str(control.get("launch_id") or ""), runtime_root), updated)
    return updated


def _target_state(action: str, control: Mapping[str, Any], runtime_root=None) -> tuple[str, str]:
    if action == "acknowledge_review":
        return str(control.get("session_state") or "active"), ""
    if action == "pause":
        safe, stage = _safe_monitor_stage(control, runtime_root)
        return ("paused", "") if safe else ("pause_pending_safe_boundary", stage)
    if action == "resume":
        return "active", ""
    if action == "cancel":
        return "cancelled", ""
    if action == "recover":
        return "paused", ""
    raise ValueError("unsupported_transition_action")


def _ensure_namespace_for_recovery(launch: Mapping[str, Any], runtime_root=None) -> None:
    namespace = _runtime_namespace_path(str(launch.get("launch_id") or ""), runtime_root)
    namespace.mkdir(parents=True, exist_ok=True)
    row = {
        "launch_id": str(launch.get("launch_id") or ""),
        "launch_digest": str(launch.get("launch_digest") or ""),
        "content_free": True,
        "recovered_by_v1228": True,
        "project_files_materialized": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
    }
    _atomic_json(namespace / "session.json", row)


def apply_execution_session_transition(
    authorization_id: str,
    *,
    expected_authorization_digest: str,
    expected_control_id: str,
    expected_control_digest: str,
    exact_phrase: str = "",
    expected_action: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            authorization = load_execution_session_transition_authorization(authorization_id, runtime_root=runtime_root)
            if not authorization:
                raise ValueError("transition_authorization_missing_or_invalid")
            if str(authorization.get("authorization_digest") or "") != str(expected_authorization_digest or ""):
                raise ValueError("stale_transition_authorization_digest")
            if str(authorization.get("control_id") or "") != str(expected_control_id or ""):
                raise ValueError("transition_control_id_mismatch")
            if str(authorization.get("control_digest") or "") != str(expected_control_digest or ""):
                raise ValueError("transition_control_digest_mismatch")
            normalized_expected_action = str(expected_action or "").strip().lower().replace(" ", "_")
            if normalized_expected_action == "review_acknowledgment":
                normalized_expected_action = "acknowledge_review"
            if normalized_expected_action == "recovery":
                normalized_expected_action = "recover"
            if normalized_expected_action and str(authorization.get("action") or "") != normalized_expected_action:
                raise ValueError("transition_action_phrase_mismatch")
            consumption = _read_json(_consumption_path(authorization_id, runtime_root))
            if consumption:
                if not _validate_consumption(consumption):
                    raise ValueError("transition_authorization_consumption_tampered")
                transition = _read_json(_transition_path(str(consumption.get("transition_id") or ""), runtime_root))
                if not transition or not _validate_transition(transition):
                    raise ValueError("consumed_transition_missing_or_invalid")
                return {**transition, "operation_status": "replayed"}
            controls = [row for row in _control_rows(runtime_root) if row.get("control_id") == expected_control_id]
            if len(controls) != 1:
                raise ValueError("execution_session_control_missing_or_invalid")
            control = controls[0]
            if str(control.get("control_digest") or "") != expected_control_digest:
                raise ValueError("stale_execution_session_control_digest")
            request = None
            if authorization.get("request_id"):
                request = _load_request(
                    str(authorization.get("request_id") or ""),
                    str(authorization.get("request_digest") or ""),
                    runtime_root,
                )
            action = str(authorization.get("action") or "")
            _allowed_action(control, action, request)
            to_state, pending_stage = _target_state(action, control, runtime_root)
            generation = int(control.get("generation") or 0) + 1
            if generation > MAX_TRANSITIONS_PER_SESSION + 1:
                raise ValueError("execution_session_transition_limit_exceeded")
            transition_id = "transition_" + _digest({
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "control_id": expected_control_id,
                "control_digest": expected_control_digest,
            })[:24]
            journal = {
                "ok": True,
                "status": "execution_session_transition_prepared",
                "phase": "prepared",
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "transition_id": transition_id,
                "control_id": expected_control_id,
                "from_state": str(control.get("session_state") or ""),
                "to_state": to_state,
                "content_free": True,
            }
            journal = _sealed(journal, "execution_session_transition_journal_record_digest")
            _atomic_json(_journal_path(authorization_id, runtime_root), journal)
            launch = _raw_launch(str(control.get("launch_id") or ""), runtime_root)
            if action == "recover":
                attempts = int(control.get("recovery_attempts") or 0) + 1
                if attempts > MAX_RECOVERY_ATTEMPTS:
                    raise ValueError("recovery_attempt_limit_exceeded")
                _ensure_namespace_for_recovery(launch, runtime_root)
            else:
                attempts = int(control.get("recovery_attempts") or 0)
            if action == "cancel":
                shutil.rmtree(_runtime_namespace_path(str(control.get("launch_id") or ""), runtime_root), ignore_errors=True)
            transition_digest = _digest({
                "transition_id": transition_id,
                "control_id": expected_control_id,
                "generation": generation,
                "action": action,
                "from_state": str(control.get("session_state") or ""),
                "to_state": to_state,
                "authorization_id": authorization_id,
            })
            transition = {
                "ok": True,
                "status": "execution_session_transition_applied",
                "transition_id": transition_id,
                "transition_digest": transition_digest,
                "control_id": expected_control_id,
                "launch_id": str(control.get("launch_id") or ""),
                "generation": generation,
                "action": action,
                "from_state": str(control.get("session_state") or ""),
                "to_state": to_state,
                "pending_safe_boundary_stage": pending_stage,
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "request_id": str((request or {}).get("request_id") or ""),
                "request_digest": str((request or {}).get("request_digest") or ""),
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                "transition_authorization_consumed": True,
                **_base(),
                "transition_authorization_consumed": True,
                "pause_applied": action == "pause" and to_state == "paused",
                "resume_applied": action == "resume",
                "cancel_applied": action == "cancel",
                "recovery_applied": action == "recover",
            }
            transition = _sealed(transition, "execution_session_transition_record_digest")
            updated = _state_record(
                launch,
                generation=generation,
                session_state=to_state,
                last_transition_digest=transition_digest,
                pending_action="pause" if to_state == "pause_pending_safe_boundary" else "",
                latest_request_id=str((request or {}).get("request_id") or control.get("latest_request_id") or ""),
                recovery_attempts=attempts,
                runtime_root=runtime_root,
            )
            consumption_row = {
                "ok": True,
                "status": "execution_session_transition_authorization_consumed",
                "authorization_id": authorization_id,
                "authorization_digest": expected_authorization_digest,
                "transition_id": transition_id,
                "transition_digest": transition_digest,
                "authorization_consumed": True,
                "consumption_count": 1,
                "old_authority_reusable": False,
                "content_free": True,
            }
            consumption_row = _sealed(consumption_row, "execution_session_transition_authorization_consumption_record_digest")
            _atomic_json(_transition_path(transition_id, runtime_root), transition)
            _atomic_json(_snapshot_path(str(control.get("launch_id") or ""), generation, runtime_root), updated)
            _atomic_json(_control_path(str(control.get("launch_id") or ""), runtime_root), updated)
            if request:
                _atomic_json(
                    _request_resolution_path(str(request.get("request_id") or ""), runtime_root),
                    _resolution_record(
                        str(request.get("request_id") or ""),
                        str(request.get("request_digest") or ""),
                        action,
                        transition_id,
                    ),
                )
            _atomic_json(_consumption_path(authorization_id, runtime_root), consumption_row)
            committed = {**journal, "status": "execution_session_transition_committed", "phase": "committed"}
            committed = _sealed(
                {key: value for key, value in committed.items() if key != "execution_session_transition_journal_record_digest"},
                "execution_session_transition_journal_record_digest",
            )
            _atomic_json(_journal_path(authorization_id, runtime_root), committed)
            return {**transition, "control": _public_control(updated), "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("execution_session_transition_blocked", str(exc))


def reconcile_execution_session_control(control_id: str, *, expected_control_digest: str, runtime_root=None) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            controls = [row for row in _control_rows(runtime_root) if row.get("control_id") == str(control_id or "").lower()]
            if len(controls) != 1:
                raise ValueError("execution_session_control_missing_or_invalid")
            control = controls[0]
            if str(control.get("control_digest") or "") != str(expected_control_digest or ""):
                raise ValueError("stale_execution_session_control_digest")
            state = str(control.get("session_state") or "")
            if state == "pause_pending_safe_boundary":
                safe, stage = _safe_monitor_stage(control, runtime_root)
                if not safe:
                    return {**control, "status": "execution_session_pause_still_pending", "current_stage": stage, "operation_status": "unchanged"}
                updated = _write_state_transition_without_authorization(
                    control,
                    action="pause",
                    to_state="paused",
                    runtime_root=runtime_root,
                    status="execution_session_pause_completed_at_safe_boundary",
                )
                return {**updated, "operation_status": "reconciled"}
            if state in {"active", "paused"} and _detect_recovery_need(control, runtime_root):
                updated = _write_state_transition_without_authorization(
                    control,
                    action="recover",
                    to_state="recovery_required",
                    runtime_root=runtime_root,
                    status="execution_session_recovery_required",
                    recovery_detection_only=True,
                )
                return {**updated, "operation_status": "reconciled"}
            return {**control, "operation_status": "unchanged"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("execution_session_control_reconciliation_blocked", str(exc))


def intervention_request_resolution(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_request_resolution_path(str(request_id or "").lower(), runtime_root))
    if not row:
        return {}
    return row if _valid(row, "execution_session_intervention_request_resolution_record_digest") else {}


def _public_control(row: Mapping[str, Any]) -> dict[str, Any]:
    if row.get("ok") is not True:
        return {key: row.get(key) for key in ("ok", "status", "reason") if key in row} | _base()
    allowed = {
        "ok", "status", "control_id", "control_digest", "launch_id", "launch_digest",
        "source_session_id", "source_session_digest", "queue_item_id", "project_reference", "proposal_id",
        "generation", "session_state", "pending_action", "latest_request_id", "last_transition_digest",
        "recovery_attempts", "runtime_namespace_present", "fresh_transition_authorization_required",
        "fresh_resume_authorization_required", "operation_status",
    }
    public = {key: row.get(key) for key in allowed if key in row}
    public.update(_base())
    public["public_execution_session_control_digest"] = _digest(public)
    return public


def _public_authorization(row: Mapping[str, Any]) -> dict[str, Any]:
    if row.get("ok") is not True:
        return {key: row.get(key) for key in ("ok", "status", "reason") if key in row} | _base()
    allowed = {
        "ok", "status", "authorization_id", "authorization_digest", "action", "control_id", "control_digest",
        "launch_id", "launch_digest", "request_id", "request_digest", "authorization_consumed",
        "authorize_phrase", "operation_status",
    }
    public = {key: row.get(key) for key in allowed if key in row}
    public.update(_base())
    public["public_execution_session_transition_authorization_digest"] = _digest(public)
    return public


def _public_transition(row: Mapping[str, Any]) -> dict[str, Any]:
    if row.get("ok") is not True:
        return {key: row.get(key) for key in ("ok", "status", "reason") if key in row} | _base()
    allowed = {
        "ok", "status", "transition_id", "transition_digest", "control_id", "launch_id", "generation", "action",
        "from_state", "to_state", "pending_safe_boundary_stage", "authorization_id", "authorization_digest",
        "request_id", "request_digest", "transition_authorization_consumed", "pause_applied", "resume_applied",
        "cancel_applied", "recovery_applied", "operation_status", "control",
    }
    public = {key: row.get(key) for key in allowed if key in row}
    public.update(_base())
    for key in ("transition_authorization_consumed", "pause_applied", "resume_applied", "cancel_applied", "recovery_applied"):
        if key in row:
            public[key] = bool(row.get(key))
    public["public_execution_session_transition_digest"] = _digest(public)
    return public


def public_execution_session_controls(*, runtime_root=None) -> dict[str, Any]:
    try:
        controls = [_public_control(inspect_execution_session_control(str(row.get("launch_id") or ""), runtime_root=runtime_root)) for row in _control_rows(runtime_root)]
        result = {"ok": True, "status": "execution_session_control_list_ready", "control_count": len(controls), "controls": controls, **_base()}
        result["public_execution_session_control_list_digest"] = _digest(result)
        return result
    except (OSError, ValueError) as exc:
        return _failure("execution_session_control_list_blocked", str(exc))


def public_execution_session_transition_authorizations(*, runtime_root=None) -> dict[str, Any]:
    try:
        rows = [_public_authorization(row) for row in _authorization_rows(runtime_root)]
        result = {"ok": True, "status": "execution_session_transition_authorization_list_ready", "authorization_count": len(rows), "authorizations": rows, **_base()}
        result["public_execution_session_transition_authorization_list_digest"] = _digest(result)
        return result
    except (OSError, ValueError) as exc:
        return _failure("execution_session_transition_authorization_list_blocked", str(exc))


def public_execution_session_transitions(*, runtime_root=None) -> dict[str, Any]:
    try:
        rows = [_public_transition(row) for row in _transition_rows(runtime_root)]
        result = {"ok": True, "status": "execution_session_transition_list_ready", "transition_count": len(rows), "transitions": rows, **_base()}
        result["public_execution_session_transition_list_digest"] = _digest(result)
        return result
    except (OSError, ValueError) as exc:
        return _failure("execution_session_transition_list_blocked", str(exc))


def execution_session_control_response(row: Mapping[str, Any]) -> str:
    if row.get("ok") is not True:
        return f"Execution-session control was blocked: {row.get('reason', row.get('status') or 'invalid evidence')}."
    status = str(row.get("status") or "")
    if status in {"execution_session_control_ready", "execution_session_recovery_required"}:
        return (
            f"Execution-session control {row.get('control_id')} is {row.get('session_state')}. "
            "Every transition requires fresh authority; monitoring, provider, command, test, workspace, project, and cognition authority remain separate."
        )
    if status == "execution_session_transition_authorization_ready":
        return f"Transition authorization {row.get('authorization_id')} is ready for {row.get('action')}. Use the exact authorization phrase; no transition has been applied."
    if status in {"execution_session_transition_applied", "execution_session_pause_completed_at_safe_boundary"}:
        return (
            f"Execution-session transition {row.get('transition_id')} recorded: {row.get('from_state')} to {row.get('to_state')}. "
            "No provider, command, test, workspace, project, or cognition action was authorized."
        )
    if status.endswith("_list_ready"):
        count = row.get("control_count", row.get("authorization_count", row.get("transition_count", 0)))
        return f"There are {count} execution-session control records."
    if status == "execution_session_pause_still_pending":
        return f"Pause remains pending until a safe boundary; current stage: {row.get('current_stage')}."
    return f"Execution-session control recorded: {status}."


def process_execution_session_pause_resume_cancel_recovery_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE_CONTROL.fullmatch(text)
    show_one = _SHOW_ONE.fullmatch(text)
    request_action = _PREPARE_REQUEST_ACTION.fullmatch(text)
    direct_action = _PREPARE_DIRECT_ACTION.fullmatch(text)
    apply = _APPLY.fullmatch(text)
    reconcile = _RECONCILE.fullmatch(text)
    if prepare:
        result = _public_control(prepare_execution_session_control(
            prepare.group("launch").lower(), expected_launch_digest=prepare.group("digest").lower(), runtime_root=runtime_root
        ))
    elif _SHOW_ALL.fullmatch(text):
        result = public_execution_session_controls(runtime_root=runtime_root)
    elif show_one:
        result = _public_control(inspect_execution_session_control(show_one.group("launch").lower(), runtime_root=runtime_root))
    elif request_action:
        action = request_action.group("action").lower().replace(" ", "_")
        result = _public_authorization(prepare_execution_session_transition_authorization(
            action,
            request_id=request_action.group("request").lower(),
            expected_request_digest=request_action.group("digest").lower(),
            exact_phrase=text,
            runtime_root=runtime_root,
        ))
    elif direct_action:
        action = direct_action.group("action").lower()
        result = _public_authorization(prepare_execution_session_transition_authorization(
            action,
            control_id=direct_action.group("control").lower(),
            expected_control_digest=direct_action.group("digest").lower(),
            exact_phrase=text,
            runtime_root=runtime_root,
        ))
    elif apply:
        action = apply.group("action").lower().replace(" ", "_")
        result = _public_transition(apply_execution_session_transition(
            apply.group("authorization").lower(),
            expected_authorization_digest=apply.group("authorization_digest").lower(),
            expected_control_id=apply.group("control").lower(),
            expected_control_digest=apply.group("control_digest").lower(),
            exact_phrase=text,
            expected_action=action,
            runtime_root=runtime_root,
        ))
    elif reconcile:
        result = _public_control(reconcile_execution_session_control(
            reconcile.group("control").lower(), expected_control_digest=reconcile.group("digest").lower(), runtime_root=runtime_root
        ))
    elif _SHOW_AUTHS.fullmatch(text):
        result = public_execution_session_transition_authorizations(runtime_root=runtime_root)
    elif _SHOW_TRANSITIONS.fullmatch(text):
        result = public_execution_session_transitions(runtime_root=runtime_root)
    else:
        return {"active": False, "event": "not_execution_session_control", "conversation_response": ""}
    return {
        "active": True,
        "event": str(result.get("status") or "execution_session_control"),
        "conversation_response": execution_session_control_response(result),
        "execution_session_control": result,
    }
