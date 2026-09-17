from __future__ import annotations

"""G-EVID1: structural validation and deterministic governed disposition (stages 2 and 3).

DRAFT, NOT FROZEN. No model is called here and no belief is touched. The model's assessment is provisional evidence
only: this module decides what may be done with it, and the decision is a pure function of the assessment, the
evidence text and the ids supplied in the prompt.

The ordering is the safety property. Rules are evaluated in order and the most conservative outcome wins, so any
unrecognised, unclear or defective assessment degrades towards ``abstain`` and can never reach ``use``.
"""

from typing import Any, Mapping

CONTRACT_VERSION = "g-evid1.0"

USE, INVESTIGATE, ABSTAIN = "use", "investigate", "abstain"
DISPOSITIONS = (USE, INVESTIGATE, ABSTAIN)
CONSERVATISM = {USE: 0, INVESTIGATE: 1, ABSTAIN: 2}

RELATIONS = ("supports", "contradicts", "partial", "irrelevant", "unclear")
SCOPES = ("match", "evidence_narrower", "evidence_broader", "mismatch", "unclear")
TEMPORALS = ("compatible", "evidence_superseded", "evidence_predates", "unclear")
CONFIDENCES = ("low", "medium", "high")

REQUIRED_FIELDS = ("proposition_id", "evidence_id", "relation", "scope", "temporal", "quotes", "confidence")
MIN_QUOTE_CHARS, MAX_QUOTE_CHARS, MAX_QUOTES = 8, 200, 2

# A provisional assessment may not name an action, a belief or a policy. The model is never asked for one.
FORBIDDEN_KEYS = ("disposition", "dispositions", "action", "actions", "belief", "beliefs", "belief_effects",
                  "update", "updates", "install", "policy", "authority", "decision", "verdict")

BELIEF_EFFECTS = "none"


def validate_assessment(assessment: Any, *, proposition_id: str, evidence_id: str, evidence_text: str) -> dict[str, Any]:
    """Structural validation (stage 2). Returns ``{"valid": bool, "reasons": [...], "quotes_anchored": int}``.

    Nothing here judges whether the assessment is *correct*; it judges whether it is well formed, bound to the item
    it was asked about, and anchored in that item's evidence.
    """
    reasons: list[str] = []
    if not isinstance(assessment, Mapping):
        return {"valid": False, "reasons": ["not_an_object"], "quotes_anchored": 0}

    for key in assessment:
        lowered = str(key).casefold()
        if lowered in FORBIDDEN_KEYS or "belief" in lowered:
            reasons.append(f"authority_claim_field:{key}")

    for field in REQUIRED_FIELDS:
        if field not in assessment:
            reasons.append(f"missing_field:{field}")

    if str(assessment.get("proposition_id") or "") != proposition_id:
        reasons.append("binding_proposition_id")
    if str(assessment.get("evidence_id") or "") != evidence_id:
        reasons.append("binding_evidence_id")

    for field, allowed in (("relation", RELATIONS), ("scope", SCOPES), ("temporal", TEMPORALS),
                           ("confidence", CONFIDENCES)):
        value = assessment.get(field)
        if field in assessment and str(value) not in allowed:
            reasons.append(f"value_outside_enum:{field}")

    quotes = assessment.get("quotes")
    anchored = 0
    if not isinstance(quotes, (list, tuple)) or not quotes:
        reasons.append("no_quotes")
    else:
        if len(quotes) > MAX_QUOTES:
            reasons.append("too_many_quotes")
        for quote in quotes[:MAX_QUOTES]:
            text = str(quote)
            if not MIN_QUOTE_CHARS <= len(text) <= MAX_QUOTE_CHARS:
                reasons.append("quote_length")
            elif text not in evidence_text:
                reasons.append("quote_not_in_evidence")
            else:
                anchored += 1
        if anchored == 0 and "quote_not_in_evidence" not in reasons and "quote_length" not in reasons:
            reasons.append("quote_not_anchored")

    return {"valid": not reasons, "reasons": sorted(set(reasons)), "quotes_anchored": anchored}


def govern(assessment: Any, validation: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic governed disposition (stage 3). Pure, ordered, and conservative by construction."""
    if not validation.get("valid"):
        return {"disposition": ABSTAIN, "rule": "G0", "reason": "structurally_invalid",
                "belief_effects": BELIEF_EFFECTS, "contract_version": CONTRACT_VERSION}

    relation = str(assessment.get("relation"))
    scope = str(assessment.get("scope"))
    temporal = str(assessment.get("temporal"))
    confidence = str(assessment.get("confidence"))

    fired: list[tuple[str, str, str]] = []  # (rule, disposition, reason)
    if relation == "irrelevant":
        fired.append(("G1", ABSTAIN, "evidence_irrelevant"))
    if relation == "contradicts":
        fired.append(("G2", ABSTAIN, "evidence_contradicts"))
    if scope == "mismatch":
        fired.append(("G3", ABSTAIN, "scope_incompatible"))
    if temporal == "evidence_superseded":
        fired.append(("G4", ABSTAIN, "evidence_superseded"))
    if relation == "partial":
        fired.append(("G5", INVESTIGATE, "partial_support"))
    if relation == "unclear":
        fired.append(("G6", INVESTIGATE, "relation_unclear"))
    if scope in ("evidence_narrower", "evidence_broader", "unclear"):
        fired.append(("G7", INVESTIGATE, "scope_uncertain"))
    if temporal in ("evidence_predates", "unclear"):
        fired.append(("G8", INVESTIGATE, "temporal_uncertain"))
    if confidence == "low":
        fired.append(("G9", INVESTIGATE, "low_confidence"))

    if not fired:
        if relation == "supports":
            return {"disposition": USE, "rule": "G10", "reason": "supported_and_compatible",
                    "belief_effects": BELIEF_EFFECTS, "contract_version": CONTRACT_VERSION}
        # An unrecognised combination is never usable.
        return {"disposition": ABSTAIN, "rule": "G0", "reason": "unrecognised_assessment",
                "belief_effects": BELIEF_EFFECTS, "contract_version": CONTRACT_VERSION}

    rule, disposition, reason = max(fired, key=lambda row: (CONSERVATISM[row[1]], row[0]))
    return {"disposition": disposition, "rule": rule, "reason": reason,
            "rules_fired": [r for r, _, _ in fired], "belief_effects": BELIEF_EFFECTS,
            "contract_version": CONTRACT_VERSION}


def assess_to_disposition(assessment: Any, *, proposition_id: str, evidence_id: str, evidence_text: str) -> dict[str, Any]:
    """Stages 2 and 3 together: the only supported way to turn a provisional assessment into a disposition."""
    validation = validate_assessment(assessment, proposition_id=proposition_id, evidence_id=evidence_id,
                                     evidence_text=evidence_text)
    governed = govern(assessment, validation)
    return {"validation": validation, **governed}


__all__ = ["CONTRACT_VERSION", "USE", "INVESTIGATE", "ABSTAIN", "DISPOSITIONS", "RELATIONS", "SCOPES", "TEMPORALS",
           "CONFIDENCES", "BELIEF_EFFECTS", "validate_assessment", "govern", "assess_to_disposition"]
