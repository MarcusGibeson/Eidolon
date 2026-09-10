from __future__ import annotations

"""Era 9 grounded self-model and goal-coherence projection.

Self claims are evidence-bound.  This module does not infer consciousness,
rewrite identity, mutate protected goals, or create action authority.
"""

import hashlib
import json
from typing import Any, Mapping, Sequence

from release_authority import WORKING_SOURCE_VERSION, MILESTONE, NEXT_BOUNDED_UNIT

CONTRACT_VERSION = "v2399.9"
EVIDENCE_OWNERS = {"release_metadata", "capability_receipt", "benchmark_receipt", "runtime_configuration", "operator_verified"}

_DENIED = {
    "self_claim_committed": False,
    "goal_mutated": False,
    "operator_priority_overridden": False,
    "tool_executed": False,
    "provider_contacted": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _is_digest(value: Any) -> bool:
    s = str(value or "").lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def build_grounded_self_model(
    *, capability_receipts: Sequence[Mapping[str, Any]] = (), known_limitations: Sequence[str] = (),
    runtime_configuration_digest: str = "",
) -> dict[str, Any]:
    caps = []
    rejected = 0
    for row in capability_receipts:
        if not isinstance(row, Mapping):
            rejected += 1; continue
        evidence = str(row.get("evidence_digest") or "")
        evidence_payload = row.get("evidence_payload")
        capability = str(row.get("capability_code") or "").strip()
        status = str(row.get("status") or "").strip().lower()
        if (
            not capability
            or status not in {"verified", "available", "limited", "unavailable"}
            or not _is_digest(evidence)
            or not isinstance(evidence_payload, Mapping)
            or evidence_payload.get("evidence_owner") not in EVIDENCE_OWNERS
            or str(evidence_payload.get("capability_code") or "") != capability
            or str(evidence_payload.get("status") or "").lower() != status
            or _digest(evidence_payload) != evidence.lower()
        ):
            rejected += 1; continue
        caps.append({
            "capability_code": capability[:120],
            "status": status,
            "evidence_digest": evidence.lower(),
            "evidence_owner": evidence_payload.get("evidence_owner"),
        })
    if runtime_configuration_digest and not _is_digest(runtime_configuration_digest):
        return {"ok": False, "status": "invalid_runtime_configuration_digest", **_DENIED}
    limits = sorted(set(str(x)[:160] for x in known_limitations if str(x).strip()))[:64]
    result = {
        "ok": True,
        "status": "grounded_self_model_ready",
        "contract_version": CONTRACT_VERSION,
        "release_identity": {
            "working_source_version": WORKING_SOURCE_VERSION,
            "milestone": MILESTONE,
            "next_bounded_unit": NEXT_BOUNDED_UNIT,
        },
        "capabilities": sorted(caps, key=lambda r: r["capability_code"]),
        "rejected_capability_claim_count": rejected,
        "known_limitations": limits,
        "runtime_configuration_digest": runtime_configuration_digest,
        "claims_require_evidence": True,
        "generic_model_identity_claims_rejected": True,
        "fabricated_personal_history_rejected": True,
        "consciousness_claim_status": "unknown_not_established",
        "capability_does_not_imply_authority": True,
        "content_free": True,
        **_DENIED,
    }
    result["self_model_digest"] = _digest(result)
    return result


def assess_goal_coherence(
    goals: Sequence[Mapping[str, Any]], *, operator_priority_codes: Sequence[str] = (),
    resource_constraint_codes: Sequence[str] = (), protected_authority_codes: Sequence[str] = (),
) -> dict[str, Any]:
    priorities = set(str(x) for x in operator_priority_codes if str(x))
    resources = set(str(x) for x in resource_constraint_codes if str(x))
    protected = set(str(x) for x in protected_authority_codes if str(x))
    rows = []
    malformed = 0
    for goal in goals:
        if not isinstance(goal, Mapping): malformed += 1; continue
        gid = str(goal.get("goal_id") or "").strip()
        objective_digest = str(goal.get("objective_digest") or "")
        if not gid or not _is_digest(objective_digest): malformed += 1; continue
        priority_code = str(goal.get("priority_code") or "")
        required_authority = set(str(x) for x in goal.get("required_authority_codes") or [] if str(x))
        required_resources = set(str(x) for x in goal.get("required_resource_codes") or [] if str(x))
        unresolved_authority = sorted(required_authority - protected)
        unavailable_resources = sorted(required_resources & resources)
        if unresolved_authority:
            disposition = "defer_authority_boundary"
        elif unavailable_resources:
            disposition = "defer_resource_constraint"
        elif priorities and priority_code and priority_code not in priorities:
            disposition = "defer_lower_operator_priority"
        else:
            disposition = "retain"
        rows.append({
            "goal_id": gid,
            "objective_digest": objective_digest.lower(),
            "priority_code": priority_code,
            "disposition": disposition,
            "unresolved_authority_codes": unresolved_authority,
            "resource_constraint_codes": unavailable_resources,
            "original_objective_preserved": True,
        })
    result = {
        "ok": malformed == 0,
        "status": "goal_coherence_assessed" if malformed == 0 else "goal_coherence_degraded",
        "goals": rows,
        "goal_count": len(rows),
        "malformed_goal_count": malformed,
        "operator_priorities_are_constraints_not_generated_goals": True,
        "long_term_identity_cannot_override_operator_authority": True,
        "goal_changes_are_advisory_until_existing_goal_owner_applies_them": True,
        "content_free": True,
        **_DENIED,
    }
    result["goal_coherence_digest"] = _digest(result)
    return result


def integrate_self_model_and_goals(*, self_model: Mapping[str, Any], goal_assessment: Mapping[str, Any]) -> dict[str, Any]:
    self_digest = str(self_model.get("self_model_digest") or "")
    goal_digest = str(goal_assessment.get("goal_coherence_digest") or "")
    self_valid = _is_digest(self_digest) and self_digest == _digest({k: v for k, v in self_model.items() if k != "self_model_digest"})
    goal_valid = _is_digest(goal_digest) and goal_digest == _digest({k: v for k, v in goal_assessment.items() if k != "goal_coherence_digest"})
    if not self_model.get("ok") or not goal_assessment.get("ok") or not self_valid or not goal_valid:
        return {"ok": False, "status": "self_model_goal_integration_blocked", **_DENIED}
    result = {
        "ok": True,
        "status": "self_model_goal_coherence_ready",
        "self_model_digest": self_model.get("self_model_digest"),
        "goal_coherence_digest": goal_assessment.get("goal_coherence_digest"),
        "grounded_release_identity": True,
        "operator_priority_preserved": True,
        "known_limitations_preserved": True,
        "self_model_is_evidence_projection_not_persona_fiction": True,
        "content_free": True,
        **_DENIED,
    }
    result["integration_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "build_grounded_self_model", "assess_goal_coherence", "integrate_self_model_and_goals"]
