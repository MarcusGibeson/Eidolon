from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from execution_session_authorization_bounded_launch import AUTHORITY_FLAGS, CONTRACT_VERSION as RETAINED_CONTRACT_VERSION, MAX_BOUNDED_EXECUTION_SESSIONS, MAX_LAUNCH_AUTHORIZATIONS, _base, _launch_bounds, _public_authorization, _public_launch, _sealed, _validate_authorization, _validate_consumption, _validate_launch

CONTRACT_VERSION = "v1226.9"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _tree_signature(root: Path) -> tuple[str, int]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            rows.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return _digest(rows), len(rows)


def _synthetic_records() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    session_id = "session_0123456789abcdef01234567"
    session_digest = hashlib.sha256(b"prepared-session").hexdigest()
    review_digest = hashlib.sha256(b"prepared-review").hexdigest()
    authorization_id = "launch_auth_0123456789abcdef01234567"
    queue_item_id = "work_0123456789abcdef01234567"
    project_reference = "project_0123456789abcdef"
    proposal_id = "devc_0123456789abcdef01234567"
    authorization_digest = _digest({
        "authorization_id": authorization_id,
        "source_session_id": session_id,
        "source_session_digest": session_digest,
        "source_prepared_review_digest": review_digest,
        "queue_item_id": queue_item_id,
        "project_reference": project_reference,
        "proposal_id": proposal_id,
    })
    authorization = {
        "ok": True,
        "status": "bounded_execution_session_launch_authorization_ready",
        "authorization_id": authorization_id,
        "authorization_digest": authorization_digest,
        "source_session_id": session_id,
        "source_session_digest": session_digest,
        "source_prepared_review_digest": review_digest,
        "source_schedule_digest": hashlib.sha256(b"schedule").hexdigest(),
        "source_queue_digest": hashlib.sha256(b"queue").hexdigest(),
        "queue_item_id": queue_item_id,
        "project_reference": project_reference,
        "proposal_id": proposal_id,
        "priority_rank": 1,
        "priority_level": "high",
        "dependency_item_ids": [],
        "requirements_digest": hashlib.sha256(b"requirements").hexdigest(),
        "authorization_consumed": False,
        "authorize_phrase": (
            f"Authorize bounded launch for prepared development execution session {session_id} "
            f"digest {session_digest} authorization {authorization_id} digest {authorization_digest}."
        ),
        **_base(),
    }
    authorization = _sealed(authorization, "bounded_launch_authorization_record_digest")

    launch_id = "launch_0123456789abcdef01234567"
    session = {
        "project_reference": project_reference,
        "queue_item_id": queue_item_id,
        "proposal_id": proposal_id,
    }
    bounds = _launch_bounds(session)
    bounds_digest = _digest(bounds)
    launch_digest = _digest({
        "launch_id": launch_id,
        "generation": 1,
        "authorization_id": authorization_id,
        "authorization_digest": authorization_digest,
        "source_session_id": session_id,
        "source_session_digest": session_digest,
        "queue_item_id": queue_item_id,
        "project_reference": project_reference,
        "proposal_id": proposal_id,
        "launch_bounds_digest": bounds_digest,
    })
    launch = {
        "ok": True,
        "status": "bounded_development_execution_session_launched",
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "generation": 1,
        "session_state": "active",
        "authorization_id": authorization_id,
        "authorization_digest": authorization_digest,
        "authorization_consumed": True,
        "source_session_id": session_id,
        "source_session_digest": session_digest,
        "source_prepared_review_digest": review_digest,
        "source_schedule_digest": authorization["source_schedule_digest"],
        "source_queue_digest": authorization["source_queue_digest"],
        "queue_item_id": queue_item_id,
        "project_reference": project_reference,
        "proposal_id": proposal_id,
        "priority_rank": 1,
        "priority_level": "high",
        "dependency_item_ids": [],
        "launch_bounds": bounds,
        "launch_bounds_digest": bounds_digest,
        "session_runtime_namespace_created": True,
        "project_workspace_materialized": False,
        "mindful_launch_gate_passed": True,
        "goal_alignment_review_required": True,
        "uncertainty_review_required": True,
        "outcome_reflection_required": True,
        "fresh_step_authorization_required": True,
        **_base(),
        "execution_session_launch_authorized": True,
        "execution_session_launched": True,
    }
    launch = _sealed(launch, "bounded_execution_session_launch_record_digest")
    consumption = {
        "ok": True,
        "status": "bounded_launch_authorization_consumed",
        "authorization_id": authorization_id,
        "authorization_digest": authorization_digest,
        "launch_id": launch_id,
        "launch_digest": launch_digest,
        "source_session_id": session_id,
        "source_session_digest": session_digest,
        "authorization_consumed": True,
        "consumption_count": 1,
        "old_authority_reusable": False,
        "content_free": True,
    }
    consumption = _sealed(consumption, "bounded_launch_authorization_consumption_record_digest")
    return authorization, launch, consumption


