from __future__ import annotations

"""Bounded Goal and Planning Alpha consolidation for ordinary conversation.

This module reconciles the existing v1170-v1173 goal nomination, hierarchy,
simulation, and follow-through projections. It adds no second planning path and
never activates, persists, schedules, routes, edits, or executes a goal or plan.
"""

import hashlib
import json
from typing import Any, Mapping

from internally_generated_goal_runtime import verify_internally_generated_goal_candidate_reliability
from hierarchical_planning_runtime import (
    verify_hierarchical_planning_reliability,
    verify_hierarchical_planning_review_packet,
    verify_hierarchical_planning_review_state,
)
from plan_simulation_runtime import (
    verify_plan_simulation_reliability,
    verify_plan_simulation_review_packet,
    verify_plan_simulation_review_state,
)
from persistent_follow_through_runtime import (
    verify_persistent_follow_through_reliability,
    verify_persistent_follow_through_review_packet,
    verify_persistent_follow_through_review_state,
)

CONTRACT_VERSION = "v1174.2"
MAX_COMPONENT_BYTES = 65536
MAX_PRIOR_RECEIPTS = 64
MAX_STAGE_COUNT = 4

_STAGE_SET = (
    "goal_candidate",
    "hierarchical_planning",
    "plan_simulation",
    "persistent_follow_through",
)
_REQUIRED_CONSTRAINTS = {
    "literal_current_request_precedence",
    "operator_review_required",
    "no_goal_activation",
    "no_plan_activation",
    "no_plan_persistence",
    "no_alternative_selection",
    "no_scheduling",
    "no_tool_routing",
    "no_action_execution",
    "no_source_editing",
    "no_autonomous_work",
}
_HANDOFF_FIELDS = {
    "contract_version",
    "alpha_available",
    "available_stage_count",
    "coherent_stage_count",
    "provider_completed",
    "assistant_memory_committed",
    "eligible_for_continuity",
    "goal_activated",
    "plan_activated",
    "plan_persisted",
    "alternative_selected",
    "schedule_created",
    "tool_routed",
    "action_executed",
    "source_edited",
    "autonomous_work_started",
    "authority",
    "content_free",
    "receipt_digest",
}
_POLICY_FIELDS = {
    "contract_version", "literal_current_request_precedence", "operator_review_required",
    "operator_approval_required", "goal_activation_permitted", "plan_activation_permitted",
    "plan_persistence_permitted", "alternative_selection_permitted", "scheduling_permitted",
    "tool_routing_permitted", "action_execution_permitted", "source_editing_permitted",
    "autonomous_work_permitted", "authority", "content_free", "policy_recovered",
}
_EVIDENCE_FIELDS = {
    "contract_version", "goal_candidate_reliable", "hierarchical_planning_reliable",
    "plan_simulation_reliable", "persistent_follow_through_reliable",
    "stage_availability_coherent", "stage_counts_coherent", "protected_constraints_complete",
    "historical_goal_governance_preserved", "historical_planning_governance_preserved",
    "verified_receipt_count", "replayed_receipt_count", "malformed_receipt_count",
    "tampered_receipt_count", "receipt_budget_exceeded", "continuity_available",
    "recovered", "content_free",
}
_STATE_FIELDS = {
    "contract_version", "alpha_posture", "stage_set", "stage_postures",
    "available_stage_count", "coherent_stage_count", "milestone_count", "dependency_count",
    "stopping_condition_count", "alternative_count", "risk_count", "continuity_disposition",
    "content_free", "state_digest",
}
_DIAGNOSTICS_FIELDS = {
    "contract_version", "alpha_available", "available_stage_count", "coherent_stage_count",
    "recovered", "authority_field_count", "private_field_count", "integrity_digest",
}


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _size_ok(value: object) -> bool:
    try:
        return len(json.dumps(value, sort_keys=True, default=str).encode()) <= MAX_COMPONENT_BYTES
    except Exception:
        return False


def _report(value: object) -> dict[str, Any]:
    row = _mapping(value)
    return _mapping(row.get("report") or row)


