from __future__ import annotations

"""Bounded, review-only plan simulation and alternative comparison.

Consumes the verified v1171 hierarchical-planning projection. It predicts only
structural risk bands and compares fixed alternative classes. It never selects,
approves, persists, schedules, routes, edits, or executes a plan.
"""

import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1172.2"
MAX_COMPONENT_BYTES = 65536
MAX_PRIOR_RECEIPTS = 64
MAX_ALTERNATIVES = 3


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _size_ok(value: object) -> bool:
    try:
        return len(json.dumps(value, sort_keys=True, default=str).encode()) <= MAX_COMPONENT_BYTES
    except Exception:
        return False


def _planning_status(projection: object, reliability: object) -> tuple[bool, dict[str, Any]]:
    plan = _mapping(projection)
    hierarchy = _mapping(plan.get("hierarchy"))
    policy = _mapping(plan.get("policy"))
    reliable = _mapping(reliability)
    valid = bool(
        plan and hierarchy and policy and reliable and _size_ok(plan) and _size_ok(reliable)
        and hierarchy.get("plan_candidate_available") is True
        and policy.get("operator_review_required") is True
        and policy.get("plan_activation_permitted") is False
        and policy.get("action_execution_permitted") is False
        and reliable.get("reliability_posture") == "hierarchical_planning_context_reliable"
        and reliable.get("ordinary_conversation_ready") is True
        and reliable.get("plan_candidate_available") is True
    )
    return valid, hierarchy


def verify_plan_simulation_review_handoff(value: object) -> bool:
    row = _mapping(value)
    expected = {
        "contract_version", "simulation_available", "alternative_count", "risk_count",
        "provider_completed", "assistant_memory_committed", "eligible_for_review_continuity",
        "alternative_selected", "plan_activated", "action_executed", "authority",
        "content_free", "receipt_digest",
    }
    if set(row) != expected or row.get("contract_version") != CONTRACT_VERSION:
        return False
    supplied = row.pop("receipt_digest", None)
    return bool(
        isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in ("alternative_count", "risk_count"))
        and row.get("alternative_selected") is False and row.get("plan_activated") is False
        and row.get("action_executed") is False and row.get("authority") == "none"
        and row.get("content_free") is True
    )


def _receipt_from_row(row: object) -> dict[str, Any]:
    return _mapping(_mapping(row).get("plan_simulation_review_handoff"))


def validate_prior_plan_simulation_receipts(rows: object) -> dict[str, Any]:
    items = list(rows) if isinstance(rows, (list, tuple)) else []
    inspected = items[-MAX_PRIOR_RECEIPTS:]
    seen: set[str] = set()
    verified = replayed = malformed = tampered = 0
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
        if not verify_plan_simulation_review_handoff(receipt):
            tampered += 1
            continue
        seen.add(digest)
        verified += 1
    recovered = malformed > 0 or tampered > 0 or len(items) > MAX_PRIOR_RECEIPTS
    return {
        "verified_receipt_count": 0 if recovered else min(verified, 1),
        "replayed_receipt_count": replayed,
        "malformed_receipt_count": malformed,
        "tampered_receipt_count": tampered,
        "receipt_budget_exceeded": len(items) > MAX_PRIOR_RECEIPTS,
        "recovered": recovered,
        "continuity_available": verified > 0 and not recovered,
    }


