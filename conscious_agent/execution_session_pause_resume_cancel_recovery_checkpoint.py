from __future__ import annotations

"""Read-only v1228.9 Execution Pause, Resume, Cancel, and Recovery checkpoint."""

import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from execution_session_pause_resume_cancel_recovery import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, MAX_CONTROL_STATES, MAX_RECOVERY_ATTEMPTS, MAX_TRANSITION_AUTHORIZATIONS, MAX_TRANSITIONS_PER_SESSION, REQUEST_ACTION_MAP, SAFE_PAUSE_STAGES, SESSION_STATES, TRANSITION_ACTIONS, UNSAFE_ACTIVE_STAGES, _authorization_digest, _base, _control_digest, _public_authorization, _public_control, _public_transition, _sealed, _validate_authorization, _validate_consumption, _validate_control, _validate_transition

CONTRACT_VERSION = "v1228.9"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(source: Path) -> tuple[str, int]:
    rows: list[tuple[str, str]] = []
    for path in sorted(p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rows.append((path.relative_to(source).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(rows), len(rows)


def _synthetic_records() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    launch_id = "launch_0123456789abcdef01234567"
    launch_digest = hashlib.sha256(b"launch-v1228").hexdigest()
    control_id = "control_0123456789abcdef01234567"
    control = {
        "ok": True,
        "status": "execution_session_control_ready",
        "control_id": control_id,
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "source_session_id": "session_0123456789abcdef01234567",
        "source_session_digest": hashlib.sha256(b"session-v1228").hexdigest(),
        "queue_item_id": "work_0123456789abcdef01234567",
        "project_reference": "project_0123456789abcdef",
        "proposal_id": "devc_0123456789abcdef01234567",
        "generation": 2,
        "session_state": "paused",
        "pending_action": "",
        "latest_request_id": "intervention_0123456789abcdef01234567",
        "last_transition_digest": hashlib.sha256(b"transition-v1228").hexdigest(),
        "recovery_attempts": 0,
        "runtime_namespace_present": True,
        "fresh_transition_authorization_required": True,
        "fresh_resume_authorization_required": True,
        **_base(),
    }
    control["control_digest"] = _control_digest(control)
    control = _sealed(control, "execution_session_control_record_digest")

    authorization_id = "transition_auth_0123456789abcdef01234567"
    authorization = {
        "ok": True,
        "status": "execution_session_transition_authorization_ready",
        "authorization_id": authorization_id,
        "action": "resume",
        "control_id": control_id,
        "control_digest": control["control_digest"],
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "request_id": "",
        "request_digest": "",
        "authorization_consumed": False,
        "authorize_phrase": "synthetic exact authorization phrase",
        **_base(),
    }
    authorization["authorization_digest"] = _authorization_digest(authorization)
    authorization = _sealed(authorization, "execution_session_transition_authorization_record_digest")

    transition_id = "transition_0123456789abcdef01234567"
    transition_digest = _digest({
        "transition_id": transition_id,
        "control_id": control_id,
        "generation": 3,
        "action": "resume",
        "from_state": "paused",
        "to_state": "active",
        "authorization_id": authorization_id,
    })
    transition = {
        "ok": True,
        "status": "execution_session_transition_applied",
        "transition_id": transition_id,
        "transition_digest": transition_digest,
        "control_id": control_id,
        "launch_id": launch_id,
        "generation": 3,
        "action": "resume",
        "from_state": "paused",
        "to_state": "active",
        "pending_safe_boundary_stage": "",
        "authorization_id": authorization_id,
        "authorization_digest": authorization["authorization_digest"],
        "request_id": "",
        "request_digest": "",
        "transition_authorization_consumed": True,
        **_base(),
        "transition_authorization_consumed": True,
        "pause_applied": False,
        "resume_applied": True,
        "cancel_applied": False,
        "recovery_applied": False,
    }
    transition = _sealed(transition, "execution_session_transition_record_digest")
    consumption = {
        "ok": True,
        "status": "execution_session_transition_authorization_consumed",
        "authorization_id": authorization_id,
        "authorization_digest": authorization["authorization_digest"],
        "transition_id": transition_id,
        "transition_digest": transition_digest,
        "authorization_consumed": True,
        "consumption_count": 1,
        "old_authority_reusable": False,
        "content_free": True,
    }
    consumption = _sealed(consumption, "execution_session_transition_authorization_consumption_record_digest")
    return control, authorization, transition, consumption


def build_execution_session_pause_resume_cancel_recovery_checkpoint(*, source_root=None, runtime_root=None):
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    control, authorization, transition, consumption = _synthetic_records()
    public_control = _public_control(control)
    public_authorization = _public_authorization(authorization)
    public_transition = _public_transition(transition)
    for value in (
        _validate_control(control),
        _validate_authorization(authorization),
        _validate_transition(transition),
        _validate_consumption(consumption),
        public_control["ok"] is True,
        public_control["status"] == "execution_session_control_ready",
        public_control["control_id"].startswith("control_"),
        len(public_control["control_digest"]) == 64,
        public_control["session_state"] == "paused",
        public_control["runtime_namespace_present"] is True,
        public_control["fresh_transition_authorization_required"] is True,
        public_control["fresh_resume_authorization_required"] is True,
        public_authorization["ok"] is True,
        public_authorization["status"] == "execution_session_transition_authorization_ready",
        public_authorization["authorization_id"].startswith("transition_auth_"),
        len(public_authorization["authorization_digest"]) == 64,
        public_authorization["action"] == "resume",
        public_authorization["authorization_consumed"] is False,
        public_transition["ok"] is True,
        public_transition["status"] == "execution_session_transition_applied",
        public_transition["transition_id"].startswith("transition_"),
        public_transition["from_state"] == "paused",
        public_transition["to_state"] == "active",
        public_transition["resume_applied"] is True,
        public_transition["transition_authorization_consumed"] is True,
        public_control["content_free"] is True,
        public_control["runtime_records_external"] is True,
        public_control["safe_boundary_pause_required"] is True,
        public_control["fresh_resume_authorization_required"] is True,
        public_control["recovery_defaults_to_paused"] is True,
        public_control["goal_alignment_preserved"] is True,
        public_control["uncertainty_preserved"] is True,
        public_control["eventual_outcome_reflection_required"] is True,
    ):
        check(value)

    for record in (public_control, public_authorization, public_transition):
        for key in (
            "provider_execution_authorized", "command_execution_authorized", "test_execution_authorized",
            "workspace_materialization_authorized", "project_mutation_authorized", "background_execution_authorized",
            "cognition_write_authorized", "installation_authorized", "promotion_authorized", "release_authorized",
            "model_management_authorized", "old_authority_reusable",
        ):
            check(record.get(key) is False)
        for key in (
            "provider_contacted", "commands_executed", "tests_executed", "workspace_materialized",
            "project_modified", "selected_project_modified", "source_modified", "private_request_exposed",
            "private_path_exposed", "private_content_exposed", "project_name_exposed",
            "raw_provider_output_exposed", "raw_test_output_exposed", "cognition_written",
        ):
            check(record.get(key) is False)

    check(RETAINED_CONTRACT_VERSION == "v1228.8")
    check(MAX_CONTROL_STATES == 100)
    check(MAX_TRANSITIONS_PER_SESSION == 100)
    check(MAX_TRANSITION_AUTHORIZATIONS == 200)
    check(MAX_RECOVERY_ATTEMPTS == 10)
    check(TRANSITION_ACTIONS == {"acknowledge_review", "pause", "resume", "cancel", "recover"})
    check(REQUEST_ACTION_MAP == {"operator_review": "acknowledge_review", "pause": "pause", "stop": "cancel"})
    check("active" in SESSION_STATES and "paused" in SESSION_STATES and "cancelled" in SESSION_STATES)
    check("recovery_required" in SESSION_STATES)
    check("step_authorization_review" in SAFE_PAUSE_STAGES)
    check("provider_step_active" in UNSAFE_ACTIVE_STAGES)
    check(AUTHORITY_FLAGS["session_control_authorized"] is True)
    check(AUTHORITY_FLAGS["transition_authorization_required"] is True)
    check(AUTHORITY_FLAGS["pause_applied"] is False)
    check(AUTHORITY_FLAGS["provider_execution_authorized"] is False)

    tampered_control = dict(control); tampered_control["session_state"] = "cancelled"
    tampered_authorization = dict(authorization); tampered_authorization["action"] = "cancel"
    tampered_transition = dict(transition); tampered_transition["to_state"] = "cancelled"
    tampered_consumption = dict(consumption); tampered_consumption["consumption_count"] = 2
    check(_validate_control(tampered_control) is False)
    check(_validate_authorization(tampered_authorization) is False)
    check(_validate_transition(tampered_transition) is False)
    check(_validate_consumption(tampered_consumption) is False)

    module = (source / "conscious_agent" / "execution_session_pause_resume_cancel_recovery.py").read_text(encoding="utf-8")
    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    api = (source / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
    cli = (source / "eidolon.py").read_text(encoding="utf-8")
    release = (source / "tools" / "release_verify.py").read_text(encoding="utf-8")
    metadata = (source / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    for value in (
        "process_execution_session_pause_resume_cancel_recovery_control" in ordinary,
        "execution-session-pause-resume-cancel-recovery-checkpoint" in api,
        "execution-session-pause-resume-cancel-recovery-checkpoint" in cli,
        "v1228.9-execution-session-pause-resume-cancel-recovery-checkpoint" in release,
        'WORKING_SOURCE_VERSION = "1228.9"' in metadata,
        'NEXT_RECOMMENDED_ARC = "v1229.0-v1229.2 Execution Outcome Reflection and Learning Integration Foundations"' in metadata,
        "LocalModelClient" not in module,
        "recovery_defaults_to_paused" in module,
        '"provider_execution_authorized": False' in module,
        '"project_mutation_authorized": False' in module,
        "fresh_resume_authorization_required" in module,
    ):
        check(value)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next(
        (row for row in registry["checkpoints"] if row["checkpoint_id"] == "execution-session-pause-resume-cancel-recovery-checkpoint"),
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
        "status": "execution_session_pause_resume_cancel_recovery_checkpoint_ready" if ok else "execution_session_pause_resume_cancel_recovery_checkpoint_failed",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "runtime_data_read": False,
        "source_modified": False,
        "project_modified": False,
        "authority_granted": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "pause_applied": False,
        "resume_applied": False,
        "cancel_applied": False,
        "recovery_applied": False,
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
