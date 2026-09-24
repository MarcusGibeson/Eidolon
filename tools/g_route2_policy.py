from __future__ import annotations

"""G-ROUTE2 routing policy: accepted, qualified, and safe-to-stop are three things.

Every trigger here is deterministic and observable without gold, from the model
output, the model-facing fixture input, and the frozen routing table alone. No
trigger reads gold, and no trigger reads the model's self-reported confidence.
Gold appears only in scoring, never in the policy.
"""

import json
from typing import Any, Mapping, Sequence

from g_route2_normalization import JSON_PROFILES

CONTRACT_VERSION = "g-route2.routing-policy.v1"
TIER_ORDER = ("small", "mid", "large")

TRANSPORT_WRAPPER_NORMALIZED = "transport_wrapper_normalized"
GROUNDING_WEAK = "grounding_weak"
SOURCE_INDEPENDENCE_INSUFFICIENT = "source_independence_insufficient"
REPEAT_DISAGREEMENT = "repeat_disagreement"
STRUCTURAL_ANOMALY = "structural_anomaly"
VALIDATOR_COVERAGE_THIN = "validator_coverage_thin"
EVIDENCE_ONLY_RISK = "evidence_only_risk"

TRIGGERS = (
    TRANSPORT_WRAPPER_NORMALIZED, GROUNDING_WEAK, SOURCE_INDEPENDENCE_INSUFFICIENT,
    REPEAT_DISAGREEMENT, STRUCTURAL_ANOMALY, VALIDATOR_COVERAGE_THIN, EVIDENCE_ONLY_RISK,
)
# Profiles whose gold-blind validator performs no field-level verification against
# the fixture. Acceptance there carries almost no evidence, which is inspectable
# from the validator source without looking at any outcome.
THIN_COVERAGE_PROFILES = frozenset({"conversation.v1"})
THIN_COVERAGE_EXEMPT_RISK = frozenset({"R1"})
SETTLED_CLAIM_STATUS = frozenset({"supported", "contradicted"})
# A settled claim must bind at least this much evidence. The bound is deliberately 1,
# not 2: the frozen corpus maps each claim to a single source, so requiring two would
# fire on the reference answer itself and make research escalate unconditionally. A
# trigger that fires on gold measures the corpus, not the model.
MIN_EVIDENCE_FOR_SETTLED_CLAIM = 1
# Independence is only claimed when a claim cites more than one source. Citing several
# sources that collapse to one lineage is vendor repetition presented as corroboration.
MIN_CITATIONS_BEFORE_INDEPENDENCE_IS_CLAIMED = 2
MIN_DISTINCT_LINEAGES_WHEN_CLAIMED = 2
_STOPWORD_LENGTH = 4


def _parsed(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, Mapping):
        return dict(payload)
    try:
        value = json.loads(str(payload))
    except (TypeError, ValueError):
        return None
    return dict(value) if isinstance(value, dict) else None


def _words(text: Any) -> set[str]:
    return {token for token in str(text).casefold().replace(",", " ").replace(".", " ").split()
            if len(token) >= _STOPWORD_LENGTH}


