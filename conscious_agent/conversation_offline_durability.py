from __future__ import annotations

"""Content-free local conversation durability state.

This module reports which conversation surfaces remain usable without provider-backed
text generation. It reads local session metadata only. It never calls a provider,
changes settings, replays a request, or stores conversation content.
"""

from typing import Any

from conversation_navigation import load_conversation_presentation_state
from conversation_sessions import (
    get_active_conversation_session,
    list_conversation_sessions,
    load_conversation_draft,
    load_conversation_session,
)

OFFLINE_SESSION_DURABILITY_SCHEMA_VERSION = "1"


def _safe_count(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def offline_session_durability_state(session_id: str = "") -> dict[str, Any]:
    """Return one bounded, content-free snapshot of local continuity surfaces."""
    requested = str(session_id or "").strip()
    session = load_conversation_session(requested, include_turns=False) if requested else None
    if not session:
        session = get_active_conversation_session(create_if_missing=False) or {}
    resolved_session_id = str(session.get("id") or "")
    active_sessions = list_conversation_sessions(include_archived=False)
    all_sessions = list_conversation_sessions(include_archived=True)
    archived_count = sum(1 for item in all_sessions if str(item.get("status") or "active") == "archived")
    draft = load_conversation_draft(resolved_session_id) if resolved_session_id else {}
    presentation = load_conversation_presentation_state(resolved_session_id) if resolved_session_id else {}
    session_active = bool(resolved_session_id and str(session.get("status") or "active") != "archived")
    capabilities = {
        "conversation_history": bool(resolved_session_id),
        "conversation_selection": bool(active_sessions),
        "draft_editing": session_active,
        "conversation_search": True,
        "archive_browsing": True,
        "archive_restore": True,
        "reading_position": session_active,
        "attention_center": True,
        "memory_curation": True,
        "memory_browse": True,
        "context_inspection": True,
        "pinned_working_context": session_active,
        "message_branching": session_active,
        "queued_operator_intent": session_active,
        "settings_inspection": True,
        "provider_generation": False,
        "provider_switching": False,
        "model_management": False,
        "automatic_request_replay": False,
        "queued_intent_auto_execution": False,
    }
    return {
        "type": "offline_session_durability",
        "schema_version": OFFLINE_SESSION_DURABILITY_SCHEMA_VERSION,
        "session_id": resolved_session_id,
        "session_available": bool(resolved_session_id),
        "session_active": session_active,
        "active_session_count": len(active_sessions),
        "archived_session_count": archived_count,
        "turn_count": _safe_count(session.get("turn_count")),
        "completed_turn_count": _safe_count(session.get("completed_turn_count")),
        "has_draft": bool(draft.get("content")),
        "draft_revision": _safe_count(draft.get("revision")),
        "follow_latest": bool(presentation.get("follow_latest", True)),
        "unread_turn_count": _safe_count(presentation.get("unread_turn_count")),
        "capabilities": capabilities,
        "provider_dependency": "none_for_local_surfaces",
        "provider_response_fabricated": False,
        "assistant_memory_commit_allowed": False,
        "local_private": True,
        "content_free": True,
    }


def offline_session_state_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "content", "text", "message", "user_message", "assistant_response", "transcript",
        "prompt", "prompts", "partial", "partial_tokens", "memory", "memories",
        "relationship", "mood", "important_moment", "provider_payload", "credentials",
        "raw_response", "raw_output", "command_output", "receipt", "diagnostic",
        "acceptance_key", "operation_id", "model_inventory",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
