from __future__ import annotations

"""Bounded v1087.0 Desktop Alpha daily-evaluation protocol.

The protocol consumes the v1086.9 read-only conversation-readiness checkpoint
and defines an operator-guided evaluation contract. It does not create an
evaluation, inspect transcript content, call a provider, score model quality,
write runtime state, or authorize release activity.
"""

from typing import Any, Mapping

from conversation_readiness_checkpoint import build_conversation_readiness_checkpoint
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

DAILY_EVALUATION_PROTOCOL_SCHEMA_VERSION = "1"
RATING_DIMENSIONS = (
    "continuity",
    "relevance",
    "tone",
    "responsiveness",
    "recovery",
    "usability",
)
RATING_MINIMUM = 1
RATING_MAXIMUM = 5
MAX_EVALUATION_OBSERVATIONS = 64
MAX_OPERATOR_NOTE_CHARS = 4_000
EVALUATION_STATES = ("active", "completed", "aborted")
ISSUE_DOMAINS = (
    "none",
    "model_quality",
    "provider_transport",
    "interface",
    "session_continuity",
    "operator",
)
ISSUE_SEVERITIES = ("none", "minor", "major", "blocking")
EVALUATION_SIGNALS = (
    "consecutive_use",
    "restart_resume",
    "provider_outage",
    "provider_return",
    "generation_interruption",
    "failed_retry",
    "completed_regeneration",
    "explicit_resend",
    "message_branch",
    "response_preference",
    "temporary_instruction",
    "pinned_context",
    "offline_intent",
    "long_history",
    "multi_tab",
    "memory_correction",
    "topic_transition",
    "draft_continuity",
    "scroll_anchor",
    "jump_to_latest",
    "context_inspection",
    "search_navigation",
    "memory_browse",
)


def build_daily_evaluation_protocol(*, session_id: str = "") -> dict[str, Any]:
    readiness = build_conversation_readiness_checkpoint(session_id=session_id)
    readiness_ready = readiness.get("checkpoint_status") == "ready_for_operator_evaluation"
    return {
        "type": "desktop_alpha_daily_evaluation_protocol",
        "schema_version": DAILY_EVALUATION_PROTOCOL_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "protocol_status": "ready" if readiness_ready else "review_required",
        "readiness_checkpoint_status": str(readiness.get("checkpoint_status") or "unknown"),
        "readiness_contract_digest": str(readiness.get("contract_digest") or ""),
        "readiness_areas_digest": str(readiness.get("areas_digest") or ""),
        "readiness_area_count": int(readiness.get("area_count") or 0),
        "session_requested": bool(readiness.get("session_requested")),
        "session_available": bool(readiness.get("session_available")),
        "rating_dimensions": list(RATING_DIMENSIONS),
        "rating_scale": {"minimum": RATING_MINIMUM, "maximum": RATING_MAXIMUM},
        "evaluation_states": list(EVALUATION_STATES),
        "issue_domains": list(ISSUE_DOMAINS),
        "issue_severities": list(ISSUE_SEVERITIES),
        "evaluation_signals": list(EVALUATION_SIGNALS),
        "limits": {
            "maximum_observations": MAX_EVALUATION_OBSERVATIONS,
            "maximum_operator_note_chars": MAX_OPERATOR_NOTE_CHARS,
        },
        "operator_observation_required": True,
        "explicit_confirmation_required_for_mutation": True,
        "private_notes_runtime_only": True,
        "transcript_content_required": False,
        "autonomous_scoring": False,
        "automatic_promotion": False,
        "automatic_release_certification": False,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "model_management": False,
        "provider_switching": False,
        "generation_settings_changed": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def daily_evaluation_protocol_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content",
        "text",
        "message",
        "user_message",
        "assistant_response",
        "transcript",
        "prompt",
        "note",
        "notes",
        "temporary_instruction",
        "pinned_context",
        "queued_operator_intent",
        "provider_payload",
        "credentials",
        "vectors",
        "embedding",
        "receipt",
        "receipts",
        "hidden_reasoning",
        "chain_of_thought",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            keys = {str(key) for key in current}
            if forbidden & keys:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
