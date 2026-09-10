from __future__ import annotations

"""Private, content-free conversation navigation and presentation state.

Navigation records are runtime-only coordination data. They never contain draft text,
transcript fragments, prompts, responses, memories, provider details, diagnostics, or
runtime receipts. Draft text remains solely in the existing private per-session draft
records managed by ``conversation_sessions``.
"""

import hashlib
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import DATA_DIR
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic
from conversation_operations import latest_operation_marker
from conversation_sessions import (
    archive_conversation_session,
    create_conversation_session,
    get_active_conversation_session,
    list_conversation_sessions,
    load_conversation_session,
    new_conversation_session_id,
    rename_conversation_session,
    restore_conversation_session,
    save_conversation_draft,
    select_conversation_session,
)


PRESENTATION_SCHEMA_VERSION = "2"
NAVIGATION_CLIENT_SCHEMA_VERSION = "1"
LIFECYCLE_REQUEST_SCHEMA_VERSION = "1"
CONVERSATION_PRESENTATION_DIR = DATA_DIR / "conversation_sessions" / "presentation"
CONVERSATION_NAVIGATION_CLIENTS_DIR = DATA_DIR / "conversation_sessions" / "navigation_clients"
CONVERSATION_LIFECYCLE_REQUESTS_DIR = DATA_DIR / "conversation_sessions" / "lifecycle_requests"
MAX_SCROLL_FROM_BOTTOM_PX = 1_000_000
_NAVIGATION_LOCK = threading.RLock()
_SESSION_ID_PATTERN = re.compile(r"^conversation_session_[0-9]{8}T[0-9]{6}_[a-f0-9]{10}$")
_NAVIGATION_CLIENT_PATTERN = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$")
_LIFECYCLE_REQUEST_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
_LIFECYCLE_ACTIONS = {"create", "rename", "archive", "restore", "restore_open"}
_UPDATE_STAMP_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")


