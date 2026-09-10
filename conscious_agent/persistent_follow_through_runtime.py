from __future__ import annotations

"""Bounded, review-only persistent follow-through continuity.

Consumes verified v1172 plan-simulation state and produces structural continuity
for resuming review across turns, interruptions, and restarts. It never activates,
persists, schedules, routes, edits, or executes a plan.
"""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1173.2"
MAX_COMPONENT_BYTES = 65536
MAX_PRIOR_RECEIPTS = 64


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _size_ok(value: object) -> bool:
    try:
        return len(json.dumps(value, sort_keys=True, default=str).encode()) <= MAX_COMPONENT_BYTES
    except Exception:
        return False


def verify_persistent_follow_through_handoff(value: object) -> bool:
    row = _mapping(value)
    expected = {
        "contract_version", "follow_through_available", "milestone_count", "dependency_count",
        "stopping_condition_count", "provider_completed", "assistant_memory_committed",
        "eligible_for_continuity", "plan_activated", "plan_persisted", "schedule_created",
        "tool_routed", "action_executed", "authority", "content_free", "receipt_digest",
    }
    if set(row) != expected or row.get("contract_version") != CONTRACT_VERSION or not _size_ok(row):
        return False
    supplied = row.pop("receipt_digest", None)
    bounded = all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in (
        "milestone_count", "dependency_count", "stopping_condition_count"
    ))
    return bool(
        isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)
        and bounded and row.get("plan_activated") is False and row.get("plan_persisted") is False
        and row.get("schedule_created") is False and row.get("tool_routed") is False
        and row.get("action_executed") is False and row.get("authority") == "none"
        and row.get("content_free") is True
    )


def _receipt_from_row(row: object) -> dict[str, Any]:
    return _mapping(_mapping(row).get("persistent_follow_through_handoff"))


def validate_prior_follow_through_receipts(rows: object) -> dict[str, Any]:
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
        if not verify_persistent_follow_through_handoff(receipt):
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
        "recovered": recovered,
        "continuity_available": bool(latest.get("eligible_for_continuity")) and not recovered,
        "prior_milestone_count": int(latest.get("milestone_count") or 0) if not recovered else 0,
    }


def _simulation_status(simulation: object, review: object, reliability: object) -> tuple[bool, dict[str, Any]]:
    sim = _mapping(simulation)
    comparison = _mapping(sim.get("comparison"))
    policy = _mapping(sim.get("policy"))
    packet = _mapping(_mapping(review).get("review_packet"))
    reliable = _mapping(_mapping(reliability).get("report") or reliability)
    valid = bool(
        sim and comparison and policy and packet and reliable
        and _size_ok(sim) and _size_ok(review) and _size_ok(reliability)
        and comparison.get("alternative_count") == 3
        and comparison.get("preferred_alternative_selected") is False
        and policy.get("operator_review_required") is True
        and policy.get("alternative_selection_permitted") is False
        and packet.get("operator_approval_required") is True
        and packet.get("alternative_selected") is False
        and reliable.get("reliability_posture") == "plan_simulation_context_reliable"
        and reliable.get("ordinary_conversation_ready") is True
        and reliable.get("simulation_available") is True
    )
    return valid, comparison