def build_execution_session_authorization_bounded_launch_checkpoint(*, source_root=None, runtime_root=None):
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root) if runtime_root is not None else None
    runtime_existed = runtime.exists() if runtime is not None else False
    before, count = _tree_signature(source)
    checks: list[bool] = []
    check = lambda value: checks.append(bool(value))

    authorization, launch, consumption = _synthetic_records()
    public_authorization = _public_authorization(authorization)
    public_launch = _public_launch(launch)
    for value in (
        _validate_authorization(authorization),
        _validate_launch(launch),
        _validate_consumption(consumption),
        public_authorization["ok"] is True,
        public_authorization["status"] == "bounded_execution_session_launch_authorization_ready",
        public_authorization["authorization_id"].startswith("launch_auth_"),
        len(public_authorization["authorization_digest"]) == 64,
        public_authorization["authorization_consumed"] is False,
        public_launch["ok"] is True,
        public_launch["status"] == "bounded_development_execution_session_launched",
        public_launch["launch_id"].startswith("launch_"),
        len(public_launch["launch_digest"]) == 64,
        public_launch["session_state"] == "active",
        public_launch["authorization_consumed"] is True,
        public_launch["execution_session_launch_authorized"] is True,
        public_launch["execution_session_launched"] is True,
        public_launch["session_runtime_namespace_created"] is True,
        public_launch["project_workspace_materialized"] is False,
        public_launch["mindful_launch_gate_passed"] is True,
        public_launch["goal_alignment_review_required"] is True,
        public_launch["uncertainty_review_required"] is True,
        public_launch["outcome_reflection_required"] is True,
        public_launch["fresh_step_authorization_required"] is True,
        public_launch["content_free"] is True,
        public_launch["runtime_records_external"] is True,
        public_launch["bounded_launch_is_not_step_execution_authority"] is True,
    ):
        check(value)
    for key in (
        "provider_execution_authorized", "command_execution_authorized", "test_execution_authorized",
        "workspace_materialization_authorized", "project_mutation_authorized", "background_execution_authorized",
        "installation_authorized", "promotion_authorized", "release_authorized", "old_authority_reusable",
    ):
        check(public_launch.get(key) is False)
    for key in (
        "provider_contacted", "commands_executed", "tests_executed", "workspace_created", "project_modified",
        "selected_project_modified", "source_modified", "private_request_exposed", "private_path_exposed",
        "private_content_exposed", "project_name_exposed", "raw_provider_output_exposed",
        "raw_test_output_exposed", "cognition_written",
    ):
        check(public_launch.get(key) is False)
    check(consumption["consumption_count"] == 1)
    check(consumption["authorization_consumed"] is True)
    check(consumption["old_authority_reusable"] is False)
    check(MAX_LAUNCH_AUTHORIZATIONS == 100)
    check(MAX_BOUNDED_EXECUTION_SESSIONS == 100)
    check(RETAINED_CONTRACT_VERSION == "v1226.8")
    check(all(launch["launch_bounds"].values()))

    tampered = dict(launch)
    tampered["priority_level"] = "critical"
    check(_validate_launch(tampered) is False)
    malformed = dict(authorization)
    malformed["authorization_digest"] = "0" * 64
    malformed = _sealed(malformed, "bounded_launch_authorization_record_digest")
    check(_validate_authorization(malformed) is False)
    bad_consumption = dict(consumption)
    bad_consumption["consumption_count"] = 2
    check(_validate_consumption(bad_consumption) is False)

    module = (source / "conscious_agent" / "execution_session_authorization_bounded_launch.py").read_text(encoding="utf-8")
    ordinary = (source / "conscious_agent" / "ordinary_chat_development_campaign.py").read_text(encoding="utf-8")
    for value in (
        "process_execution_session_authorization_bounded_launch_control" in ordinary,
        "LocalModelClient" not in module,
        "single_use_launch_authorization_required" in module,
        "fresh_step_authorization_required" in module,
        "goal_alignment_review_required" in module,
        "outcome_reflection_required" in module,
        'provider_execution_authorized": False' in module,
        'project_mutation_authorized": False' in module,
        "consumption_count" in module,
    ):
        check(value)

    registry = inspect_checkpoint_registry(source_root=source)
    descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "execution-session-authorization-bounded-launch-checkpoint"), None)
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
        "status": "execution_session_authorization_bounded_launch_checkpoint_ready" if ok else "execution_session_authorization_bounded_launch_checkpoint_failed",
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "runtime_data_read": False,
        "source_modified": False,
        "project_modified": False,
        "authority_granted": False,
        "provider_contacted": False,
        "commands_executed": False,
        "tests_executed": False,
        "execution_session_launch_authorized": False,
        "execution_session_launched": False,
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