def verify_goal_and_planning_alpha_handoff(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _HANDOFF_FIELDS or row.get("contract_version") != CONTRACT_VERSION or not _size_ok(row):
        return False
    supplied = row.pop("receipt_digest", None)
    bounded = all(
        isinstance(row.get(key), int) and 0 <= row[key] <= MAX_STAGE_COUNT
        for key in ("available_stage_count", "coherent_stage_count")
    )
    denied = all(
        row.get(key) is False
        for key in (
            "goal_activated",
            "plan_activated",
            "plan_persisted",
            "alternative_selected",
            "schedule_created",
            "tool_routed",
            "action_executed",
            "source_edited",
            "autonomous_work_started",
        )
    )
    return bool(
        isinstance(supplied, str)
        and len(supplied) == 64
        and supplied == _digest(row)
        and bounded
        and denied
        and row.get("authority") == "none"
        and row.get("content_free") is True
        and isinstance(row.get("alpha_available"), bool)
        and isinstance(row.get("provider_completed"), bool)
        and isinstance(row.get("assistant_memory_committed"), bool)
        and row.get("eligible_for_continuity")
        is bool(
            row.get("alpha_available")
            and row.get("provider_completed")
            and row.get("assistant_memory_committed")
        )
    )


def _receipt_from_row(value: object) -> dict[str, Any]:
    row = _mapping(value)
    direct = _mapping(row.get("goal_and_planning_alpha_handoff"))
    if direct:
        return direct
    cognitive = _mapping(row.get("cognitive_context"))
    return _mapping(cognitive.get("goal_and_planning_alpha_handoff"))


def validate_prior_goal_and_planning_alpha_receipts(rows: object) -> dict[str, Any]:
    items = list(rows) if isinstance(rows, (list, tuple)) else []
    inspected = items[-MAX_PRIOR_RECEIPTS:]
    seen: set[str] = set()
    verified = replayed = malformed = tampered = 0
    latest: dict[str, Any] = {}
    for item in inspected:
        receipt = _receipt_from_row(item)
        if not receipt:
            continue
        if not _size_ok(receipt):
            malformed += 1
            continue
        digest = str(receipt.get("receipt_digest") or "")
        if digest in seen:
            replayed += 1
            continue
        if not verify_goal_and_planning_alpha_handoff(receipt):
            tampered += 1
            continue
        seen.add(digest)
        verified += 1
        latest = receipt
    budget_exceeded = len(items) > MAX_PRIOR_RECEIPTS
    recovered = malformed > 0 or tampered > 0 or budget_exceeded
    return {
        "verified_receipt_count": 0 if recovered else min(verified, 1),
        "replayed_receipt_count": replayed,
        "malformed_receipt_count": malformed,
        "tampered_receipt_count": tampered,
        "receipt_budget_exceeded": budget_exceeded,
        "continuity_available": bool(latest.get("eligible_for_continuity")) and not recovered,
        "recovered": recovered,
    }


def _goal_status(projection: object, reliability: object) -> tuple[bool, bool]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    report = _report(reliability)
    valid = bool(
        value
        and _size_ok(value)
        and verify_internally_generated_goal_candidate_reliability(report)
        and report.get("ordinary_conversation_ready") is True
        and report.get("reliability_posture") == "goal_candidate_context_reliable"
        and policy.get("goal_activation_permitted") is False
        and policy.get("plan_creation_permitted") is False
        and policy.get("tool_routing_permitted") is False
        and policy.get("action_execution_permitted") is False
    )
    return valid, bool(report.get("candidate_available")) if valid else False


def _planning_status(projection: object, review: object, reliability: object) -> tuple[bool, bool, int, int, int]:
    value = _mapping(projection)
    review_value = _mapping(review)
    hierarchy = _mapping(value.get("hierarchy"))
    report = _report(reliability)
    valid = bool(
        value
        and _size_ok(value)
        and verify_hierarchical_planning_review_state(review_value.get("state"))
        and verify_hierarchical_planning_review_packet(review_value.get("review_packet"))
        and verify_hierarchical_planning_reliability(report)
    )
    available = bool(
        valid
        and report.get("ordinary_conversation_ready") is True
        and report.get("reliability_posture") == "hierarchical_planning_context_reliable"
        and report.get("plan_candidate_available") is True
    )
    counts = tuple(
        int(hierarchy.get(key) or 0) if available else 0
        for key in ("milestone_count", "dependency_count", "stopping_condition_count")
    )
    return valid, available, counts[0], counts[1], counts[2]


def _simulation_status(projection: object, review: object, reliability: object) -> tuple[bool, bool, int, int]:
    value = _mapping(projection)
    review_value = _mapping(review)
    comparison = _mapping(value.get("comparison"))
    report = _report(reliability)
    valid = bool(
        value
        and _size_ok(value)
        and verify_plan_simulation_review_state(review_value.get("state"))
        and verify_plan_simulation_review_packet(review_value.get("review_packet"))
        and verify_plan_simulation_reliability(report)
    )
    available = bool(
        valid
        and report.get("ordinary_conversation_ready") is True
        and report.get("reliability_posture") == "plan_simulation_context_reliable"
        and report.get("simulation_available") is True
    )
    return (
        valid,
        available,
        int(comparison.get("alternative_count") or 0) if available else 0,
        int(comparison.get("risk_category_count") or 0) if available else 0,
    )


def _follow_status(projection: object, review: object, reliability: object) -> tuple[bool, bool, int, int, int]:
    value = _mapping(projection)
    review_value = _mapping(review)
    continuity = _mapping(value.get("continuity"))
    report = _report(reliability)
    valid = bool(
        value
        and _size_ok(value)
        and verify_persistent_follow_through_review_state(review_value.get("state"))
        and verify_persistent_follow_through_review_packet(review_value.get("review_packet"))
        and verify_persistent_follow_through_reliability(report)
    )
    available = bool(
        valid
        and report.get("ordinary_conversation_ready") is True
        and report.get("reliability_posture") == "persistent_follow_through_context_reliable"
        and report.get("follow_through_available") is True
    )
    counts = tuple(
        int(continuity.get(key) or 0) if available else 0
        for key in ("milestone_count", "dependency_count", "stopping_condition_count")
    )
    return valid, available, counts[0], counts[1], counts[2]


def build_goal_and_planning_alpha_projection(
    goal_projection: object,
    goal_reliability: object,
    hierarchical_planning_projection: object,
    hierarchical_planning_review: object,
    hierarchical_planning_reliability: object,
    plan_simulation_projection: object,
    plan_simulation_review: object,
    plan_simulation_reliability: object,
    persistent_follow_through_projection: object,
    persistent_follow_through_review: object,
    persistent_follow_through_reliability: object,
    *,
    prior_goal_planning_alpha_receipts: object = (),
    protected_operator_constraints: tuple[str, ...] = tuple(sorted(_REQUIRED_CONSTRAINTS)),
) -> dict[str, Any]:
    """Build one structural alpha posture over the existing v1170-v1173 layers."""
    goal_valid, goal_available = _goal_status(goal_projection, goal_reliability)
    plan_valid, plan_available, plan_milestones, plan_dependencies, plan_stops = _planning_status(
        hierarchical_planning_projection, hierarchical_planning_review, hierarchical_planning_reliability
    )
    sim_valid, sim_available, alternative_count, risk_count = _simulation_status(
        plan_simulation_projection, plan_simulation_review, plan_simulation_reliability
    )
    follow_valid, follow_available, follow_milestones, follow_dependencies, follow_stops = _follow_status(
        persistent_follow_through_projection, persistent_follow_through_review, persistent_follow_through_reliability
    )
    continuity = validate_prior_goal_and_planning_alpha_receipts(prior_goal_planning_alpha_receipts)
    constraints_valid = _REQUIRED_CONSTRAINTS.issubset(set(protected_operator_constraints))
    validity = (goal_valid, plan_valid, sim_valid, follow_valid)
    availability = (goal_available, plan_available, sim_available, follow_available)
    chain_coherent = len(set(availability)) == 1
    counts_coherent = bool(
        not all(availability)
        or (
            1 <= plan_milestones <= 3
            and follow_milestones == 3
            and plan_dependencies == 2
            and follow_dependencies == 3
            and plan_stops == 3
            and follow_stops == 4
            and alternative_count == 3
            and risk_count == 3
        )
    )
    recovered = bool(
        not constraints_valid
        or not all(validity)
        or not chain_coherent
        or not counts_coherent
        or continuity["recovered"]
    )
    alpha_available = bool(all(availability) and not recovered)
    available_stage_count = sum(bool(value) for value in availability) if not recovered else 0
    coherent_stage_count = MAX_STAGE_COUNT if not recovered else 0
    stage_postures = {
        "goal_candidate": "review_available" if alpha_available else "none",
        "hierarchical_planning": "review_available" if alpha_available else "none",
        "plan_simulation": "review_available" if alpha_available else "none",
        "persistent_follow_through": "review_available" if alpha_available else "none",
    }
    state = {
        "contract_version": CONTRACT_VERSION,
        "alpha_posture": "goal_and_planning_alpha_review" if alpha_available else (
            "literal_current_request_only_recovery" if recovered else "no_goal_and_planning_candidate"
        ),
        "stage_set": list(_STAGE_SET),
        "stage_postures": stage_postures,
        "available_stage_count": available_stage_count,
        "coherent_stage_count": coherent_stage_count,
        "milestone_count": follow_milestones if alpha_available else 0,
        "dependency_count": follow_dependencies if alpha_available else 0,
        "stopping_condition_count": follow_stops if alpha_available else 0,
        "alternative_count": alternative_count if alpha_available else 0,
        "risk_count": risk_count if alpha_available else 0,
        "continuity_disposition": "verified_alpha_resume" if alpha_available and continuity["continuity_available"] else (
            "current_turn_alpha_review" if alpha_available else "none"
        ),
        "content_free": True,
    }
    state["state_digest"] = _digest(state)
    policy = {
        "contract_version": CONTRACT_VERSION,
        "literal_current_request_precedence": True,
        "operator_review_required": True,
        "operator_approval_required": True,
        "goal_activation_permitted": False,
        "plan_activation_permitted": False,
        "plan_persistence_permitted": False,
        "alternative_selection_permitted": False,
        "scheduling_permitted": False,
        "tool_routing_permitted": False,
        "action_execution_permitted": False,
        "source_editing_permitted": False,
        "autonomous_work_permitted": False,
        "authority": "none",
        "content_free": True,
        "policy_recovered": recovered,
    }
    evidence = {
        "contract_version": CONTRACT_VERSION,
        "goal_candidate_reliable": goal_valid,
        "hierarchical_planning_reliable": plan_valid,
        "plan_simulation_reliable": sim_valid,
        "persistent_follow_through_reliable": follow_valid,
        "stage_availability_coherent": chain_coherent,
        "stage_counts_coherent": counts_coherent,
        "protected_constraints_complete": constraints_valid,
        "historical_goal_governance_preserved": True,
        "historical_planning_governance_preserved": True,
        **continuity,
        "content_free": True,
    }
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "alpha_available": alpha_available,
        "available_stage_count": available_stage_count,
        "coherent_stage_count": coherent_stage_count,
        "recovered": recovered,
        "authority_field_count": 0,
        "private_field_count": 0,
        "integrity_digest": _digest({"policy": policy, "evidence": evidence, "state": state}),
    }
    prompt = (
        '<goal_and_planning_alpha data_only="true" authority="none">'
        + json.dumps(
            {
                "alpha_posture": state["alpha_posture"],
                "stage_set": state["stage_set"],
                "available_stage_count": state["available_stage_count"],
                "milestone_count": state["milestone_count"],
                "dependency_count": state["dependency_count"],
                "stopping_condition_count": state["stopping_condition_count"],
                "alternative_count": state["alternative_count"],
                "risk_count": state["risk_count"],
                "continuity_disposition": state["continuity_disposition"],
                "operator_review_required": True,
                "operator_approval_required": True,
                "goal_activation_permitted": False,
                "plan_activation_permitted": False,
                "plan_persistence_permitted": False,
                "alternative_selection_permitted": False,
                "scheduling_permitted": False,
                "tool_routing_permitted": False,
                "action_execution_permitted": False,
                "authority": "none",
                "content_free": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "</goal_and_planning_alpha>"
    )
    return {
        "policy": policy,
        "evidence": evidence,
        "state": state,
        "diagnostics": diagnostics,
        "prompt_section": prompt,
    }


def verify_goal_and_planning_alpha_diagnostics_strict(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _DIAGNOSTICS_FIELDS or not _size_ok(row):
        return False
    counts_valid = all(
        isinstance(row.get(key), int) and 0 <= row[key] <= MAX_STAGE_COUNT
        for key in ("available_stage_count", "coherent_stage_count")
    )
    alpha_available = row.get("alpha_available")
    recovered = row.get("recovered")
    coherent = (
        alpha_available is True
        and recovered is False
        and row.get("available_stage_count") == MAX_STAGE_COUNT
        and row.get("coherent_stage_count") == MAX_STAGE_COUNT
    ) or (
        alpha_available is False
        and row.get("available_stage_count") == 0
        and row.get("coherent_stage_count") in (0, MAX_STAGE_COUNT)
    )
    return bool(
        row.get("contract_version") == CONTRACT_VERSION
        and isinstance(alpha_available, bool)
        and isinstance(recovered, bool)
        and counts_valid
        and coherent
        and row.get("authority_field_count") == 0
        and row.get("private_field_count") == 0
        and isinstance(row.get("integrity_digest"), str)
        and len(row["integrity_digest"]) == 64
    )


def verify_goal_and_planning_alpha_projection(value: object) -> bool:
    row = _mapping(value)
    if set(row) != {"policy", "evidence", "state", "diagnostics", "prompt_section"} or not _size_ok(row):
        return False
    policy = _mapping(row.get("policy"))
    evidence = _mapping(row.get("evidence"))
    state = _mapping(row.get("state"))
    diagnostics = _mapping(row.get("diagnostics"))
    if set(policy) != _POLICY_FIELDS or set(evidence) != _EVIDENCE_FIELDS or set(state) != _STATE_FIELDS:
        return False
    state_unsigned = {key: item for key, item in state.items() if key != "state_digest"}
    denied = all(
        policy.get(key) is False
        for key in (
            "goal_activation_permitted", "plan_activation_permitted", "plan_persistence_permitted",
            "alternative_selection_permitted", "scheduling_permitted", "tool_routing_permitted",
            "action_execution_permitted", "source_editing_permitted", "autonomous_work_permitted",
        )
    )
    counts = ("available_stage_count", "coherent_stage_count", "milestone_count", "dependency_count",
              "stopping_condition_count", "alternative_count", "risk_count")
    counts_valid = all(isinstance(state.get(key), int) and 0 <= state[key] <= MAX_PRIOR_RECEIPTS for key in counts)
    receipt_counts_valid = all(
        isinstance(evidence.get(key), int) and 0 <= evidence[key] <= MAX_PRIOR_RECEIPTS
        for key in ("verified_receipt_count", "replayed_receipt_count", "malformed_receipt_count", "tampered_receipt_count")
    )
    alpha_available = diagnostics.get("alpha_available") is True
    recovered = policy.get("policy_recovered") is True
    stage_shape_valid = bool(
        state.get("stage_set") == list(_STAGE_SET)
        and isinstance(state.get("stage_postures"), dict)
        and set(state["stage_postures"]) == set(_STAGE_SET)
        and (
            alpha_available
            and not recovered
            and state.get("available_stage_count") == MAX_STAGE_COUNT
            and state.get("coherent_stage_count") == MAX_STAGE_COUNT
            and state.get("milestone_count") == 3
            and state.get("dependency_count") == 3
            and state.get("stopping_condition_count") == 4
            and state.get("alternative_count") == 3
            and state.get("risk_count") == 3
            and set(state["stage_postures"].values()) == {"review_available"}
            or (
                not alpha_available
                and all(state.get(key) == 0 for key in counts if key != "coherent_stage_count")
                and state.get("coherent_stage_count") in (0, MAX_STAGE_COUNT)
                and set(state["stage_postures"].values()) == {"none"}
            )
        )
    )
    return bool(
        policy.get("contract_version") == CONTRACT_VERSION
        and evidence.get("contract_version") == CONTRACT_VERSION
        and state.get("contract_version") == CONTRACT_VERSION
        and verify_goal_and_planning_alpha_diagnostics_strict(diagnostics)
        and state.get("state_digest") == _digest(state_unsigned)
        and diagnostics.get("integrity_digest") == _digest({"policy": policy, "evidence": evidence, "state": state})
        and policy.get("literal_current_request_precedence") is True
        and policy.get("operator_review_required") is True
        and policy.get("operator_approval_required") is True
        and policy.get("authority") == "none"
        and policy.get("content_free") is True
        and evidence.get("content_free") is True
        and state.get("content_free") is True
        and evidence.get("verified_receipt_count") <= 1
        and isinstance(evidence.get("receipt_budget_exceeded"), bool)
        and isinstance(evidence.get("continuity_available"), bool)
        and isinstance(evidence.get("recovered"), bool)
        and counts_valid and receipt_counts_valid and stage_shape_valid and denied
        and isinstance(row.get("prompt_section"), str)
        and len(row["prompt_section"]) <= 4096
    )


def build_goal_and_planning_alpha_handoff(
    projection: object,
    *,
    provider_completed: bool,
    assistant_memory_committed: bool,
) -> dict[str, Any]:
    value = _mapping(projection)
    valid = verify_goal_and_planning_alpha_projection(value)
    policy = _mapping(value.get("policy"))
    diagnostics = _mapping(value.get("diagnostics"))
    alpha_available = bool(valid and diagnostics.get("alpha_available") and not policy.get("policy_recovered"))
    row = {
        "contract_version": CONTRACT_VERSION,
        "alpha_available": alpha_available,
        "available_stage_count": int(diagnostics.get("available_stage_count") or 0) if alpha_available else 0,
        "coherent_stage_count": int(diagnostics.get("coherent_stage_count") or 0) if alpha_available else 0,
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_continuity": bool(alpha_available and provider_completed and assistant_memory_committed),
        "goal_activated": False,
        "plan_activated": False,
        "plan_persisted": False,
        "alternative_selected": False,
        "schedule_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "authority": "none",
        "content_free": True,
    }
    row["receipt_digest"] = _digest(row)
    return row


# v1174.3-v1174.5 cross-turn alpha review and operator-facing integration.
REVIEW_CONTRACT_VERSION = "v1174.5"
MAX_REVIEW_PROMPT_CHARS = 4096
_REVIEW_STATE_FIELDS = {
    "contract_version", "review_disposition", "alpha_stability_band",
    "stage_set", "stage_postures", "available_stage_count", "coherent_stage_count",
    "milestone_count", "dependency_count", "stopping_condition_count",
    "alternative_count", "risk_count", "verified_prior_receipt_count",
    "replayed_prior_receipt_count", "alpha_available", "operator_review_required",
    "operator_approval_required", "goal_activated", "plan_activated", "plan_persisted",
    "alternative_selected", "schedule_created", "tool_routed", "action_executed",
    "source_edited", "autonomous_work_started", "authority", "content_free",
    "review_state_digest",
}
_REVIEW_PACKET_FIELDS = {
    "contract_version", "review_disposition", "alpha_stability_band",
    "stage_coherence_band", "planning_readiness_band", "simulation_risk_posture",
    "follow_through_posture", "continuity_disposition", "stage_set", "stage_postures",
    "available_stage_count", "coherent_stage_count", "milestone_count",
    "dependency_count", "stopping_condition_count", "alternative_count", "risk_count",
    "operator_review_required", "operator_approval_required", "alpha_available",
    "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
    "schedule_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "authority", "content_free", "alpha_state_digest",
    "review_packet_digest",
}


def _valid_exact_digest(value: object, fields: set[str], digest_key: str) -> bool:
    row = _mapping(value)
    if set(row) != fields or not _size_ok(row):
        return False
    supplied = row.pop(digest_key, None)
    return isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)


def build_goal_and_planning_alpha_review_projection(projection: object) -> dict[str, Any]:
    """Build one bounded operator-review view over the consolidated alpha posture."""
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    state = _mapping(value.get("state"))
    diagnostics = _mapping(value.get("diagnostics"))
    projection_valid = verify_goal_and_planning_alpha_projection(value)
    recovered = bool(policy.get("policy_recovered")) or not projection_valid
    available = bool(diagnostics.get("alpha_available")) and not recovered
    verified = int(evidence.get("verified_receipt_count") or 0) if available else 0
    replayed = int(evidence.get("replayed_receipt_count") or 0)
    stable = bool(
        available
        and verified > 0
        and evidence.get("continuity_available") is True
        and state.get("continuity_disposition") == "verified_alpha_resume"
    )
    review_disposition = "literal_current_request_only_recovery" if recovered else (
        "stable_goal_and_planning_alpha_review" if stable else (
            "emerging_goal_and_planning_alpha_review" if available else "no_goal_and_planning_alpha_review"
        )
    )
    stage_set = list(state.get("stage_set") or []) if available else list(_STAGE_SET)
    stage_postures = dict(state.get("stage_postures") or {}) if available else {
        stage: "none" for stage in _STAGE_SET
    }
    counts = {
        key: int(state.get(key) or 0) if available else 0
        for key in (
            "available_stage_count", "coherent_stage_count", "milestone_count",
            "dependency_count", "stopping_condition_count", "alternative_count", "risk_count",
        )
    }
    review_state = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": review_disposition,
        "alpha_stability_band": "verified_cross_turn" if stable else (
            "current_turn_only" if available else "none"
        ),
        "stage_set": stage_set,
        "stage_postures": stage_postures,
        **counts,
        "verified_prior_receipt_count": verified,
        "replayed_prior_receipt_count": replayed,
        "alpha_available": available,
        "operator_review_required": True,
        "operator_approval_required": True,
        "goal_activated": False,
        "plan_activated": False,
        "plan_persisted": False,
        "alternative_selected": False,
        "schedule_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "authority": "none",
        "content_free": True,
    }
    review_state["review_state_digest"] = _digest(review_state)
    packet = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": review_disposition,
        "alpha_stability_band": review_state["alpha_stability_band"],
        "stage_coherence_band": "four_stage_coherent" if available else "none",
        "planning_readiness_band": "bounded_review_ready" if available else "none",
        "simulation_risk_posture": "bounded_risks_for_operator_comparison" if available else "none",
        "follow_through_posture": "verified_review_continuity" if stable else (
            "current_turn_review_continuity" if available else "none"
        ),
        "continuity_disposition": str(state.get("continuity_disposition") or "none") if available else "none",
        "stage_set": stage_set,
        "stage_postures": stage_postures,
        **counts,
        "operator_review_required": True,
        "operator_approval_required": True,
        "alpha_available": available,
        "goal_activated": False,
        "plan_activated": False,
        "plan_persisted": False,
        "alternative_selected": False,
        "schedule_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "authority": "none",
        "content_free": True,
        "alpha_state_digest": str(state.get("state_digest") or "") if available else "",
    }
    packet["review_packet_digest"] = _digest(packet)
    prompt_payload = {
        key: packet[key]
        for key in (
            "contract_version", "review_disposition", "alpha_stability_band",
            "stage_coherence_band", "planning_readiness_band", "simulation_risk_posture",
            "follow_through_posture", "continuity_disposition", "stage_set", "stage_postures",
            "available_stage_count", "coherent_stage_count", "milestone_count",
            "dependency_count", "stopping_condition_count", "alternative_count", "risk_count",
            "operator_review_required", "operator_approval_required", "alpha_available",
            "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
            "schedule_created", "tool_routed", "action_executed", "authority", "content_free",
        )
    }
    prompt = (
        '<goal_and_planning_alpha_review data_only="true" authority="none">'
        + json.dumps(prompt_payload, sort_keys=True, separators=(",", ":"))
        + "</goal_and_planning_alpha_review>"
    )
    if len(prompt) > MAX_REVIEW_PROMPT_CHARS:
        raise ValueError("goal and planning alpha review prompt exceeded bound")
    return {"state": review_state, "review_packet": packet, "prompt_section": prompt}