def build_persistent_follow_through_projection(
    simulation_projection: object,
    simulation_review_projection: object,
    simulation_reliability: object,
    *,
    prior_follow_through_receipts: object = (),
    protected_operator_constraints: tuple[str, ...] = (
        "literal_current_request_precedence", "no_plan_activation", "no_plan_persistence",
        "no_scheduling", "no_tool_routing", "no_action_execution", "operator_review_required",
    ),
) -> dict[str, Any]:
    required = {
        "literal_current_request_precedence", "no_plan_activation", "no_plan_persistence",
        "no_scheduling", "no_tool_routing", "no_action_execution", "operator_review_required",
    }
    valid_simulation, comparison = _simulation_status(
        simulation_projection, simulation_review_projection, simulation_reliability
    )
    continuity = validate_prior_follow_through_receipts(prior_follow_through_receipts)
    recovered = not required.issubset(set(protected_operator_constraints)) or not valid_simulation or continuity["recovered"]
    available = valid_simulation and not recovered
    resumed = available and continuity["continuity_available"]

    milestone_categories = (
        ["review_current_evidence", "reconcile_interruption_state", "verify_resume_conditions"] if available else []
    )
    dependency_categories = ["operator_review", "verified_simulation", "current_priority_confirmation"] if available else []
    stopping_categories = ["operator_stop", "priority_changed", "evidence_invalid", "budget_exhausted"] if available else []
    continuity_state = {
        "contract_version": CONTRACT_VERSION,
        "follow_through_available": available,
        "continuity_disposition": "verified_resume_review" if resumed else ("current_turn_review" if available else "none"),
        "interruption_disposition": "resume_from_verified_structural_receipt" if resumed else "start_from_current_verified_state",
        "priority_disposition": "current_operator_request_controls",
        "milestone_categories": milestone_categories,
        "milestone_count": len(milestone_categories),
        "dependency_categories": dependency_categories,
        "dependency_count": len(dependency_categories),
        "stopping_condition_categories": stopping_categories,
        "stopping_condition_count": len(stopping_categories),
        "alternative_count": int(comparison.get("alternative_count") or 0) if available else 0,
        "content_free": True,
    }
    continuity_state["continuity_digest"] = _digest(continuity_state)
    policy = {
        "contract_version": CONTRACT_VERSION,
        "follow_through_posture": "review_only_persistent_continuity" if available else (
            "literal_current_request_only_recovery" if recovered else "no_follow_through_candidate"
        ),
        "literal_current_request_precedence": True,
        "changing_priority_requires_reconciliation": True,
        "operator_review_required": True,
        "plan_activation_permitted": False,
        "plan_persistence_permitted": False,
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
        "verified_simulation_available": valid_simulation,
        **continuity,
        "interruption_recovery_supported": available,
        "restart_resume_supported": available,
        "priority_change_reconciliation_supported": available,
        "historical_follow_through_architecture_reused": True,
        "content_free": True,
    }
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "follow_through_available": available,
        "resumed_from_verified_receipt": resumed,
        "milestone_count": len(milestone_categories),
        "dependency_count": len(dependency_categories),
        "stopping_condition_count": len(stopping_categories),
        "recovered": recovered,
        "authority_field_count": 0,
        "private_field_count": 0,
        "integrity_digest": _digest({"policy": policy, "evidence": evidence, "continuity": continuity_state}),
    }
    prompt = (
        "[Persistent follow-through: review-only continuity; milestones=%d; dependencies=%d; "
        "resume only from verified structural receipts; current operator priority controls; do not persist, schedule, route, or execute.]"
        % (len(milestone_categories), len(dependency_categories))
        if available else "[Persistent follow-through: no reliable continuity candidate.]"
    )
    return {"policy": policy, "evidence": evidence, "continuity": continuity_state, "diagnostics": diagnostics, "prompt_section": prompt}


