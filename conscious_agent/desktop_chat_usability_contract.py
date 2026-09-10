from __future__ import annotations
"""Bounded desktop/browser chat usability contracts for v1489 Bundle 11.

The helpers are deliberately content-free. They describe UI state and input
semantics without persisting conversation text or changing operator authority.
"""
from dataclasses import dataclass, asdict
import hashlib, json
from typing import Any, Mapping

MIN_COMPOSER_HEIGHT_PX = 78
MIN_CHAT_WIDTH_PX = 320
SUPPORTED_WINDOWS_SCALING_PERCENT = 100


def composer_key_action(*, keysym: str, shift: bool = False, ime_composing: bool = False) -> str:
    """Return send/newline/noop without performing either action."""
    if ime_composing:
        return "noop"
    if str(keysym or "") != "Return":
        return "noop"
    return "newline" if shift else "send"


def should_focus_composer(*, target: str, disabled: bool = False) -> bool:
    return not disabled and str(target or "") in {"composer", "composer_host", "composer_frame", "message_area"}


@dataclass(frozen=True)
class DesktopChatLayoutProjection:
    width_px: int
    height_px: int
    scaling_percent: int
    composer_visible: bool
    chat_usable: bool
    min_composer_height_px: int = MIN_COMPOSER_HEIGHT_PX
    content_free: bool = True

    def public_summary(self) -> dict[str, Any]:
        row = asdict(self)
        row["projection_digest"] = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return row


def desktop_chat_layout_projection(width_px: int, height_px: int, scaling_percent: int = 100) -> DesktopChatLayoutProjection:
    width = max(0, int(width_px or 0)); height = max(0, int(height_px or 0)); scaling = max(1, int(scaling_percent or 100))
    composer_visible = width >= MIN_CHAT_WIDTH_PX and height >= 360
    usable = composer_visible and scaling <= 200
    return DesktopChatLayoutProjection(width, height, scaling, composer_visible, usable)


def draft_switch_projection(*, source_session_id: str, target_session_id: str, source_saved: bool, target_loaded: bool) -> dict[str, Any]:
    return {
        "source_session_id": str(source_session_id or ""),
        "target_session_id": str(target_session_id or ""),
        "source_draft_preserved": bool(source_saved),
        "target_draft_loaded": bool(target_loaded),
        "safe_to_switch": bool(source_saved and target_loaded),
        "provider_request_required": False,
        "content_free": True,
    }


def reading_position_projection(*, following_latest: bool, unread_turn_count: int, manual_scroll: bool = False) -> dict[str, Any]:
    unread = max(0, int(unread_turn_count or 0))
    following = bool(following_latest and not manual_scroll)
    return {
        "follow_latest": following,
        "manual_scroll_preserved": bool(manual_scroll),
        "jump_to_latest_visible": bool(not following),
        "unread_turn_count": 0 if following else unread,
        "content_free": True,
    }


def assistant_marker_projection(*, accepted: bool, visible_text: bool, terminal: bool, failed: bool = False) -> dict[str, Any]:
    # Empty assistant bubbles are never required merely because a request was accepted.
    show_marker = bool(visible_text or terminal or failed)
    return {
        "accepted": bool(accepted),
        "show_assistant_marker": show_marker,
        "empty_marker_allowed": False,
        "terminal": bool(terminal),
        "failed": bool(failed),
        "content_free": True,
    }