def verify_goal_and_planning_alpha_review_state(value: object) -> bool:
    if not _valid_exact_digest(value, _REVIEW_STATE_FIELDS, "review_state_digest"):
        return False
    row = _mapping(value)
    counts_valid = all(
        isinstance(row.get(key), int) and 0 <= row[key] <= MAX_PRIOR_RECEIPTS
        for key in (
            "available_stage_count", "coherent_stage_count", "milestone_count",
            "dependency_count", "stopping_condition_count", "alternative_count", "risk_count",
            "verified_prior_receipt_count", "replayed_prior_receipt_count",
        )
    )
    denied = all(
        row.get(key) is False
        for key in (
            "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
            "schedule_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started",
        )
    )
    return bool(
        row.get("contract_version") == REVIEW_CONTRACT_VERSION
        and row.get("operator_review_required") is True
        and row.get("operator_approval_required") is True
        and row.get("authority") == "none"
        and row.get("content_free") is True
        and isinstance(row.get("alpha_available"), bool)
        and row.get("stage_set") == list(_STAGE_SET)
        and isinstance(row.get("stage_postures"), dict)
        and set(row["stage_postures"]) == set(_STAGE_SET)
        and counts_valid
        and row.get("verified_prior_receipt_count") <= 1
        and (
            (
                row.get("alpha_available") is True
                and row.get("available_stage_count") == MAX_STAGE_COUNT
                and row.get("coherent_stage_count") == MAX_STAGE_COUNT
                and row.get("milestone_count") == 3
                and row.get("dependency_count") == 3
                and row.get("stopping_condition_count") == 4
                and row.get("alternative_count") == 3
                and row.get("risk_count") == 3
                and set(row["stage_postures"].values()) == {"review_available"}
            )
            or (
                row.get("alpha_available") is False
                and all(row.get(key) == 0 for key in (
                    "available_stage_count", "coherent_stage_count", "milestone_count",
                    "dependency_count", "stopping_condition_count", "alternative_count", "risk_count",
                ))
                and set(row["stage_postures"].values()) == {"none"}
            )
        )
        and denied
    )