def build_persistent_follow_through_handoff(
    projection: object, *, provider_completed: bool, assistant_memory_committed: bool
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    continuity = _mapping(value.get("continuity"))
    available = bool(continuity.get("follow_through_available")) and not bool(policy.get("policy_recovered"))
    row = {
        "contract_version": CONTRACT_VERSION,
        "follow_through_available": available,
        "milestone_count": int(continuity.get("milestone_count") or 0) if available else 0,
        "dependency_count": int(continuity.get("dependency_count") or 0) if available else 0,
        "stopping_condition_count": int(continuity.get("stopping_condition_count") or 0) if available else 0,
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_continuity": bool(available and provider_completed and assistant_memory_committed),
        "plan_activated": False,
        "plan_persisted": False,
        "schedule_created": False,
        "tool_routed": False,
        "action_executed": False,
        "authority": "none",
        "content_free": True,
    }
    row["receipt_digest"] = _digest(row)
    return row

# v1173.3-v1173.5 cross-turn review integration.
REVIEW_CONTRACT_VERSION = "v1173.5"
MAX_REVIEW_PROMPT_CHARS = 4096
_REVIEW_STATE_FIELDS = {
    "contract_version", "review_disposition", "continuity_stability_band",
    "milestone_readiness_band", "dependency_disposition", "stopping_posture",
    "milestone_count", "dependency_count", "stopping_condition_count",
    "verified_prior_receipt_count", "replayed_prior_receipt_count",
    "follow_through_available", "operator_review_required", "plan_activated",
    "plan_persisted", "schedule_created", "tool_routed", "action_executed",
    "authority", "content_free", "review_state_digest",
}
_REVIEW_PACKET_FIELDS = {
    "contract_version", "review_disposition", "continuity_stability_band",
    "milestone_categories", "dependency_categories", "stopping_condition_categories",
    "milestone_readiness_band", "dependency_disposition", "stopping_posture",
    "operator_review_required", "operator_approval_required", "follow_through_available",
    "plan_activated", "plan_persisted", "schedule_created", "tool_routed",
    "action_executed", "source_edited", "autonomous_work_started", "authority",
    "content_free", "continuity_digest", "review_packet_digest",
}


def _valid_exact_digest(value: object, fields: set[str], digest_key: str) -> bool:
    row = _mapping(value)
    if set(row) != fields or not _size_ok(row):
        return False
    supplied = row.pop(digest_key, None)
    return isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)


def build_persistent_follow_through_review_projection(projection: object) -> dict[str, Any]:
    """Build a bounded operator-review view without persisting or executing a plan."""
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    continuity = _mapping(value.get("continuity"))
    diagnostics = _mapping(value.get("diagnostics"))
    supplied = str(continuity.get("continuity_digest") or "")
    unsigned = {k: v for k, v in continuity.items() if k != "continuity_digest"}
    continuity_valid = bool(
        continuity and _size_ok(continuity) and supplied == _digest(unsigned)
        and policy.get("authority") == "none"
        and policy.get("operator_review_required") is True
        and policy.get("plan_activation_permitted") is False
        and policy.get("plan_persistence_permitted") is False
        and policy.get("scheduling_permitted") is False
        and diagnostics.get("integrity_digest") == _digest({"policy": policy, "evidence": evidence, "continuity": continuity})
    )
    recovered = bool(policy.get("policy_recovered")) or not continuity_valid
    available = bool(continuity.get("follow_through_available")) and not recovered
    milestones = list(continuity.get("milestone_categories") or []) if available else []
    dependencies = list(continuity.get("dependency_categories") or []) if available else []
    stopping = list(continuity.get("stopping_condition_categories") or []) if available else []
    counts_ok = bool(
        len(milestones) == int(continuity.get("milestone_count") or 0)
        and len(dependencies) == int(continuity.get("dependency_count") or 0)
        and len(stopping) == int(continuity.get("stopping_condition_count") or 0)
        and max((len(milestones), len(dependencies), len(stopping)), default=0) <= 64
    )
    if available and not counts_ok:
        recovered, available = True, False
        milestones, dependencies, stopping = [], [], []
    verified = int(evidence.get("verified_receipt_count") or 0) if available else 0
    replayed = int(evidence.get("replayed_receipt_count") or 0)
    stable = bool(available and verified > 0 and evidence.get("continuity_available"))
    disposition = "literal_current_request_only_recovery" if recovered else (
        "stable_follow_through_review" if stable else ("emerging_follow_through_review" if available else "no_follow_through_review")
    )
    state = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": disposition,
        "continuity_stability_band": "verified_cross_turn" if stable else ("current_turn_only" if available else "none"),
        "milestone_readiness_band": "reviewable" if available else "none",
        "dependency_disposition": "operator_and_evidence_gated" if available else "none",
        "stopping_posture": "explicit_bounded_stops" if available else "none",
        "milestone_count": len(milestones), "dependency_count": len(dependencies),
        "stopping_condition_count": len(stopping),
        "verified_prior_receipt_count": verified, "replayed_prior_receipt_count": replayed,
        "follow_through_available": available, "operator_review_required": True,
        "plan_activated": False, "plan_persisted": False, "schedule_created": False,
        "tool_routed": False, "action_executed": False, "authority": "none", "content_free": True,
    }
    state["review_state_digest"] = _digest(state)
    packet = {
        "contract_version": REVIEW_CONTRACT_VERSION, "review_disposition": disposition,
        "continuity_stability_band": state["continuity_stability_band"],
        "milestone_categories": milestones, "dependency_categories": dependencies,
        "stopping_condition_categories": stopping,
        "milestone_readiness_band": state["milestone_readiness_band"],
        "dependency_disposition": state["dependency_disposition"], "stopping_posture": state["stopping_posture"],
        "operator_review_required": True, "operator_approval_required": True,
        "follow_through_available": available, "plan_activated": False, "plan_persisted": False,
        "schedule_created": False, "tool_routed": False, "action_executed": False,
        "source_edited": False, "autonomous_work_started": False, "authority": "none",
        "content_free": True, "continuity_digest": supplied if available else "",
    }
    packet["review_packet_digest"] = _digest(packet)
    prompt_payload = {k: packet[k] for k in (
        "contract_version", "review_disposition", "continuity_stability_band",
        "milestone_categories", "dependency_categories", "stopping_condition_categories",
        "milestone_readiness_band", "dependency_disposition", "stopping_posture",
        "operator_review_required", "operator_approval_required", "follow_through_available",
        "plan_activated", "plan_persisted", "schedule_created", "tool_routed",
        "action_executed", "authority", "content_free",
    )}
    prompt = '<persistent_follow_through_review data_only="true" authority="none">' + json.dumps(
        prompt_payload, sort_keys=True, separators=(",", ":")
    ) + '</persistent_follow_through_review>'
    if len(prompt) > MAX_REVIEW_PROMPT_CHARS:
        raise ValueError("persistent follow-through review prompt exceeded bound")
    return {"state": state, "review_packet": packet, "prompt_section": prompt}