def build_plan_simulation_projection(
    planning_projection: object,
    planning_reliability: object,
    *,
    prior_simulation_receipts: object = (),
    protected_operator_constraints: tuple[str, ...] = (
        "literal_current_request_precedence", "no_plan_activation", "no_alternative_selection",
        "no_tool_routing", "no_action_execution", "operator_review_required",
    ),
) -> dict[str, Any]:
    required = {
        "literal_current_request_precedence", "no_plan_activation", "no_alternative_selection",
        "no_tool_routing", "no_action_execution", "operator_review_required",
    }
    valid_plan, hierarchy = _planning_status(planning_projection, planning_reliability)
    continuity = validate_prior_plan_simulation_receipts(prior_simulation_receipts)
    recovered = not required.issubset(set(protected_operator_constraints)) or not valid_plan or continuity["recovered"]
    available = valid_plan and not recovered
    milestone_count = int(hierarchy.get("milestone_count") or 0) if available else 0
    dependency_count = int(hierarchy.get("dependency_count") or 0) if available else 0
    stopping_count = int(hierarchy.get("stopping_condition_count") or 0) if available else 0

    alternatives = [
        {"alternative_class": "evidence_first", "change_scope_band": "narrow", "verification_intensity_band": "high", "resource_cost_band": "medium"},
        {"alternative_class": "balanced", "change_scope_band": "bounded", "verification_intensity_band": "medium", "resource_cost_band": "medium"},
        {"alternative_class": "minimal_change", "change_scope_band": "minimal", "verification_intensity_band": "medium", "resource_cost_band": "low"},
    ] if available else []
    risk_categories = ["insufficient_evidence", "dependency_failure", "verification_gap"] if available else []
    risk_bands = {
        "insufficient_evidence": "medium" if milestone_count < 3 else "low",
        "dependency_failure": "medium" if dependency_count else "low",
        "verification_gap": "medium" if stopping_count < 3 else "low",
    } if available else {}
    comparison = {
        "contract_version": CONTRACT_VERSION,
        "alternative_count": len(alternatives),
        "alternatives": alternatives[:MAX_ALTERNATIVES],
        "risk_category_count": len(risk_categories),
        "risk_categories": risk_categories,
        "risk_bands": risk_bands,
        "comparison_posture": "operator_review_required" if available else "none",
        "preferred_alternative_selected": False,
        "content_free": True,
    }
    comparison["comparison_digest"] = _digest(comparison)
    policy = {
        "contract_version": CONTRACT_VERSION,
        "simulation_posture": "review_only_structural_comparison" if available else ("literal_current_request_only_recovery" if recovered else "no_simulation_candidate"),
        "authority": "none", "content_free": True,
        "literal_current_request_precedence": True,
        "operator_review_required": True,
        "alternative_selection_permitted": False,
        "plan_activation_permitted": False,
        "plan_persistence_permitted": False,
        "scheduling_permitted": False,
        "tool_routing_permitted": False,
        "action_execution_permitted": False,
        "source_editing_permitted": False,
        "autonomous_work_permitted": False,
        "policy_recovered": recovered,
    }
    evidence = {
        "contract_version": CONTRACT_VERSION,
        "hierarchical_plan_verified": valid_plan,
        "milestone_count": milestone_count,
        "dependency_count": dependency_count,
        "stopping_condition_count": stopping_count,
        **continuity,
        "historical_simulation_architecture_reused": True,
        "content_free": True,
    }
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "simulation_available": available,
        "alternative_count": len(alternatives),
        "risk_count": len(risk_categories),
        "recovered": recovered,
        "authority_field_count": 0,
        "private_field_count": 0,
        "integrity_digest": _digest({"policy": policy, "evidence": evidence, "comparison": comparison}),
    }
    prompt = (
        "[Plan simulation: review-only structural alternatives=%d; predicted-risk-categories=%d; "
        "do not select, activate, persist, schedule, route tools, or execute.]" % (len(alternatives), len(risk_categories))
        if available else "[Plan simulation: no reliable comparison candidate.]"
    )
    return {"policy": policy, "evidence": evidence, "comparison": comparison, "diagnostics": diagnostics, "prompt_section": prompt}


def build_plan_simulation_review_handoff(
    projection: object, *, provider_completed: bool, assistant_memory_committed: bool
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    comparison = _mapping(value.get("comparison"))
    available = bool(comparison.get("alternative_count")) and not bool(policy.get("policy_recovered"))
    row = {
        "contract_version": CONTRACT_VERSION,
        "simulation_available": available,
        "alternative_count": int(comparison.get("alternative_count") or 0) if available else 0,
        "risk_count": int(comparison.get("risk_category_count") or 0) if available else 0,
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_review_continuity": bool(available and provider_completed and assistant_memory_committed),
        "alternative_selected": False,
        "plan_activated": False,
        "action_executed": False,
        "authority": "none",
        "content_free": True,
    }
    row["receipt_digest"] = _digest(row)
    return row

# v1172.3-v1172.5 cross-turn simulation coherence and operator-review integration.
REVIEW_CONTRACT_VERSION = "v1172.5"
MAX_REVIEW_PROMPT_CHARS = 2048
_REVIEW_STATE_FIELDS = {
    "contract_version", "review_disposition", "alternative_count", "risk_count",
    "comparison_stability_band", "risk_disposition", "continuity_disposition",
    "verified_prior_receipt_count", "replayed_prior_receipt_count",
    "simulation_available", "operator_review_required", "alternative_selected",
    "plan_activated", "tool_routed", "action_executed", "authority", "content_free",
    "review_state_digest",
}
_REVIEW_PACKET_FIELDS = {
    "contract_version", "review_disposition", "alternative_classes", "risk_categories",
    "risk_bands", "comparison_stability_band", "risk_disposition",
    "continuity_disposition", "operator_review_required", "operator_approval_required",
    "simulation_available", "alternative_selected", "plan_activated", "plan_persisted",
    "schedule_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "authority", "content_free", "comparison_digest",
    "review_packet_digest",
}


def _valid_exact_digest(value: object, fields: set[str], digest_field: str) -> bool:
    row = _mapping(value)
    if set(row) != fields or not _size_ok(row):
        return False
    supplied = row.pop(digest_field, None)
    return isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)