def verify_goal_and_planning_alpha_review_packet(value: object) -> bool:
    if not _valid_exact_digest(value, _REVIEW_PACKET_FIELDS, "review_packet_digest"):
        return False
    row = _mapping(value)
    counts_valid = all(
        isinstance(row.get(key), int) and 0 <= row[key] <= MAX_PRIOR_RECEIPTS
        for key in (
            "available_stage_count", "coherent_stage_count", "milestone_count",
            "dependency_count", "stopping_condition_count", "alternative_count", "risk_count",
        )
    )
    denied = all(
        row.get(key) is False
        for key in (
            "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
            "schedule_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started",
        )
    )
    return bool(
        row.get("contract_version") == REVIEW_CONTRACT_VERSION
        and row.get("operator_review_required") is True
        and row.get("operator_approval_required") is True
        and row.get("authority") == "none"
        and row.get("content_free") is True
        and isinstance(row.get("alpha_available"), bool)
        and row.get("stage_set") == list(_STAGE_SET)
        and isinstance(row.get("stage_postures"), dict)
        and set(row["stage_postures"]) == set(_STAGE_SET)
        and counts_valid
        and denied
        and (
            (
                row.get("alpha_available") is True
                and len(str(row.get("alpha_state_digest") or "")) == 64
                and row.get("available_stage_count") == MAX_STAGE_COUNT
                and row.get("coherent_stage_count") == MAX_STAGE_COUNT
                and row.get("milestone_count") == 3
                and row.get("dependency_count") == 3
                and row.get("stopping_condition_count") == 4
                and row.get("alternative_count") == 3
                and row.get("risk_count") == 3
                and set(row["stage_postures"].values()) == {"review_available"}
            )
            or (
                row.get("alpha_available") is False
                and row.get("alpha_state_digest") == ""
                and all(row.get(key) == 0 for key in (
                    "available_stage_count", "coherent_stage_count", "milestone_count",
                    "dependency_count", "stopping_condition_count", "alternative_count", "risk_count",
                ))
                and set(row["stage_postures"].values()) == {"none"}
            )
        )
    )

