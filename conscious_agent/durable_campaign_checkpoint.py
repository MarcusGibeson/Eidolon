from __future__ import annotations
"""v1380 consolidated evidence gate for durable multi-step campaigns."""

import hashlib
import json
import re
from typing import Any, Mapping

CONTRACT_VERSION = "v1380.8"
DIGEST = re.compile(r"^[a-f0-9]{64}$")
MIN_MULTI_HOUR_SECONDS = 2 * 60 * 60
DENIED = {
    "work_execution_authorized": False,
    "automatic_resume_authorized": False,
    "project_mutation_authorized": False,
    "source_mutation_authorized": False,
    "provider_contact_authorized": False,
    "release_authorized": False,
    "approval_granted": False,
    "independent_authority_granted": False,
}


def _d(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def build_durable_campaign_checkpoint(
    *,
    campaign_record_digest: str,
    step_checkpoint_digest: str,
    dependency_schedule_digest: str,
    parallel_plan_digest: str,
    heartbeat_digest: str,
    partial_result_digest: str,
    continuity_capsule_digest: str,
    resume_assessment_digest: str,
    conflict_assessment_digest: str,
    reconciliation_disposition_digest: str,
    final_result_digest: str,
    started_at_unix: int,
    interrupted_at_unix: int,
    restarted_at_unix: int,
    external_change_at_unix: int,
    reconciled_at_unix: int,
    completed_at_unix: int,
    interruption_observed: bool,
    restart_observed: bool,
    external_change_detected: bool,
    operator_change_preserved: bool,
    reconciliation_completed: bool,
    campaign_completed: bool,
    duplicate_side_effect_replay: bool = False,
    chat_replay_used: bool = False,
) -> dict[str, Any]:
    digests = [
        campaign_record_digest, step_checkpoint_digest, dependency_schedule_digest, parallel_plan_digest,
        heartbeat_digest, partial_result_digest, continuity_capsule_digest, resume_assessment_digest,
        conflict_assessment_digest, reconciliation_disposition_digest, final_result_digest,
    ]
    if any(not DIGEST.fullmatch(str(x or "")) for x in digests):
        return {"ok": False, "status": "durable_campaign_lineage_invalid", "action_executed": False, **DENIED}
    try:
        times = [int(started_at_unix), int(interrupted_at_unix), int(restarted_at_unix), int(external_change_at_unix), int(reconciled_at_unix), int(completed_at_unix)]
    except Exception:
        return {"ok": False, "status": "durable_campaign_timeline_invalid", "action_executed": False, **DENIED}
    if any(x < 0 for x in times) or times != sorted(times) or len(set(times)) != len(times):
        return {"ok": False, "status": "durable_campaign_timeline_invalid", "action_executed": False, **DENIED}
    duration = times[-1] - times[0]
    flags = [interruption_observed, restart_observed, external_change_detected, operator_change_preserved, reconciliation_completed, campaign_completed]
    if duration < MIN_MULTI_HOUR_SECONDS:
        return {"ok": False, "status": "multi_hour_campaign_evidence_required", "action_executed": False, **DENIED}
    if not all(bool(x) for x in flags):
        return {"ok": False, "status": "durable_campaign_scenario_incomplete", "action_executed": False, **DENIED}
    if duplicate_side_effect_replay or chat_replay_used:
        return {"ok": False, "status": "durable_campaign_recovery_boundary_failed", "action_executed": False, **DENIED}
    row = {
        "contract_version": CONTRACT_VERSION,
        "campaign_record_digest": campaign_record_digest,
        "step_checkpoint_digest": step_checkpoint_digest,
        "dependency_schedule_digest": dependency_schedule_digest,
        "parallel_plan_digest": parallel_plan_digest,
        "heartbeat_digest": heartbeat_digest,
        "partial_result_digest": partial_result_digest,
        "continuity_capsule_digest": continuity_capsule_digest,
        "resume_assessment_digest": resume_assessment_digest,
        "conflict_assessment_digest": conflict_assessment_digest,
        "reconciliation_disposition_digest": reconciliation_disposition_digest,
        "final_result_digest": final_result_digest,
        "started_at_unix": times[0],
        "interrupted_at_unix": times[1],
        "restarted_at_unix": times[2],
        "external_change_at_unix": times[3],
        "reconciled_at_unix": times[4],
        "completed_at_unix": times[5],
        "logical_duration_seconds": duration,
        "multi_hour_duration_satisfied": True,
        "interruption_observed": True,
        "restart_observed": True,
        "external_change_detected": True,
        "operator_change_preserved": True,
        "reconciliation_completed": True,
        "campaign_completed": True,
        "duplicate_side_effect_replay": False,
        "chat_replay_used": False,
        "compact_project_state_used": True,
        "content_free": True,
        "read_only_checkpoint": True,
        "action_executed": False,
        **DENIED,
    }
    row["checkpoint_digest"] = _d(row)
    return {"ok": True, "status": "durable_campaign_checkpoint_ready", "durable_campaign_checkpoint": row, "action_executed": False, **DENIED}


def validate_durable_campaign_checkpoint(checkpoint: Mapping[str, Any], *, expected_checkpoint_digest: str) -> dict[str, Any]:
    row = dict(checkpoint); supplied = str(row.pop("checkpoint_digest", ""))
    valid = bool(DIGEST.fullmatch(str(expected_checkpoint_digest or ""))) and supplied == expected_checkpoint_digest and supplied == _d(row)
    checks = {
        "digest_valid": valid,
        "multi_hour": bool(row.get("multi_hour_duration_satisfied")),
        "interruption": bool(row.get("interruption_observed")),
        "restart": bool(row.get("restart_observed")),
        "external_change": bool(row.get("external_change_detected")),
        "operator_change_preserved": bool(row.get("operator_change_preserved")),
        "reconciled": bool(row.get("reconciliation_completed")),
        "completed": bool(row.get("campaign_completed")),
        "no_duplicate_side_effect": row.get("duplicate_side_effect_replay") is False,
        "no_chat_replay": row.get("chat_replay_used") is False,
        "content_free": row.get("content_free") is True,
    }
    return {"ok": all(checks.values()), "status": "durable_campaign_checkpoint_valid" if all(checks.values()) else "durable_campaign_checkpoint_invalid", "checks": checks, "passed": sum(checks.values()), "total": len(checks), "action_executed": False, **DENIED}


def process_durable_campaign_checkpoint_control(text: str, *, project_state=None, **_) -> dict[str, Any]:
    if str(text or "").strip().lower() not in {"show durable campaign checkpoint", "inspect durable campaign checkpoint", "show campaign checkpoint"}:
        return {"active": False}
    rec = dict((project_state or {}).get("durable_campaign_checkpoint") or {})
    return {"active": True, "ok": bool(rec), "status": "durable_campaign_checkpoint_found" if rec else "durable_campaign_checkpoint_missing", "durable_campaign_checkpoint": rec, "action_executed": False, **DENIED}


__all__ = ["CONTRACT_VERSION", "MIN_MULTI_HOUR_SECONDS", "build_durable_campaign_checkpoint", "validate_durable_campaign_checkpoint", "process_durable_campaign_checkpoint_control"]