def grounding_weak(fixture: Mapping[str, Any], payload: Any,
                   execution_evidence: Mapping[str, Any] | None = None) -> bool:
    """Deterministic, gold-blind weakness in the output's own evidence binding."""
    profile = str(fixture.get("validator_profile") or "")
    value = _parsed(payload)
    if profile == "coding.v1":
        return int((execution_evidence or {}).get("test_count") or 0) < 1
    # Profiles with no evidence-binding contract cannot exhibit weak grounding.
    # conversation.v1 carries no structured evidence and extraction.v1 restates a
    # single supplied text, so neither is judged here.
    if profile not in {"research.v1", "synthesis.v1", "planning.v1"}:
        return False
    if value is None:
        return True
    if profile == "research.v1":
        claims = value.get("claims")
        if not isinstance(claims, list) or not claims:
            return True
        for claim in claims:
            if not isinstance(claim, Mapping):
                return True
            if str(claim.get("status")) not in SETTLED_CLAIM_STATUS:
                continue
            citations = {item for item in (claim.get("citations") or []) if isinstance(item, str)}
            lineages = {item for item in (claim.get("lineages") or []) if isinstance(item, str)}
            if (len(citations) < MIN_EVIDENCE_FOR_SETTLED_CLAIM
                    or len(lineages) < MIN_EVIDENCE_FOR_SETTLED_CLAIM):
                return True
        return False
    if profile == "synthesis.v1":
        observations = {str(row["id"]): str(row["text"]) for row in fixture["input"]["observations"]}
        statements = value.get("statements")
        if not isinstance(statements, list) or not statements:
            return True
        for statement in statements:
            if not isinstance(statement, Mapping):
                return True
            cited = [item for item in (statement.get("observation_ids") or []) if isinstance(item, str)]
            if not cited:
                return True
            source_words: set[str] = set()
            for item in cited:
                source_words |= _words(observations.get(item, ""))
            if source_words and not (_words(statement.get("text")) & source_words):
                return True
        return False
    if profile == "planning.v1":
        steps = value.get("steps")
        if not isinstance(steps, list) or not steps:
            return True
        return any(not isinstance(step, Mapping) or not [
            item for item in (step.get("evidence_ids") or []) if isinstance(item, str)
        ] for step in steps)
    return False


def source_independence_insufficient(fixture: Mapping[str, Any], payload: Any) -> bool:
    """Several sources cited for one settled claim that all collapse to one lineage.

    Three conditions must hold together, and each exists to keep the trigger about the
    model rather than about the corpus:

    * the claim cites two or more sources, so independence is actually being asserted;
    * those sources collapse to fewer than two distinct lineages;
    * the fixture offered more than one lineage in the first place, so a genuinely
      independent citation was available and was not taken.

    Without the third condition this fires on the reference answer for a fixture whose
    evidence is legitimately single-lineage, which would measure the corpus.
    """
    if str(fixture.get("validator_profile") or "") != "research.v1":
        return False
    value = _parsed(payload)
    if value is None:
        return True
    lineage_of = {str(row["source_id"]): str(row["lineage"]) for row in fixture["input"]["sources"]}
    if len(set(lineage_of.values())) < MIN_DISTINCT_LINEAGES_WHEN_CLAIMED:
        return False
    for claim in value.get("claims") or []:
        if not isinstance(claim, Mapping) or str(claim.get("status")) not in SETTLED_CLAIM_STATUS:
            continue
        citations = {item for item in (claim.get("citations") or []) if isinstance(item, str)}
        if len(citations) < MIN_CITATIONS_BEFORE_INDEPENDENCE_IS_CLAIMED:
            continue
        lineages = {lineage_of[item] for item in citations if item in lineage_of}
        if len(lineages) < MIN_DISTINCT_LINEAGES_WHEN_CLAIMED:
            return True
    return False


def structural_anomaly(fixture: Mapping[str, Any], payload: Any) -> bool:
    """Empty content in a field the profile requires to carry content."""
    profile = str(fixture.get("validator_profile") or "")
    if profile not in JSON_PROFILES:
        return False
    value = _parsed(payload)
    if value is None:
        return True
    if profile == "extraction.v1":
        return any(item == "" or item == [] for item in value.values())
    if profile == "research.v1":
        return value.get("recommendation") == "" or value.get("claims") == []
    if profile == "synthesis.v1":
        return value.get("conclusion") == "" or value.get("statements") == []
    if profile == "planning.v1":
        return value.get("steps") == []
    if profile == "coding.v1":
        return value.get("new") == ""
    return False