def build_plan_simulation_review_projection(projection: object) -> dict[str, Any]:
    """Create one bounded, non-selecting operator-review view over simulation output."""
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    comparison = _mapping(value.get("comparison"))
    diagnostics = _mapping(value.get("diagnostics"))
    supplied = str(comparison.get("comparison_digest") or "")
    unsigned = {k: v for k, v in comparison.items() if k != "comparison_digest"}
    comparison_valid = bool(
        comparison and _size_ok(comparison) and supplied == _digest(unsigned)
        and policy.get("authority") == "none"
        and policy.get("operator_review_required") is True
        and policy.get("alternative_selection_permitted") is False
        and policy.get("plan_activation_permitted") is False
        and policy.get("action_execution_permitted") is False
        and diagnostics.get("integrity_digest") == _digest({"policy": policy, "evidence": evidence, "comparison": comparison})
    )
    recovered = bool(policy.get("policy_recovered")) or not comparison_valid
    available = bool(comparison.get("alternative_count")) and not recovered
    alternatives = list(comparison.get("alternatives") or []) if available else []
    risks = list(comparison.get("risk_categories") or []) if available else []
    risk_bands = dict(comparison.get("risk_bands") or {}) if available else {}
    counts_ok = bool(
        len(alternatives) == int(comparison.get("alternative_count") or 0)
        and len(risks) == int(comparison.get("risk_category_count") or 0)
        and len(alternatives) <= MAX_ALTERNATIVES
        and set(risk_bands) == set(risks)
    )
    if available and not counts_ok:
        recovered = True
        available = False
        alternatives, risks, risk_bands = [], [], {}
    verified = int(evidence.get("verified_receipt_count") or 0) if available else 0
    replayed = int(evidence.get("replayed_receipt_count") or 0)
    stable = bool(available and verified > 0 and evidence.get("continuity_available"))
    disposition = "literal_current_request_only_recovery" if recovered else (
        "stable_simulation_review" if stable else ("emerging_simulation_review" if available else "no_simulation_review")
    )
    state = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": disposition,
        "alternative_count": len(alternatives),
        "risk_count": len(risks),
        "comparison_stability_band": "verified_cross_turn" if stable else ("current_turn_only" if available else "none"),
        "risk_disposition": "bounded_prediction_only" if available else "none",
        "continuity_disposition": "verified_same_simulation_continuity" if stable else ("current_turn_only" if available else "none"),
        "verified_prior_receipt_count": verified,
        "replayed_prior_receipt_count": replayed,
        "simulation_available": available,
        "operator_review_required": True,
        "alternative_selected": False,
        "plan_activated": False,
        "tool_routed": False,
        "action_executed": False,
        "authority": "none",
        "content_free": True,
    }
    state["review_state_digest"] = _digest(state)
    packet = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": disposition,
        "alternative_classes": [str(row.get("alternative_class") or "none") for row in alternatives],
        "risk_categories": risks,
        "risk_bands": risk_bands,
        "comparison_stability_band": state["comparison_stability_band"],
        "risk_disposition": state["risk_disposition"],
        "continuity_disposition": state["continuity_disposition"],
        "operator_review_required": True,
        "operator_approval_required": True,
        "simulation_available": available,
        "alternative_selected": False,
        "plan_activated": False,
        "plan_persisted": False,
        "schedule_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "authority": "none",
        "content_free": True,
        "comparison_digest": supplied if available else "",
    }
    packet["review_packet_digest"] = _digest(packet)
    prompt_payload = {k: packet[k] for k in (
        "contract_version", "review_disposition", "alternative_classes", "risk_categories",
        "risk_bands", "comparison_stability_band", "risk_disposition", "continuity_disposition",
        "operator_review_required", "operator_approval_required", "simulation_available",
        "alternative_selected", "plan_activated", "plan_persisted", "tool_routed",
        "action_executed", "authority", "content_free",
    )}
    prompt = '<plan_simulation_review data_only="true" authority="none">' + json.dumps(
        prompt_payload, sort_keys=True, separators=(",", ":")
    ) + '</plan_simulation_review>'
    if len(prompt) > MAX_REVIEW_PROMPT_CHARS:
        raise ValueError("plan simulation review prompt exceeded bound")
    return {"state": state, "review_packet": packet, "prompt_section": prompt}