def verify_persistent_follow_through_review_state(value: object) -> bool:
    if not _valid_exact_digest(value, _REVIEW_STATE_FIELDS, "review_state_digest"):
        return False
    row = _mapping(value)
    return bool(
        row.get("contract_version") == REVIEW_CONTRACT_VERSION
        and row.get("operator_review_required") is True and row.get("authority") == "none"
        and row.get("content_free") is True
        and all(row.get(k) is False for k in ("plan_activated", "plan_persisted", "schedule_created", "tool_routed", "action_executed"))
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in (
            "milestone_count", "dependency_count", "stopping_condition_count",
            "verified_prior_receipt_count", "replayed_prior_receipt_count",
        ))
    )


def verify_persistent_follow_through_review_packet(value: object) -> bool:
    if not _valid_exact_digest(value, _REVIEW_PACKET_FIELDS, "review_packet_digest"):
        return False
    row = _mapping(value)
    return bool(
        row.get("contract_version") == REVIEW_CONTRACT_VERSION
        and row.get("operator_review_required") is True and row.get("operator_approval_required") is True
        and row.get("authority") == "none" and row.get("content_free") is True
        and all(row.get(k) is False for k in (
            "plan_activated", "plan_persisted", "schedule_created", "tool_routed", "action_executed",
            "source_edited", "autonomous_work_started",
        ))
        and all(isinstance(row.get(k), list) and len(row[k]) <= 64 for k in (
            "milestone_categories", "dependency_categories", "stopping_condition_categories",
        ))
    )

