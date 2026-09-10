from __future__ import annotations

"""Live execution monitoring and operator intervention requests.

v1227 derives one sealed, content-free monitoring stream from an active v1226
bounded execution session. Trusted execution subsystems may append bounded
progress evidence, while ordinary chat may inspect progress and request review,
pause, or stop intervention. Intervention requests are evidence only: they do
not pause, stop, resume, cancel, execute, contact a provider, run a command or
test, materialize a workspace, modify a project, or write cognition. Those
state transitions remain separately authorized v1228 work.
"""

import os
import re
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _read_json, _store_root
from execution_session_authorization_bounded_launch import (
    inspect_bounded_development_execution_session,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1227.8"
MAX_MONITORED_SESSIONS = 100
MAX_PROGRESS_EVENTS_PER_SESSION = 250
MAX_INTERVENTION_REQUESTS = 100

ALLOWED_EVENT_TYPES = {
    "monitoring_started",
    "stage_entered",
    "progress_updated",
    "blocker_reported",
    "risk_reported",
    "operator_review_required",
    "step_completed",
    "session_completed_pending_review",
}
ALLOWED_STAGES = {
    "launched_waiting_for_step_authorization",
    "step_authorization_review",
    "provider_step_active",
    "command_step_active",
    "test_step_active",
    "verification_active",
    "operator_review_required",
    "blocked",
    "completed_pending_review",
}
ALLOWED_BLOCKER_CODES = {
    "authorization_required",
    "provider_unavailable",
    "command_blocked",
    "test_blocked",
    "dependency_blocked",
    "risk_review_required",
    "operator_decision_required",
    "unknown_blocker",
}
ALLOWED_RISK_CODES = {
    "none",
    "scope_drift",
    "uncertainty_high",
    "budget_pressure",
    "rollback_readiness",
    "test_coverage_gap",
    "operator_attention",
    "unknown_risk",
}
INTERVENTION_TYPES = {"operator_review", "pause", "stop"}

AUTHORITY_FLAGS = {
    "monitoring_authorized": True,
    "progress_reporting_authorized": True,
    "operator_intervention_request_authorized": True,
    "operator_intervention_applied": False,
    "pause_authorized": False,
    "stop_authorized": False,
    "resume_authorized": False,
    "cancel_authorized": False,
    "provider_execution_authorized": False,
    "command_execution_authorized": False,
    "test_execution_authorized": False,
    "workspace_materialization_authorized": False,
    "project_mutation_authorized": False,
    "background_execution_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "old_authority_reusable": False,
}

_PREPARE = re.compile(
    r"^prepare live execution monitoring for bounded development execution session "
    r"(?P<launch>launch_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_ALL = re.compile(r"^show live execution monitoring sessions[.!?]*$", re.I)
_SHOW_ONE = re.compile(
    r"^show live execution monitoring for bounded development execution session "
    r"(?P<launch>launch_[a-f0-9]{24})[.!?]*$",
    re.I,
)
_REQUEST = re.compile(
    r"^request bounded (?P<kind>operator review|pause|stop) intervention for live execution monitoring "
    r"(?P<monitor>monitor_[a-f0-9]{24}) digest (?P<digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)
_SHOW_REQUESTS = re.compile(r"^show live execution intervention requests[.!?]*$", re.I)


def _monitor_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "live_execution_monitoring"


def _monitor_path(launch_id: str, runtime_root=None) -> Path:
    return _monitor_root(runtime_root) / f"{str(launch_id or '').lower()}.json"


def _event_root(launch_id: str, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "live_execution_monitoring_events" / str(launch_id or "").lower()


def _event_path(launch_id: str, generation: int, runtime_root=None) -> Path:
    return _event_root(launch_id, runtime_root) / f"generation-{generation:06d}.json"


def _request_root(runtime_root=None) -> Path:
    return _store_root(runtime_root) / "live_execution_intervention_requests"


def _request_path(request_id: str, runtime_root=None) -> Path:
    return _request_root(runtime_root) / f"{str(request_id or '').lower()}.json"


@contextmanager
def _lock(runtime_root=None):
    path = _store_root(runtime_root) / "locks" / "live-execution-monitoring-operator-intervention.lock"
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
                raise TimeoutError("Timed out waiting for live-monitoring lock")
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
        "live_monitoring_is_not_execution_authority": True,
        "intervention_request_is_not_intervention_authority": True,
        "v1228_state_transition_required": True,
        "goal_alignment_visible": True,
        "uncertainty_visible": True,
        "eventual_outcome_reflection_required": True,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "workspace_created": False,
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
    row["live_execution_monitoring_result_digest"] = _digest(row)
    return row


def _normalize_codes(values: Iterable[str] | None, allowed: set[str], *, empty_default: list[str]) -> list[str]:
    rows = sorted({str(value or "").strip().lower() for value in (values or []) if str(value or "").strip()})
    if not rows:
        return list(empty_default)
    if len(rows) > 8 or any(value not in allowed for value in rows):
        raise ValueError("unsupported_monitoring_code")
    return rows


def _validate_monitor(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "live_execution_monitoring_record_digest"):
        return False
    expected = _digest({
        "monitor_id": str(record.get("monitor_id") or ""),
        "launch_id": str(record.get("launch_id") or ""),
        "launch_digest": str(record.get("launch_digest") or ""),
        "generation": int(record.get("generation") or 0),
        "current_stage": str(record.get("current_stage") or ""),
        "progress_percent": int(record.get("progress_percent") or 0),
        "last_event_digest": str(record.get("last_event_digest") or ""),
        "latest_intervention_request_digest": str(record.get("latest_intervention_request_digest") or ""),
    })
    return (
        str(record.get("monitor_digest") or "") == expected
        and str(record.get("monitor_id") or "").startswith("monitor_")
        and str(record.get("launch_id") or "").startswith("launch_")
        and int(record.get("generation") or 0) >= 1
        and str(record.get("current_stage") or "") in ALLOWED_STAGES
        and 0 <= int(record.get("progress_percent") or 0) <= 100
        and record.get("operator_intervention_applied") is False
        and record.get("pause_authorized") is False
        and record.get("stop_authorized") is False
    )


def _validate_event(record: Mapping[str, Any]) -> bool:
    return (
        _valid(record, "live_execution_progress_event_record_digest")
        and str(record.get("launch_id") or "").startswith("launch_")
        and str(record.get("monitor_id") or "").startswith("monitor_")
        and str(record.get("event_type") or "") in ALLOWED_EVENT_TYPES
        and str(record.get("current_stage") or "") in ALLOWED_STAGES
        and 0 <= int(record.get("progress_percent") or 0) <= 100
    )


def _validate_request(record: Mapping[str, Any]) -> bool:
    if not _valid(record, "live_execution_intervention_request_record_digest"):
        return False
    expected = _digest({
        "request_id": str(record.get("request_id") or ""),
        "monitor_id": str(record.get("monitor_id") or ""),
        "monitor_digest": str(record.get("monitor_digest") or ""),
        "launch_id": str(record.get("launch_id") or ""),
        "intervention_type": str(record.get("intervention_type") or ""),
    })
    return (
        str(record.get("request_digest") or "") == expected
        and str(record.get("request_id") or "").startswith("intervention_")
        and str(record.get("intervention_type") or "") in INTERVENTION_TYPES
        and str(record.get("request_state") or "") == "pending_v1228_action"
        and record.get("operator_intervention_applied") is False
    )


def _load_current_launch(launch_id: str, expected_launch_digest: str, runtime_root=None) -> dict[str, Any]:
    launch = inspect_bounded_development_execution_session(str(launch_id or "").lower(), runtime_root=runtime_root)
    if launch.get("ok") is not True:
        raise ValueError(str(launch.get("reason") or "bounded_launch_missing_or_stale"))
    if str(launch.get("launch_digest") or "") != str(expected_launch_digest or ""):
        raise ValueError("stale_bounded_launch_digest")
    if str(launch.get("session_state") or "") != "active":
        raise ValueError("bounded_launch_not_active")
    return launch


def _monitor_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _monitor_root(runtime_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("launch_*.json"))[: MAX_MONITORED_SESSIONS + 1]:
        row = _read_json(path)
        if not row or not _validate_monitor(row) or path.stem != row.get("launch_id"):
            raise ValueError("live_execution_monitor_tampered_or_malformed")
        rows.append(row)
    if len(rows) > MAX_MONITORED_SESSIONS:
        raise ValueError("live_execution_monitor_limit_exceeded")
    return rows


def _request_rows(runtime_root=None) -> list[dict[str, Any]]:
    root = _request_root(runtime_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("intervention_*.json"))[: MAX_INTERVENTION_REQUESTS + 1]:
        row = _read_json(path)
        if not row or not _validate_request(row) or path.stem != row.get("request_id"):
            raise ValueError("intervention_request_tampered_or_malformed")
        rows.append(row)
    if len(rows) > MAX_INTERVENTION_REQUESTS:
        raise ValueError("intervention_request_limit_exceeded")
    return rows


def _event_record(
    *,
    monitor_id: str,
    launch: Mapping[str, Any],
    generation: int,
    event_type: str,
    current_stage: str,
    completed_units: int,
    total_units: int,
    blocker_codes: list[str],
    risk_codes: list[str],
    operator_attention_required: bool,
    previous_event_digest: str,
) -> dict[str, Any]:
    percent = 0 if total_units <= 0 else min(100, max(0, int((completed_units * 100) / total_units)))
    event_digest = _digest({
        "monitor_id": monitor_id,
        "launch_id": str(launch.get("launch_id") or ""),
        "launch_digest": str(launch.get("launch_digest") or ""),
        "generation": generation,
        "event_type": event_type,
        "current_stage": current_stage,
        "completed_units": completed_units,
        "total_units": total_units,
        "progress_percent": percent,
        "blocker_codes": blocker_codes,
        "risk_codes": risk_codes,
        "operator_attention_required": bool(operator_attention_required),
        "previous_event_digest": previous_event_digest,
    })
    row = {
        "ok": True,
        "status": "live_execution_progress_recorded",
        "monitor_id": monitor_id,
        "launch_id": str(launch.get("launch_id") or ""),
        "launch_digest": str(launch.get("launch_digest") or ""),
        "generation": generation,
        "event_type": event_type,
        "current_stage": current_stage,
        "completed_units": completed_units,
        "total_units": total_units,
        "progress_percent": percent,
        "blocker_codes": blocker_codes,
        "risk_codes": risk_codes,
        "operator_attention_required": bool(operator_attention_required),
        "previous_event_digest": previous_event_digest,
        "event_digest": event_digest,
        **_base(),
    }
    return _sealed(row, "live_execution_progress_event_record_digest")


def _monitor_from_event(launch: Mapping[str, Any], event: Mapping[str, Any], *, latest_request_digest: str = "") -> dict[str, Any]:
    monitor_id = str(event.get("monitor_id") or "")
    monitor_digest = _digest({
        "monitor_id": monitor_id,
        "launch_id": str(launch.get("launch_id") or ""),
        "launch_digest": str(launch.get("launch_digest") or ""),
        "generation": int(event.get("generation") or 0),
        "current_stage": str(event.get("current_stage") or ""),
        "progress_percent": int(event.get("progress_percent") or 0),
        "last_event_digest": str(event.get("event_digest") or ""),
        "latest_intervention_request_digest": str(latest_request_digest or ""),
    })
    row = {
        "ok": True,
        "status": "live_execution_monitoring_ready",
        "monitor_id": monitor_id,
        "monitor_digest": monitor_digest,
        "launch_id": str(launch.get("launch_id") or ""),
        "launch_digest": str(launch.get("launch_digest") or ""),
        "source_session_id": str(launch.get("source_session_id") or ""),
        "source_session_digest": str(launch.get("source_session_digest") or ""),
        "queue_item_id": str(launch.get("queue_item_id") or ""),
        "project_reference": str(launch.get("project_reference") or ""),
        "proposal_id": str(launch.get("proposal_id") or ""),
        "generation": int(event.get("generation") or 0),
        "session_state": str(launch.get("session_state") or "active"),
        "monitoring_state": "active",
        "current_stage": str(event.get("current_stage") or ""),
        "last_event_type": str(event.get("event_type") or ""),
        "completed_units": int(event.get("completed_units") or 0),
        "total_units": int(event.get("total_units") or 0),
        "progress_percent": int(event.get("progress_percent") or 0),
        "blocker_codes": list(event.get("blocker_codes") or []),
        "risk_codes": list(event.get("risk_codes") or []),
        "operator_attention_required": bool(event.get("operator_attention_required")),
        "last_event_digest": str(event.get("event_digest") or ""),
        "latest_intervention_request_digest": str(latest_request_digest or ""),
        "fresh_step_authorization_required": True,
        "mindful_progress_reporting": True,
        **_base(),
    }
    return _sealed(row, "live_execution_monitoring_record_digest")


def prepare_live_execution_monitoring(
    launch_id: str,
    *,
    expected_launch_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        with _lock(runtime_root):
            launch = _load_current_launch(launch_id, expected_launch_digest, runtime_root)
            path = _monitor_path(launch_id, runtime_root)
            existing = _read_json(path)
            if existing:
                if not _validate_monitor(existing):
                    raise ValueError("live_execution_monitor_tampered_or_malformed")
                if str(existing.get("launch_digest") or "") != expected_launch_digest:
                    raise ValueError("stale_live_execution_monitor_launch")
                return {**existing, "operation_status": "resumed"}
            monitor_id = "monitor_" + _digest({
                "launch_id": str(launch.get("launch_id") or ""),
                "launch_digest": str(launch.get("launch_digest") or ""),
            })[:24]
            event = _event_record(
                monitor_id=monitor_id,
                launch=launch,
                generation=1,
                event_type="monitoring_started",
                current_stage="launched_waiting_for_step_authorization",
                completed_units=0,
                total_units=1,
                blocker_codes=["authorization_required"],
                risk_codes=["none"],
                operator_attention_required=False,
                previous_event_digest="",
            )
            monitor = _monitor_from_event(launch, event)
            _atomic_json(_event_path(launch_id, 1, runtime_root), event)
            _atomic_json(path, monitor)
            return {**monitor, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("live_execution_monitoring_blocked", str(exc))


def load_live_execution_monitoring(launch_id: str, *, runtime_root=None) -> dict[str, Any]:
    row = _read_json(_monitor_path(str(launch_id or "").lower(), runtime_root))
    return row if row and _validate_monitor(row) else {}


def inspect_live_execution_monitoring(launch_id: str, *, runtime_root=None) -> dict[str, Any]:
    try:
        row = load_live_execution_monitoring(launch_id, runtime_root=runtime_root)
        if not row:
            raise ValueError("live_execution_monitor_missing_or_invalid")
        _load_current_launch(str(row.get("launch_id") or ""), str(row.get("launch_digest") or ""), runtime_root)
        event = _read_json(_event_path(str(row.get("launch_id") or ""), int(row.get("generation") or 0), runtime_root))
        if not event or not _validate_event(event) or str(event.get("event_digest") or "") != str(row.get("last_event_digest") or ""):
            raise ValueError("live_execution_progress_event_missing_or_invalid")
        latest_request = str(row.get("latest_intervention_request_digest") or "")
        if latest_request:
            matches = [request for request in _request_rows(runtime_root) if request.get("request_digest") == latest_request]
            if len(matches) != 1:
                raise ValueError("latest_intervention_request_missing_or_invalid")
        displayed = dict(row)
        try:
            from execution_session_pause_resume_cancel_recovery import get_effective_execution_session_state
            effective_state = get_effective_execution_session_state(
                str(row.get("launch_id") or ""), runtime_root=runtime_root
            )
            displayed["session_state"] = effective_state
            if effective_state != "active":
                displayed["monitoring_state"] = effective_state
        except Exception:
            pass
        return displayed
    except (OSError, ValueError) as exc:
        return _failure("live_execution_monitoring_expired", str(exc))


def record_live_execution_progress(
    launch_id: str,
    *,
    expected_launch_digest: str,
    event_type: str,
    current_stage: str,
    completed_units: int,
    total_units: int,
    blocker_codes: Iterable[str] | None = None,
    risk_codes: Iterable[str] | None = None,
    operator_attention_required: bool = False,
    runtime_root=None,
) -> dict[str, Any]:
    try:
        event_type = str(event_type or "").strip().lower()
        current_stage = str(current_stage or "").strip().lower()
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError("unsupported_progress_event_type")
        if current_stage not in ALLOWED_STAGES:
            raise ValueError("unsupported_execution_stage")
        completed_units = int(completed_units)
        total_units = int(total_units)
        if total_units < 1 or completed_units < 0 or completed_units > total_units or total_units > 100000:
            raise ValueError("invalid_progress_units")
        blockers = _normalize_codes(blocker_codes, ALLOWED_BLOCKER_CODES, empty_default=[])
        risks = _normalize_codes(risk_codes, ALLOWED_RISK_CODES, empty_default=["none"])
        if current_stage == "blocked" and not blockers:
            raise ValueError("blocked_stage_requires_blocker")
        if current_stage == "completed_pending_review" and completed_units != total_units:
            raise ValueError("completed_stage_requires_full_progress")
        monitor = load_live_execution_monitoring(launch_id, runtime_root=runtime_root)
        if not monitor:
            created = prepare_live_execution_monitoring(
                launch_id, expected_launch_digest=expected_launch_digest, runtime_root=runtime_root
            )
            if created.get("ok") is not True:
                raise ValueError(str(created.get("reason") or "monitoring_preparation_failed"))
        with _lock(runtime_root):
            launch = _load_current_launch(launch_id, expected_launch_digest, runtime_root)
            monitor = load_live_execution_monitoring(launch_id, runtime_root=runtime_root)
            if not monitor:
                raise ValueError("live_execution_monitor_missing_after_preparation")
            if str(monitor.get("launch_digest") or "") != expected_launch_digest:
                raise ValueError("stale_live_execution_monitor_launch")
            generation = int(monitor.get("generation") or 0) + 1
            if generation > MAX_PROGRESS_EVENTS_PER_SESSION:
                raise ValueError("progress_event_limit_exceeded")
            event = _event_record(
                monitor_id=str(monitor.get("monitor_id") or ""),
                launch=launch,
                generation=generation,
                event_type=event_type,
                current_stage=current_stage,
                completed_units=completed_units,
                total_units=total_units,
                blocker_codes=blockers,
                risk_codes=risks,
                operator_attention_required=bool(operator_attention_required),
                previous_event_digest=str(monitor.get("last_event_digest") or ""),
            )
            updated = _monitor_from_event(
                launch,
                event,
                latest_request_digest=str(monitor.get("latest_intervention_request_digest") or ""),
            )
            _atomic_json(_event_path(launch_id, generation, runtime_root), event)
            _atomic_json(_monitor_path(launch_id, runtime_root), updated)
            return {**updated, "operation_status": "updated"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("live_execution_progress_blocked", str(exc))


def request_live_execution_intervention(
    intervention_type: str,
    *,
    monitor_id: str,
    expected_monitor_digest: str,
    exact_phrase: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    try:
        intervention_type = str(intervention_type or "").strip().lower().replace(" ", "_")
        if intervention_type not in INTERVENTION_TYPES:
            raise ValueError("unsupported_intervention_type")
        with _lock(runtime_root):
            monitors = _monitor_rows(runtime_root)
            monitor = next((row for row in monitors if row.get("monitor_id") == str(monitor_id or "").lower()), None)
            if not monitor:
                raise ValueError("live_execution_monitor_missing_or_invalid")
            seed = _digest({
                "monitor_id": str(monitor_id or "").lower(),
                "monitor_digest": str(expected_monitor_digest or "").lower(),
                "intervention_type": intervention_type,
            })
            request_id = "intervention_" + seed[:24]
            existing = _read_json(_request_path(request_id, runtime_root))
            if existing:
                if not _validate_request(existing):
                    raise ValueError("intervention_request_tampered_or_malformed")
                return {**existing, "operation_status": "replayed"}
            current = inspect_live_execution_monitoring(str(monitor.get("launch_id") or ""), runtime_root=runtime_root)
            if current.get("ok") is not True:
                raise ValueError(str(current.get("reason") or "live_execution_monitor_expired"))
            if str(current.get("monitor_digest") or "") != str(expected_monitor_digest or ""):
                raise ValueError("stale_live_execution_monitor_digest")
            unresolved = []
            for candidate in _request_rows(runtime_root):
                if candidate.get("launch_id") != current.get("launch_id") or candidate.get("request_state") != "pending_v1228_action":
                    continue
                resolved = False
                try:
                    from execution_session_pause_resume_cancel_recovery import intervention_request_resolution
                    resolved = bool(intervention_request_resolution(
                        str(candidate.get("request_id") or ""), runtime_root=runtime_root
                    ))
                except Exception:
                    resolved = False
                if not resolved:
                    unresolved.append(candidate)
            if unresolved:
                raise ValueError("conflicting_pending_intervention_request")
            request_digest = _digest({
                "request_id": request_id,
                "monitor_id": str(current.get("monitor_id") or ""),
                "monitor_digest": str(current.get("monitor_digest") or ""),
                "launch_id": str(current.get("launch_id") or ""),
                "intervention_type": intervention_type,
            })
            row = {
                "ok": True,
                "status": "live_execution_intervention_requested",
                "request_id": request_id,
                "request_digest": request_digest,
                "request_state": "pending_v1228_action",
                "intervention_type": intervention_type,
                "monitor_id": str(current.get("monitor_id") or ""),
                "monitor_digest": str(current.get("monitor_digest") or ""),
                "launch_id": str(current.get("launch_id") or ""),
                "launch_digest": str(current.get("launch_digest") or ""),
                "queue_item_id": str(current.get("queue_item_id") or ""),
                "project_reference": str(current.get("project_reference") or ""),
                "proposal_id": str(current.get("proposal_id") or ""),
                "current_stage": str(current.get("current_stage") or ""),
                "progress_percent": int(current.get("progress_percent") or 0),
                "operator_attention_required": True,
                "exact_phrase_digest": _digest(str(exact_phrase or "")),
                "fresh_v1228_authorization_required": True,
                **_base(),
            }
            row = _sealed(row, "live_execution_intervention_request_record_digest")
            _atomic_json(_request_path(request_id, runtime_root), row)
            event = _read_json(_event_path(str(current.get("launch_id") or ""), int(current.get("generation") or 0), runtime_root))
            if not event or not _validate_event(event):
                raise ValueError("live_execution_progress_event_missing_or_invalid")
            updated = _monitor_from_event(current, event, latest_request_digest=request_digest)
            # _monitor_from_event only reads launch identity fields; restore source identity from current.
            for key in ("source_session_id", "source_session_digest", "queue_item_id", "project_reference", "proposal_id", "session_state"):
                updated[key] = current.get(key)
            updated["monitor_digest"] = _digest({
                "monitor_id": str(updated.get("monitor_id") or ""),
                "launch_id": str(updated.get("launch_id") or ""),
                "launch_digest": str(updated.get("launch_digest") or ""),
                "generation": int(updated.get("generation") or 0),
                "current_stage": str(updated.get("current_stage") or ""),
                "progress_percent": int(updated.get("progress_percent") or 0),
                "last_event_digest": str(updated.get("last_event_digest") or ""),
                "latest_intervention_request_digest": request_digest,
            })
            updated = _sealed(updated, "live_execution_monitoring_record_digest")
            _atomic_json(_monitor_path(str(current.get("launch_id") or ""), runtime_root), updated)
            return {**row, "operation_status": "created"}
    except (OSError, ValueError, TimeoutError) as exc:
        return _failure("live_execution_intervention_request_blocked", str(exc))


def _public_monitor(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    allowed = {
        "ok", "status", "monitor_id", "monitor_digest", "launch_id", "launch_digest",
        "source_session_id", "source_session_digest", "queue_item_id", "project_reference", "proposal_id",
        "generation", "session_state", "monitoring_state", "current_stage", "last_event_type",
        "completed_units", "total_units", "progress_percent", "blocker_codes", "risk_codes",
        "operator_attention_required", "last_event_digest", "latest_intervention_request_digest",
        "fresh_step_authorization_required", "mindful_progress_reporting", "operation_status",
    }
    row = {key: record.get(key) for key in allowed if key in record}
    row.update(_base())
    row["public_live_execution_monitoring_digest"] = _digest(row)
    return row


def _public_request(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("ok") is not True:
        return {key: record.get(key) for key in ("ok", "status", "reason") if key in record} | _base()
    allowed = {
        "ok", "status", "request_id", "request_digest", "request_state", "intervention_type",
        "monitor_id", "monitor_digest", "launch_id", "launch_digest", "queue_item_id",
        "project_reference", "proposal_id", "current_stage", "progress_percent",
        "operator_attention_required", "fresh_v1228_authorization_required", "operation_status",
    }
    row = {key: record.get(key) for key in allowed if key in record}
    row.update(_base())
    row["public_live_execution_intervention_request_digest"] = _digest(row)
    return row


def public_live_execution_monitoring_sessions(*, runtime_root=None) -> dict[str, Any]:
    try:
        rows = []
        for monitor in _monitor_rows(runtime_root):
            inspected = inspect_live_execution_monitoring(str(monitor.get("launch_id") or ""), runtime_root=runtime_root)
            rows.append(_public_monitor(inspected))
        result = {
            "ok": True,
            "status": "live_execution_monitoring_session_list_ready",
            "monitor_count": len(rows),
            "monitors": rows,
            **_base(),
        }
        result["public_live_execution_monitoring_session_list_digest"] = _digest(result)
        return result
    except (OSError, ValueError) as exc:
        return _failure("live_execution_monitoring_session_list_blocked", str(exc))


def public_live_execution_intervention_requests(*, runtime_root=None) -> dict[str, Any]:
    try:
        rows = []
        for raw in _request_rows(runtime_root):
            row = _public_request(raw)
            try:
                from execution_session_pause_resume_cancel_recovery import intervention_request_resolution
                resolution = intervention_request_resolution(str(raw.get("request_id") or ""), runtime_root=runtime_root)
                if resolution:
                    row["request_state"] = str(resolution.get("request_state") or "resolved_by_v1228")
                    row["resolution_action"] = str(resolution.get("action") or "")
                    row["resolution_transition_id"] = str(resolution.get("transition_id") or "")
            except Exception:
                pass
            rows.append(row)
        result = {
            "ok": True,
            "status": "live_execution_intervention_request_list_ready",
            "request_count": len(rows),
            "requests": rows,
            **_base(),
        }
        result["public_live_execution_intervention_request_list_digest"] = _digest(result)
        return result
    except (OSError, ValueError) as exc:
        return _failure("live_execution_intervention_request_list_blocked", str(exc))


def live_execution_monitoring_response(record: Mapping[str, Any]) -> str:
    if record.get("ok") is not True:
        return f"Live execution monitoring was blocked: {record.get('reason', record.get('status') or 'invalid evidence')}."
    status = str(record.get("status") or "")
    if status == "live_execution_monitoring_ready":
        return (
            f"Live monitoring {record.get('monitor_id')} is active for session {record.get('launch_id')}. "
            f"Stage: {record.get('current_stage')}; progress: {record.get('progress_percent', 0)}%; "
            f"operator attention required: {bool(record.get('operator_attention_required'))}. "
            "Monitoring grants no execution or intervention authority."
        )
    if status == "live_execution_intervention_requested":
        return (
            f"Intervention request {record.get('request_id')} recorded: {record.get('intervention_type')}. "
            "No pause, stop, resume, cancel, provider, command, test, workspace, or project action was applied. "
            "A fresh v1228 control remains required."
        )
    if status == "live_execution_monitoring_session_list_ready":
        return f"There are {record.get('monitor_count', 0)} live execution monitoring sessions."
    if status == "live_execution_intervention_request_list_ready":
        return f"There are {record.get('request_count', 0)} live execution intervention requests."
    return f"The live execution monitoring control recorded: {status}."


def process_live_execution_monitoring_operator_intervention_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    text = str(user_text or "").strip()
    prepare = _PREPARE.fullmatch(text)
    show_one = _SHOW_ONE.fullmatch(text)
    request = _REQUEST.fullmatch(text)
    if prepare:
        result = _public_monitor(prepare_live_execution_monitoring(
            prepare.group("launch").lower(),
            expected_launch_digest=prepare.group("digest").lower(),
            runtime_root=runtime_root,
        ))
    elif _SHOW_ALL.fullmatch(text):
        result = public_live_execution_monitoring_sessions(runtime_root=runtime_root)
    elif show_one:
        result = _public_monitor(inspect_live_execution_monitoring(show_one.group("launch").lower(), runtime_root=runtime_root))
    elif request:
        result = _public_request(request_live_execution_intervention(
            request.group("kind").lower(),
            monitor_id=request.group("monitor").lower(),
            expected_monitor_digest=request.group("digest").lower(),
            exact_phrase=text,
            runtime_root=runtime_root,
        ))
    elif _SHOW_REQUESTS.fullmatch(text):
        result = public_live_execution_intervention_requests(runtime_root=runtime_root)
    else:
        return {"active": False, "event": "inactive"}
    return {
        "active": True,
        "event": str(result.get("status") or "live_execution_monitoring_blocked"),
        "live_execution_monitoring": result,
        "conversation_response": live_execution_monitoring_response(result),
    }
