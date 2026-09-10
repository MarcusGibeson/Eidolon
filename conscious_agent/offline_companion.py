from __future__ import annotations

"""Canonical offline-companion and provider-return presentation.

The helpers in this module are deterministic and content-free. They classify
already-redacted readiness evidence and describe operator-controlled recovery.
They never contact a provider, synthesize assistant text, commit memory, change
settings, select models, or authorize request replay.
"""

from typing import Any

CANONICAL_STATE_COPY: dict[str, tuple[str, str]] = {
    "checking": (
        "Checking configured provider",
        "Running a bounded readiness check. No message is sent and no provider, model, or setting is changed.",
    ),
    "ready": (
        "Configured provider is ready",
        "Provider-backed conversation is available through the configured provider and model.",
    ),
    "recovering": (
        "Configured provider recovered",
        "Verified readiness returned. Your draft is preserved; resume or resend only through an explicit operator action.",
    ),
    "temporarily_unavailable": (
        "Configured provider is temporarily unavailable",
        "Generation is unavailable right now. Your draft and local history remain available, and no assistant reply will be fabricated.",
    ),
    "misconfigured": (
        "Provider configuration needs attention",
        "Review the configured provider, endpoint, model, and timing values explicitly. Nothing was switched, installed, or saved automatically.",
    ),
    "degraded": (
        "Conversation generation is available with reduced capability",
        "Generation is ready, but embeddings or another optional provider capability is unavailable.",
    ),
    "generation_unavailable": (
        "Configured generation is unavailable",
        "The configured generation service or model cannot produce a reply. Your draft and local companion surfaces remain available.",
    ),
}

LOCAL_SURFACES = (
    "conversation_history",
    "drafts",
    "conversation_search",
    "conversation_archive_restore",
    "attention_center",
    "action_history",
    "memory_curation",
    "settings_inspection",
    "supervised_operator_tools",
)

EMBEDDING_DEPENDENT_SURFACES = (
    "semantic_memory_retrieval",
    "embedding_refresh",
)


def canonical_copy(state: str) -> tuple[str, str]:
    return CANONICAL_STATE_COPY.get(
        str(state or ""),
        ("Provider status needs attention", "No provider request was replayed and local records remain available."),
    )


def dependency_boundaries(*, generation_available: bool, embedding_available: bool, configuration_valid: bool = True) -> dict[str, Any]:
    local = {name: True for name in LOCAL_SURFACES}
    provider = {
        "provider_backed_conversation": bool(generation_available and configuration_valid),
        "semantic_memory_retrieval": bool(embedding_available and configuration_valid),
        "embedding_refresh": bool(embedding_available and configuration_valid),
    }
    unavailable_reasons: dict[str, str] = {}
    if not configuration_valid:
        unavailable_reasons.update({name: "invalid_configuration" for name in provider})
    else:
        if not generation_available:
            unavailable_reasons["provider_backed_conversation"] = "generation_unavailable"
        if not embedding_available:
            unavailable_reasons["semantic_memory_retrieval"] = "embedding_unavailable"
            unavailable_reasons["embedding_refresh"] = "embedding_unavailable"
    return {
        "local_surfaces": local,
        "provider_surfaces": provider,
        "unavailable_reasons": unavailable_reasons,
        "unrelated_local_features_disabled": False,
    }


def manual_recovery_handoff(state: str, *, readiness_persisted: bool = False) -> dict[str, Any]:
    recovered = str(state or "") in {"ready", "recovering"} and bool(readiness_persisted)
    return {
        "steps": [
            {"id": "check_provider", "label": "Check configured provider", "method": "bounded_readiness"},
            {"id": "open_settings", "label": "Open provider settings", "method": "navigation_only"},
            {"id": "review_diagnostics", "label": "Review readiness diagnostics", "method": "redacted_evidence"},
            {"id": "resume_composition", "label": "Resume composition", "method": "explicit_operator_action", "enabled": recovered},
        ],
        "recovery_proven": recovered,
        "automatic_generation_replay": False,
        "automatic_resend": False,
        "automatic_provider_switch": False,
        "automatic_model_selection": False,
        "settings_saved": False,
    }


def resend_policy(*, accepted: bool, persisted_not_accepted: bool) -> dict[str, Any]:
    allowed = bool(not accepted and persisted_not_accepted)
    return {
        "explicit_resend_allowed": allowed,
        "new_acceptance_identity_required": allowed,
        "automatic_resend": False,
        "reason": "persisted_not_accepted" if allowed else ("already_accepted" if accepted else "acceptance_unproven"),
    }


def offline_turn_contract() -> dict[str, Any]:
    return {
        "preserve_unsent_draft": True,
        "synthetic_assistant_response": False,
        "assistant_memory_commit": False,
        "provider_payload_persisted": False,
        "raw_prompt_or_response_persisted": False,
        "private_receipt_in_conversation_history": False,
    }