# v1174.6-v1174.8 strict alpha diagnostics, fail-closed recovery, and shared reliability.
RELIABILITY_CONTRACT_VERSION = "1174.8"
MAX_RELIABILITY_FAULTS = 64
_ALPHA_RELIABILITY_FIELDS = {
    "contract_version", "reliability_posture", "ordinary_conversation_ready",
    "projection_valid", "diagnostics_valid", "review_state_valid", "review_packet_valid",
    "prior_continuity_valid", "recovered_projection", "residual_alpha_detected",
    "receipt_budget_exceeded", "fault_count", "verified_prior_receipt_count",
    "replayed_prior_receipt_count", "malformed_prior_receipt_count",
    "tampered_prior_receipt_count", "alpha_available", "review_available",
    "literal_current_request_precedence", "historical_truth_preserved", "goal_activated",
    "plan_activated", "plan_persisted", "alternative_selected", "schedule_created",
    "tool_routed", "action_executed", "source_edited", "autonomous_work_started",
    "memory_mutated", "lesson_committed", "model_trained", "model_weights_changed",
    "installation_performed", "promotion_performed", "certification_performed",
    "authority", "content_free", "alpha_state_digest", "review_state_digest",
    "review_packet_digest", "reliability_digest",
}


def build_goal_and_planning_alpha_reliability(
    projection: object,
    review_projection: object,
    *,
    prior_goal_planning_alpha_receipts: object = (),
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    state = _mapping(value.get("state"))
    diagnostics = _mapping(value.get("diagnostics"))
    review = _mapping(review_projection)
    review_state = _mapping(review.get("state"))
    packet = _mapping(review.get("review_packet"))
    prior = validate_prior_goal_and_planning_alpha_receipts(prior_goal_planning_alpha_receipts)
    diagnostics_valid = verify_goal_and_planning_alpha_diagnostics_strict(diagnostics)
    projection_valid = verify_goal_and_planning_alpha_projection(value)
    state_valid = verify_goal_and_planning_alpha_review_state(review_state)
    packet_valid = verify_goal_and_planning_alpha_review_packet(packet)
    recovered = bool(policy.get("policy_recovered") or diagnostics.get("recovered"))
    residual = bool(recovered and (
        diagnostics.get("alpha_available")
        or state.get("available_stage_count") or state.get("milestone_count")
        or state.get("dependency_count") or state.get("stopping_condition_count")
        or state.get("alternative_count") or state.get("risk_count")
        or review_state.get("alpha_available") or review_state.get("available_stage_count")
        or packet.get("alpha_available") or packet.get("available_stage_count")
    ))
    budget = bool(prior.get("receipt_budget_exceeded"))
    faults = sum((
        int(not projection_valid), int(not diagnostics_valid), int(not state_valid), int(not packet_valid),
        int(recovered), int(residual), int(prior.get("recovered")), int(budget),
    ))
    ready = faults == 0
    alpha_available = bool(diagnostics.get("alpha_available")) if ready else False
    review_available = bool(packet.get("alpha_available")) if ready else False
    report = {
        "contract_version": RELIABILITY_CONTRACT_VERSION,
        "reliability_posture": "goal_and_planning_alpha_context_reliable" if ready else "literal_current_request_only_recovery",
        "ordinary_conversation_ready": ready,
        "projection_valid": projection_valid,
        "diagnostics_valid": diagnostics_valid,
        "review_state_valid": state_valid,
        "review_packet_valid": packet_valid,
        "prior_continuity_valid": not bool(prior.get("recovered")),
        "recovered_projection": recovered,
        "residual_alpha_detected": residual,
        "receipt_budget_exceeded": budget,
        "fault_count": min(faults, MAX_RELIABILITY_FAULTS),
        "verified_prior_receipt_count": int(prior.get("verified_receipt_count") or 0),
        "replayed_prior_receipt_count": int(prior.get("replayed_receipt_count") or 0),
        "malformed_prior_receipt_count": int(prior.get("malformed_receipt_count") or 0),
        "tampered_prior_receipt_count": int(prior.get("tampered_receipt_count") or 0),
        "alpha_available": alpha_available,
        "review_available": review_available,
        "literal_current_request_precedence": True,
        "historical_truth_preserved": True,
        "goal_activated": False, "plan_activated": False, "plan_persisted": False,
        "alternative_selected": False, "schedule_created": False, "tool_routed": False,
        "action_executed": False, "source_edited": False, "autonomous_work_started": False,
        "memory_mutated": False, "lesson_committed": False, "model_trained": False,
        "model_weights_changed": False, "installation_performed": False,
        "promotion_performed": False, "certification_performed": False,
        "authority": "none", "content_free": True,
        "alpha_state_digest": str(state.get("state_digest") or "") if ready else "",
        "review_state_digest": str(review_state.get("review_state_digest") or "") if ready else "",
        "review_packet_digest": str(packet.get("review_packet_digest") or "") if ready else "",
    }
    report["reliability_digest"] = _digest(report)
    prompt = '<goal_and_planning_alpha_reliability data_only="true" authority="none">' + json.dumps(
        {key: report[key] for key in (
            "contract_version", "reliability_posture", "ordinary_conversation_ready",
            "alpha_available", "review_available", "fault_count", "authority", "content_free",
        )}, sort_keys=True, separators=(",", ":")
    ) + '</goal_and_planning_alpha_reliability>'
    return {"report": report, "prompt_section": prompt}


def verify_goal_and_planning_alpha_reliability(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _ALPHA_RELIABILITY_FIELDS or not _size_ok(row):
        return False
    supplied = row.pop("reliability_digest", None)
    ready = row.get("ordinary_conversation_ready")
    counts = all(
        isinstance(row.get(key), int) and 0 <= row[key] <= MAX_PRIOR_RECEIPTS
        for key in (
            "verified_prior_receipt_count", "replayed_prior_receipt_count",
            "malformed_prior_receipt_count", "tampered_prior_receipt_count",
        )
    )
    coherent = (
        ready is True
        and row.get("reliability_posture") == "goal_and_planning_alpha_context_reliable"
        and row.get("fault_count") == 0
        and row.get("projection_valid") is True
        and row.get("diagnostics_valid") is True
        and row.get("review_state_valid") is True
        and row.get("review_packet_valid") is True
        and row.get("prior_continuity_valid") is True
        and row.get("alpha_available") is row.get("review_available")
        and all(len(str(row.get(key) or "")) == 64 for key in (
            "alpha_state_digest", "review_state_digest", "review_packet_digest",
        ))
    ) or (
        ready is False
        and row.get("reliability_posture") == "literal_current_request_only_recovery"
        and row.get("alpha_available") is False
        and row.get("review_available") is False
        and row.get("alpha_state_digest") == ""
        and row.get("review_state_digest") == ""
        and row.get("review_packet_digest") == ""
    )
    return bool(
        isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)
        and row.get("contract_version") == RELIABILITY_CONTRACT_VERSION
        and isinstance(ready, bool) and coherent and counts
        and isinstance(row.get("fault_count"), int) and 0 <= row["fault_count"] <= MAX_RELIABILITY_FAULTS
        and row.get("verified_prior_receipt_count") <= 1
        and row.get("literal_current_request_precedence") is True
        and row.get("historical_truth_preserved") is True
        and all(row.get(key) is False for key in (
            "goal_activated", "plan_activated", "plan_persisted", "alternative_selected",
            "schedule_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
            "model_weights_changed", "installation_performed", "promotion_performed",
            "certification_performed",
        ))
        and row.get("authority") == "none" and row.get("content_free") is True
    )

