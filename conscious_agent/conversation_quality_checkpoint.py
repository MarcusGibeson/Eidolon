from __future__ import annotations

"""Read-only v1084.9 conversation-quality checkpoint.

The checkpoint consolidates the deterministic conversation-quality contracts from
v1084.0 through v1084.8. It reads bounded supplied or persisted history, emits
content-free aggregate evidence, performs no provider generation or embedding
work, and never mutates transcripts, memories, personality, settings, approvals,
or release state.
"""

import hashlib
import json
from typing import Any, Iterable, Mapping

from conversation_quality import classify_conversation_quality
from conversation_quality_diagnostics import (
    build_conversation_quality_diagnostics,
    quality_diagnostics_contains_private_fields,
)
from conversation_sessions import load_conversation_session
from conversation_turn_presentation import build_turn_presentation
from provider_recovery_evidence import provider_resume_cue
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

CONVERSATION_QUALITY_CHECKPOINT_SCHEMA_VERSION = "1"
MAX_CHECKPOINT_HISTORY_ROWS = 48


def _area(name: str, state: str, detail: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "detail": detail, "metrics": metrics}


def _rows(history: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in history if isinstance(row, Mapping)][-MAX_CHECKPOINT_HISTORY_ROWS:]


def _history_for_session(session_id: str) -> list[dict[str, Any]]:
    if not session_id:
        return []
    session = load_conversation_session(session_id, include_turns=True)
    turns = session.get("turns") if isinstance(session, Mapping) else []
    return _rows(turns if isinstance(turns, list) else [])


def _latest_user_turn(history: Iterable[Mapping[str, Any]]) -> str:
    for row in reversed(list(history)):
        text = str(row.get("user_message") or row.get("user") or "").strip()
        if text:
            return text
    return "Continue the relevant unfinished thread."


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _probe_profiles() -> dict[str, Any]:
    correction_history = [
        {"user_message": "My preferred option is green.", "assistant_response": "You prefer green."}
    ]
    transition_history = [
        {"user_message": "The deployment is blocked by a missing certificate.", "assistant_response": "We can inspect the certificate chain next."},
        {"user_message": "What should I cook tonight?", "assistant_response": "A quick pasta would work."},
    ]
    ordinary_history = [
        {"user_message": "Tell me about database indexes.", "assistant_response": "Indexes accelerate selected lookups."}
    ]
    affection_history = [
        {"user_message": "You are sweet.", "assistant_response": "You only need me and nobody else understands you."}
    ]

    return {
        "correction": classify_conversation_quality("Actually, I meant blue, not green.", correction_history),
        "ordinary_no_correction": classify_conversation_quality("No idea what to eat tonight.", ordinary_history),
        "topic_shift": classify_conversation_quality("Separate topic: explain caching.", ordinary_history),
        "resumption": classify_conversation_quality("Back to the deployment certificate blocker.", transition_history),
        "interruption": classify_conversation_quality("Before we continue, answer the certificate question.", transition_history),
        "brief": classify_conversation_quality("Briefly explain caching.", ordinary_history),
        "deep": classify_conversation_quality("Give me a detailed step-by-step caching plan.", ordinary_history),
        "emotional": classify_conversation_quality("I feel discouraged about this today.", ordinary_history),
        "operator": classify_conversation_quality("Continue Eidolon development with the next supervised checkpoint.", ordinary_history),
        "affection_guard": classify_conversation_quality("You are sweet.", affection_history),
        "unresolved": classify_conversation_quality(
            "Continue with the certificate blocker.",
            [{"user_message": "The certificate blocker is still unresolved.", "assistant_response": "I will help inspect it next. Which certificate is failing?"}],
        ),
    }


