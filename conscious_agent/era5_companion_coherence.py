from __future__ import annotations

"""Integrated Era 5 daily-companion coherence projection.

This is the portable integration boundary for v1901-v1999.9.  It composes
retained conversation/memory evidence with new discourse planning, grounded
personality expression, bounded affective regulation, and explicit relationship
continuity.  It never grants action or release authority and never initiates a
new turn by itself.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from affective_regulation_v1900 import (
    affective_prompt_section,
    public_affective_state,
    read_affective_state,
    update_affective_regulation,
)
from discourse_response_planning import build_discourse_response_projection
from personality_identity_expression_v1900 import build_personality_identity_projection, output_identity_risk
from relationship_companion_continuity_v1900 import build_relationship_companion_projection

CONTRACT_VERSION = "v1999.9"
SCHEMA_VERSION = "1"
MAX_PROMPT_CHARS = 2600

_DENIED_AUTHORITY = {
    "action_execution_authorized": False,
    "memory_mutation_authorized": False,
    "personality_mutation_authorized": False,
    "identity_mutation_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "provider_contact_authorized": False,
    "autonomous_new_turn_authorized": False,
    "independent_authority_granted": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _lane(response_intent: Mapping[str, Any] | None, contextual_behavior: Mapping[str, Any] | None) -> str:
    intent = str((response_intent or {}).get("selected_intent") or "direct_answer").strip().lower()
    mood = str((contextual_behavior or {}).get("mood_signal") or "absent").strip().lower()
    relationship = str((contextual_behavior or {}).get("relationship_signal") or "absent").strip().lower()
    if intent in {"correction", "governed_approval_request"}:
        return "operator" if intent == "governed_approval_request" else "correction"
    if mood in {"distressed", "positive", "present_unverified"}:
        return "emotional"
    if relationship == "relevant":
        return "relational"
    if intent in {"explanation", "follow_up"}:
        return "ordinary"
    return "ordinary"


def _event_id(session_id: str, message: Any, conversation_history: Iterable[Mapping[str, Any]] | None) -> str:
    try:
        history_count = sum(1 for row in (conversation_history or ()) if isinstance(row, Mapping))
    except Exception:
        history_count = 0
    message_digest = hashlib.sha256(str(message or "").encode("utf-8", errors="replace")).hexdigest()
    return f"era5-turn:{session_id or 'session'}:{history_count}:{message_digest}"


def build_era5_companion_projection(
    message: Any,
    *,
    response_intent: Mapping[str, Any] | None = None,
    contextual_behavior: Mapping[str, Any] | None = None,
    conversation_discourse: Mapping[str, Any] | None = None,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
    memories: Iterable[Mapping[str, Any]] | None = None,
    self_model: Mapping[str, Any] | None = None,
    session_id: str = "",
    runtime_root: str | Path | None = None,
    mutate_affect: bool = True,
) -> dict[str, Any]:
    discourse = build_discourse_response_projection(
        message,
        response_intent=response_intent,
        contextual_behavior=contextual_behavior,
        conversation_discourse=conversation_discourse,
        conversation_history=conversation_history,
    )
    lane = _lane(response_intent, contextual_behavior)
    personality = build_personality_identity_projection(
        self_model,
        lane=lane,
        response_plan=discourse["response_plan"],
        conversation_history=conversation_history,
    )
    if mutate_affect:
        affect_result = update_affective_regulation(
            message,
            event_id=_event_id(session_id, message, conversation_history),
            contextual_behavior=contextual_behavior,
            runtime_root=runtime_root,
        )
        affect_state = affect_result["state"]
    else:
        raw_state = read_affective_state(runtime_root=runtime_root)
        affect_state = public_affective_state(raw_state)
        affect_result = {"ok": True, "status": "affective_state_read_only", "state": affect_state, "idempotent": True}
    relationship = build_relationship_companion_projection(
        memories,
        conversation_history=conversation_history,
        prior_candidate_receipts=conversation_history,
    )

    response_plan = discourse["response_plan"]
    traits = personality["trait_architecture"]
    regulation = affect_state["regulation"]
    relationship_model = relationship["relationship_model"]
    risks = personality.get("drift_risk_codes") or []
    steps = ", ".join(response_plan.get("response_steps") or [])
    prompt = (
        "ERA 5 DAILY COMPANION COHERENCE\n"
        f"Response order: {steps or 'answer_first'}; ask at most {response_plan.get('maximum_questions', 0)} question(s). "
        f"Style: directness={response_plan.get('directness', .7):.2f}, warmth={response_plan.get('warmth', .5):.2f}, "
        f"curiosity={response_plan.get('curiosity', .4):.2f}, brevity={response_plan.get('brevity', .5):.2f}.\n"
        f"Configured identity stays stable; expression lane={traits.get('current_lane', 'ordinary')}; "
        f"affective expression={regulation.get('expression_mode', 'steady_natural')}. "
        f"Relationship context={relationship_model.get('familiarity_band', 'no_explicit_context')} with "
        f"{relationship_model.get('boundary_count', 0)} explicit boundary cue(s) and {relationship_model.get('preference_count', 0)} preference cue(s).\n"
        "Use current-message precedence, specific context instead of canned empathy, and grounded shared history instead of invented intimacy. "
        "Affective state modulates tone only; it is not proof of subjective feeling and grants no authority. "
        "Do not infer trust, dependency, exclusivity, relationship progress, or personal history. Do not initiate a new turn."
    )
    if risks:
        prompt += " Current expression drift to avoid: " + ", ".join(str(item) for item in risks[:5]) + "."
    prompt = prompt[:MAX_PROMPT_CHARS]

    public = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "lane": lane,
        "discourse": {key: value for key, value in discourse.items() if key != "prompt_section"},
        "personality_identity": {key: value for key, value in personality.items() if key != "prompt_section"},
        "affective_regulation": affect_state,
        "affective_update_status": str(affect_result.get("status") or "unknown"),
        "relationship_companion": {key: value for key, value in relationship.items() if key != "prompt_section"},
        "contains_message_content": False,
        "contains_memory_content": False,
        "contains_relationship_content": False,
        "contains_provider_payload": False,
        "contains_private_chain_of_thought": False,
        "prompt_characters": len(prompt),
        **_DENIED_AUTHORITY,
    }
    public["projection_digest"] = _digest(public)
    return {"ok": True, **public, "prompt_section": prompt}


def process_era5_companion_control(text: str, *, runtime_root: str | Path | None = None) -> dict[str, Any]:
    raw = " ".join(str(text or "").split())
    low = raw.lower()
    if not low.startswith(("inspect companion coherence", "show companion coherence", "inspect affective regulation", "show affective regulation")):
        return {"active": False}
    scope_expansion = any(token in low for token in (" install", " promote", " certify", " execute", " run command", " change personality", " expand authority"))
    if scope_expansion:
        return {"active": True, "ok": False, "status": "read_only_scope_expansion_rejected", **_DENIED_AUTHORITY}
    affect = public_affective_state(read_affective_state(runtime_root=runtime_root))
    return {
        "active": True,
        "ok": True,
        "status": "affective_regulation_inspected" if "affective" in low else "companion_coherence_inspected",
        "affective_regulation": affect,
        "conversation_content_exposed": False,
        "relationship_content_exposed": False,
        "memory_content_exposed": False,
        "runtime_mutated": False,
        **_DENIED_AUTHORITY,
    }


def audit_era5_companion_output(text: str, *, projection: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a content-free post-generation companion-quality receipt.

    This is deliberately diagnostic only.  It never rewrites model output,
    retries a provider, mutates personality/relationship state, or grants
    authority.  The v2000 operator/Desktop gate can use the receipt to score
    whether the prompt-layer policy is actually producing the intended daily
    companion behavior.
    """
    identity = output_identity_risk(text)
    compact = " ".join(str(text or "").split())
    question_count = compact.count("?")
    projection_map = projection if isinstance(projection, Mapping) else {}
    response_plan = projection_map.get("response_plan")
    if not isinstance(response_plan, Mapping):
        discourse = projection_map.get("discourse")
        response_plan = discourse.get("response_plan") if isinstance(discourse, Mapping) else {}
    if not isinstance(response_plan, Mapping):
        response_plan = {}
    raw_maximum_questions = response_plan.get(
        "maximum_questions", response_plan.get("max_questions", 1)
    )
    try:
        maximum_questions = max(0, min(8, int(raw_maximum_questions)))
    except (TypeError, ValueError):
        maximum_questions = 1
    result = {
        "sentience_fact_claim": bool(identity.get("sentience_fact_claim")),
        "generic_ai_identity_reset": bool(identity.get("generic_ai_identity_reset")),
        "sycophancy_signal": bool(identity.get("sycophancy_signal")),
        "question_pressure_exceeded": question_count > maximum_questions,
        "question_count": min(question_count, 9),
        "operator_review_recommended": False,
        "response_content_included": False,
        "provider_retry_authorized": False,
        "output_rewrite_authorized": False,
        "personality_mutation_authorized": False,
        "relationship_mutation_authorized": False,
        "authority_granted": False,
        "content_free": True,
    }
    result["operator_review_recommended"] = any(
        bool(result[key]) for key in (
            "sentience_fact_claim", "generic_ai_identity_reset",
            "sycophancy_signal", "question_pressure_exceeded",
        )
    )
    result["audit_digest"] = _digest(result)
    return result


__all__ = [
    "CONTRACT_VERSION", "build_era5_companion_projection", "audit_era5_companion_output", "process_era5_companion_control",
]