# v1173.6-v1173.8 strict diagnostics, fail-closed recovery, and shared reliability.
RELIABILITY_CONTRACT_VERSION = "1173.8"
MAX_RELIABILITY_FAULTS = 64
_FOLLOW_THROUGH_DIAGNOSTICS_FIELDS = {
    "contract_version", "follow_through_available", "resumed_from_verified_receipt",
    "milestone_count", "dependency_count", "stopping_condition_count", "recovered",
    "authority_field_count", "private_field_count", "integrity_digest",
}
_FOLLOW_THROUGH_RELIABILITY_FIELDS = {
    "contract_version", "reliability_posture", "ordinary_conversation_ready",
    "projection_valid", "review_state_valid", "review_packet_valid", "prior_continuity_valid",
    "recovered_projection", "residual_follow_through_detected", "receipt_budget_exceeded",
    "fault_count", "verified_prior_receipt_count", "replayed_prior_receipt_count",
    "malformed_prior_receipt_count", "tampered_prior_receipt_count",
    "follow_through_available", "review_available", "literal_current_request_precedence",
    "historical_truth_preserved", "goal_activated", "plan_activated", "plan_persisted",
    "schedule_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
    "model_weights_changed", "installation_performed", "promotion_performed",
    "certification_performed", "authority", "content_free", "continuity_digest",
    "review_state_digest", "review_packet_digest", "reliability_digest",
}


def verify_persistent_follow_through_diagnostics_strict(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _FOLLOW_THROUGH_DIAGNOSTICS_FIELDS or not _size_ok(row):
        return False
    supplied = row.pop("integrity_digest", None)
    return bool(
        isinstance(supplied, str) and len(supplied) == 64
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in (
            "milestone_count", "dependency_count", "stopping_condition_count",
            "authority_field_count", "private_field_count",
        ))
        and row.get("authority_field_count") == 0 and row.get("private_field_count") == 0
        and isinstance(row.get("follow_through_available"), bool)
        and isinstance(row.get("resumed_from_verified_receipt"), bool)
        and isinstance(row.get("recovered"), bool)
    )


