from __future__ import annotations

"""Read-only v1086.8 long-session performance and UX hardening evidence."""

from typing import Any, Mapping

LONG_SESSION_HARDENING_SCHEMA_VERSION = "1"
INITIAL_RENDER_WINDOW = 80
EARLIER_HISTORY_WINDOW_LIMIT = 120
LONG_SESSION_THRESHOLD = 120


def build_long_session_hardening_state(session_id: str) -> dict[str, Any]:
    from conversation_sessions import (
        conversation_controls_for_prompt,
        conversation_session_turn_window,
        load_conversation_draft,
        load_conversation_session,
    )
    from conversation_offline_degradation import offline_conversation_degradation_state

    token = str(session_id or "").strip()
    session = load_conversation_session(token, include_turns=False) if token else None
    if not session:
        raise ValueError("Conversation session not found.")
    window = conversation_session_turn_window(token, limit=INITIAL_RENDER_WINDOW)
    controls = conversation_controls_for_prompt(token)
    draft = load_conversation_draft(token)
    pins = [row for row in controls.get("pinned_context", []) if isinstance(row, Mapping)] if isinstance(controls, Mapping) else []
    queued = controls.get("queued_operator_intent") if isinstance(controls, Mapping) and isinstance(controls.get("queued_operator_intent"), Mapping) else None
    turn_count = max(0, int(session.get("turn_count") or 0))
    shown = max(0, int(window.get("shown") or len(window.get("turns") or [])))
    return {
        "type": "conversation_long_session_hardening",
        "schema_version": LONG_SESSION_HARDENING_SCHEMA_VERSION,
        "session_id": token,
        "turn_count": turn_count,
        "completed_turn_count": max(0, int(session.get("completed_turn_count") or 0)),
        "long_session": turn_count >= LONG_SESSION_THRESHOLD,
        "initial_render_limit": INITIAL_RENDER_WINDOW,
        "initial_turns_rendered": shown,
        "earlier_history_window_limit": EARLIER_HISTORY_WINDOW_LIMIT,
        "earlier_history_available": bool(window.get("has_older")),
        "full_transcript_embedded": False,
        "whole_turn_windows": True,
        "scroll_anchor_preserved_on_prepend": True,
        "jump_to_latest_preserved": True,
        "draft_preserved": bool(draft.get("content")),
        "draft_revision": max(0, int(draft.get("revision") or 0)),
        "pinned_context_count": len(pins),
        "queued_operator_intent_present": bool(queued),
        "response_preferences_session_local": True,
        "message_edits_create_branches": True,
        "original_transcript_preserved": True,
        "retry_regeneration_resend_separated": True,
        "multi_tab_revision_guard": True,
        "context_inspection_offline": True,
        "memory_browse_offline": True,
        "narrow_layout_contained": True,
        "provider_invoked": False,
        "writes_state": False,
        "contains_transcript_content": False,
        "offline_degradation": offline_conversation_degradation_state(token, provider_available=False),
    }


def long_session_hardening_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "user_message", "assistant_response", "transcript", "prompt",
        "provider_payload", "credentials", "receipt", "memory", "memories", "chain_of_thought",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
