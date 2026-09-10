from __future__ import annotations

"""Calm, redacted presentation state for the daily conversation surface.

This module translates existing runtime/session truth into companion-facing labels,
explicit recovery choices, and bounded diagnostics. It never calls a provider,
writes runtime data, changes memories, selects models, or enables fallback/autonomy.
"""

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlparse


_FAILURE_PRESENTATION: dict[str, tuple[str, str, str]] = {
    "cancelled": (
        "cancelled",
        "Cancelled safely",
        "The partial reply was kept visible only where useful and was not added to memory or future continuity.",
    ),
    "timeout": (
        "attention",
        "Eidolon took too long",
        "The turn stopped safely. Retry is available only as an explicit action.",
    ),
    "unavailable_service": (
        "offline",
        "Eidolon cannot reach the local service",
        "The configured local service is unavailable. Nothing was switched or installed.",
    ),
    "missing_model": (
        "offline",
        "The selected model is unavailable",
        "Eidolon kept the configured model and did not pull, replace, or switch anything.",
    ),
    "invalid_configuration": (
        "attention",
        "Local generation needs attention",
        "The current provider settings could not be used safely. No provider request or fallback was attempted.",
    ),
    "interrupted_stream": (
        "disconnected",
        "The reply was interrupted",
        "The incomplete reply was excluded from memory and future continuity. Retry remains explicit.",
    ),
    "consumer_disconnected": (
        "disconnected",
        "The conversation connection ended",
        "The accepted turn remains visible, but no automatic retry or duplicate submission occurred.",
    ),
    "closed_client": (
        "disconnected",
        "The local connection closed",
        "The reply did not complete and was excluded from memory and future continuity.",
    ),
    "unsupported_streaming": (
        "attention",
        "Streaming is unavailable",
        "The current provider configuration did not support this streaming request. Nothing was switched automatically.",
    ),
    "context_limit": (
        "attention",
        "This conversation is too large for the current model",
        "Protected instructions and the latest message were kept intact; the failed turn was not added to future continuity.",
    ),
    "malformed_response": (
        "attention",
        "The local service returned an unusable reply",
        "Raw provider content was not accepted, displayed as trusted output, or saved to memory.",
    ),
    "empty_response": (
        "attention",
        "No usable reply arrived",
        "The provider completed without content Eidolon could safely accept.",
    ),
    "http_failure": (
        "attention",
        "The local request failed",
        "The provider returned a bounded request failure. No fallback or model switch occurred.",
    ),
    "memory_write_failure": (
        "attention",
        "The reply could not be saved",
        "The response was not reported as complete because its memory commit did not finish safely.",
    ),
    "runtime_io_failure": (
        "attention",
        "The local conversation could not finish",
        "The failed turn was kept out of memory and future continuity.",
    ),
    "conversation_runtime_failure": (
        "attention",
        "The conversation stopped safely",
        "The incomplete turn remains visible but was excluded from memory and future continuity.",
    ),
    "ai_disabled": (
        "offline",
        "Local generation is off",
        "The message was recorded without contacting a provider. You can keep organizing the conversation offline.",
    ),
}

_FAILURE_ALIASES = {
    "provider_unavailable": "unavailable_service",
    "provider_disconnect": "interrupted_stream",
    "model_unavailable": "missing_model",
    "malformed_event": "malformed_response",
    "empty_output": "empty_response",
    "memory_write_failed": "memory_write_failure",
    "response_generated_memory_failed": "memory_write_failure",
}

_RETRYABLE_FAILURES = {
    "cancelled",
    "timeout",
    "unavailable_service",
    "missing_model",
    "invalid_configuration",
    "interrupted_stream",
    "consumer_disconnected",
    "closed_client",
    "unsupported_streaming",
    "context_limit",
    "malformed_response",
    "empty_response",
    "http_failure",
    "runtime_io_failure",
    "conversation_runtime_failure",
}

_SETTINGS_FAILURES = {
    "timeout",
    "unavailable_service",
    "missing_model",
    "invalid_configuration",
    "interrupted_stream",
    "consumer_disconnected",
    "closed_client",
    "unsupported_streaming",
    "context_limit",
    "malformed_response",
    "empty_response",
    "http_failure",
}

_OFFLINE_OPTION_FAILURES = _SETTINGS_FAILURES | {"ai_disabled"}


@dataclass(frozen=True)
class TurnExperienceState:
    state: str
    label: str
    detail: str
    category: str
    retry_allowed: bool
    settings_allowed: bool
    offline_allowed: bool
    recovered: bool = False

    def public_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "label": self.label,
            "detail": self.detail,
            "category": self.category,
            "retry_allowed": self.retry_allowed,
            "settings_allowed": self.settings_allowed,
            "offline_allowed": self.offline_allowed,
            "recovered": self.recovered,
        }


@dataclass(frozen=True)
class ConversationExperienceState:
    state: str
    label: str
    detail: str
    provider_label: str
    model_label: str
    endpoint_label: str
    session_title: str
    continuity_label: str

    def public_dict(self) -> dict[str, str]:
        return {
            "state": self.state,
            "label": self.label,
            "detail": self.detail,
            "provider_label": self.provider_label,
            "model_label": self.model_label,
            "endpoint_label": self.endpoint_label,
            "session_title": self.session_title,
            "continuity_label": self.continuity_label,
        }


def _clean_public_label(value: Any, fallback: str, *, limit: int = 80) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return fallback
    return text[:limit].rstrip() or fallback


def provider_display_name(provider: Any) -> str:
    token = str(provider or "").strip().lower()
    if token == "ollama":
        return "Ollama"
    if token == "llama_cpp":
        return "llama.cpp"
    return _clean_public_label(token, "Local provider", limit=32)


