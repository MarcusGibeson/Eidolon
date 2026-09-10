from __future__ import annotations

"""Read-only v1227.9 Live Execution Monitoring and Operator Intervention checkpoint."""

import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from live_execution_monitoring_operator_intervention import ALLOWED_BLOCKER_CODES, ALLOWED_EVENT_TYPES, ALLOWED_RISK_CODES, ALLOWED_STAGES, AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, INTERVENTION_TYPES, MAX_INTERVENTION_REQUESTS, MAX_MONITORED_SESSIONS, MAX_PROGRESS_EVENTS_PER_SESSION, _base, _public_monitor, _public_request, _sealed, _validate_event, _validate_monitor, _validate_request

CONTRACT_VERSION = "v1227.9"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(rows), len(rows)


def _synthetic_records() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    launch_id = "launch_0123456789abcdef01234567"
    launch_digest = hashlib.sha256(b"launch").hexdigest()
    monitor_id = "monitor_0123456789abcdef01234567"
    event_digest = _digest({
        "monitor_id": monitor_id,
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "generation": 2,
        "event_type": "progress_updated",
        "current_stage": "step_authorization_review",
        "completed_units": 1,
        "total_units": 4,
        "progress_percent": 25,
        "blocker_codes": ["authorization_required"],
        "risk_codes": ["uncertainty_high"],
        "operator_attention_required": True,
        "previous_event_digest": hashlib.sha256(b"event-1").hexdigest(),
    })
    event = {
        "ok": True,
        "status": "live_execution_progress_recorded",
        "monitor_id": monitor_id,
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "generation": 2,
        "event_type": "progress_updated",
        "current_stage": "step_authorization_review",
        "completed_units": 1,
        "total_units": 4,
        "progress_percent": 25,
        "blocker_codes": ["authorization_required"],
        "risk_codes": ["uncertainty_high"],
        "operator_attention_required": True,
        "previous_event_digest": hashlib.sha256(b"event-1").hexdigest(),
        "event_digest": event_digest,
        **_base(),
    }
    event = _sealed(event, "live_execution_progress_event_record_digest")
    monitor_digest = _digest({
        "monitor_id": monitor_id,
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "generation": 2,
        "current_stage": "step_authorization_review",
        "progress_percent": 25,
        "last_event_digest": event_digest,
        "latest_intervention_request_digest": "",
    })
    monitor = {
        "ok": True,
        "status": "live_execution_monitoring_ready",
        "monitor_id": monitor_id,
        "monitor_digest": monitor_digest,
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "source_session_id": "session_0123456789abcdef01234567",
        "source_session_digest": hashlib.sha256(b"session").hexdigest(),
        "queue_item_id": "work_0123456789abcdef01234567",
        "project_reference": "project_0123456789abcdef",
        "proposal_id": "devc_0123456789abcdef01234567",
        "generation": 2,
        "session_state": "active",
        "monitoring_state": "active",
        "current_stage": "step_authorization_review",
        "last_event_type": "progress_updated",
        "completed_units": 1,
        "total_units": 4,
        "progress_percent": 25,
        "blocker_codes": ["authorization_required"],
        "risk_codes": ["uncertainty_high"],
        "operator_attention_required": True,
        "last_event_digest": event_digest,
        "latest_intervention_request_digest": "",
        "fresh_step_authorization_required": True,
        "mindful_progress_reporting": True,
        **_base(),
    }
    monitor = _sealed(monitor, "live_execution_monitoring_record_digest")
    request_id = "intervention_0123456789abcdef01234567"
    request_digest = _digest({
        "request_id": request_id,
        "monitor_id": monitor_id,
        "monitor_digest": monitor_digest,
        "launch_id": launch_id,
        "intervention_type": "operator_review",
    })
    request = {
        "ok": True,
        "status": "live_execution_intervention_requested",
        "request_id": request_id,
        "request_digest": request_digest,
        "request_state": "pending_v1228_action",
        "intervention_type": "operator_review",
        "monitor_id": monitor_id,
        "monitor_digest": monitor_digest,
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "queue_item_id": monitor["queue_item_id"],
        "project_reference": monitor["project_reference"],
        "proposal_id": monitor["proposal_id"],
        "current_stage": monitor["current_stage"],
        "progress_percent": monitor["progress_percent"],
        "operator_attention_required": True,
        "fresh_v1228_authorization_required": True,
        **_base(),
    }
    request = _sealed(request, "live_execution_intervention_request_record_digest")
    return monitor, event, request