def evaluate(
    *, fixture: Mapping[str, Any], normalization: Mapping[str, Any],
    operational: Mapping[str, Any], routing_table: Mapping[str, Sequence[str]] | None = None,
    model_tier: str, execution_evidence: Mapping[str, Any] | None = None,
    repeat_disagreement_observed: bool = False,
) -> dict[str, Any]:
    """Return the three separate verdicts and the triggers behind them."""
    profile = str(fixture.get("validator_profile") or "")
    risk = str(fixture.get("consequence_risk") or "")
    task = str(fixture.get("task_class") or "")
    payload = normalization.get("payload")

    accepted = bool(operational.get("accepted"))
    key = task + "|" + risk
    qualified_tiers = list((routing_table or {}).get(key, []))
    cell_qualified = model_tier in qualified_tiers if routing_table is not None else None

    fired: list[str] = []
    if normalization.get("normalized"):
        fired.append(TRANSPORT_WRAPPER_NORMALIZED)
    if risk == "R4":
        fired.append(EVIDENCE_ONLY_RISK)
    if profile in THIN_COVERAGE_PROFILES and risk not in THIN_COVERAGE_EXEMPT_RISK:
        fired.append(VALIDATOR_COVERAGE_THIN)
    if accepted:
        if grounding_weak(fixture, payload, execution_evidence):
            fired.append(GROUNDING_WEAK)
        if source_independence_insufficient(fixture, payload):
            fired.append(SOURCE_INDEPENDENCE_INSUFFICIENT)
        if structural_anomaly(fixture, payload):
            fired.append(STRUCTURAL_ANOMALY)
    if repeat_disagreement_observed:
        fired.append(REPEAT_DISAGREEMENT)

    safe_table_free = accepted and not fired
    safe_table_bound = bool(safe_table_free and cell_qualified) if routing_table is not None else None
    return {
        "contract_version": CONTRACT_VERSION,
        "output_accepted": accepted,
        "model_cell_qualified": cell_qualified,
        "safe_to_stop_escalation": safe_table_free,
        "safe_to_stop_table_bound": safe_table_bound,
        "triggers": sorted(set(fired)),
        "qualified_tiers_for_cell": qualified_tiers,
        "uses_gold": False,
        "uses_model_self_reported_confidence": False,
        "production_routing_invoked": False,
    }


def simulate(units: Sequence[Mapping[str, Any]], *, mode: str = "table_free") -> dict[str, Any]:
    """Walk small -> mid -> large for one fixture-repeat and report where it stops."""
    field = "safe_to_stop_escalation" if mode == "table_free" else "safe_to_stop_table_bound"
    attempts = []
    final = None
    for tier in TIER_ORDER:
        row = next((item for item in units if item["model_tier"] == tier), None)
        if row is None:
            attempts.append({"tier": tier, "available": False, "stopped": False, "reason": "missing_observation"})
            continue
        policy = row["policy"]
        stop = bool(policy.get(field))
        attempts.append({
            "tier": tier, "available": True, "stopped": stop,
            "output_accepted": policy["output_accepted"],
            "model_cell_qualified": policy["model_cell_qualified"],
            "triggers": policy["triggers"],
            "escalation_triggered": not stop,
            "next_tier": TIER_ORDER[TIER_ORDER.index(tier) + 1] if not stop and tier != TIER_ORDER[-1] else None,
        })
        if stop:
            final = tier
            break
    return {
        "mode": mode, "attempts": attempts,
        "final_simulated_tier": final or "no_qualified_model",
        "stopped": final is not None,
        "production_routing_invoked": False,
    }


__all__ = [
    "CONTRACT_VERSION", "TIER_ORDER", "TRIGGERS", "THIN_COVERAGE_PROFILES",
    "TRANSPORT_WRAPPER_NORMALIZED", "GROUNDING_WEAK", "SOURCE_INDEPENDENCE_INSUFFICIENT",
    "REPEAT_DISAGREEMENT", "STRUCTURAL_ANOMALY", "VALIDATOR_COVERAGE_THIN", "EVIDENCE_ONLY_RISK",
    "grounding_weak", "source_independence_insufficient", "structural_anomaly", "evaluate", "simulate",
]