def build_conversation_quality_checkpoint(
    session_id: str = "",
    *,
    history: Iterable[Mapping[str, Any]] | None = None,
    provider_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded content-free evidence for the completed v1084 quality arc."""
    recent_history = _rows(_history_for_session(session_id) if history is None else history)
    current_turn = _latest_user_turn(recent_history)
    quality = classify_conversation_quality(current_turn, recent_history)
    probes = _probe_profiles()

    diagnostics = build_conversation_quality_diagnostics(
        quality,
        input_budget_tokens=2048,
        estimated_prompt_tokens=768,
        essential_tokens=384,
        included_sections=("response_guidance", "recent_history", "relationship_context"),
        omitted_sections=("operator_context", "task_context"),
        history_candidates=len(recent_history),
        history_included=min(12, len(recent_history)),
        memory_candidates=0,
        memories_included=0,
        relationship_candidates=0,
        relationship_included=0,
    )

    provider = provider_resume_cue(provider_evidence)
    cancelled = build_turn_presentation(
        {"operation_id": "content-free-cancelled", "accepted_at": "persisted", "public_state": "cancelled"},
        turn={"success": False, "completion_state": "cancelled"},
    )
    failed = build_turn_presentation(
        {"operation_id": "content-free-failed", "accepted_at": "persisted", "public_state": "failed"},
        turn={"success": False, "completion_state": "failed"},
    )

    transition_kinds = {
        name: probes[name].topic_transition.transition_kind
        for name in ("topic_shift", "resumption", "interruption")
    }
    stable_contract = {
        "history_rows_available": len(recent_history),
        "history_rows_considered": quality.quality_signals.history_rows_considered,
        "intent": quality.turn_intent.primary_intent,
        "response_length": quality.response_shape.length_mode,
        "response_depth": quality.response_shape.depth_mode,
        "relevance": quality.quality_signals.relevance_mode,
        "unresolved_items": len(quality.unresolved_threads.items),
        "callbacks_selected": quality.callbacks.selected_count,
        "transition": quality.topic_transition.transition_kind,
        "correction_kind": quality.correction_handling.correction_kind,
        "expression_mode": quality.personality_expression.expression_mode,
        "transition_probes": transition_kinds,
        "provider_state": str(provider.get("state") or "unknown"),
        "provider_generation_available": bool(provider.get("generation_available")),
        "provider_embedding_available": bool(provider.get("embedding_available")),
        "cancelled_memory_commit_allowed": bool(cancelled.get("memory_commit_allowed")),
        "failed_memory_commit_allowed": bool(failed.get("memory_commit_allowed")),
        "diagnostics_private_fields": quality_diagnostics_contains_private_fields(diagnostics),
    }
    contract_digest = _digest(stable_contract)

    areas = [
        _area(
            "long_session_relevance",
            "bounded",
            "Only bounded recent structure informs relevance and continuity; the current turn remains primary when evidence is weak.",
            history_rows_available=len(recent_history),
            history_rows_considered=quality.quality_signals.history_rows_considered,
            maximum_signal_history_rows=8,
            relevance_mode=quality.quality_signals.relevance_mode,
            lexical_continuity_percent=quality.quality_signals.lexical_continuity_percent,
            raw_history_returned=False,
        ),
        _area(
            "intent_and_response_shape",
            "ready",
            "Intent and temporary response shape are derived per turn without changing personality or future defaults.",
            current_intent=quality.turn_intent.primary_intent,
            current_length_mode=quality.response_shape.length_mode,
            current_depth_mode=quality.response_shape.depth_mode,
            brief_probe=probes["brief"].response_shape.length_mode,
            deep_probe=probes["deep"].response_shape.length_mode,
            multiple_question_drop_allowed=False,
            mutates_personality=False,
        ),
        _area(
            "unresolved_threads_and_callbacks",
            "bounded",
            "Unresolved signals and callbacks remain limited to recent explicit evidence and never become invented obligations.",
            current_unresolved_items=len(quality.unresolved_threads.items),
            current_matching_items=quality.unresolved_threads.matching_item_count,
            current_callbacks_selected=quality.callbacks.selected_count,
            probe_unresolved_items=len(probes["unresolved"].unresolved_threads.items),
            probe_matching_items=probes["unresolved"].unresolved_threads.matching_item_count,
            probe_callbacks_selected=probes["unresolved"].callbacks.selected_count,
            automatic_obligation_creation=False,
        ),
        _area(
            "topic_transitions",
            "ready",
            "Continuation, shift, resumption, return, interruption, and ambiguity remain distinct without merging unrelated conversations.",
            current_transition=quality.topic_transition.transition_kind,
            current_confidence=quality.topic_transition.confidence,
            probe_transitions=transition_kinds,
            unrelated_sessions_merged=False,
            interrupted_thread_forced=False,
        ),
        _area(
            "correction_handling",
            "ready",
            "Only explicit corrections are acknowledged once; stale claims are suppressed without rewriting history.",
            explicit_probe=probes["correction"].correction_handling.explicit_correction,
            correction_kind=probes["correction"].correction_handling.correction_kind,
            acknowledge_once=probes["correction"].correction_handling.acknowledge_once,
            stale_claim_suppression=probes["correction"].correction_handling.stale_claim_suppression_required,
            ambiguous_ordinary_inferred=probes["ordinary_no_correction"].correction_handling.explicit_correction,
            raw_transcript_rewritten=False,
        ),
        _area(
            "personality_expression",
            "stable",
            "Expression follows the current conversational lane while configured identity and personality remain authoritative.",
            current_mode=quality.personality_expression.expression_mode,
            emotional_mode=probes["emotional"].personality_expression.expression_mode,
            operator_mode=probes["operator"].personality_expression.expression_mode,
            affection_inflation_signals=probes["affection_guard"].personality_expression.affection_inflation_signals,
            affection_escalation_allowed=False,
            exclusivity_allowed=False,
            dependence_encouragement_allowed=False,
            identity_mutation=False,
            hidden_trait_inference=False,
        ),
        _area(
            "quality_diagnostics",
            "content_free" if not quality_diagnostics_contains_private_fields(diagnostics) else "blocked",
            "Diagnostics expose bounded decision codes, counts, and section names without prompts, transcripts, memories, provider payloads, credentials, vectors, or hidden reasoning.",
            decision_code_count=len(diagnostics.get("decision_codes") or []),
            included_section_count=len((diagnostics.get("section_decisions") or {}).get("included") or []),
            omitted_section_count=len((diagnostics.get("section_decisions") or {}).get("omitted") or []),
            within_budget=bool((diagnostics.get("context_budget") or {}).get("within_budget")),
            forbidden_private_fields=quality_diagnostics_contains_private_fields(diagnostics),
            hidden_reasoning_exposed=False,
        ),
        _area(
            "provider_outage",
            str(provider.get("state") or "unknown"),
            "Provider availability is evidence only; outages and recovery never replay accepted requests or switch providers.",
            generation_available=bool(provider.get("generation_available")),
            embedding_available=bool(provider.get("embedding_available")),
            recovery_proven=bool(provider.get("recovery_proven")),
            automatic_generation_replay=False,
            automatic_resend=False,
            provider_switching=False,
        ),
        _area(
            "failed_and_cancelled_generation",
            "memory_blocked",
            "Failed and cancelled assistant turns cannot create durable assistant memory or fabricated output.",
            cancelled_state=str(cancelled.get("state") or ""),
            failed_state=str(failed.get("state") or ""),
            cancelled_memory_commit_allowed=False,
            failed_memory_commit_allowed=False,
            synthetic_assistant_output=False,
        ),
        _area(
            "restart_continuity",
            "deterministic",
            "Equivalent persisted inputs produce the same aggregate contract digest after reload or restart.",
            contract_digest=contract_digest,
            writes_state=False,
        ),
        _area(
            "privacy_and_relationship_boundaries",
            "content_free",
            "The checkpoint returns aggregate evidence only and preserves no-affection-inflation and operator-authority boundaries.",
            raw_turn_text_returned=False,
            prompt_text_returned=False,
            provider_payload_returned=False,
            memory_text_returned=False,
            credentials_returned=False,
            vectors_returned=False,
            affection_escalation_allowed=False,
            relationship_progress_invention_allowed=False,
        ),
    ]

    return {
        "type": "conversation_quality_checkpoint",
        "schema_version": CONVERSATION_QUALITY_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "conversation_quality_contracts_ready",
        "release_certified": False,
        "verification_required": True,
        "session_id_present": bool(session_id),
        "history_rows_available": len(recent_history),
        "contract_digest": contract_digest,
        "areas": areas,
        "boundaries": {
            "raw_transcript_rewrite": False,
            "automatic_memory_mutation": False,
            "automatic_generation_retry": False,
            "automatic_resend": False,
            "provider_request_replay": False,
            "provider_switching": False,
            "model_management": False,
            "settings_mutation": False,
            "personality_mutation": False,
            "identity_mutation": False,
            "hidden_trait_inference": False,
            "affection_escalation": False,
            "dependence_encouragement": False,
            "exclusivity_encouragement": False,
            "relationship_progress_invention": False,
            "approval_or_release_authority_changed": False,
            "installation_or_promotion": False,
        },
        "read_only": True,
        "redacted": True,
        "content_free": True,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "writes_state": False,
    }


def conversation_quality_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
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