def verify_plan_simulation_review_state(value: object) -> bool:
    if not _valid_exact_digest(value, _REVIEW_STATE_FIELDS, "review_state_digest"):
        return False
    row = _mapping(value)
    return bool(
        row.get("contract_version") == REVIEW_CONTRACT_VERSION
        and row.get("authority") == "none" and row.get("content_free") is True
        and row.get("operator_review_required") is True
        and row.get("alternative_selected") is False and row.get("plan_activated") is False
        and row.get("tool_routed") is False and row.get("action_executed") is False
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in (
            "alternative_count", "risk_count", "verified_prior_receipt_count", "replayed_prior_receipt_count"
        ))
    )


def verify_plan_simulation_review_packet(value: object) -> bool:
    if not _valid_exact_digest(value, _REVIEW_PACKET_FIELDS, "review_packet_digest"):
        return False
    row = _mapping(value)
    return bool(
        row.get("contract_version") == REVIEW_CONTRACT_VERSION
        and row.get("authority") == "none" and row.get("content_free") is True
        and row.get("operator_review_required") is True and row.get("operator_approval_required") is True
        and all(row.get(k) is False for k in (
            "alternative_selected", "plan_activated", "plan_persisted", "schedule_created",
            "tool_routed", "action_executed", "source_edited", "autonomous_work_started"
        ))
        and isinstance(row.get("alternative_classes"), list) and len(row["alternative_classes"]) <= MAX_ALTERNATIVES
        and isinstance(row.get("risk_categories"), list) and len(row["risk_categories"]) <= 64
        and isinstance(row.get("risk_bands"), dict) and set(row["risk_bands"]) == set(row["risk_categories"])
    )


# v1172.6-v1172.8 reliability, recovery, usability, and adversarial hardening.
RELIABILITY_CONTRACT_VERSION = "1172.8"
MAX_RELIABILITY_FAULTS = 64
_SIMULATION_DIAGNOSTICS_FIELDS = {
    "contract_version", "simulation_available", "alternative_count", "risk_count",
    "recovered", "authority_field_count", "private_field_count", "integrity_digest",
}
_SIMULATION_RELIABILITY_FIELDS = {
    "contract_version", "reliability_posture", "ordinary_conversation_ready",
    "projection_valid", "review_state_valid", "review_packet_valid", "prior_continuity_valid",
    "recovered_projection", "residual_simulation_detected", "receipt_budget_exceeded",
    "fault_count", "verified_prior_receipt_count", "replayed_prior_receipt_count",
    "malformed_prior_receipt_count", "tampered_prior_receipt_count",
    "simulation_available", "review_available", "literal_current_request_precedence",
    "historical_truth_preserved", "alternative_selected", "goal_activated", "plan_activated",
    "plan_persisted", "schedule_created", "tool_routed", "action_executed", "source_edited",
    "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
    "model_weights_changed", "installation_performed", "promotion_performed",
    "certification_performed", "authority", "content_free", "comparison_digest",
    "review_state_digest", "review_packet_digest", "reliability_digest",
}


def verify_plan_simulation_diagnostics_strict(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _SIMULATION_DIAGNOSTICS_FIELDS or not _size_ok(row):
        return False
    supplied = row.pop("integrity_digest", None)
    return bool(
        isinstance(supplied, str) and len(supplied) == 64
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in (
            "alternative_count", "risk_count", "authority_field_count", "private_field_count",
        ))
        and row.get("authority_field_count") == 0 and row.get("private_field_count") == 0
    )