def _now_utc_precise() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validated_update_stamp(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if len(token) > 32 or not _UPDATE_STAMP_PATTERN.fullmatch(token):
        raise ValueError("Invalid presentation update timestamp.")
    try:
        datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Invalid presentation update timestamp.") from error
    return token


def _validate_session_id(session_id: str) -> str:
    token = str(session_id or "").strip()
    if not _SESSION_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation session identifier.")
    return token


def _validate_navigation_client_id(client_id: str) -> str:
    token = str(client_id or "").strip().lower()
    if not _NAVIGATION_CLIENT_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation navigation client identifier.")
    return token




def _validate_lifecycle_request_key(request_key: str) -> str:
    token = str(request_key or "").strip()
    if not _LIFECYCLE_REQUEST_KEY_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation lifecycle request key.")
    return token


def _lifecycle_request_path(client_id: str, request_key: str) -> Path:
    client_token = _validate_navigation_client_id(client_id)
    request_token = _validate_lifecycle_request_key(request_key)
    digest = hashlib.sha256(f"{client_token}:{request_token}".encode("utf-8")).hexdigest()
    return CONVERSATION_LIFECYCLE_REQUESTS_DIR / f"{digest}.json"


def _validated_generation(value: Any) -> int:
    try:
        generation = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid conversation lifecycle generation.") from error
    if generation < 1:
        raise ValueError("Conversation lifecycle generation must be positive.")
    return generation


def _write_navigation_client(client_id: str, generation: int, selected_session_id: str) -> dict[str, Any]:
    record = {
        "type": "conversation_navigation_client",
        "schema_version": NAVIGATION_CLIENT_SCHEMA_VERSION,
        "client_id": _validate_navigation_client_id(client_id),
        "latest_generation": max(0, int(generation)),
        "selected_session_id": str(selected_session_id or ""),
        "updated_at": _now_utc_precise(),
        "local_private": True,
        "content_free": True,
    }
    _atomic_write(_navigation_client_path(record["client_id"]), record)
    return record


def _load_lifecycle_request(client_id: str, request_key: str) -> dict[str, Any] | None:
    value = _load_json(_lifecycle_request_path(client_id, request_key))
    if not value or value.get("type") != "conversation_lifecycle_request":
        return None
    return dict(value)


def _public_lifecycle_result(value: dict[str, Any], *, duplicate: bool = False) -> dict[str, Any]:
    return {
        "ok": bool(value.get("ok", True)),
        "status": str(value.get("status") or "completed")[:80],
        "action": str(value.get("action") or "")[:40],
        "request_key": str(value.get("request_key") or "")[:96],
        "selection_generation": max(0, int(value.get("selection_generation") or 0)),
        "latest_generation": max(0, int(value.get("latest_generation") or value.get("selection_generation") or 0)),
        "stale_lifecycle_ignored": bool(value.get("stale_lifecycle_ignored")),
        "duplicate_request": bool(duplicate or value.get("duplicate_request")),
        "affected_session_id": str(value.get("affected_session_id") or ""),
        "created_session_id": str(value.get("created_session_id") or ""),
        "fallback_session_id": str(value.get("fallback_session_id") or ""),
        "selected_session_id": str(value.get("selected_session_id") or ""),
        "title": str(value.get("title") or "")[:72],
        "message": str(value.get("message") or "")[:240],
        "changed": bool(value.get("changed")),
        "blocked": bool(value.get("blocked")),
        "local_private": True,
    }


def lifecycle_request_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "content", "text", "message_text", "user_message", "assistant_response", "transcript",
        "prompt", "prompts", "partial", "partial_tokens", "memory", "memories",
        "relationship", "mood", "important_moment", "provider", "model", "endpoint",
        "operation_id", "acceptance_key", "diagnostic", "evidence", "receipt", "credentials",
        "stack_trace", "traceback", "raw_response", "draft", "draft_content",
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


def _presentation_path(session_id: str) -> Path:
    return CONVERSATION_PRESENTATION_DIR / f"{_validate_session_id(session_id)}.json"


def _navigation_client_path(client_id: str) -> Path:
    return CONVERSATION_NAVIGATION_CLIENTS_DIR / f"{_validate_navigation_client_id(client_id)}.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    return load_json_file(path, None, expected_type=dict)


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    write_json_atomic(path, value, expected_type=dict, sort_keys=True)


def _bounded_scroll(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 0
    return max(0, min(MAX_SCROLL_FROM_BOTTOM_PX, parsed))


def _bounded_turn_count(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 0
    return max(0, min(10_000_000, parsed))


def _bounded_anchor_offset(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 0
    return max(-1_000_000, min(1_000_000, parsed))


def _bounded_turn_id(value: str) -> str:
    token = str(value or "").strip()
    if len(token) > 160 or any(ord(char) < 32 for char in token):
        return ""
    return token


def _empty_presentation(session_id: str) -> dict[str, Any]:
    return {
        "type": "conversation_session_presentation",
        "schema_version": PRESENTATION_SCHEMA_VERSION,
        "session_id": session_id,
        "follow_latest": True,
        "scroll_from_bottom_px": 0,
        "view_anchor_turn_id": "",
        "view_anchor_offset_px": 0,
        "last_seen_turn_id": "",
        "last_seen_turn_count": 0,
        "unread_turn_count": 0,
        "composer_intentionally_empty": True,
        "updated_at": "",
        "source": "",
        "local_private": True,
        "content_free": True,
    }


def _session_turn_summary(session_id: str) -> tuple[int, str]:
    session = load_conversation_session(session_id, include_turns=True) or {}
    turns = [turn for turn in session.get("turns", []) if isinstance(turn, dict)]
    return len(turns), str(turns[-1].get("id") or "") if turns else ""


def load_conversation_presentation_state(session_id: str) -> dict[str, Any]:
    """Read one session's bounded presentation state and derive its unread boundary."""
    token = _validate_session_id(session_id)
    value = _load_json(_presentation_path(token)) or _empty_presentation(token)
    if value.get("type") != "conversation_session_presentation" or str(value.get("session_id") or "") != token:
        value = _empty_presentation(token)
    turn_count, latest_turn_id = _session_turn_summary(token)
    follow_latest = bool(value.get("follow_latest", True))
    seen_count = _bounded_turn_count(value.get("last_seen_turn_count"))
    if follow_latest:
        seen_count = turn_count
    else:
        seen_count = min(seen_count, turn_count)
    last_seen_turn_id = _bounded_turn_id(str(value.get("last_seen_turn_id") or ""))
    if follow_latest:
        last_seen_turn_id = latest_turn_id
    return {
        "type": "conversation_session_presentation",
        "schema_version": PRESENTATION_SCHEMA_VERSION,
        "session_id": token,
        "follow_latest": follow_latest,
        "scroll_from_bottom_px": _bounded_scroll(value.get("scroll_from_bottom_px")),
        "view_anchor_turn_id": _bounded_turn_id(str(value.get("view_anchor_turn_id") or "")),
        "view_anchor_offset_px": _bounded_anchor_offset(value.get("view_anchor_offset_px")),
        "last_seen_turn_id": last_seen_turn_id,
        "last_seen_turn_count": seen_count,
        "unread_turn_count": max(0, turn_count - seen_count),
        "turn_count": turn_count,
        "composer_intentionally_empty": bool(value.get("composer_intentionally_empty", True)),
        "updated_at": str(value.get("updated_at") or ""),
        "source": str(value.get("source") or "")[:80],
        "local_private": True,
        "content_free": True,
    }


def save_conversation_presentation_state(
    session_id: str,
    *,
    follow_latest: bool,
    scroll_from_bottom_px: int = 0,
    composer_intentionally_empty: bool,
    client_updated_at: str = "",
    source: str = "dashboard_chat_browser_presentation",
    view_anchor_turn_id: str = "",
    view_anchor_offset_px: int = 0,
    last_seen_turn_id: str = "",
    last_seen_turn_count: int | None = None,
) -> dict[str, Any]:
    """Atomically save content-free reading state with stable turn anchoring."""
    with _NAVIGATION_LOCK:
        token = _validate_session_id(session_id)
        session = load_conversation_session(token, include_turns=True)
        if not session:
            raise ValueError("Conversation session not found.")
        if session.get("status") == "archived":
            raise ValueError("Archived conversation must be restored before presentation state can change.")
        existing = load_conversation_presentation_state(token)
        client_stamp = _validated_update_stamp(client_updated_at)
        existing_stamp = str(existing.get("updated_at") or "")
        if client_stamp and existing_stamp and client_stamp <= existing_stamp:
            result = dict(existing)
            result.update({"changed": False, "stale_update_ignored": True})
            return result
        turns = [turn for turn in session.get("turns", []) if isinstance(turn, dict)]
        turn_count = len(turns)
        latest_turn_id = str(turns[-1].get("id") or "") if turns else ""
        follow = bool(follow_latest)
        requested_seen = existing.get("last_seen_turn_count", 0) if last_seen_turn_count is None else last_seen_turn_count
        seen_count = min(turn_count, _bounded_turn_count(requested_seen))
        seen_id = _bounded_turn_id(last_seen_turn_id)
        if follow:
            seen_count = turn_count
            seen_id = latest_turn_id
        ordering_stamp = client_stamp or _now_utc_precise()
        candidate = {
            "type": "conversation_session_presentation",
            "schema_version": PRESENTATION_SCHEMA_VERSION,
            "session_id": token,
            "follow_latest": follow,
            "scroll_from_bottom_px": 0 if follow else _bounded_scroll(scroll_from_bottom_px),
            "view_anchor_turn_id": "" if follow else _bounded_turn_id(view_anchor_turn_id),
            "view_anchor_offset_px": 0 if follow else _bounded_anchor_offset(view_anchor_offset_px),
            "last_seen_turn_id": seen_id,
            "last_seen_turn_count": seen_count,
            "unread_turn_count": max(0, turn_count - seen_count),
            "turn_count": turn_count,
            "composer_intentionally_empty": bool(composer_intentionally_empty),
            "updated_at": ordering_stamp,
            "source": str(source or "dashboard_chat_browser_presentation")[:80],
            "local_private": True,
            "content_free": True,
        }
        comparison = (
            "follow_latest", "scroll_from_bottom_px", "view_anchor_turn_id", "view_anchor_offset_px",
            "last_seen_turn_id", "last_seen_turn_count", "composer_intentionally_empty",
        )
        unchanged = all(existing.get(key) == candidate.get(key) for key in comparison)
        if unchanged:
            if client_stamp and (not existing_stamp or client_stamp > existing_stamp):
                _atomic_write(_presentation_path(token), candidate)
                existing = candidate
            result = dict(existing)
            result.update({"changed": False, "stale_update_ignored": False})
            return result
        _atomic_write(_presentation_path(token), candidate)
        result = dict(candidate)
        result.update({"changed": True, "stale_update_ignored": False})
        return result


def _load_navigation_client(client_id: str) -> dict[str, Any] | None:
    token = _validate_navigation_client_id(client_id)
    value = _load_json(_navigation_client_path(token))
    if not value or value.get("type") != "conversation_navigation_client":
        return None
    return {
        "type": "conversation_navigation_client",
        "schema_version": NAVIGATION_CLIENT_SCHEMA_VERSION,
        "client_id": token,
        "latest_generation": max(0, int(value.get("latest_generation") or 0)),
        "selected_session_id": str(value.get("selected_session_id") or ""),
        "updated_at": str(value.get("updated_at") or ""),
        "local_private": True,
        "content_free": True,
    }


def switch_conversation_session(
    *,
    source_session_id: str,
    target_session_id: str,
    navigation_client_id: str,
    selection_generation: int,
    source_draft_content: str,
    source_draft_updated_at: str,
    source_draft_base_revision: int | None = None,
    source_draft_editor_id: str = "",
    source_follow_latest: bool = True,
    source_scroll_from_bottom_px: int = 0,
    source_composer_intentionally_empty: bool = True,
    source_presentation_updated_at: str = "",
    source_view_anchor_turn_id: str = "",
    source_view_anchor_offset_px: int = 0,
    source_last_seen_turn_id: str = "",
    source_last_seen_turn_count: int = 0,
) -> dict[str, Any]:
    """Save source state, then select target only if this client generation is newest.

    A delayed stale request may still safely finish its source-session draft/presentation
    writes because those records are session-bound and timestamp guarded. It can never
    move the global active-session pointer after a newer generation has been accepted.
    """
    source_token = _validate_session_id(source_session_id)
    target_token = _validate_session_id(target_session_id)
    client_token = _validate_navigation_client_id(navigation_client_id)
    try:
        generation = int(selection_generation)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid conversation selection generation.") from error
    if generation < 1:
        raise ValueError("Conversation selection generation must be positive.")

    draft_result = save_conversation_draft(
        source_token,
        source_draft_content,
        source="dashboard_chat_navigation_source",
        client_updated_at=str(source_draft_updated_at or "").strip(),
        base_revision=source_draft_base_revision,
        editor_id=str(source_draft_editor_id or ""),
    )
    presentation_result = save_conversation_presentation_state(
        source_token,
        follow_latest=bool(source_follow_latest),
        scroll_from_bottom_px=source_scroll_from_bottom_px,
        composer_intentionally_empty=bool(source_composer_intentionally_empty),
        client_updated_at=str(source_presentation_updated_at or "").strip(),
        source="dashboard_chat_navigation_source",
        view_anchor_turn_id=str(source_view_anchor_turn_id or ""),
        view_anchor_offset_px=int(source_view_anchor_offset_px or 0),
        last_seen_turn_id=str(source_last_seen_turn_id or ""),
        last_seen_turn_count=int(source_last_seen_turn_count or 0),
    )

    with _NAVIGATION_LOCK:
        current = _load_navigation_client(client_token) or {}
        latest_generation = max(0, int(current.get("latest_generation") or 0))
        if generation <= latest_generation:
            return {
                "ok": True,
                "status": "stale_selection_ignored",
                "stale_selection_ignored": True,
                "selection_generation": generation,
                "latest_generation": latest_generation,
                "selected_session_id": str(current.get("selected_session_id") or ""),
                "source_draft": draft_result,
                "source_presentation": presentation_result,
            }
        selected = select_conversation_session(target_token)
        record = {
            "type": "conversation_navigation_client",
            "schema_version": NAVIGATION_CLIENT_SCHEMA_VERSION,
            "client_id": client_token,
            "latest_generation": generation,
            "selected_session_id": target_token,
            "updated_at": _now_utc_precise(),
            "local_private": True,
            "content_free": True,
        }
        _atomic_write(_navigation_client_path(client_token), record)
        return {
            "ok": True,
            "status": "selected",
            "stale_selection_ignored": False,
            "selection_generation": generation,
            "latest_generation": generation,
            "selected_session_id": target_token,
            "selected_session": selected,
            "source_draft": draft_result,
            "source_presentation": presentation_result,
        }



def perform_conversation_lifecycle(
    *,
    action: str,
    navigation_client_id: str,
    lifecycle_generation: int,
    request_key: str,
    source_session_id: str = "",
    target_session_id: str = "",
    title: str = "",
    source_draft_content: str = "",
    source_draft_updated_at: str = "",
    source_draft_base_revision: int | None = None,
    source_draft_editor_id: str = "",
    source_follow_latest: bool = True,
    source_scroll_from_bottom_px: int = 0,
    source_composer_intentionally_empty: bool = True,
    source_presentation_updated_at: str = "",
    source_view_anchor_turn_id: str = "",
    source_view_anchor_offset_px: int = 0,
    source_last_seen_turn_id: str = "",
    source_last_seen_turn_count: int = 0,
) -> dict[str, Any]:
    """Apply one exact, idempotent conversation lifecycle transaction.

    The request record contains only lifecycle coordination fields and an explicitly
    bounded title. Draft text remains solely in the normal private draft record.
    """
    action_token = str(action or "").strip().lower()
    if action_token not in _LIFECYCLE_ACTIONS:
        raise ValueError("Unsupported conversation lifecycle action.")
    client_token = _validate_navigation_client_id(navigation_client_id)
    request_token = _validate_lifecycle_request_key(request_key)
    generation = _validated_generation(lifecycle_generation)
    source_token = _validate_session_id(source_session_id) if source_session_id else ""
    target_token = _validate_session_id(target_session_id) if target_session_id else ""
    if action_token in {"rename", "archive", "restore", "restore_open"} and not target_token:
        raise ValueError("Conversation lifecycle target is required.")

    # Duplicate delivery must be harmless even when the first request archived the
    # source session. Check before trying to save source state, then check again
    # under the mutation lock after the save to close the simultaneous-delivery race.
    with _NAVIGATION_LOCK:
        already_completed = _load_lifecycle_request(client_token, request_token)
        if already_completed:
            return _public_lifecycle_result(already_completed, duplicate=True)

    source_draft_result: dict[str, Any] | None = None
    source_presentation_result: dict[str, Any] | None = None
    # Every explicit lifecycle request saves the currently visible source state first.
    # This keeps a later snapshot from replacing an unsaved composer even when the
    # lifecycle mutation itself does not change selection (for example rename).
    if source_token:
        source_draft_result = save_conversation_draft(
            source_token, source_draft_content, source="dashboard_chat_lifecycle_source",
            client_updated_at=str(source_draft_updated_at or "").strip(),
            base_revision=source_draft_base_revision,
            editor_id=str(source_draft_editor_id or ""),
        )
        source_presentation_result = save_conversation_presentation_state(
            source_token, follow_latest=bool(source_follow_latest),
            scroll_from_bottom_px=source_scroll_from_bottom_px,
            composer_intentionally_empty=bool(source_composer_intentionally_empty),
            client_updated_at=str(source_presentation_updated_at or "").strip(),
            source="dashboard_chat_lifecycle_source",
            view_anchor_turn_id=str(source_view_anchor_turn_id or ""),
            view_anchor_offset_px=int(source_view_anchor_offset_px or 0),
            last_seen_turn_id=str(source_last_seen_turn_id or ""),
            last_seen_turn_count=int(source_last_seen_turn_count or 0),
        )

    with _NAVIGATION_LOCK:
        duplicate = _load_lifecycle_request(client_token, request_token)
        if duplicate:
            result = _public_lifecycle_result(duplicate, duplicate=True)
            if source_draft_result is not None:
                result["source_draft"] = source_draft_result
                result["source_presentation"] = source_presentation_result
            return result

        current = _load_navigation_client(client_token) or {}
        latest_generation = max(0, int(current.get("latest_generation") or 0))
        current_selected = str(current.get("selected_session_id") or "")
        if not current_selected:
            active = get_active_conversation_session(create_if_missing=False) or {}
            current_selected = str(active.get("id") or "")
        if generation <= latest_generation:
            stale = {
                "type": "conversation_lifecycle_request",
                "schema_version": LIFECYCLE_REQUEST_SCHEMA_VERSION,
                "ok": True, "status": "stale_lifecycle_ignored", "action": action_token,
                "request_key": request_token, "navigation_client_id": client_token,
                "selection_generation": generation, "latest_generation": latest_generation,
                "stale_lifecycle_ignored": True, "duplicate_request": False,
                "affected_session_id": target_token, "selected_session_id": current_selected,
                "title": str(title or "")[:72], "message": "A newer conversation choice already won.",
                "changed": False, "blocked": False, "completed_at": _now_utc_precise(),
                "local_private": True, "content_free_except_title": True,
            }
            _atomic_write(_lifecycle_request_path(client_token, request_token), stale)
            result = _public_lifecycle_result(stale)
            if source_draft_result is not None:
                result["source_draft"] = source_draft_result
                result["source_presentation"] = source_presentation_result
            return result

        planned_session_id = new_conversation_session_id() if action_token == "create" else ""
        planned_fallback_id = new_conversation_session_id() if action_token == "archive" else ""
        pending = {
            "type": "conversation_lifecycle_request",
            "schema_version": LIFECYCLE_REQUEST_SCHEMA_VERSION,
            "ok": True, "status": "pending", "action": action_token,
            "request_key": request_token, "navigation_client_id": client_token,
            "selection_generation": generation, "latest_generation": generation,
            "stale_lifecycle_ignored": False, "duplicate_request": False,
            "affected_session_id": target_token, "planned_session_id": planned_session_id,
            "planned_fallback_id": planned_fallback_id, "selected_session_id": current_selected,
            "title": str(title or "")[:72], "started_at": _now_utc_precise(),
            "local_private": True, "content_free_except_title": True,
        }
        _atomic_write(_lifecycle_request_path(client_token, request_token), pending)

        selected_session_id = current_selected
        affected_session_id = target_token
        created_session_id = ""
        fallback_session_id = ""
        changed = False
        blocked = False
        message = "Conversation updated."
        status = "completed"

        if action_token == "create":
            session = create_conversation_session(
                title, source="dashboard_chat_lifecycle_create", session_id=planned_session_id, select_session=True,
            )
            created_session_id = str(session.get("id") or planned_session_id)
            affected_session_id = created_session_id
            selected_session_id = created_session_id
            changed = True
            message = "New conversation created."
        elif action_token == "rename":
            before = load_conversation_session(target_token, include_turns=False) or {}
            session = rename_conversation_session(target_token, title)
            changed = str(before.get("title") or "") != str(session.get("title") or "")
            message = "Conversation renamed." if changed else "Conversation name was already current."
        elif action_token == "archive":
            marker = latest_operation_marker(target_token)
            if marker and str(marker.get("public_state") or "") == "running":
                blocked = True
                status = "blocked_running_operation"
                message = "This conversation is still responding and cannot be archived yet."
            else:
                before = load_conversation_session(target_token, include_turns=False) or {}
                if not before:
                    raise ValueError("Conversation session not found.")
                was_active = current_selected == target_token
                session = archive_conversation_session(target_token)
                changed = str(before.get("status") or "active") != "archived"
                if was_active:
                    remaining = list_conversation_sessions(include_archived=False)
                    if remaining:
                        selected_session_id = str(remaining[0].get("id") or "")
                        select_conversation_session(selected_session_id)
                    else:
                        replacement = create_conversation_session(
                            "", source="dashboard_chat_lifecycle_archive_fallback",
                            session_id=planned_fallback_id, select_session=True,
                        )
                        fallback_session_id = str(replacement.get("id") or planned_fallback_id)
                        selected_session_id = fallback_session_id
                message = "Conversation archived." if changed else "Conversation was already archived."
        elif action_token in {"restore", "restore_open"}:
            before = load_conversation_session(target_token, include_turns=False) or {}
            if not before:
                raise ValueError("Conversation session not found.")
            session = restore_conversation_session(target_token)
            changed = str(before.get("status") or "active") == "archived"
            if action_token == "restore_open":
                select_conversation_session(target_token)
                selected_session_id = target_token
            message = "Conversation restored and opened." if action_token == "restore_open" else "Conversation restored."

        _write_navigation_client(client_token, generation, selected_session_id)
        final = dict(pending)
        final.update({
            "ok": True, "status": status, "latest_generation": generation,
            "affected_session_id": affected_session_id, "created_session_id": created_session_id,
            "fallback_session_id": fallback_session_id, "selected_session_id": selected_session_id,
            "message": message, "changed": changed, "blocked": blocked,
            "completed_at": _now_utc_precise(),
        })
        _atomic_write(_lifecycle_request_path(client_token, request_token), final)
        result = _public_lifecycle_result(final)
        if source_draft_result is not None:
            result["source_draft"] = source_draft_result
            result["source_presentation"] = source_presentation_result
        return result

def presentation_state_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "content", "text", "message", "user_message", "assistant_response", "transcript",
        "prompt", "prompts", "partial", "partial_tokens", "memory", "memories",
        "relationship", "mood", "important_moment", "provider", "model", "endpoint",
        "operation", "operation_id", "acceptance_key", "diagnostic", "evidence",
        "receipt", "credentials", "stack_trace", "traceback", "raw_response",
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