def build_persistent_follow_through_reliability(
    projection: object, review_projection: object, *, prior_follow_through_receipts: object = (),
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    continuity = _mapping(value.get("continuity"))
    diagnostics = _mapping(value.get("diagnostics"))
    review = _mapping(review_projection)
    state = _mapping(review.get("state"))
    packet = _mapping(review.get("review_packet"))
    prior = validate_prior_follow_through_receipts(prior_follow_through_receipts)
    continuity_digest = str(continuity.get("continuity_digest") or "")
    projection_valid = bool(
        continuity and continuity_digest == _digest({k: v for k, v in continuity.items() if k != "continuity_digest"})
        and policy.get("authority") == "none"
        and policy.get("plan_activation_permitted") is False
        and policy.get("plan_persistence_permitted") is False
        and policy.get("scheduling_permitted") is False
        and policy.get("tool_routing_permitted") is False
        and policy.get("action_execution_permitted") is False
        and diagnostics.get("integrity_digest") == _digest({"policy": policy, "evidence": evidence, "continuity": continuity})
        and verify_persistent_follow_through_diagnostics_strict(diagnostics)
    )
    state_valid = verify_persistent_follow_through_review_state(state)
    packet_valid = verify_persistent_follow_through_review_packet(packet)
    recovered = bool(policy.get("policy_recovered"))
    residual = bool(recovered and (
        continuity.get("follow_through_available") or continuity.get("milestone_categories")
        or continuity.get("dependency_categories") or continuity.get("stopping_condition_categories")
        or state.get("follow_through_available") or packet.get("follow_through_available")
    ))
    budget = bool(prior.get("receipt_budget_exceeded"))
    faults = sum((
        int(not projection_valid), int(not state_valid), int(not packet_valid), int(recovered),
        int(residual), int(prior.get("recovered")), int(budget),
    ))
    ready = faults == 0
    report = {
        "contract_version": RELIABILITY_CONTRACT_VERSION,
        "reliability_posture": "persistent_follow_through_context_reliable" if ready else "literal_current_request_only_recovery",
        "ordinary_conversation_ready": ready,
        "projection_valid": projection_valid,
        "review_state_valid": state_valid,
        "review_packet_valid": packet_valid,
        "prior_continuity_valid": not bool(prior.get("recovered")),
        "recovered_projection": recovered,
        "residual_follow_through_detected": residual,
        "receipt_budget_exceeded": budget,
        "fault_count": min(faults, MAX_RELIABILITY_FAULTS),
        "verified_prior_receipt_count": int(prior.get("verified_receipt_count") or 0),
        "replayed_prior_receipt_count": int(prior.get("replayed_receipt_count") or 0),
        "malformed_prior_receipt_count": int(prior.get("malformed_receipt_count") or 0),
        "tampered_prior_receipt_count": int(prior.get("tampered_receipt_count") or 0),
        "follow_through_available": bool(continuity.get("follow_through_available")) if ready else False,
        "review_available": bool(packet.get("follow_through_available")) if ready else False,
        "literal_current_request_precedence": True,
        "historical_truth_preserved": True,
        "goal_activated": False, "plan_activated": False, "plan_persisted": False,
        "schedule_created": False, "tool_routed": False, "action_executed": False,
        "source_edited": False, "autonomous_work_started": False, "memory_mutated": False,
        "lesson_committed": False, "model_trained": False, "model_weights_changed": False,
        "installation_performed": False, "promotion_performed": False, "certification_performed": False,
        "authority": "none", "content_free": True,
        "continuity_digest": continuity_digest if ready else "",
        "review_state_digest": str(state.get("review_state_digest") or "") if ready else "",
        "review_packet_digest": str(packet.get("review_packet_digest") or "") if ready else "",
    }
    report["reliability_digest"] = _digest(report)
    prompt = '<persistent_follow_through_reliability data_only="true" authority="none">' + json.dumps(
        {k: report[k] for k in (
            "contract_version", "reliability_posture", "ordinary_conversation_ready",
            "follow_through_available", "review_available", "fault_count", "authority", "content_free",
        )}, sort_keys=True, separators=(",", ":")
    ) + '</persistent_follow_through_reliability>'
    return {"report": report, "prompt_section": prompt}


def verify_persistent_follow_through_reliability(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _FOLLOW_THROUGH_RELIABILITY_FIELDS or not _size_ok(row):
        return False
    supplied = row.pop("reliability_digest", None)
    ready = row.get("ordinary_conversation_ready")
    counts = all(isinstance(row.get(k), int) and 0 <= row[k] <= MAX_PRIOR_RECEIPTS for k in (
        "verified_prior_receipt_count", "replayed_prior_receipt_count",
        "malformed_prior_receipt_count", "tampered_prior_receipt_count",
    ))
    coherent = (
        ready is True and row.get("reliability_posture") == "persistent_follow_through_context_reliable"
        and row.get("fault_count") == 0 and row.get("projection_valid") is True
        and row.get("review_state_valid") is True and row.get("review_packet_valid") is True
    ) or (
        ready is False and row.get("reliability_posture") == "literal_current_request_only_recovery"
        and row.get("follow_through_available") is False and row.get("review_available") is False
        and row.get("continuity_digest") == "" and row.get("review_state_digest") == ""
        and row.get("review_packet_digest") == ""
    )
    return bool(
        isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)
        and row.get("contract_version") == RELIABILITY_CONTRACT_VERSION and isinstance(ready, bool)
        and coherent and counts and isinstance(row.get("fault_count"), int)
        and 0 <= row["fault_count"] <= MAX_RELIABILITY_FAULTS
        and row.get("verified_prior_receipt_count") <= 1
        and row.get("literal_current_request_precedence") is True
        and row.get("historical_truth_preserved") is True
        and all(row.get(k) is False for k in (
            "goal_activated", "plan_activated", "plan_persisted", "schedule_created", "tool_routed",
            "action_executed", "source_edited", "autonomous_work_started", "memory_mutated",
            "lesson_committed", "model_trained", "model_weights_changed", "installation_performed",
            "promotion_performed", "certification_performed",
        ))
        and row.get("authority") == "none" and row.get("content_free") is True
    )