def build_live_execution_monitoring_operator_intervention_checkpoint(*, source_root=None, runtime_root=None):
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    monitor, event, request = _synthetic_records()
    public_monitor = _public_monitor(monitor)
    public_request = _public_request(request)
    for value in (
        _validate_monitor(monitor),
        _validate_event(event),
        _validate_request(request),
        public_monitor["ok"] is True,
        public_monitor["status"] == "live_execution_monitoring_ready",
        public_monitor["monitor_id"].startswith("monitor_"),
        len(public_monitor["monitor_digest"]) == 64,
        public_monitor["launch_id"].startswith("launch_"),
        len(public_monitor["launch_digest"]) == 64,
        public_monitor["session_state"] == "active",
        public_monitor["monitoring_state"] == "active",
        public_monitor["current_stage"] == "step_authorization_review",
        public_monitor["progress_percent"] == 25,
        public_monitor["completed_units"] == 1,
        public_monitor["total_units"] == 4,
        public_monitor["operator_attention_required"] is True,
        public_monitor["fresh_step_authorization_required"] is True,
        public_monitor["mindful_progress_reporting"] is True,
        public_request["ok"] is True,
        public_request["status"] == "live_execution_intervention_requested",
        public_request["request_id"].startswith("intervention_"),
        len(public_request["request_digest"]) == 64,
        public_request["request_state"] == "pending_v1228_action",
        public_request["intervention_type"] == "operator_review",
        public_request["operator_attention_required"] is True,
        public_request["fresh_v1228_authorization_required"] is True,
        public_monitor["content_free"] is True,
        public_monitor["runtime_records_external"] is True,
        public_monitor["live_monitoring_is_not_execution_authority"] is True,
        public_monitor["intervention_request_is_not_intervention_authority"] is True,
        public_monitor["v1228_state_transition_required"] is True,
        public_monitor["goal_alignment_visible"] is True,
        public_monitor["uncertainty_visible"] is True,
        public_monitor["eventual_outcome_reflection_required"] is True,
    ):
        check(value)
    for key in (
        "operator_intervention_applied", "pause_authorized", "stop_authorized", "resume_authorized",
        "cancel_authorized", "provider_execution_authorized", "command_execution_authorized",
        "test_execution_authorized", "workspace_materialization_authorized", "project_mutation_authorized",
        "background_execution_authorized", "installation_authorized", "promotion_authorized",
        "release_authorized", "old_authority_reusable",
    ):
        check(public_monitor.get(key) is False)
        check(public_request.get(key) is False)
    for key in (
        "provider_contacted", "commands_executed", "tests_executed", "workspace_created", "project_modified",
        "selected_project_modified", "source_modified", "private_request_exposed", "private_path_exposed",
        "private_content_exposed", "project_name_exposed", "raw_provider_output_exposed",
        "raw_test_output_exposed", "cognition_written",
    ):
        check(public_monitor.get(key) is False)
        check(public_request.get(key) is False)

    check(RETAINED_CONTRACT_VERSION == "v1227.8")
    check(MAX_MONITORED_SESSIONS == 100)
    check(MAX_PROGRESS_EVENTS_PER_SESSION == 250)
    check(MAX_INTERVENTION_REQUESTS == 100)
    check(INTERVENTION_TYPES == {"operator_review", "pause", "stop"})
    check("monitoring_started" in ALLOWED_EVENT_TYPES)
    check("session_completed_pending_review" in ALLOWED_EVENT_TYPES)
    check("launched_waiting_for_step_authorization" in ALLOWED_STAGES)
    check("completed_pending_review" in ALLOWED_STAGES)
    check("authorization_required" in ALLOWED_BLOCKER_CODES)
    check("uncertainty_high" in ALLOWED_RISK_CODES)
    check(AUTHORITY_FLAGS["operator_intervention_applied"] is False)
    check(AUTHORITY_FLAGS["monitoring_authorized"] is True)

    tampered_monitor = dict(monitor)
    tampered_monitor["progress_percent"] = 90
    check(_validate_monitor(tampered_monitor) is False)
    tampered_event = dict(event)
    tampered_event["current_stage"] = "completed_pending_review"
    check(_validate_event(tampered_event) is False)
    tampered_request = dict(request)
    tampered_request["intervention_type"] = "pause"
    check(_validate_request(tampered_request) is False)

    module = (source / "conscious_agent" / "live_execution_monitoring_operator_intervention.py").read_text(encoding="utf-8")
    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api = (source / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
    cli = (source / "eidolon.py").read_text(encoding="utf-8")
    release = (source / "tools" / "release_verify.py").read_text(encoding="utf-8")
    for value in (
        "process_live_execution_monitoring_operator_intervention_control" in ordinary,
        "live-execution-monitoring-operator-intervention-checkpoint" in api,
        "live-execution-monitoring-operator-intervention-checkpoint" in cli,
        "v1227.9-live-execution-monitoring-operator-intervention-checkpoint" in release,
        "LocalModelClient" not in module,
        "intervention_request_is_not_intervention_authority" in module,
        "v1228_state_transition_required" in module,
        '"pause_authorized": False' in module,
        '"stop_authorized": False' in module,
        '"provider_execution_authorized": False' in module,
        '"project_mutation_authorized": False' in module,
    ):
        check(value)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry["checkpoints"] if row["checkpoint_id"] == "live-execution-monitoring-operator-intervention-checkpoint"),
        None,
    )
    for value in (
        descriptor is not None,
        (descriptor or {}).get("contract_version") == CONTRACT_VERSION,
        (descriptor or {}).get("read_only") is True,
        (descriptor or {}).get("post_available") is False,
        (descriptor or {}).get("required_input_count") == 0,
    ):
        check(value)

    after, after_count = _tree_signature(source)
    check(before == after and count == after_count)
    check(runtime is None or runtime.exists() is runtime_existed)
    ok = all(checks)
    return {
        "ok": ok,
        "status": "live_execution_monitoring_operator_intervention_checkpoint_ready" if ok else "live_execution_monitoring_operator_intervention_checkpoint_failed",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "runtime_data_read": False,
        "source_modified": False,
        "project_modified": False,
        "authority_granted": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "operator_intervention_applied": False,
        "pause_authorized": False,
        "stop_authorized": False,
        "content_free": True,
        "checks": len(checks),
        "passed": sum(checks),
        "source_file_count": count,
        "source_signature": before,
        "checkpoint_digest": _digest({
            "contract_version": CONTRACT_VERSION,
            "checks": len(checks),
            "passed": sum(checks),
            "source_signature": before,
        }),
    }