def safe_endpoint_label(endpoint: Any) -> str:
    text = str(endpoint or "").strip()
    if not text:
        return "Not available"
    try:
        parsed = urlparse(text)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "Redacted or invalid"
        host = parsed.hostname
        host_text = f"[{host}]" if ":" in host and not host.startswith("[") else host
        netloc = f"{host_text}:{parsed.port}" if parsed.port is not None else host_text
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme.lower()}://{netloc}{path}"[:200]
    except (TypeError, ValueError):
        return "Redacted or invalid"


def normalize_failure_category(value: Any) -> str:
    token = str(value or "").strip().lower()
    return _FAILURE_ALIASES.get(token, token)


def retry_allowed_for_failure(value: Any) -> bool:
    return normalize_failure_category(value) in _RETRYABLE_FAILURES


def turn_experience_state(turn: Mapping[str, Any] | None) -> TurnExperienceState:
    if not turn:
        return TurnExperienceState(
            state="ready",
            label="Ready to talk",
            detail="Start a new conversation or continue where you left off.",
            category="",
            retry_allowed=False,
            settings_allowed=False,
            offline_allowed=False,
        )
    success = turn.get("success") is True
    completion_state = str(turn.get("completion_state") or "").strip().lower()
    if success and completion_state == "completed":
        recovered = bool(str(turn.get("recovery_of") or "").strip())
        return TurnExperienceState(
            state="recovered" if recovered else "ready",
            label="Recovered successfully" if recovered else "Ready to continue",
            detail=(
                "The explicit retry completed once and was saved to this conversation."
                if recovered
                else "The last reply was saved to this conversation."
            ),
            category="recovered" if recovered else "completed",
            retry_allowed=False,
            settings_allowed=False,
            offline_allowed=False,
            recovered=recovered,
        )
    category = normalize_failure_category(turn.get("failure_category") or completion_state)
    state, label, detail = _FAILURE_PRESENTATION.get(
        category,
        (
            "attention",
            "The last turn needs attention",
            "The incomplete reply was kept out of memory and future continuity.",
        ),
    )
    return TurnExperienceState(
        state=state,
        label=label,
        detail=detail,
        category=category,
        retry_allowed=category in _RETRYABLE_FAILURES,
        settings_allowed=category in _SETTINGS_FAILURES,
        offline_allowed=category in _OFFLINE_OPTION_FAILURES,
    )


def presentation_for_turn(turn: Mapping[str, Any] | None) -> tuple[str, str, str]:
    """Compatibility tuple for callers that only need state, label, and detail."""
    presentation = turn_experience_state(turn)
    return presentation.state, presentation.label, presentation.detail


def redacted_turn_diagnostics(turn: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return only bounded, non-secret diagnostics suitable for a closed details block."""
    if not turn:
        return {}
    raw = turn.get("diagnostic") if isinstance(turn.get("diagnostic"), Mapping) else {}
    category = normalize_failure_category(
        raw.get("technical_category") or raw.get("code") or turn.get("failure_category")
    )
    evidence_raw = raw.get("evidence") if isinstance(raw.get("evidence"), Mapping) else {}
    evidence = {
        key: value
        for key, value in evidence_raw.items()
        if key in {"failure_kind", "exception_type", "yielded_content", "stream_supported"}
        and isinstance(value, (str, int, float, bool, type(None)))
    }
    status_code = raw.get("status_code")
    if not isinstance(status_code, int):
        status_code = None
    return {
        "provider": provider_display_name(raw.get("provider") or turn.get("provider")),
        "model": _clean_public_label(raw.get("model") or turn.get("model"), "Not selected", limit=160),
        "endpoint": safe_endpoint_label(raw.get("endpoint")),
        "technical_category": category or "not_available",
        "status_code": status_code,
        "retryable": bool(raw.get("retryable")) if "retryable" in raw else retry_allowed_for_failure(category),
        "evidence": evidence,
        "redacted": True,
    }


_COMPANION_STATUS_LABELS = {
    "ready": "Ready",
    "recovered": "Ready",
    "offline": "Offline mode",
    "cancelled": "Cancelled safely",
    "attention": "Needs recovery",
    "disconnected": "Completion uncertain",
}


def build_conversation_experience_state(
    *,
    active_session: Mapping[str, Any] | None,
    latest_turn: Mapping[str, Any] | None,
    settings: Mapping[str, Any] | None,
    continuity_summary: Mapping[str, Any] | None,
) -> ConversationExperienceState:
    turn_state = turn_experience_state(latest_turn)
    configured = settings or {}
    provider = provider_display_name(configured.get("local_model_provider"))
    model = _clean_public_label(configured.get("local_model"), "Not selected", limit=80)
    endpoint = safe_endpoint_label(configured.get("local_model_endpoint") or configured.get("ollama_base_url"))
    session_title = _clean_public_label((active_session or {}).get("title"), "New conversation", limit=72)
    summary = continuity_summary or {}
    cue_count = max(0, int(summary.get("cue_count") or 0))
    mood = _clean_public_label(summary.get("mood_label"), "neutral", limit=32)
    continuity_label = f"{cue_count} continuity cue{'s' if cue_count != 1 else ''} · mood {mood}"
    state = turn_state.state
    label = _COMPANION_STATUS_LABELS.get(state, turn_state.label)
    detail = turn_state.detail
    if configured.get("ai_chat_enabled") is False:
        state = "offline"
        label = "Offline mode"
        detail = "Messages can still be organized, but no local provider will be contacted."
    return ConversationExperienceState(
        state=state,
        label=label,
        detail=detail,
        provider_label=provider,
        model_label=model,
        endpoint_label=endpoint,
        session_title=session_title,
        continuity_label=continuity_label,
    )
