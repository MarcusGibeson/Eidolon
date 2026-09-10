from __future__ import annotations

"""Bounded, review-only hierarchical planning projections for ordinary conversation.

This layer consumes the verified v1170 goal-candidate projection.  It never
persists, approves, activates, schedules, routes tools, or executes a plan.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

CONTRACT_VERSION = "v1171.5"
MAX_COMPONENT_BYTES = 65536
MAX_PRIOR_RECEIPTS = 64
MAX_MILESTONES = 8
MAX_DEPENDENCIES = 12


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _size_ok(value: object) -> bool:
    try:
        return len(json.dumps(value, sort_keys=True, default=str).encode()) <= MAX_COMPONENT_BYTES
    except Exception:
        return False


def _goal_status(goal_projection: object, goal_reliability: object) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    projection = _mapping(goal_projection)
    policy = _mapping(projection.get("policy"))
    candidate = _mapping(projection.get("candidate"))
    reliability = _mapping(goal_reliability)
    valid = bool(
        projection and policy and candidate and reliability
        and _size_ok(projection) and _size_ok(reliability)
        and policy.get("operator_review_required") is True
        and policy.get("goal_activation_permitted") is False
        and policy.get("plan_creation_permitted") is False
        and reliability.get("reliability_posture") == "goal_candidate_context_reliable"
        and reliability.get("candidate_available") is True
    )
    return valid, policy, candidate


def _receipt_from_row(row: object) -> dict[str, Any]:
    item = _mapping(row)
    receipt = item.get("hierarchical_planning_review_handoff")
    return _mapping(receipt)


def verify_hierarchical_planning_review_handoff(value: object) -> bool:
    row = _mapping(value)
    expected = {
        "contract_version", "plan_candidate_available", "candidate_type", "milestone_count",
        "dependency_count", "stopping_condition_count", "provider_completed",
        "assistant_memory_committed", "eligible_for_review_continuity", "plan_activated",
        "action_executed", "authority", "content_free", "receipt_digest",
    }
    if set(row) != expected or row.get("contract_version") != CONTRACT_VERSION:
        return False
    digest = row.pop("receipt_digest", None)
    ok = (
        isinstance(digest, str) and len(digest) == 64 and digest == _digest(row)
        and row.get("authority") == "none" and row.get("content_free") is True
        and row.get("plan_activated") is False and row.get("action_executed") is False
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in ("milestone_count", "dependency_count", "stopping_condition_count"))
    )
    return bool(ok)


def validate_prior_hierarchical_planning_receipts(rows: object) -> dict[str, Any]:
    items = list(rows) if isinstance(rows, (list, tuple)) else []
    inspected = items[-MAX_PRIOR_RECEIPTS:]
    verified: list[dict[str, Any]] = []
    replayed = malformed = tampered = 0
    seen: set[str] = set()
    for item in inspected:
        receipt = _receipt_from_row(item)
        if not receipt:
            continue
        if not _size_ok(receipt):
            malformed += 1; continue
        digest = str(receipt.get("receipt_digest") or "")
        if digest in seen:
            replayed += 1; continue
        if not verify_hierarchical_planning_review_handoff(receipt):
            tampered += 1; continue
        seen.add(digest); verified.append(receipt)
    conflict = len({r.get("candidate_type") for r in verified if r.get("eligible_for_review_continuity")}) > 1
    recovered = malformed > 0 or tampered > 0 or conflict or len(items) > MAX_PRIOR_RECEIPTS
    return {
        "verified_receipt_count": 0 if recovered else len(verified),
        "replayed_receipt_count": replayed,
        "malformed_receipt_count": malformed,
        "tampered_receipt_count": tampered,
        "receipt_budget_exceeded": len(items) > MAX_PRIOR_RECEIPTS,
        "conflicting_receipts": conflict,
        "recovered": recovered,
        "continuity_available": bool(verified) and not recovered,
    }


def build_hierarchical_planning_projection(
    goal_projection: object,
    goal_reliability: object,
    *,
    prior_planning_receipts: object = (),
    protected_operator_constraints: tuple[str, ...] = (
        "literal_current_request_precedence", "no_goal_activation", "no_plan_activation",
        "no_tool_routing", "no_action_execution", "operator_review_required",
    ),
) -> dict[str, Any]:
    required = {
        "literal_current_request_precedence", "no_goal_activation", "no_plan_activation",
        "no_tool_routing", "no_action_execution", "operator_review_required",
    }
    valid_goal, goal_policy, candidate = _goal_status(goal_projection, goal_reliability)
    continuity = validate_prior_hierarchical_planning_receipts(prior_planning_receipts)
    recovered = not required.issubset(set(protected_operator_constraints)) or not valid_goal or continuity["recovered"]
    candidate_type = str(candidate.get("candidate_type") or "none") if valid_goal and not recovered else "none"
    scope = str(candidate.get("scope_band") or "bounded") if valid_goal and not recovered else "none"
    evidence_count = int(_mapping(goal_projection).get("evidence", {}).get("candidate_evidence_count") or 0) if valid_goal and not recovered else 0
    milestone_count = min(MAX_MILESTONES, 3 if evidence_count >= 2 else 2) if candidate_type != "none" else 0
    dependency_count = min(MAX_DEPENDENCIES, 2 if milestone_count else 0)
    stopping_count = 3 if milestone_count else 0
    posture = "literal_current_request_only_recovery" if recovered else ("review_only_plan_candidate" if milestone_count else "no_plan_candidate")
    milestone_categories = {
        "capability_improvement": ["define_capability_gap", "implement_bounded_capability", "verify_capability_outcome"],
        "reliability_improvement": ["reproduce_reliability_failure", "repair_bounded_failure", "verify_regression_absent"],
        "coherence_repair": ["identify_conflicting_state", "reconcile_bounded_state", "verify_coherent_behavior"],
        "knowledge_improvement": ["identify_knowledge_gap", "acquire_bounded_evidence", "verify_supported_conclusion"],
        "interaction_quality_improvement": ["reproduce_interaction_failure", "repair_conversation_behavior", "verify_natural_continuity"],
        "maintenance_improvement": ["inspect_maintenance_need", "perform_bounded_maintenance", "verify_system_health"],
    }.get(candidate_type, ["establish_baseline", "implement_bounded_change", "verify_outcome"])
    hierarchy = {
        "contract_version": CONTRACT_VERSION,
        "candidate_type": candidate_type,
        "scope_band": scope,
        "hierarchy_depth": 3 if milestone_count else 0,
        "milestone_count": milestone_count,
        "dependency_count": dependency_count,
        "stopping_condition_count": stopping_count,
        "milestone_categories": milestone_categories[:milestone_count],
        "dependency_categories": ["operator_review", "verified_evidence"][:dependency_count],
        "stopping_condition_categories": ["budget_exhausted", "evidence_insufficient", "operator_stop"][:stopping_count],
        "plan_candidate_available": bool(milestone_count),
        "plan_activated": False,
        "content_free": True,
    }
    hierarchy["integrity_digest"] = _digest(hierarchy)
    policy = {
        "contract_version": CONTRACT_VERSION,
        "planning_posture": posture,
        "authority": "none",
        "content_free": True,
        "literal_current_request_precedence": True,
        "operator_review_required": True,
        "goal_activation_permitted": False,
        "plan_activation_permitted": False,
        "tool_routing_permitted": False,
        "action_execution_permitted": False,
        "source_editing_permitted": False,
        "autonomous_work_permitted": False,
        "provider_contact_permitted": False,
        "plan_persistence_permitted": False,
        "response_influence": "bounded_optional_plan_explanation" if milestone_count else "none",
        "policy_recovered": recovered,
    }
    evidence = {
        "contract_version": CONTRACT_VERSION,
        "goal_candidate_verified": valid_goal,
        "goal_candidate_type": candidate_type,
        "goal_evidence_count": evidence_count,
        **continuity,
        "historical_prospective_planning_architecture_reused": True,
        "content_free": True,
    }
    diagnostics = {
        "contract_version": CONTRACT_VERSION,
        "plan_candidate_available": bool(milestone_count),
        "milestone_count": milestone_count,
        "dependency_count": dependency_count,
        "stopping_condition_count": stopping_count,
        "recovered": recovered,
        "authority_field_count": 0,
        "private_field_count": 0,
        "integrity_digest": _digest({"policy": policy, "evidence": evidence, "hierarchy": hierarchy}),
    }
    prompt = (
        "[Hierarchical planning: review-only; objective=%s; milestones=%s; dependencies=%d; stopping-conditions=%d; "
        "do not activate, persist, route tools, or execute.]" % (candidate_type, ",".join(milestone_categories[:milestone_count]), dependency_count, stopping_count)
        if milestone_count else "[Hierarchical planning: no plan candidate.]"
    )
    return {"policy": policy, "evidence": evidence, "hierarchy": hierarchy, "diagnostics": diagnostics, "prompt_section": prompt}


def build_hierarchical_planning_review_handoff(
    projection: object, *, provider_completed: bool, assistant_memory_committed: bool
) -> dict[str, Any]:
    value = _mapping(projection)
    hierarchy = _mapping(value.get("hierarchy"))
    policy = _mapping(value.get("policy"))
    available = bool(hierarchy.get("plan_candidate_available")) and not bool(policy.get("policy_recovered"))
    row = {
        "contract_version": CONTRACT_VERSION,
        "plan_candidate_available": available,
        "candidate_type": str(hierarchy.get("candidate_type") or "none") if available else "none",
        "milestone_count": int(hierarchy.get("milestone_count") or 0) if available else 0,
        "dependency_count": int(hierarchy.get("dependency_count") or 0) if available else 0,
        "stopping_condition_count": int(hierarchy.get("stopping_condition_count") or 0) if available else 0,
        "provider_completed": bool(provider_completed),
        "assistant_memory_committed": bool(assistant_memory_committed),
        "eligible_for_review_continuity": bool(available and provider_completed and assistant_memory_committed),
        "plan_activated": False,
        "action_executed": False,
        "authority": "none",
        "content_free": True,
    }
    row["receipt_digest"] = _digest(row)
    return row

# v1171.3-v1171.5 cross-hierarchy coherence and operator-review integration.
REVIEW_CONTRACT_VERSION = "v1171.5"
MAX_REVIEW_PROMPT_CHARS = 2048
_REVIEW_STATE_FIELDS = {
    "contract_version", "review_disposition", "candidate_type", "hierarchy_depth",
    "milestone_count", "dependency_count", "stopping_condition_count",
    "milestone_readiness_band", "dependency_disposition", "stopping_posture",
    "continuity_disposition", "verified_prior_receipt_count", "replayed_prior_receipt_count",
    "candidate_available", "operator_review_required", "plan_activated", "plan_persisted",
    "tool_routed", "action_executed", "authority", "content_free", "review_state_digest",
}
_REVIEW_PACKET_FIELDS = {
    "contract_version", "review_disposition", "candidate_type", "scope_band",
    "hierarchy_depth", "milestone_categories", "dependency_categories",
    "stopping_condition_categories", "milestone_readiness_band", "dependency_disposition",
    "stopping_posture", "continuity_disposition", "operator_review_required",
    "operator_approval_required", "plan_candidate_available", "plan_activated",
    "plan_persisted", "schedule_created", "tool_routed", "action_executed",
    "source_edited", "autonomous_work_started", "authority", "content_free",
    "hierarchy_digest", "review_packet_digest",
}


def _valid_digest_exact(value: object, fields: set[str], digest_field: str) -> bool:
    row = _mapping(value)
    if set(row) != fields or not _size_ok(row):
        return False
    supplied = row.pop(digest_field, None)
    return isinstance(supplied, str) and len(supplied) == 64 and supplied == _digest(row)


def build_hierarchical_planning_review_projection(projection: object) -> dict[str, Any]:
    """Create one content-free operator-review view over a bounded hierarchy."""
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    hierarchy = _mapping(value.get("hierarchy"))
    diagnostics = _mapping(value.get("diagnostics"))
    hierarchy_digest = str(hierarchy.get("integrity_digest") or "")
    hierarchy_unsigned = {k: v for k, v in hierarchy.items() if k != "integrity_digest"}
    hierarchy_valid = bool(
        hierarchy and _size_ok(hierarchy)
        and hierarchy_digest == _digest(hierarchy_unsigned)
        and policy.get("authority") == "none"
        and policy.get("operator_review_required") is True
        and policy.get("plan_activation_permitted") is False
        and policy.get("action_execution_permitted") is False
        and diagnostics.get("integrity_digest") == _digest({"policy": policy, "evidence": evidence, "hierarchy": hierarchy})
    )
    recovered = bool(policy.get("policy_recovered")) or not hierarchy_valid
    available = bool(hierarchy.get("plan_candidate_available")) and not recovered
    milestones = list(hierarchy.get("milestone_categories") or []) if available else []
    dependencies = list(hierarchy.get("dependency_categories") or []) if available else []
    stops = list(hierarchy.get("stopping_condition_categories") or []) if available else []
    counts_coherent = bool(
        len(milestones) == int(hierarchy.get("milestone_count") or 0)
        and len(dependencies) == int(hierarchy.get("dependency_count") or 0)
        and len(stops) == int(hierarchy.get("stopping_condition_count") or 0)
        and len(milestones) <= MAX_MILESTONES and len(dependencies) <= MAX_DEPENDENCIES
    )
    if available and not counts_coherent:
        recovered = True
        available = False
        milestones = dependencies = stops = []
    verified = int(evidence.get("verified_receipt_count") or 0) if available else 0
    replayed = int(evidence.get("replayed_receipt_count") or 0)
    stable = bool(available and verified > 0 and evidence.get("continuity_available"))
    review_disposition = "literal_current_request_only_recovery" if recovered else (
        "stable_plan_review" if stable else ("emerging_plan_review" if available else "no_plan_review")
    )
    state = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": review_disposition,
        "candidate_type": str(hierarchy.get("candidate_type") or "none") if available else "none",
        "hierarchy_depth": int(hierarchy.get("hierarchy_depth") or 0) if available else 0,
        "milestone_count": len(milestones),
        "dependency_count": len(dependencies),
        "stopping_condition_count": len(stops),
        "milestone_readiness_band": "structured_for_review" if available else "none",
        "dependency_disposition": "operator_and_evidence_pending" if available else "none",
        "stopping_posture": "bounded_and_explicit" if available else "none",
        "continuity_disposition": "verified_same_candidate_continuity" if stable else ("current_turn_only" if available else "none"),
        "verified_prior_receipt_count": verified,
        "replayed_prior_receipt_count": replayed,
        "candidate_available": available,
        "operator_review_required": True,
        "plan_activated": False,
        "plan_persisted": False,
        "tool_routed": False,
        "action_executed": False,
        "authority": "none",
        "content_free": True,
    }
    state["review_state_digest"] = _digest(state)
    packet = {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "review_disposition": review_disposition,
        "candidate_type": state["candidate_type"],
        "scope_band": str(hierarchy.get("scope_band") or "none") if available else "none",
        "hierarchy_depth": state["hierarchy_depth"],
        "milestone_categories": milestones,
        "dependency_categories": dependencies,
        "stopping_condition_categories": stops,
        "milestone_readiness_band": state["milestone_readiness_band"],
        "dependency_disposition": state["dependency_disposition"],
        "stopping_posture": state["stopping_posture"],
        "continuity_disposition": state["continuity_disposition"],
        "operator_review_required": True,
        "operator_approval_required": True,
        "plan_candidate_available": available,
        "plan_activated": False,
        "plan_persisted": False,
        "schedule_created": False,
        "tool_routed": False,
        "action_executed": False,
        "source_edited": False,
        "autonomous_work_started": False,
        "authority": "none",
        "content_free": True,
        "hierarchy_digest": hierarchy_digest if available else "",
    }
    packet["review_packet_digest"] = _digest(packet)
    prompt_payload = {k: packet[k] for k in (
        "contract_version", "review_disposition", "candidate_type", "scope_band",
        "hierarchy_depth", "milestone_categories", "dependency_categories",
        "stopping_condition_categories", "milestone_readiness_band", "dependency_disposition",
        "stopping_posture", "continuity_disposition", "operator_review_required",
        "operator_approval_required", "plan_candidate_available", "plan_activated",
        "plan_persisted", "tool_routed", "action_executed", "authority", "content_free",
    )}
    prompt = '<hierarchical_planning_review data_only="true" authority="none">' + json.dumps(
        prompt_payload, sort_keys=True, separators=(",", ":")
    ) + '</hierarchical_planning_review>'
    if len(prompt) > MAX_REVIEW_PROMPT_CHARS:
        raise ValueError("hierarchical planning review prompt exceeded bound")
    return {"state": state, "review_packet": packet, "prompt_section": prompt}


def verify_hierarchical_planning_review_state(value: object) -> bool:
    if not _valid_digest_exact(value, _REVIEW_STATE_FIELDS, "review_state_digest"):
        return False
    row = _mapping(value)
    return bool(
        row.get("authority") == "none" and row.get("content_free") is True
        and row.get("operator_review_required") is True
        and row.get("plan_activated") is False and row.get("plan_persisted") is False
        and row.get("tool_routed") is False and row.get("action_executed") is False
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in (
            "hierarchy_depth", "milestone_count", "dependency_count", "stopping_condition_count",
            "verified_prior_receipt_count", "replayed_prior_receipt_count",
        ))
    )


def verify_hierarchical_planning_review_packet(value: object) -> bool:
    if not _valid_digest_exact(value, _REVIEW_PACKET_FIELDS, "review_packet_digest"):
        return False
    row = _mapping(value)
    return bool(
        row.get("authority") == "none" and row.get("content_free") is True
        and row.get("operator_review_required") is True and row.get("operator_approval_required") is True
        and all(row.get(k) is False for k in (
            "plan_activated", "plan_persisted", "schedule_created", "tool_routed",
            "action_executed", "source_edited", "autonomous_work_started",
        ))
        and isinstance(row.get("milestone_categories"), list)
        and isinstance(row.get("dependency_categories"), list)
        and isinstance(row.get("stopping_condition_categories"), list)
    )

# v1171.6-v1171.8 reliability, recovery, usability, and adversarial hardening.
RELIABILITY_CONTRACT_VERSION = "1171.8"
MAX_RELIABILITY_FAULTS = 64
_DIAGNOSTICS_FIELDS = {
    "contract_version", "plan_candidate_available", "milestone_count", "dependency_count",
    "stopping_condition_count", "recovered", "authority_field_count", "private_field_count",
    "integrity_digest",
}
_RELIABILITY_FIELDS = {
    "contract_version", "reliability_posture", "ordinary_conversation_ready",
    "projection_valid", "review_state_valid", "review_packet_valid", "prior_continuity_valid",
    "recovered_projection", "residual_plan_detected", "receipt_budget_exceeded", "fault_count",
    "verified_prior_receipt_count", "replayed_prior_receipt_count", "malformed_prior_receipt_count",
    "tampered_prior_receipt_count", "plan_candidate_available", "review_available",
    "literal_current_request_precedence", "historical_truth_preserved", "goal_activated",
    "plan_activated", "plan_persisted", "schedule_created", "tool_routed", "action_executed",
    "source_edited", "autonomous_work_started", "memory_mutated", "lesson_committed",
    "model_trained", "model_weights_changed", "installation_performed", "promotion_performed",
    "certification_performed", "authority", "content_free", "hierarchy_digest",
    "review_state_digest", "review_packet_digest", "reliability_digest",
}


def verify_hierarchical_planning_diagnostics_strict(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _DIAGNOSTICS_FIELDS or not _size_ok(row):
        return False
    supplied = row.pop("integrity_digest", None)
    return bool(
        isinstance(supplied, str) and len(supplied) == 64
        and all(isinstance(row.get(k), int) and 0 <= row[k] <= 64 for k in (
            "milestone_count", "dependency_count", "stopping_condition_count",
            "authority_field_count", "private_field_count",
        ))
        and row.get("authority_field_count") == 0 and row.get("private_field_count") == 0
    )


def build_hierarchical_planning_reliability(
    projection: object, review_projection: object, *, prior_planning_receipts: object = (),
) -> dict[str, Any]:
    value = _mapping(projection)
    policy = _mapping(value.get("policy"))
    evidence = _mapping(value.get("evidence"))
    hierarchy = _mapping(value.get("hierarchy"))
    diagnostics = _mapping(value.get("diagnostics"))
    review = _mapping(review_projection)
    state = _mapping(review.get("state"))
    packet = _mapping(review.get("review_packet"))
    prior = validate_prior_hierarchical_planning_receipts(prior_planning_receipts)
    hierarchy_digest = str(hierarchy.get("integrity_digest") or "")
    hierarchy_valid = bool(
        hierarchy and hierarchy_digest == _digest({k: v for k, v in hierarchy.items() if k != "integrity_digest"})
        and policy.get("authority") == "none" and policy.get("plan_activation_permitted") is False
        and policy.get("action_execution_permitted") is False
        and diagnostics.get("integrity_digest") == _digest({"policy": policy, "evidence": evidence, "hierarchy": hierarchy})
        and verify_hierarchical_planning_diagnostics_strict(diagnostics)
    )
    state_valid = verify_hierarchical_planning_review_state(state)
    packet_valid = verify_hierarchical_planning_review_packet(packet)
    recovered = bool(policy.get("policy_recovered"))
    residual = bool(recovered and (
        hierarchy.get("plan_candidate_available") or state.get("candidate_available")
        or packet.get("plan_candidate_available") or hierarchy.get("milestone_count")
    ))
    budget = bool(prior.get("receipt_budget_exceeded"))
    faults = sum((
        int(not hierarchy_valid), int(not state_valid), int(not packet_valid), int(recovered),
        int(residual), int(prior.get("recovered")), int(budget),
    ))
    ready = faults == 0
    report = {
        "contract_version": RELIABILITY_CONTRACT_VERSION,
        "reliability_posture": "hierarchical_planning_context_reliable" if ready else "literal_current_request_only_recovery",
        "ordinary_conversation_ready": ready,
        "projection_valid": hierarchy_valid,
        "review_state_valid": state_valid,
        "review_packet_valid": packet_valid,
        "prior_continuity_valid": not bool(prior.get("recovered")),
        "recovered_projection": recovered,
        "residual_plan_detected": residual,
        "receipt_budget_exceeded": budget,
        "fault_count": min(faults, MAX_RELIABILITY_FAULTS),
        "verified_prior_receipt_count": int(prior.get("verified_receipt_count") or 0),
        "replayed_prior_receipt_count": int(prior.get("replayed_receipt_count") or 0),
        "malformed_prior_receipt_count": int(prior.get("malformed_receipt_count") or 0),
        "tampered_prior_receipt_count": int(prior.get("tampered_receipt_count") or 0),
        "plan_candidate_available": bool(hierarchy.get("plan_candidate_available")) if ready else False,
        "review_available": bool(packet.get("plan_candidate_available")) if ready else False,
        "literal_current_request_precedence": True,
        "historical_truth_preserved": True,
        "goal_activated": False, "plan_activated": False, "plan_persisted": False,
        "schedule_created": False, "tool_routed": False, "action_executed": False,
        "source_edited": False, "autonomous_work_started": False, "memory_mutated": False,
        "lesson_committed": False, "model_trained": False, "model_weights_changed": False,
        "installation_performed": False, "promotion_performed": False, "certification_performed": False,
        "authority": "none", "content_free": True,
        "hierarchy_digest": hierarchy_digest if ready else "",
        "review_state_digest": str(state.get("review_state_digest") or "") if ready else "",
        "review_packet_digest": str(packet.get("review_packet_digest") or "") if ready else "",
    }
    report["reliability_digest"] = _digest(report)
    prompt = (
        '<hierarchical_planning_reliability data_only="true" authority="none">'
        + json.dumps({k: report[k] for k in (
            "contract_version", "reliability_posture", "ordinary_conversation_ready",
            "plan_candidate_available", "review_available", "fault_count", "authority", "content_free",
        )}, sort_keys=True, separators=(",", ":"))
        + '</hierarchical_planning_reliability>'
    )
    return {"report": report, "prompt_section": prompt}


def verify_hierarchical_planning_reliability(value: object) -> bool:
    row = _mapping(value)
    if set(row) != _RELIABILITY_FIELDS or not _size_ok(row):
        return False
    supplied = row.pop("reliability_digest", None)
    ready = row.get("ordinary_conversation_ready")
    counts = all(isinstance(row.get(k), int) and 0 <= row[k] <= MAX_PRIOR_RECEIPTS for k in (
        "verified_prior_receipt_count", "replayed_prior_receipt_count",
        "malformed_prior_receipt_count", "tampered_prior_receipt_count",
    ))
    coherent = (
        ready is True and row.get("reliability_posture") == "hierarchical_planning_context_reliable"
        and row.get("fault_count") == 0 and row.get("projection_valid") is True
        and row.get("review_state_valid") is True and row.get("review_packet_valid") is True
    ) or (
        ready is False and row.get("reliability_posture") == "literal_current_request_only_recovery"
        and row.get("plan_candidate_available") is False and row.get("review_available") is False
        and row.get("hierarchy_digest") == "" and row.get("review_state_digest") == ""
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