def build_plan_simulation_reliability(
    projection: object, review_projection: object, *, prior_simulation_receipts: object = (),
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    comparison = _mapping(value.get("comparison"))
    diagnostics = _mapping(value.get("diagnostics"))
    review = _mapping(review_projection)
    state = _mapping(review.get("state"))
    packet = _mapping(review.get("review_packet"))
    prior = validate_prior_plan_simulation_receipts(prior_simulation_receipts)
    comparison_digest = str(comparison.get("comparison_digest") or "")
    projection_valid = bool(
        comparison and comparison_digest == _digest({k: v for k, v in comparison.items() if k != "comparison_digest"})
        and policy.get("authority") == "none"
        and policy.get("alternative_selection_permitted") is False
        and policy.get("plan_activation_permitted") is False
        and policy.get("action_execution_permitted") is False
        and diagnostics.get("integrity_digest") == _digest({"policy": policy, "evidence": evidence, "comparison": comparison})
        and verify_plan_simulation_diagnostics_strict(diagnostics)
    )
    state_valid = verify_plan_simulation_review_state(state)
    packet_valid = verify_plan_simulation_review_packet(packet)
    recovered = bool(policy.get("policy_recovered"))
    residual = bool(recovered and (
        comparison.get("alternative_count") or comparison.get("alternatives")
        or state.get("simulation_available") or packet.get("simulation_available")
    ))
    budget = bool(prior.get("receipt_budget_exceeded"))
    faults = sum((
        int(not projection_valid), int(not state_valid), int(not packet_valid), int(recovered),
        int(residual), int(prior.get("recovered")), int(budget),
    ))
    ready = faults == 0
    report = {
        "contract_version": RELIABILITY_CONTRACT_VERSION,
        "reliability_posture": "plan_simulation_context_reliable" if ready else "literal_current_request_only_recovery",
        "ordinary_conversation_ready": ready,
        "projection_valid": projection_valid,
        "review_state_valid": state_valid,
        "review_packet_valid": packet_valid,
        "prior_continuity_valid": not bool(prior.get("recovered")),
        "recovered_projection": recovered,
        "residual_simulation_detected": residual,
        "receipt_budget_exceeded": budget,
        "fault_count": min(faults, MAX_RELIABILITY_FAULTS),
        "verified_prior_receipt_count": int(prior.get("verified_receipt_count") or 0),
        "replayed_prior_receipt_count": int(prior.get("replayed_receipt_count") or 0),
        "malformed_prior_receipt_count": int(prior.get("malformed_receipt_count") or 0),
        "tampered_prior_receipt_count": int(prior.get("tampered_receipt_count") or 0),
        "simulation_available": bool(comparison.get("alternative_count")) if ready else False,
        "review_available": bool(packet.get("simulation_available")) if ready else False,
        "literal_current_request_precedence": True,
        "historical_truth_preserved": True,
        "alternative_selected": False, "goal_activated": False, "plan_activated": False,
        "plan_persisted": False, "schedule_created": False, "tool_routed": False,
        "action_executed": False, "source_edited": False, "autonomous_work_started": False,
        "memory_mutated": False, "lesson_committed": False, "model_trained": False,
        "model_weights_changed": False, "installation_performed": False,
        "promotion_performed": False, "certification_performed": False,
        "authority": "none", "content_free": True,
        "comparison_digest": comparison_digest if ready else "",
        "review_state_digest": str(state.get("review_state_digest") or "") if ready else "",
        "review_packet_digest": str(packet.get("review_packet_digest") or "") if ready else "",
    }
    report["reliability_digest"] = _digest(report)
    prompt = '<plan_simulation_reliability data_only="true" authority="none">' + json.dumps(
        {k: report[k] for k in (
            "contract_version", "reliability_posture", "ordinary_conversation_ready",
            "simulation_available", "review_available", "fault_count", "authority", "content_free",
        )}, sort_keys=True, separators=(",", ":")
    ) + '</plan_simulation_reliability>'
    return {"report": report, "prompt_section": prompt}


def verify_plan_simulation_reliability(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _SIMULATION_RELIABILITY_FIELDS or not _size_ok(row):
        return False
    supplied = row.pop("reliability_digest", None)
    ready = row.get("ordinary_conversation_ready")
    counts = all(isinstance(row.get(k), int) and 0 <= row[k] <= MAX_PRIOR_RECEIPTS for k in (
        "verified_prior_receipt_count", "replayed_prior_receipt_count",
        "malformed_prior_receipt_count", "tampered_prior_receipt_count",
    ))
    coherent = (
        ready is True and row.get("reliability_posture") == "plan_simulation_context_reliable"
        and row.get("fault_count") == 0 and row.get("projection_valid") is True
        and row.get("review_state_valid") is True and row.get("review_packet_valid") is True
    ) or (
        ready is False and row.get("reliability_posture") == "literal_current_request_only_recovery"
        and row.get("simulation_available") is False and row.get("review_available") is False
        and row.get("comparison_digest") == "" and row.get("review_state_digest") == ""
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
            "alternative_selected", "goal_activated", "plan_activated", "plan_persisted",
            "schedule_created", "tool_routed", "action_executed", "source_edited",
            "autonomous_work_started", "memory_mutated", "lesson_committed", "model_trained",
            "model_weights_changed", "installation_performed", "promotion_performed",
            "certification_performed",
        ))
        and row.get("authority") == "none" and row.get("content_free") is True
    )
