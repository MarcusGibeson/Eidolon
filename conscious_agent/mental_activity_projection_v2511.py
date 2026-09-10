from __future__ import annotations

"""v2511 structural adapters into the unified mental activity timeline."""

from typing import Any, Mapping


def cognitive_transition(cycle: Mapping[str, Any]) -> tuple[str, str, str]:
    status = str(cycle.get("status") or "")
    transition = "cycle_started" if status == "awaiting_cognitive_work" else "cycle_completed"
    return "cognitive", transition, str(cycle.get("outcome_type") or cycle.get("selected_operation") or "")[:80]


def background_transition(record: Mapping[str, Any]) -> tuple[str, str, str]:
    status = str(record.get("status") or "")
    transition = "cycle_suppressed" if status == "suppressed" else "cycle_completed"
    return "background", transition, str(record.get("selected_operation") or "")[:80]


def memory_transition(candidate: Mapping[str, Any]) -> tuple[str, str, str]:
    return "memory", "consolidation_candidate", str(candidate.get("candidate_type") or "")[:80]


def self_model_transition(candidate: Mapping[str, Any]) -> tuple[str, str, str]:
    return "self_model", "trait_candidate", str(candidate.get("trait_code") or "")[:80]


def planning_transition(review: Mapping[str, Any]) -> tuple[str, str, str]:
    return "planning", "plan_review", str(review.get("health_state") or "")[:80]


def action_transition(record: Mapping[str, Any]) -> tuple[str, str, str]:
    if record.get("proposal_ready") is True:
        return "action", "proposal_ready", str(record.get("capability_id") or "")[:80]
    return "action", "review_waiting", str(record.get("capability_id") or "")[:80]


__all__ = ["cognitive_transition", "background_transition", "memory_transition", "self_model_transition", "planning_transition", "action_transition"]
