from __future__ import annotations

"""Strict R2 structural validation and deterministic governance/comparison."""

import json
from typing import Any, Mapping

import g_evid1_policy as frozen_individual


CONTRACT_VERSION = "g-corrob1.r2.policy-candidate.1"
REQUIRED_FIELDS = frozenset(frozen_individual.REQUIRED_FIELDS)
USE, INVESTIGATE, ABSTAIN = frozen_individual.USE, frozen_individual.INVESTIGATE, frozen_individual.ABSTAIN


def parse_assessment(raw_response: str) -> tuple[dict[str, Any] | None, str | None]:
    text = str(raw_response or "").strip()
    if not text:
        return None, "empty_response"
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None, "malformed_json"
    if not isinstance(value, dict):
        return None, "not_an_object"
    return value, None


def validate_assessment(assessment: Any, *, proposition_id: str, evidence_id: str, evidence_text: str,
                        truncated: bool = False, parse_error: str | None = None,
                        binding_error: str | None = None) -> dict[str, Any]:
    reasons: list[str] = []
    if parse_error:
        reasons.append(parse_error)
    if binding_error:
        reasons.append(binding_error)
    if truncated:
        reasons.append("truncated_output")
    if not isinstance(assessment, Mapping):
        return {"valid": False, "reasons": sorted(set(reasons + ["not_an_object"])), "quotes_anchored": 0}
    extra = sorted(set(str(key) for key in assessment) - REQUIRED_FIELDS)
    reasons += [f"extra_field:{key}" for key in extra]
    base = frozen_individual.validate_assessment(
        assessment, proposition_id=proposition_id, evidence_id=evidence_id,
        evidence_text=evidence_text, truncated=False,
    )
    reasons += list(base.get("reasons") or [])
    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "quotes_anchored": int(base.get("quotes_anchored") or 0),
    }


def individual_governance(assessment: Any, validation: Mapping[str, Any]) -> dict[str, Any]:
    governed = dict(frozen_individual.govern(assessment, validation))
    governed["individual_policy_contract"] = frozen_individual.CONTRACT_VERSION
    governed["belief_effects"] = "none"
    return governed


def process_assessment(raw_response: str, *, proposition_id: str, evidence_id: str, evidence_text: str,
                       truncated: bool = False, binding_error: str | None = None) -> dict[str, Any]:
    assessment, parse_error = parse_assessment(raw_response)
    validation = validate_assessment(
        assessment, proposition_id=proposition_id, evidence_id=evidence_id, evidence_text=evidence_text,
        truncated=truncated, parse_error=parse_error, binding_error=binding_error,
    )
    governance = individual_governance(assessment, validation)
    return {"assessment": assessment, "parse_error": parse_error, "validation": validation, **governance}


def compare_pair(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    dispositions = {"A": str(a.get("disposition")), "B": str(b.get("disposition"))}
    if any(value not in frozen_individual.DISPOSITIONS for value in dispositions.values()):
        raise ValueError("invalid_individual_disposition")
    structural_rejection = not bool((a.get("validation") or {}).get("valid")) or not bool(
        (b.get("validation") or {}).get("valid")
    )
    if ABSTAIN in dispositions.values():
        disposition, rule = ABSTAIN, "P0_STRUCTURAL" if structural_rejection else "P1_ANY_ABSTAIN"
    elif dispositions["A"] == USE and dispositions["B"] == USE:
        disposition, rule = USE, "P2_BOTH_USE"
    else:
        disposition, rule = INVESTIGATE, "P3_REMAINDER_INVESTIGATE"
    return {
        "disposition": disposition,
        "rule": rule,
        "scientific_status": "structural_rejection" if structural_rejection else "compared",
        "individual_dispositions": dispositions,
        "belief_effects": "none",
        "contract_version": CONTRACT_VERSION,
    }


def enumerate_policy_state_space() -> dict[str, Any]:
    counts = {USE: 0, INVESTIGATE: 0, ABSTAIN: 0}
    examples = []
    validation = {"valid": True, "reasons": [], "quotes_anchored": 1}
    for relation in frozen_individual.RELATIONS:
        for scope in frozen_individual.SCOPES:
            for temporal in frozen_individual.TEMPORALS:
                for confidence in frozen_individual.CONFIDENCES:
                    assessment = {"relation": relation, "scope": scope, "temporal": temporal,
                                  "confidence": confidence}
                    disposition = individual_governance(assessment, validation)["disposition"]
                    counts[disposition] += 1
                    examples.append(disposition)
    paired = {USE: 0, INVESTIGATE: 0, ABSTAIN: 0}
    valid = {"validation": validation}
    for left in examples:
        for right in examples:
            paired[compare_pair({**valid, "disposition": left}, {**valid, "disposition": right})["disposition"]] += 1
    return {"individual_states": len(examples), "individual": counts,
            "paired_states": len(examples) ** 2, "paired": paired}


__all__ = [
    "CONTRACT_VERSION", "REQUIRED_FIELDS", "USE", "INVESTIGATE", "ABSTAIN", "parse_assessment",
    "validate_assessment", "individual_governance", "process_assessment", "compare_pair",
    "enumerate_policy_state_space",
]
