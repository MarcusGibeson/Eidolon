from __future__ import annotations

"""v2505.8 provider-free structural background cognition.

This is intentionally modest. It interprets an already-selected cognitive
operation against the structural unified frame and emits a bounded outcome
proposal. It does not generate prose reasoning, contact a model/provider, read
raw conversation content, apply candidates, or execute actions.
"""

from typing import Any, Mapping

CONTRACT_VERSION = "v2505.8"


def _count(mapping: Mapping[str, Any], key: str) -> int:
    try:
        return max(0, int(mapping.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def derive_structural_background_outcome(operation: str, frame: Mapping[str, Any]) -> dict[str, Any]:
    op = str(operation or "").strip().upper()
    if not isinstance(frame, Mapping) or not frame.get("ok") or not frame.get("frame_digest"):
        raise ValueError("valid unified cognitive frame required")
    projection = frame.get("projection") if isinstance(frame.get("projection"), Mapping) else {}
    beliefs = projection.get("beliefs") if isinstance(projection.get("beliefs"), Mapping) else {}
    planning = projection.get("planning") if isinstance(projection.get("planning"), Mapping) else {}
    demands = projection.get("demands") if isinstance(projection.get("demands"), Mapping) else {}
    continuity = projection.get("continuity") if isinstance(projection.get("continuity"), Mapping) else {}

    outcome = "NO_DURABLE_CHANGE"
    fields: list[str] = []
    confidence = 0.55
    reason_code = "no_structural_change_supported"

    if op == "INTEGRATE_EXPERIENCE":
        outcome, fields, confidence, reason_code = "MEMORY_INTEGRATION_CANDIDATE", ["experience_consolidation"], 0.70, "experience_ready_for_candidate_consolidation"
    elif op == "RECONSIDER_BELIEF" and (_count(beliefs, "active_conflict_count") or _count(beliefs, "contested_count")):
        outcome, fields, confidence, reason_code = "BELIEF_REVISION_CANDIDATE", ["confidence_or_status"], 0.66, "belief_conflict_present"
    elif op == "RESOLVE_CONFLICT" and _count(beliefs, "active_conflict_count"):
        outcome, fields, confidence, reason_code = "CONFLICT_RESOLUTION_CANDIDATE", ["conflict_disposition"], 0.64, "active_conflict_present"
    elif op == "REVIEW_GOAL" and _count(planning, "active_count"):
        outcome, fields, confidence, reason_code = "GOAL_UPDATE_CANDIDATE", ["priority_or_status"], 0.60, "active_plan_context_present"
    elif op in {"PLAN", "REPLAN"} and (_count(planning, "active_count") or _count(demands, "candidate_count")):
        outcome, fields, confidence, reason_code = "PLAN_UPDATE_CANDIDATE", ["next_step_or_priority"], 0.60, "planning_context_present"
    elif op == "REVIEW_SELF_MODEL":
        outcome, fields, confidence, reason_code = "SELF_MODEL_EVIDENCE_CANDIDATE", ["observed_tendency"], 0.55, "self_model_review_selected"
    elif op in {"CONTINUE_THOUGHT", "REFLECT"}:
        due = _count(continuity, "due_subject_count")
        outcome, fields, confidence, reason_code = "THOUGHT_CONTINUATION", ["continuation_marker"], 0.58 if due else 0.52, "bounded_reflection_requires_future_cycle"
    elif op == "RECALL_MEMORY":
        reason_code = "recall_is_read_only_without_durable_candidate"

    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "operation": op,
        "outcome_type": outcome,
        "changed_fields": fields,
        "confidence": confidence,
        "reason_code": reason_code,
        "frame_digest": str(frame["frame_digest"]),
        "candidate_applied": False,
        "provider_contacted": False,
        "raw_content_read": False,
        "message_sent": False,
        "tool_executed": False,
        "source_mutated": False,
        "authority_broadened": False,
        "hidden_reasoning_exposed": False,
    }


__all__ = ["CONTRACT_VERSION", "derive_structural_background_outcome"]
