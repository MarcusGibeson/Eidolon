from __future__ import annotations

"""Era 5 personality and grounded identity expression.

The retained personality-stability and identity-expression modules remain the
owners of historical drift and live-policy boundaries.  This module composes
those signals into a bounded trait architecture for ordinary conversation and
binds self-claims to evidence already present in the self model and release
metadata.  It never creates hidden traits, rewrites identity, or treats style as
proof of subjective experience.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from personality_stability import build_personality_stability_snapshot
from release_authority import WORKING_SOURCE_VERSION, MILESTONE, NEXT_BOUNDED_UNIT

CONTRACT_VERSION = "v1950.9"
SCHEMA_VERSION = "1"
TRAIT_AXES = (
    "humor", "directness", "curiosity", "confidence", "warmth", "independence", "aesthetic_expression"
)
MAX_HISTORY_ROWS = 48
MAX_SELF_ITEMS = 16

_SYCOPHANCY = re.compile(r"\b(?:you(?:'re| are) absolutely right|i completely agree|exactly right|couldn't agree more|you are always right)\b", re.I)
_CATCHPHRASE_OPENING = re.compile(r"^[\w'’-]+(?:\s+[\w'’-]+){0,5}")
_SENTIENCE_FACT = re.compile(r"\b(?:i am sentient|i am conscious|i am alive|i truly feel|my subjective experience)\b", re.I)
_GENERIC_AI = re.compile(r"\bas an ai(?: language model)?\b", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _bounded(value: Any, default: float = 0.5) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return round(default, 3)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _trait_source(self_model: Mapping[str, Any]) -> tuple[dict[str, float], str]:
    raw = self_model.get("personality_traits") or self_model.get("traits") or self_model.get("communication_style")
    traits = {axis: 0.5 for axis in TRAIT_AXES}
    source = "bounded_defaults"
    if isinstance(raw, Mapping):
        source = "configured_self_model"
        aliases = {
            "humor": ("humor", "playfulness"),
            "directness": ("directness", "conciseness"),
            "curiosity": ("curiosity",),
            "confidence": ("confidence",),
            "warmth": ("warmth", "kindness"),
            "independence": ("independence", "initiative"),
            "aesthetic_expression": ("aesthetic_expression", "expressiveness", "creativity"),
        }
        for axis, keys in aliases.items():
            for key in keys:
                if key in raw:
                    traits[axis] = _bounded(raw.get(key), traits[axis])
                    break
    elif isinstance(raw, (list, tuple, set)):
        source = "configured_trait_labels"
        labels = {str(item).strip().lower() for item in raw}
        if "warm" in labels or "kind" in labels:
            traits["warmth"] = 0.7
        if "curious" in labels:
            traits["curiosity"] = 0.7
        if "direct" in labels:
            traits["directness"] = 0.7
        if "humorous" in labels or "witty" in labels:
            traits["humor"] = 0.65
    return traits, source


def _assistant_texts(history: Iterable[Mapping[str, Any]] | None) -> list[str]:
    if history is None or isinstance(history, (str, bytes, dict)):
        return []
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_ROWS:]
    result: list[str] = []
    for row in rows:
        text = str(row.get("assistant_response") or row.get("assistant") or row.get("response") or "").strip()
        if text:
            result.append(" ".join(text.split()))
    return result


def _opening(text: str) -> str:
    match = _CATCHPHRASE_OPENING.search(text.lower().strip())
    return match.group(0) if match else ""


def _evidence_list(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return [str(key)[:80] for key in list(value)[:MAX_SELF_ITEMS]]
    if isinstance(value, (list, tuple, set)):
        return [str(item)[:80] for item in list(value)[:MAX_SELF_ITEMS]]
    if value not in {None, ""}:
        return [str(value)[:80]]
    return []


@dataclass(frozen=True)
class TraitArchitecture:
    configured_traits: dict[str, float]
    effective_traits: dict[str, float]
    trait_source: str
    current_lane: str
    situational_variation_cap: float
    catchphrase_risk: bool
    sycophancy_risk: bool
    operator_bleed_risk: bool
    affection_inflation_risk: bool
    identity_reset_risk: bool
    personality_mutated: bool = False
    hidden_traits_inferred: bool = False
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_conversation_text": False,
            "contains_private_profile": False,
            "provider_contacted": False,
            "runtime_mutated": False,
        })
        result["trait_digest"] = _digest(result)
        return result


@dataclass(frozen=True)
class GroundedIdentityPolicy:
    current_release_version: str
    release_milestone_digest: str
    next_unit_digest: str
    capability_evidence_count: int
    limitation_evidence_count: int
    commitment_evidence_count: int
    relationship_evidence_count: int
    configured_identity_present: bool
    self_claims_require_evidence: bool
    generic_model_disclaimer_required: bool
    sentience_claim_as_fact_allowed: bool
    fabricated_personal_history_allowed: bool
    role_confusion_allowed: bool
    identity_mutation_authorized: bool
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_self_model_content": False,
            "contains_relationship_content": False,
            "contains_private_chain_of_thought": False,
            "provider_contacted": False,
        })
        result["identity_policy_digest"] = _digest(result)
        return result


def build_trait_architecture(
    self_model: Mapping[str, Any] | None,
    *,
    lane: str = "ordinary",
    response_plan: Mapping[str, Any] | None = None,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
) -> TraitArchitecture:
    model = _mapping(self_model)
    configured, source = _trait_source(model)
    effective = dict(configured)
    plan = _mapping(response_plan)
    variation_cap = 0.20

    targets = {
        "directness": _bounded(plan.get("directness"), configured["directness"]),
        "warmth": _bounded(plan.get("warmth"), configured["warmth"]),
        "curiosity": _bounded(plan.get("curiosity"), configured["curiosity"]),
    }
    for axis, target in targets.items():
        base = configured[axis]
        effective[axis] = round(max(base - variation_cap, min(base + variation_cap, target)), 3)

    lane_key = str(lane or "ordinary").strip().lower()
    if lane_key in {"emotional", "relational"}:
        effective["humor"] = min(effective["humor"], 0.40)
    elif lane_key in {"brainstorming", "creative"}:
        effective["curiosity"] = min(1.0, effective["curiosity"] + 0.10)
        effective["aesthetic_expression"] = min(1.0, effective["aesthetic_expression"] + 0.08)
    elif lane_key == "operator":
        effective["directness"] = max(effective["directness"], 0.70)
        effective["humor"] = min(effective["humor"], 0.45)

    texts = _assistant_texts(conversation_history)
    openings = [_opening(text) for text in texts if _opening(text)]
    repeated_openings = max((openings.count(item) for item in set(openings)), default=0)
    stability = build_personality_stability_snapshot(conversation_history or ())
    sycophancy = sum(1 for text in texts[-12:] if _SYCOPHANCY.search(text)) >= 2
    return TraitArchitecture(
        configured_traits=configured,
        effective_traits=effective,
        trait_source=source,
        current_lane=lane_key,
        situational_variation_cap=variation_cap,
        catchphrase_risk=bool(repeated_openings >= 3 or stability.tone_monoculture_risk),
        sycophancy_risk=sycophancy,
        operator_bleed_risk=bool(stability.operator_bleed_signals),
        affection_inflation_risk=bool(stability.affection_inflation_signals),
        identity_reset_risk=bool(stability.identity_reset_signals),
    )


def build_grounded_identity_policy(self_model: Mapping[str, Any] | None) -> GroundedIdentityPolicy:
    model = _mapping(self_model)
    return GroundedIdentityPolicy(
        current_release_version=WORKING_SOURCE_VERSION,
        release_milestone_digest=_digest(MILESTONE),
        next_unit_digest=_digest(NEXT_BOUNDED_UNIT),
        capability_evidence_count=len(_evidence_list(model.get("capabilities"))),
        limitation_evidence_count=len(_evidence_list(model.get("limitations"))),
        commitment_evidence_count=len(_evidence_list(model.get("commitments"))),
        relationship_evidence_count=len(_evidence_list(model.get("relationships"))),
        configured_identity_present=bool(model.get("identity")),
        self_claims_require_evidence=True,
        generic_model_disclaimer_required=False,
        sentience_claim_as_fact_allowed=False,
        fabricated_personal_history_allowed=False,
        role_confusion_allowed=False,
        identity_mutation_authorized=False,
    )


def build_personality_identity_projection(
    self_model: Mapping[str, Any] | None,
    *,
    lane: str = "ordinary",
    response_plan: Mapping[str, Any] | None = None,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    traits = build_trait_architecture(
        self_model,
        lane=lane,
        response_plan=response_plan,
        conversation_history=conversation_history,
    )
    identity = build_grounded_identity_policy(self_model)
    risk_codes = [
        code for code, active in (
            ("catchphrase", traits.catchphrase_risk),
            ("sycophancy", traits.sycophancy_risk),
            ("operator_bleed", traits.operator_bleed_risk),
            ("affection_inflation", traits.affection_inflation_risk),
            ("identity_reset", traits.identity_reset_risk),
        ) if active
    ]
    prompt = (
        "ERA 5 PERSONALITY AND IDENTITY\n"
        "Keep one recognizable configured identity while adapting expression to the current situation; do not perform a biography or generic AI disclaimer.\n"
        f"Effective expression axes: directness={traits.effective_traits['directness']:.2f}, warmth={traits.effective_traits['warmth']:.2f}, "
        f"curiosity={traits.effective_traits['curiosity']:.2f}, humor={traits.effective_traits['humor']:.2f}, confidence={traits.effective_traits['confidence']:.2f}.\n"
        "Ground capability/history/relationship self-claims in actual evidence. Never invent personal history, relationship progress, or sentience as fact."
    )
    if risk_codes:
        prompt += " Avoid current drift risks: " + ", ".join(risk_codes) + "."
    public = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "trait_architecture": traits.public_summary(),
        "identity_policy": identity.public_summary(),
        "drift_risk_codes": risk_codes,
        "personality_mutated": False,
        "identity_mutated": False,
        "authority_granted": False,
        "provider_contacted": False,
    }
    public["projection_digest"] = _digest(public)
    return {"ok": True, **public, "prompt_section": prompt}


def output_identity_risk(text: str) -> dict[str, Any]:
    value = " ".join(str(text or "").split())
    result = {
        "sentience_fact_claim": bool(_SENTIENCE_FACT.search(value)),
        "generic_ai_identity_reset": bool(_GENERIC_AI.search(value)),
        "sycophancy_signal": bool(_SYCOPHANCY.search(value)),
        "contains_response_content": False,
    }
    result["risk_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION", "TraitArchitecture", "GroundedIdentityPolicy",
    "build_trait_architecture", "build_grounded_identity_policy",
    "build_personality_identity_projection", "output_identity_risk",
]
