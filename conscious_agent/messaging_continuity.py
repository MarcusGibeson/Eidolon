from __future__ import annotations

"""Content-free message-view continuity and provider transition evidence.

The helpers in this module do not read or write conversation content, contact a
provider, select a session, change a draft, or grant release authority. They
provide bounded decisions used by the v1103.3-v1103.5 messaging surfaces.
"""

from typing import Any

SCHEMA_VERSION = "1"
DEFAULT_FOLLOW_THRESHOLD_PX = 96
MAX_SCROLL_DISTANCE_PX = 1_000_000
_RECOVERABLE_PROVIDER_STATES = {
    "unavailable",
    "unavailable_service",
    "generation_unavailable",
    "temporarily_unavailable",
    "missing_model",
    "invalid_configuration",
    "timeout",
    "unknown",
}
_READY_PROVIDER_STATES = {"ready", "recovering", "returned"}


def _bounded_int(value: Any, *, minimum: int = 0, maximum: int = MAX_SCROLL_DISTANCE_PX) -> int:
    try:
        parsed = int(round(float(value)))
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))


def _provider_state(value: Any) -> str:
    token = str(value or "unknown").strip().lower().replace(" ", "_")
    if token in _READY_PROVIDER_STATES or token in _RECOVERABLE_PROVIDER_STATES:
        return token
    return "unknown"


def build_scroll_anchor_state(
    *,
    scroll_top_px: Any,
    scroll_height_px: Any,
    client_height_px: Any,
    unread_turn_count: Any = 0,
    threshold_px: Any = DEFAULT_FOLLOW_THRESHOLD_PX,
) -> dict[str, Any]:
    """Classify whether the view follows latest without exposing transcript data."""
    top = _bounded_int(scroll_top_px)
    height = _bounded_int(scroll_height_px)
    viewport = _bounded_int(client_height_px)
    threshold = _bounded_int(threshold_px, maximum=10_000)
    distance = max(0, min(MAX_SCROLL_DISTANCE_PX, height - viewport - top))
    follow_latest = distance <= threshold
    unread = 0 if follow_latest else _bounded_int(unread_turn_count, maximum=10_000_000)
    return {
        "type": "message_scroll_anchor_state",
        "schema_version": SCHEMA_VERSION,
        "status": "following_latest" if follow_latest else "reading_history",
        "follow_latest": follow_latest,
        "distance_from_bottom_px": 0 if follow_latest else distance,
        "preserve_anchor_on_append": not follow_latest,
        "jump_to_latest_visible": not follow_latest,
        "unread_turn_count": unread,
        "content_free": True,
        "contains_message_text": False,
        "contains_response_text": False,
        "private_paths_included": False,
    }


def build_session_switch_continuity(
    *,
    source_draft_saved: bool,
    source_presentation_saved: bool,
    target_draft_restored: bool,
    target_presentation_restored: bool,
    stale_selection_ignored: bool = False,
    accepted_turn_replayed: bool = False,
    provider_contacted: bool = False,
    duplicate_switch_count: Any = 0,
) -> dict[str, Any]:
    """Summarize one content-free session-switch continuity result."""
    duplicate_count = _bounded_int(duplicate_switch_count, maximum=1_000_000)
    continuity_preserved = all((
        source_draft_saved,
        source_presentation_saved,
        target_draft_restored,
        target_presentation_restored,
        not accepted_turn_replayed,
        not provider_contacted,
    ))
    status = "stale_ignored" if stale_selection_ignored and continuity_preserved else ("pass" if continuity_preserved else "blocked")
    return {
        "type": "message_session_switch_continuity",
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "continuity_preserved": continuity_preserved,
        "source_draft_saved": bool(source_draft_saved),
        "source_presentation_saved": bool(source_presentation_saved),
        "target_draft_restored": bool(target_draft_restored),
        "target_presentation_restored": bool(target_presentation_restored),
        "stale_selection_ignored": bool(stale_selection_ignored),
        "duplicate_switch_count": duplicate_count,
        "accepted_turn_replayed": bool(accepted_turn_replayed),
        "provider_contacted": bool(provider_contacted),
        "content_free": True,
        "contains_draft_text": False,
        "contains_conversation_content": False,
    }


def build_provider_outage_transition(
    *,
    previous_state: Any,
    observed_state: Any,
    draft_present: bool = False,
    accepted_operation_pending: bool = False,
    explicit_check: bool = True,
) -> dict[str, Any]:
    """Describe outage/return truth without replaying or sending anything."""
    previous = _provider_state(previous_state)
    observed = _provider_state(observed_state)
    available = observed in _READY_PROVIDER_STATES
    recovered = available and previous in _RECOVERABLE_PROVIDER_STATES
    outage = not available
    if recovered:
        status = "returned"
    elif available:
        status = "ready"
    elif observed == "unknown":
        status = "unknown"
    else:
        status = "outage"
    return {
        "type": "message_provider_outage_transition",
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "previous_state": previous,
        "observed_state": observed,
        "generation_available": available,
        "outage_active": outage,
        "provider_returned": recovered,
        "chat_shell_usable": True,
        "draft_preserved": bool(draft_present),
        "accepted_operation_pending": bool(accepted_operation_pending),
        "explicit_check": bool(explicit_check),
        "explicit_send_required": True,
        "automatic_generation_replay": False,
        "automatic_resend": False,
        "provider_or_model_changed": False,
        "content_free": True,
        "contains_provider_payloads": False,
        "contains_message_text": False,
        "contains_response_text": False,
    }
