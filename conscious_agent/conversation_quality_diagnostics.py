from __future__ import annotations

"""Read-only v1084.8 conversation-quality assembly diagnostics.

Diagnostics expose bounded decision codes, counts, and section names already used
by prompt assembly. They never expose prompt text, transcript content, memory
content, provider payloads, credentials, vectors, or hidden chain-of-thought.
"""

from typing import Any, Iterable, Mapping

QUALITY_DIAGNOSTICS_SCHEMA_VERSION = "1"
MAX_DIAGNOSTIC_SECTION_NAMES = 24
MAX_DIAGNOSTIC_REASON_CODES = 24


def _bounded_strings(values: Iterable[Any], *, limit: int) -> list[str]:
    result: list[str] = []
    for value in values:
        token = str(value or "").strip()[:80]
        if token and token not in result:
            result.append(token)
        if len(result) >= limit:
            break
    return result


def build_conversation_quality_diagnostics(
    quality: Any,
    *,
    input_budget_tokens: int,
    estimated_prompt_tokens: int,
    essential_tokens: int,
    included_sections: Iterable[str],
    omitted_sections: Iterable[str],
    history_candidates: int,
    history_included: int,
    memory_candidates: int,
    memories_included: int,
    relationship_candidates: int,
    relationship_included: int,
) -> dict[str, Any]:
    correction = getattr(quality, "correction_handling", None)
    expression = getattr(quality, "personality_expression", None)
    intent = getattr(quality, "turn_intent", None)
    shape = getattr(quality, "response_shape", None)
    signals = getattr(quality, "quality_signals", None)
    transition = getattr(quality, "topic_transition", None)
    callbacks = getattr(quality, "callbacks", None)
    unresolved = getattr(quality, "unresolved_threads", None)

    decision_codes = _bounded_strings(
        [
            *(getattr(quality, "reasons", ()) or ()),
            *(getattr(shape, "reasons", ()) or ()),
            f"intent:{getattr(intent, 'primary_intent', 'casual_remark')}",
            f"relevance:{getattr(signals, 'relevance_mode', 'current_turn_primary')}",
            f"transition:{getattr(transition, 'transition_kind', 'no_history')}",
            f"correction:{getattr(correction, 'correction_kind', 'none')}",
            f"expression:{getattr(expression, 'expression_mode', 'conversational_grounded')}",
        ],
        limit=MAX_DIAGNOSTIC_REASON_CODES,
    )
    included = _bounded_strings(included_sections, limit=MAX_DIAGNOSTIC_SECTION_NAMES)
    omitted = _bounded_strings(omitted_sections, limit=MAX_DIAGNOSTIC_SECTION_NAMES)

    return {
        "type": "conversation_quality_diagnostics",
        "schema_version": QUALITY_DIAGNOSTICS_SCHEMA_VERSION,
        "operator_visible": True,
        "read_only": True,
        "redacted": True,
        "content_free": True,
        "decision_codes": decision_codes,
        "intent": {
            "primary": str(getattr(intent, "primary_intent", "casual_remark")),
            "flags": _bounded_strings(getattr(intent, "flags", ()) or (), limit=12),
            "question_count": int(getattr(intent, "question_count", 0) or 0),
        },
        "response_shape": {
            "length_mode": str(getattr(shape, "length_mode", "balanced")),
            "depth_mode": str(getattr(shape, "depth_mode", "reasoned")),
            "target_min_words": int(getattr(shape, "target_min_words", 0) or 0),
            "target_max_words": int(getattr(shape, "target_max_words", 0) or 0),
        },
        "continuity": {
            "relevance_mode": str(getattr(signals, "relevance_mode", "current_turn_primary")),
            "topic_transition": str(getattr(transition, "transition_kind", "no_history")),
            "topic_match_offset": getattr(transition, "matched_turn_offset", None),
            "unresolved_thread_count": len(getattr(unresolved, "items", ()) or ()),
            "callbacks_selected": int(getattr(callbacks, "selected_count", 0) or 0),
        },
        "correction": {
            "explicit": bool(getattr(correction, "explicit_correction", False)),
            "kind": str(getattr(correction, "correction_kind", "none")),
            "target_scope": str(getattr(correction, "target_scope", "none")),
            "stale_claim_suppression": bool(getattr(correction, "stale_claim_suppression_required", False)),
        },
        "personality_expression": {
            "mode": str(getattr(expression, "expression_mode", "conversational_grounded")),
            "lane": str(getattr(expression, "current_lane", "ordinary")),
            "lane_transition": str(getattr(expression, "lane_transition", "same_lane")),
            "configured_personality_preserved": bool(getattr(expression, "configured_personality_preserved", True)),
        },
        "context_budget": {
            "input_budget_tokens": max(0, int(input_budget_tokens)),
            "estimated_prompt_tokens": max(0, int(estimated_prompt_tokens)),
            "essential_tokens": max(0, int(essential_tokens)),
            "within_budget": int(estimated_prompt_tokens) <= int(input_budget_tokens),
        },
        "section_decisions": {
            "included": included,
            "omitted": omitted,
            "history_candidates": max(0, int(history_candidates)),
            "history_included": max(0, int(history_included)),
            "memory_candidates": max(0, int(memory_candidates)),
            "memories_included": max(0, int(memories_included)),
            "relationship_candidates": max(0, int(relationship_candidates)),
            "relationship_included": max(0, int(relationship_included)),
        },
        "boundaries": {
            "hidden_chain_of_thought_exposed": False,
            "prompt_text_exposed": False,
            "transcript_text_exposed": False,
            "memory_content_exposed": False,
            "provider_payload_exposed": False,
            "credentials_exposed": False,
            "vectors_exposed": False,
            "provider_invoked": False,
            "writes_state": False,
            "mutates_personality": False,
            "rewrites_transcript": False,
        },
    }


def quality_diagnostics_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "messages", "user_message", "assistant_response", "transcript", "transcripts",
        "prompt", "prompts", "response", "responses", "content", "thought", "summary",
        "provider_payload", "credentials", "endpoint", "model", "raw_response", "raw_output",
        "receipt", "receipts", "vector", "vectors", "embedding", "embeddings", "acceptance_key",
        "claim_token", "chain_of_thought", "reasoning_trace",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
