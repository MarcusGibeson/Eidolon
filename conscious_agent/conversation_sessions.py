from __future__ import annotations

"""Private conversation-session storage and continuity helpers.

Sessions are runtime data. They contain private conversation text and must never be
packaged as source evidence. This module does not call providers, alter model
configuration, execute actions, grant approvals, or enable autonomous behavior.
"""

import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from paths import DATA_DIR
try:
    from json_storage import load_json_file, write_json_atomic
    from persistent_state_index import list_indexed_sessions, rebuild_session_index, select_cross_session_ids, session_summary as indexed_session_summary, update_session_index
    from persistent_state_projection_cache import cached_projection
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from persistent_state_index import (
        list_indexed_sessions, rebuild_session_index, select_cross_session_ids, session_summary as indexed_session_summary, update_session_index,
    )
    from persistent_state_projection_cache import cached_projection
from conversation_action_portal import action_context_summary, portal_update_is_safe, sanitize_action_portal_state
from conversation_control_foundation import (
    RESPONSE_FORMATS,
    RESPONSE_MODES,
    build_conversation_control_foundation,
    default_conversation_control_state,
    normalize_conversation_control_state,
)
from conversation_response_preferences import normalize_response_preferences, response_preference_payload
from temporary_instruction_scope import build_temporary_instruction_record, resolve_temporary_instruction
from conversation_pinned_context import (
    MAX_PINNED_CONTEXT_ITEMS,
    build_pinned_context_record,
    resolve_pinned_context_records,
)
from conversation_offline_degradation import (
    build_offline_operator_intent_record,
    resolve_offline_operator_intent,
)


SESSION_SCHEMA_VERSION = "1"
DRAFT_SCHEMA_VERSION = "2"
CONVERSATION_SESSIONS_DIR = DATA_DIR / "conversation_sessions"
ACTIVE_SESSION_FILE = CONVERSATION_SESSIONS_DIR / "active_session.json"
CONVERSATION_DRAFTS_DIR = CONVERSATION_SESSIONS_DIR / "drafts"
CONVERSATION_DRAFT_CONFLICTS_DIR = CONVERSATION_SESSIONS_DIR / "draft_conflicts"
CONVERSATION_CONTROLS_DIR = CONVERSATION_SESSIONS_DIR / "controls"
LEGACY_DASHBOARD_CHAT_DIR = DATA_DIR / "dashboard_chat"
LEGACY_DASHBOARD_CHAT_IMPORT_FILE = CONVERSATION_SESSIONS_DIR / "legacy_dashboard_chat_import.json"
MAX_CONVERSATION_DRAFT_CHARS = 20_000
MAX_CONVERSATION_SEARCH_QUERY_CHARS = 240
_BRANCH_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
MAX_CONVERSATION_SEARCH_LIMIT = 100
MAX_CONVERSATION_SEARCH_CACHE_ENTRIES = 256
CATALOG_SCHEMA_VERSION = "2"
MAX_CONVERSATION_TRANSCRIPT_WINDOW = 120
_SESSION_LOCK = threading.RLock()
_LEGACY_IMPORT_SIGNATURE_SEEN = ""
_SESSION_SEARCH_CACHE_LOCK = threading.RLock()
_SESSION_SEARCH_CACHE: OrderedDict[str, tuple[tuple[int, int], dict[str, Any]]] = OrderedDict()
_SESSION_ID_PATTERN = re.compile(r"^conversation_session_[0-9]{8}T[0-9]{6}_[a-f0-9]{10}$")
_UPDATE_STAMP_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")
_DRAFT_CONFLICT_ID_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validated_update_stamp(value: str, *, field_name: str = "draft update timestamp") -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if len(token) > 32 or not _UPDATE_STAMP_PATTERN.fullmatch(token):
        raise ValueError(f"Invalid {field_name}.")
    try:
        datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid {field_name}.") from error
    return token


def _now_utc_precise() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _new_session_id() -> str:
    return f"conversation_session_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:10]}"


def new_conversation_session_id() -> str:
    """Return one validated private session identifier without writing runtime state."""
    return _new_session_id()


def _active_project_id() -> str:
    """Resolve the active project lazily so lightweight session imports stay cheap."""
    try:
        from project_manager import get_active_project
        project = get_active_project() or {}
        return str(project.get("id") or "eidolon").strip() or "eidolon"
    except Exception:
        return "eidolon"


def _session_project_id(session: Mapping[str, Any] | None) -> str:
    """Legacy sessions belong to Eidolon unless an exact project binding exists."""
    if isinstance(session, Mapping):
        token = str(session.get("project_id") or "").strip()
        if token:
            return token
    return "eidolon"


def _active_session_pointer() -> dict[str, Any]:
    raw = _load_json(ACTIVE_SESSION_FILE) or {}
    projects = raw.get("projects") if isinstance(raw.get("projects"), dict) else {}
    pointer = dict(raw)
    pointer["projects"] = {str(key): str(value) for key, value in projects.items() if str(key) and str(value)}
    legacy = str(pointer.get("session_id") or "")
    legacy_project = str(pointer.get("project_id") or "eidolon")
    if legacy and legacy_project not in pointer["projects"]:
        pointer["projects"][legacy_project] = legacy
    return pointer


def _write_active_session(session_id: str, project_id: str, *, reason: str = "selected") -> dict[str, Any]:
    token = _validate_session_id(session_id)
    project = str(project_id or "eidolon").strip() or "eidolon"
    now = _now_utc()
    pointer = _active_session_pointer()
    projects = dict(pointer.get("projects") or {})
    projects[project] = token
    payload = {
        "type": "conversation_active_session",
        "schema_version": "2",
        "session_id": token,
        "project_id": project,
        "projects": projects,
        "selected_at": now,
        "reason": str(reason or "selected")[:80],
        "local_private": True,
        "content_free": True,
    }
    _atomic_write(ACTIVE_SESSION_FILE, payload)
    return payload


def _clean_title(value: str, fallback: str = "New conversation") -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return fallback
    return text[:72].rstrip() or fallback


def _title_from_message(message: str) -> str:
    return _clean_title(message, "New conversation")


def _ensure_storage() -> None:
    CONVERSATION_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _validate_session_id(session_id: str) -> str:
    token = str(session_id or "").strip()
    if not _SESSION_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation session identifier.")
    return token


def _session_path(session_id: str) -> Path:
    return CONVERSATION_SESSIONS_DIR / f"{_validate_session_id(session_id)}.json"


def _draft_path(session_id: str) -> Path:
    return CONVERSATION_DRAFTS_DIR / f"{_validate_session_id(session_id)}.json"


def _conversation_controls_path(session_id: str) -> Path:
    return CONVERSATION_CONTROLS_DIR / f"{_validate_session_id(session_id)}.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    return load_json_file(path, None, expected_type=dict)


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    write_json_atomic(path, value, expected_type=dict, sort_keys=True)
    if path.parent == CONVERSATION_SESSIONS_DIR and path.name.startswith('conversation_session_') and value.get('type') == 'conversation_session':
        try:
            update_session_index(CONVERSATION_SESSIONS_DIR, value)
        except Exception:
            # The JSON transcript is canonical. Index repair remains rebuildable and must never block persistence.
            pass






def _conversation_controls_raw(session_id: str) -> dict[str, Any]:
    token = _validate_session_id(session_id)
    raw = _load_json(_conversation_controls_path(token))
    if not raw or raw.get("type") != "conversation_control_state":
        return default_conversation_control_state(token)
    return normalize_conversation_control_state(raw, session_id=token)


def load_conversation_controls(
    session_id: str,
    *,
    include_instruction: bool = False,
    include_pinned_context: bool = False,
) -> dict[str, Any]:
    """Return one session-local control profile without changing session selection."""
    token = _validate_session_id(session_id)
    state = _conversation_controls_raw(token)
    preferences = normalize_response_preferences(state.get("response_preferences"))
    temporary = state.get("temporary_instruction") if isinstance(state.get("temporary_instruction"), dict) else None
    temporary_summary = resolve_temporary_instruction(
        temporary,
        current_message="",
        transition_kind="no_history",
        persisted=True,
    ).public_summary() if temporary else None
    if include_instruction and temporary:
        temporary_summary = dict(temporary_summary or {})
        temporary_summary["instruction"] = str(temporary.get("instruction") or "")
    session = load_conversation_session(token, include_turns=True) or {}
    turns = [turn for turn in session.get("turns", []) if isinstance(turn, dict)]
    latest_message = ""
    for turn in reversed(turns):
        latest_message = str(turn.get("user_message") or "").strip()
        if latest_message:
            break
    pin_resolutions = resolve_pinned_context_records(
        state.get("pinned_context", []) if isinstance(state.get("pinned_context"), list) else [],
        current_message=latest_message,
        transition_kind="continuation" if latest_message else "no_history",
        short_follow_up=False,
    )
    pinned_summaries = [item.public_summary(include_content=include_pinned_context) for item in pin_resolutions]
    draft = load_conversation_draft(token)
    queued = state.get("queued_operator_intent") if isinstance(state.get("queued_operator_intent"), dict) else None
    target_id = str((queued or {}).get("target_turn_id") or "")
    target_exists = not target_id or any(str(turn.get("id") or "") == target_id for turn in turns)
    queued_summary = resolve_offline_operator_intent(
        queued,
        current_draft_revision=int(draft.get("revision") or 0),
        current_draft_digest=str(draft.get("content_digest") or ""),
        target_turn_exists=target_exists,
    ).public_summary()
    return {
        "ok": True,
        "session_id": token,
        "revision": int(state.get("revision") or 0),
        "updated_at": str(state.get("updated_at") or ""),
        "response_preferences": preferences.public_summary(),
        "temporary_instruction": temporary_summary,
        "pinned_context": pinned_summaries,
        "pinned_context_count": len(pinned_summaries),
        "queued_operator_intent": queued_summary,
        "retry_policy": str(state.get("retry_policy") or "safe_transient_only"),
        "branch_policy": str(state.get("branch_policy") or "preserve_original"),
        "foundation": build_conversation_control_foundation(),
        "provider_invoked": False,
        "receipts_included": False,
    }


def conversation_controls_for_prompt(session_id: str) -> dict[str, Any]:
    """Return private runtime controls for prompt assembly only."""
    return _conversation_controls_raw(session_id)


def _assert_controls_revision(state: dict[str, Any], expected_revision: int | None) -> None:
    if expected_revision is None:
        return
    if int(expected_revision) != int(state.get("revision") or 0):
        raise ValueError("Conversation controls changed in another tab. Reload before updating them.")


def update_conversation_response_preferences(
    session_id: str,
    *,
    mode: str,
    format: str = "default",
    expected_revision: int | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """Persist one explicit session-local response preference update."""
    token = _validate_session_id(session_id)
    if not load_conversation_session(token, include_turns=False):
        raise ValueError("Conversation session not found.")
    mode_token = str(mode or "").strip().lower()
    format_token = str(format or "").strip().lower()
    if mode_token not in RESPONSE_MODES:
        raise ValueError("Unsupported conversation response mode.")
    if format_token not in RESPONSE_FORMATS:
        raise ValueError("Unsupported conversation response format.")
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        now = _now_utc_precise()
        next_revision = int(state.get("revision") or 0) + 1
        state["revision"] = next_revision
        state["updated_at"] = now
        state["response_preferences"] = response_preference_payload(
            mode=mode_token,
            format=format_token,
            revision=next_revision,
            updated_at=now,
            source=source,
        )
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True)


def set_conversation_temporary_instruction(
    session_id: str,
    *,
    instruction: str,
    scope: str,
    expected_revision: int | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """Persist a topic/session instruction. Current-turn instructions travel with a send request."""
    token = _validate_session_id(session_id)
    session = load_conversation_session(token, include_turns=True)
    if not session:
        raise ValueError("Conversation session not found.")
    if str(scope or "").strip().lower() == "current_turn":
        raise ValueError("Current-turn instructions must be attached to the exact send request and are never persisted.")
    turns = [turn for turn in session.get("turns", []) if isinstance(turn, dict)]
    anchor = ""
    for turn in reversed(turns):
        anchor = str(turn.get("user_message") or "").strip()
        if anchor:
            break
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        now = _now_utc_precise()
        next_revision = int(state.get("revision") or 0) + 1
        state["revision"] = next_revision
        state["updated_at"] = now
        state["temporary_instruction"] = build_temporary_instruction_record(
            instruction,
            scope=scope,
            revision=next_revision,
            updated_at=now,
            source=source,
            topic_anchor_text=anchor,
        )
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True)


def clear_conversation_temporary_instruction(
    session_id: str,
    *,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    token = _validate_session_id(session_id)
    if not load_conversation_session(token, include_turns=False):
        raise ValueError("Conversation session not found.")
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        if state.get("temporary_instruction") is None:
            return load_conversation_controls(token, include_instruction=True)
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = _now_utc_precise()
        state["temporary_instruction"] = None
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True)


def add_conversation_pinned_context(
    session_id: str,
    *,
    content: str,
    kind: str,
    scope: str,
    expires_at: str = "",
    expected_revision: int | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """Persist one explicit bounded working-context item for this conversation."""
    token = _validate_session_id(session_id)
    session = load_conversation_session(token, include_turns=True)
    if not session:
        raise ValueError("Conversation session not found.")
    anchor = ""
    for turn in reversed([row for row in session.get("turns", []) if isinstance(row, dict)]):
        anchor = str(turn.get("user_message") or "").strip()
        if anchor:
            break
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        pins = [dict(item) for item in state.get("pinned_context", []) if isinstance(item, dict)]
        if len(pins) >= MAX_PINNED_CONTEXT_ITEMS:
            raise ValueError(f"A conversation may have at most {MAX_PINNED_CONTEXT_ITEMS} pinned context items.")
        now = _now_utc_precise()
        next_revision = int(state.get("revision") or 0) + 1
        pins.append(build_pinned_context_record(
            content, kind=kind, scope=scope, revision=next_revision, updated_at=now,
            expires_at=expires_at, source=source, topic_anchor_text=anchor,
        ))
        state["revision"] = next_revision
        state["updated_at"] = now
        state["pinned_context"] = pins
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)


def remove_conversation_pinned_context(
    session_id: str,
    *,
    item_id: str,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    token = _validate_session_id(session_id)
    if not load_conversation_session(token, include_turns=False):
        raise ValueError("Conversation session not found.")
    item_token = str(item_id or "").strip().lower()
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        pins = [dict(item) for item in state.get("pinned_context", []) if isinstance(item, dict)]
        retained = [item for item in pins if str(item.get("id") or "").lower() != item_token]
        if len(retained) == len(pins):
            return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = _now_utc_precise()
        state["pinned_context"] = retained
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)


def clear_conversation_pinned_context(
    session_id: str,
    *,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    token = _validate_session_id(session_id)
    if not load_conversation_session(token, include_turns=False):
        raise ValueError("Conversation session not found.")
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        if not state.get("pinned_context"):
            return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = _now_utc_precise()
        state["pinned_context"] = []
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)


def queue_conversation_operator_intent(
    session_id: str,
    *,
    kind: str,
    target_turn_id: str = "",
    expected_revision: int | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """Queue one content-free operator intent for later explicit review; never execute it."""
    token = _validate_session_id(session_id)
    session = load_conversation_session(token, include_turns=True)
    if not session:
        raise ValueError("Conversation session not found.")
    turns = [turn for turn in session.get("turns", []) if isinstance(turn, dict)]
    target = str(target_turn_id or "").strip()
    if target and not any(str(turn.get("id") or "") == target for turn in turns):
        raise ValueError("Conversation turn not found.")
    draft = load_conversation_draft(token)
    if str(kind or "").strip().lower() in {"send_current_draft", "open_branch_draft"} and not str(draft.get("content") or "").strip():
        raise ValueError("This offline intent requires a saved draft.")
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        now = _now_utc_precise()
        next_revision = int(state.get("revision") or 0) + 1
        state["revision"] = next_revision
        state["updated_at"] = now
        state["queued_operator_intent"] = build_offline_operator_intent_record(
            kind=kind, revision=next_revision, updated_at=now, target_turn_id=target,
            draft_revision=int(draft.get("revision") or 0),
            draft_content_digest=str(draft.get("content_digest") or ""), source=source,
        )
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)


def clear_conversation_operator_intent(
    session_id: str,
    *,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    token = _validate_session_id(session_id)
    if not load_conversation_session(token, include_turns=False):
        raise ValueError("Conversation session not found.")
    with _SESSION_LOCK:
        state = _conversation_controls_raw(token)
        _assert_controls_revision(state, expected_revision)
        if state.get("queued_operator_intent") is None:
            return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)
        state["revision"] = int(state.get("revision") or 0) + 1
        state["updated_at"] = _now_utc_precise()
        state["queued_operator_intent"] = None
        _atomic_write(_conversation_controls_path(token), state)
    return load_conversation_controls(token, include_instruction=True, include_pinned_context=True)


def _draft_content_digest(content: str) -> str:
    return hashlib.sha256(str(content or "").encode("utf-8")).hexdigest()


def _draft_editor_id(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return "unknown-local-editor"
    if len(token) > 160 or any(ord(char) < 32 for char in token):
        raise ValueError("Invalid conversation draft editor identifier.")
    return token


def _draft_conflict_path(session_id: str, conflict_id: str) -> Path:
    token = _validate_session_id(session_id)
    marker = str(conflict_id or "").strip().lower()
    if not _DRAFT_CONFLICT_ID_PATTERN.fullmatch(marker):
        raise ValueError("Invalid conversation draft conflict identifier.")
    return CONVERSATION_DRAFT_CONFLICTS_DIR / token / f"{marker}.json"


def _draft_conflict_id(
    session_id: str, *, base_revision: int, current_digest: str, incoming_digest: str, editor_id: str,
) -> str:
    material = f"{session_id}:{base_revision}:{current_digest}:{incoming_digest}:{editor_id}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _safe_turn_diagnostic(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Persist only bounded public diagnostics, never raw provider bodies or secrets."""
    raw = value if isinstance(value, Mapping) else {}
    endpoint = str(raw.get("endpoint") or "").strip()
    safe_endpoint = ""
    try:
        parsed = urlparse(endpoint)
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            host = parsed.hostname
            host_text = f"[{host}]" if ":" in host and not host.startswith("[") else host
            netloc = f"{host_text}:{parsed.port}" if parsed.port is not None else host_text
            safe_endpoint = f"{parsed.scheme.lower()}://{netloc}{parsed.path.rstrip('/')}"[:200]
    except (TypeError, ValueError):
        safe_endpoint = ""
    details = raw.get("details") if isinstance(raw.get("details"), Mapping) else {}
    evidence = {
        key: item
        for key, item in details.items()
        if key in {"failure_kind", "exception_type", "yielded_content", "stream_supported"}
        and isinstance(item, (str, int, float, bool, type(None)))
    }
    status_code = raw.get("status_code")
    return {
        "technical_category": str(raw.get("code") or "")[:80],
        "provider": str(raw.get("provider") or "")[:40],
        "model": str(raw.get("model") or "")[:160],
        "endpoint": safe_endpoint,
        "retryable": bool(raw.get("retryable")),
        "status_code": status_code if isinstance(status_code, int) else None,
        "evidence": evidence,
        "redacted": True,
    }

def _empty_draft(session_id: str) -> dict[str, Any]:
    return {
        "type": "conversation_session_draft",
        "schema_version": DRAFT_SCHEMA_VERSION,
        "session_id": session_id,
        "content": "",
        "content_digest": _draft_content_digest(""),
        "revision": 0,
        "editor_id": "",
        "updated_at": "",
        "cleared_at": "",
        "source": "",
    }


def load_conversation_draft(session_id: str) -> dict[str, Any]:
    """Load one private per-session draft without changing session selection."""
    token = _validate_session_id(session_id)
    draft = _load_json(_draft_path(token)) or _empty_draft(token)
    if draft.get("type") != "conversation_session_draft" or str(draft.get("session_id") or "") != token:
        return _empty_draft(token)
    content = str(draft.get("content") or "")[:MAX_CONVERSATION_DRAFT_CHARS]
    return {
        "type": "conversation_session_draft",
        "schema_version": DRAFT_SCHEMA_VERSION,
        "session_id": token,
        "content": content,
        "content_digest": str(draft.get("content_digest") or _draft_content_digest(content)),
        "revision": max(0, int(draft.get("revision") or 0)),
        "editor_id": str(draft.get("editor_id") or "")[:160],
        "updated_at": str(draft.get("updated_at") or ""),
        "cleared_at": str(draft.get("cleared_at") or ""),
        "source": str(draft.get("source") or "")[:80],
    }


def save_conversation_draft(
    session_id: str,
    content: str,
    *,
    source: str = "dashboard_chat_console",
    client_updated_at: str = "",
    base_revision: int | None = None,
    editor_id: str = "",
) -> dict[str, Any]:
    """Atomically save one bounded private draft with divergent-edit preservation."""
    with _SESSION_LOCK:
        token = _validate_session_id(session_id)
        session = load_conversation_session(token, include_turns=False)
        if not session:
            raise ValueError("Conversation session not found.")
        if session.get("status") == "archived":
            raise ValueError("Archived conversation must be restored before its draft can be edited.")
        text = str(content or "")
        if len(text) > MAX_CONVERSATION_DRAFT_CHARS:
            raise ValueError(f"Conversation draft exceeds {MAX_CONVERSATION_DRAFT_CHARS} characters.")
        existing = load_conversation_draft(token)
        client_stamp = _validated_update_stamp(client_updated_at)
        existing_stamp = str(existing.get("updated_at") or "")
        existing_revision = max(0, int(existing.get("revision") or 0))
        incoming_base = existing_revision if base_revision is None else int(base_revision)
        if incoming_base < 0:
            raise ValueError("Conversation draft base revision cannot be negative.")
        if incoming_base > existing_revision:
            raise ValueError("Conversation draft base revision is newer than persisted state.")
        editor = _draft_editor_id(editor_id)
        incoming_digest = _draft_content_digest(text)
        existing_digest = str(existing.get("content_digest") or _draft_content_digest(str(existing.get("content") or "")))
        if base_revision is None and client_stamp and existing_stamp and client_stamp <= existing_stamp and incoming_digest != existing_digest:
            result = dict(existing)
            result.update({
                "changed": False, "stale_update_ignored": True,
                "has_draft": bool(existing.get("content")), "draft_conflict": False,
            })
            return result
        if incoming_base < existing_revision and incoming_digest != existing_digest:
            conflict_id = _draft_conflict_id(
                token, base_revision=incoming_base, current_digest=existing_digest,
                incoming_digest=incoming_digest, editor_id=editor,
            )
            conflict_path = _draft_conflict_path(token, conflict_id)
            conflict = _load_json(conflict_path) or {
                "type": "conversation_draft_conflict",
                "schema_version": "1",
                "conflict_id": conflict_id,
                "session_id": token,
                "base_revision": incoming_base,
                "current_revision": existing_revision,
                "current_content": str(existing.get("content") or ""),
                "current_digest": existing_digest,
                "incoming_content": text,
                "incoming_digest": incoming_digest,
                "incoming_editor_id": editor,
                "created_at": _now_utc_precise(),
                "resolved_at": "",
                "resolution": "",
                "local_private": True,
            }
            _atomic_write(conflict_path, conflict)
            result = dict(existing)
            result.update({
                "changed": False, "stale_update_ignored": False, "has_draft": bool(existing.get("content")),
                "draft_conflict": True,
                "conflict": {
                    "conflict_id": conflict_id, "base_revision": incoming_base,
                    "current_revision": existing_revision,
                    "current_content": str(existing.get("content") or ""),
                    "incoming_content": text, "incoming_editor_id": editor,
                    "created_at": str(conflict.get("created_at") or ""),
                    "automatic_resolution": False,
                },
            })
            return result
        if client_stamp and existing_stamp and client_stamp <= existing_stamp and incoming_digest == existing_digest:
            result = dict(existing)
            result.update({"changed": False, "stale_update_ignored": True, "has_draft": bool(existing.get("content")), "draft_conflict": False})
            return result
        if incoming_digest == existing_digest:
            if client_stamp and (not existing_stamp or client_stamp > existing_stamp):
                refreshed = dict(existing)
                refreshed["updated_at"] = client_stamp
                if not text:
                    refreshed["cleared_at"] = client_stamp
                refreshed["source"] = str(source or "dashboard_chat_console")[:80]
                refreshed["editor_id"] = editor
                refreshed["schema_version"] = DRAFT_SCHEMA_VERSION
                _atomic_write(_draft_path(token), refreshed)
                existing = refreshed
            result = dict(existing)
            result.update({"changed": False, "stale_update_ignored": False, "has_draft": bool(text), "draft_conflict": False})
            return result
        ordering_stamp = client_stamp or _now_utc_precise()
        draft = {
            "type": "conversation_session_draft", "schema_version": DRAFT_SCHEMA_VERSION,
            "session_id": token, "content": text, "content_digest": incoming_digest,
            "revision": existing_revision + 1, "editor_id": editor, "updated_at": ordering_stamp,
            "cleared_at": "" if text else ordering_stamp,
            "source": str(source or "dashboard_chat_console")[:80],
        }
        _atomic_write(_draft_path(token), draft)
        result = dict(draft)
        result.update({"changed": True, "stale_update_ignored": False, "has_draft": bool(text), "draft_conflict": False})
        return result


def load_conversation_draft_conflict(session_id: str, conflict_id: str) -> dict[str, Any] | None:
    value = _load_json(_draft_conflict_path(session_id, conflict_id))
    if not value or value.get("type") != "conversation_draft_conflict":
        return None
    return dict(value)


def resolve_conversation_draft_conflict(
    session_id: str, conflict_id: str, *, choice: str, expected_revision: int, editor_id: str = "",
) -> dict[str, Any]:
    """Resolve one preserved conflict only by explicit operator choice."""
    with _SESSION_LOCK:
        token = _validate_session_id(session_id)
        conflict = load_conversation_draft_conflict(token, conflict_id)
        if not conflict:
            raise ValueError("Conversation draft conflict not found.")
        if conflict.get("resolved_at"):
            draft = load_conversation_draft(token)
            return {"ok": True, "duplicate_resolution": True, "resolution": conflict.get("resolution"), "draft": draft}
        current = load_conversation_draft(token)
        current_revision = max(0, int(current.get("revision") or 0))
        if int(expected_revision) != current_revision:
            raise ValueError("Conversation draft changed after the conflict was shown.")
        choice_token = str(choice or "").strip().lower()
        if choice_token not in {"current", "incoming"}:
            raise ValueError("Draft conflict choice must be current or incoming.")
        resolved_draft = current
        if choice_token == "incoming":
            resolved_draft = save_conversation_draft(
                token, str(conflict.get("incoming_content") or ""),
                source="dashboard_chat_draft_conflict_resolution", client_updated_at=_now_utc_precise(),
                base_revision=current_revision, editor_id=editor_id or str(conflict.get("incoming_editor_id") or ""),
            )
        conflict["resolved_at"] = _now_utc_precise()
        conflict["resolution"] = choice_token
        conflict["resolved_revision"] = max(0, int(resolved_draft.get("revision") or current_revision))
        conflict["resolved_editor_id"] = _draft_editor_id(editor_id)
        _atomic_write(_draft_conflict_path(token, conflict_id), conflict)
        return {
            "ok": True, "duplicate_resolution": False, "resolution": choice_token,
            "conflict_id": str(conflict_id), "draft": resolved_draft,
        }


def clear_conversation_draft(
    session_id: str,
    *,
    source: str = "conversation_runtime_acceptance",
) -> dict[str, Any]:
    """Write an empty draft tombstone so stale browser backups cannot resurrect sent text."""
    with _SESSION_LOCK:
        token = _validate_session_id(session_id)
        session = load_conversation_session(token, include_turns=False)
        if not session:
            raise ValueError("Conversation session not found.")
        server_now = _now_utc_precise()
        existing = load_conversation_draft(token)
        existing_stamp = str(existing.get("updated_at") or "")
        ordering_stamp = max(server_now, existing_stamp)
        draft = {
            "type": "conversation_session_draft",
            "schema_version": DRAFT_SCHEMA_VERSION,
            "session_id": token,
            "content": "",
            "content_digest": _draft_content_digest(""),
            "revision": max(0, int(existing.get("revision") or 0)) + 1,
            "editor_id": "conversation-runtime",
            "updated_at": ordering_stamp,
            "cleared_at": ordering_stamp,
            "source": str(source or "conversation_runtime_acceptance")[:80],
        }
        _atomic_write(_draft_path(token), draft)
        result = dict(draft)
        result.update({"changed": True, "stale_update_ignored": False, "has_draft": False})
        return result


def _public_session(session: dict[str, Any], *, include_turns: bool = False) -> dict[str, Any]:
    result = {key: value for key, value in session.items() if key != "turns"}
    if include_turns:
        result["turns"] = [dict(turn) for turn in session.get("turns", []) if isinstance(turn, dict)]
    return result


def create_conversation_session(
    title: str = "",
    *,
    source: str = "conversation_runtime",
    session_id: str = "",
    select_session: bool = True,
    project_id: str = "",
) -> dict[str, Any]:
    """Create one private conversation session, optionally with a preallocated identifier.

    A preallocated identifier makes an operator-visible lifecycle request idempotent: the
    same accepted request can safely ensure the same session exists after duplicate POST
    delivery without creating another conversation.
    """
    with _SESSION_LOCK:
        _ensure_storage()
        now = _now_utc()
        session_id = _validate_session_id(session_id) if session_id else _new_session_id()
        bound_project_id = str(project_id or _active_project_id()).strip() or "eidolon"
        existing = load_conversation_session(session_id, include_turns=True)
        if existing:
            if _session_project_id(existing) != bound_project_id:
                raise ValueError("Conversation session is bound to a different project.")
            if select_session and existing.get("status") != "archived":
                _write_active_session(session_id, bound_project_id, reason="existing_session_selected")
            return _public_session(existing, include_turns=True)
        session = {
            "id": session_id,
            "type": "conversation_session",
            "schema_version": SESSION_SCHEMA_VERSION,
            "project_id": bound_project_id,
            "title": _clean_title(title),
            "title_is_default": not bool(str(title or "").strip()),
            "created_at": now,
            "updated_at": now,
            "last_turn_at": "",
            "turn_count": 0,
            "completed_turn_count": 0,
            "status": "active",
            "source": str(source or "conversation_runtime")[:80],
            "last_provider": "",
            "last_model": "",
            "turns": [],
        }
        _atomic_write(_session_path(session_id), session)
        if select_session:
            _write_active_session(session_id, bound_project_id, reason="session_created")
        return _public_session(session, include_turns=True)


def _validate_branch_request_id(branch_request_id: str) -> str:
    token = str(branch_request_id or "").strip()
    if not _BRANCH_REQUEST_ID_PATTERN.fullmatch(token):
        raise ValueError("A valid explicit branch request identifier is required.")
    return token


def _branch_session_id(source_session_id: str, source_turn_id: str, branch_request_id: str, created_at: str) -> str:
    digits = re.sub(r"[^0-9]", "", str(created_at or ""))[:14]
    if len(digits) != 14:
        digits = "19700101000000"
    digest = hashlib.sha256(
        f"{source_session_id}\0{source_turn_id}\0{branch_request_id}".encode("utf-8")
    ).hexdigest()[:10]
    return f"conversation_session_{digits[:8]}T{digits[8:]}_{digest}"


def create_conversation_branch_from_turn(
    source_session_id: str,
    source_turn_id: str,
    edited_user_message: str,
    *,
    branch_request_id: str,
    title: str = "",
    select_session: bool = True,
) -> dict[str, Any]:
    """Create a new session from the prefix before one edited user turn.

    The source session and every source turn remain untouched.  The edited message
    is saved only as a private draft in the new branch; a fresh explicit send is
    required before provider work can begin.
    """
    with _SESSION_LOCK:
        source_token = _validate_session_id(source_session_id)
        source = load_conversation_session(source_token, include_turns=True)
        if not source:
            raise ValueError("Source conversation session not found.")
        if source.get("status") == "archived":
            raise ValueError("Archived conversations must be restored before branching.")
        edited = str(edited_user_message or "").strip()
        if not edited:
            raise ValueError("Edited user message cannot be empty.")
        if len(edited) > MAX_CONVERSATION_DRAFT_CHARS:
            raise ValueError(f"Edited user message exceeds {MAX_CONVERSATION_DRAFT_CHARS} characters.")
        turns = [dict(turn) for turn in source.get("turns", []) if isinstance(turn, dict)]
        source_index = next(
            (index for index, turn in enumerate(turns) if str(turn.get("id") or "") == str(source_turn_id or "").strip()),
            None,
        )
        if source_index is None:
            raise ValueError("Source conversation turn not found.")
        source_turn = turns[source_index]
        if not str(source_turn.get("user_message") or "").strip():
            raise ValueError("Only a turn with a user message can be edited into a branch.")
        request_token = _validate_branch_request_id(branch_request_id)
        request_digest = hashlib.sha256(request_token.encode("utf-8")).hexdigest()
        edited_digest = _draft_content_digest(edited)
        branch_token = _branch_session_id(
            source_token,
            str(source_turn_id or "").strip(),
            request_token,
            str(source.get("created_at") or source_turn.get("created_at") or ""),
        )
        existing_branch = load_conversation_session(branch_token, include_turns=True)
        existing_meta = dict((existing_branch or {}).get("branch") or {})
        if existing_meta:
            expected = (
                str(existing_meta.get("source_session_id") or "") == source_token
                and str(existing_meta.get("source_turn_id") or "") == str(source_turn_id or "").strip()
                and str(existing_meta.get("branch_request_digest") or "") == request_digest
                and str(existing_meta.get("edited_message_digest") or "") == edited_digest
            )
            if not expected:
                raise ValueError("Branch request identifier conflicts with an existing branch.")
            draft = load_conversation_draft(branch_token)
            if not draft or _draft_content_digest(str(draft.get("content") or "")) != edited_digest:
                draft = save_conversation_draft(
                    branch_token, edited, source="conversation_message_branching",
                    base_revision=int((draft or {}).get("revision") or 0), editor_id="message-branching",
                )
            if select_session:
                _write_active_session(branch_token, _session_project_id(existing_branch), reason="message_edit_branch_reconciled")
            public = _public_session(existing_branch, include_turns=True)
            public["draft"] = draft
            return public

        branch_title = _clean_title(title, f"Branch of {str(source.get('title') or 'conversation')}")
        branch = create_conversation_session(
            branch_title,
            source="conversation_message_branching",
            session_id=branch_token,
            select_session=False,
            project_id=_session_project_id(source),
        )
        now = _now_utc()
        copied_turns: list[dict[str, Any]] = []
        for index, turn in enumerate(turns[:source_index]):
            copied = dict(turn)
            copied["id"] = f"branch_copy_{uuid.uuid4().hex[:20]}"
            copied["branch_copy_of"] = str(turn.get("id") or "")[:100]
            copied["branch_source_session_id"] = source_token
            copied["branch_copy_index"] = index
            copied["source"] = "conversation_message_branching"
            copied_turns.append(copied)
        branch_record = load_conversation_session(branch_token, include_turns=True) or {}
        branch_record["title_is_default"] = False
        branch_record["turns"] = copied_turns
        branch_record["turn_count"] = len(copied_turns)
        branch_record["completed_turn_count"] = sum(
            1 for turn in copied_turns
            if turn.get("success") is True and str(turn.get("completion_state") or "") == "completed"
        )
        branch_record["last_turn_at"] = str((copied_turns[-1] if copied_turns else {}).get("created_at") or "")
        branch_record["updated_at"] = now
        branch_record["branch"] = {
            "schema_version": "1",
            "source_session_id": source_token,
            "source_turn_id": str(source_turn_id or "")[:100],
            "source_turn_index": int(source_index),
            "source_turns_copied": len(copied_turns),
            "edited_message_digest": edited_digest,
            "branch_request_digest": request_digest,
            "created_at": now,
            "original_session_preserved": True,
            "original_turn_preserved": True,
            "raw_transcript_rewritten": False,
            "message_submitted": False,
            "provider_invoked": False,
        }
        _atomic_write(_session_path(branch_token), branch_record)
        draft = save_conversation_draft(
            branch_token,
            edited,
            source="conversation_message_branching",
            base_revision=0,
            editor_id="message-branching",
        )
        if select_session:
            _write_active_session(branch_token, _session_project_id(branch_record), reason="message_edit_branch")
        public = _public_session(branch_record, include_turns=True)
        public["draft"] = draft
        return public


def load_conversation_session(session_id: str, *, include_turns: bool = True) -> dict[str, Any] | None:
    try:
        path = _session_path(session_id)
    except ValueError:
        return None
    session = _load_json(path)
    if not session or session.get("type") != "conversation_session":
        return None
    return _public_session(session, include_turns=include_turns)


def list_conversation_sessions(*, include_archived: bool = False, project_id: str | None = None) -> list[dict[str, Any]]:
    """List lightweight session metadata without reparsing every transcript."""
    with _SESSION_LOCK:
        if not CONVERSATION_SESSIONS_DIR.exists():
            return []
        try:
            return cached_projection(
                CONVERSATION_SESSIONS_DIR,
                "session",
                ("list", bool(include_archived), str(project_id or "") if project_id is not None else None),
                lambda: list_indexed_sessions(
                    CONVERSATION_SESSIONS_DIR, include_archived=include_archived, project_id=project_id,
                ),
            )
        except Exception:
            sessions: list[dict[str, Any]] = []
            for path in CONVERSATION_SESSIONS_DIR.glob("conversation_session_*.json"):
                session = _load_json(path)
                if not session or session.get("type") != "conversation_session":
                    continue
                if not include_archived and session.get("status") == "archived":
                    continue
                if project_id is not None and _session_project_id(session) != str(project_id or "eidolon"):
                    continue
                sessions.append(_public_session(session, include_turns=False))
            return sorted(sessions, key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)


def bounded_cross_session_candidates(
    user_message: str, *, session_id: str = "", project_id: str | None = None, limit: int = 6,
) -> list[dict[str, Any]]:
    """Load only a bounded set of likely relevant transcripts for prompt continuity."""
    with _SESSION_LOCK:
        try:
            ids = cached_projection(
                CONVERSATION_SESSIONS_DIR,
                "session",
                ("cross", str(user_message or "").casefold()[:240], str(session_id or ""), str(project_id or ""), int(limit)),
                lambda: select_cross_session_ids(
                    CONVERSATION_SESSIONS_DIR, user_message, exclude_session_id=session_id, project_id=project_id, limit=limit,
                ),
                ttl_seconds=20.0,
            )
        except Exception:
            ids = [
                str(row.get("id") or "") for row in list_conversation_sessions(include_archived=False, project_id=project_id)
                if str(row.get("id") or "") != str(session_id or "")
            ][: max(0, int(limit))]
        rows: list[dict[str, Any]] = []
        for candidate_id in ids:
            loaded = load_conversation_session(candidate_id, include_turns=True)
            if loaded:
                rows.append(loaded)
        return rows


def conversation_session_summary(session_id: str) -> dict[str, Any] | None:
    """Return the private bounded persistent summary used by the v1252 index."""
    with _SESSION_LOCK:
        try:
            return indexed_session_summary(CONVERSATION_SESSIONS_DIR, session_id)
        except Exception:
            return None


def rename_conversation_session(session_id: str, title: str) -> dict[str, Any]:
    """Rename one session without changing its identifier, turns, or provider state."""
    with _SESSION_LOCK:
        session = load_conversation_session(session_id, include_turns=True)
        if not session:
            raise ValueError("Conversation session not found.")
        cleaned = _clean_title(title, "")
        if not cleaned:
            raise ValueError("Conversation title cannot be blank.")
        if session.get("title") == cleaned and not session.get("title_is_default"):
            return _public_session(session, include_turns=False)
        session["title"] = cleaned
        session["title_is_default"] = False
        session["updated_at"] = _now_utc()
        _atomic_write(_session_path(session_id), session)
        return _public_session(session, include_turns=False)


def archive_conversation_session(session_id: str) -> dict[str, Any]:
    """Archive a session without deleting history or selecting a replacement implicitly."""
    with _SESSION_LOCK:
        session = load_conversation_session(session_id, include_turns=True)
        if not session:
            raise ValueError("Conversation session not found.")
        if session.get("status") == "archived":
            return _public_session(session, include_turns=False)
        now = _now_utc()
        session["status"] = "archived"
        session["archived_at"] = now
        session["updated_at"] = now
        _atomic_write(_session_path(session_id), session)
        pointer = _active_session_pointer()
        project_id = _session_project_id(session)
        projects = dict(pointer.get("projects") or {})
        if projects.get(project_id) == session_id:
            projects.pop(project_id, None)
            if projects:
                fallback_project, fallback_session = next(iter(projects.items()))
                pointer.update({"session_id": fallback_session, "project_id": fallback_project, "projects": projects, "selected_at": now})
                _atomic_write(ACTIVE_SESSION_FILE, pointer)
            else:
                ACTIVE_SESSION_FILE.unlink(missing_ok=True)
        return _public_session(session, include_turns=False)


def restore_conversation_session(session_id: str) -> dict[str, Any]:
    """Restore archived history without selecting it or changing provider configuration."""
    with _SESSION_LOCK:
        session = load_conversation_session(session_id, include_turns=True)
        if not session:
            raise ValueError("Conversation session not found.")
        if session.get("status") != "archived":
            return _public_session(session, include_turns=False)
        session["status"] = "active"
        session["restored_at"] = _now_utc()
        session["updated_at"] = session["restored_at"]
        _atomic_write(_session_path(session_id), session)
        return _public_session(session, include_turns=False)


def _normalize_search_text(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def _search_terms(query: str) -> tuple[str, list[str]]:
    phrase = _normalize_search_text(query)
    if len(phrase) > MAX_CONVERSATION_SEARCH_QUERY_CHARS:
        raise ValueError(f"Conversation search exceeds {MAX_CONVERSATION_SEARCH_QUERY_CHARS} characters.")
    terms = list(dict.fromkeys(re.findall(r"[\w]+", phrase, flags=re.UNICODE)))
    return phrase, terms


def _bounded_search_snippet(text: str, phrase: str, terms: list[str], *, width: int = 220) -> str:
    clean = " ".join(str(text or "").split())
    if not clean:
        return ""
    folded = clean.casefold()
    candidates = [phrase] if phrase else []
    candidates.extend(term for term in terms if term)
    position = -1
    for candidate in candidates:
        position = folded.find(candidate)
        if position >= 0:
            break
    if position < 0:
        position = 0
    half = max(40, width // 2)
    start = max(0, position - half)
    end = min(len(clean), start + width)
    if end - start < width and start > 0:
        start = max(0, end - width)
    snippet = clean[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(clean):
        snippet += "…"
    return snippet


def _session_search_document(session_id: str) -> dict[str, Any]:
    path = _session_path(session_id)
    try:
        stat = path.stat()
        stamp = (int(stat.st_mtime_ns), int(stat.st_size))
    except OSError:
        return {}
    cache_key = str(path.resolve())
    with _SESSION_SEARCH_CACHE_LOCK:
        cached = _SESSION_SEARCH_CACHE.get(cache_key)
        if cached and cached[0] == stamp:
            _SESSION_SEARCH_CACHE.move_to_end(cache_key)
            return dict(cached[1])
    session = _load_json(path) or {}
    if session.get("type") != "conversation_session":
        return {}
    title = str(session.get("title") or "New conversation")
    completed_turns: list[dict[str, str]] = []
    for turn in session.get("turns", []):
        if not isinstance(turn, dict):
            continue
        if not turn.get("success") or turn.get("completion_state") != "completed":
            continue
        user_text = str(turn.get("user_message") or "").strip()
        assistant_text = str(turn.get("assistant_response") or "").strip()
        combined = "\n".join(part for part in (user_text, assistant_text) if part)
        if not combined:
            continue
        completed_turns.append({
            "normalized": _normalize_search_text(combined),
            "text": combined,
            "created_at": str(turn.get("created_at") or ""),
        })
    document = {
        "session": session,
        "title": title,
        "title_normalized": _normalize_search_text(title),
        "completed_turns": completed_turns,
    }
    with _SESSION_SEARCH_CACHE_LOCK:
        _SESSION_SEARCH_CACHE[cache_key] = (stamp, document)
        _SESSION_SEARCH_CACHE.move_to_end(cache_key)
        while len(_SESSION_SEARCH_CACHE) > MAX_CONVERSATION_SEARCH_CACHE_ENTRIES:
            _SESSION_SEARCH_CACHE.popitem(last=False)
    return dict(document)


def clear_conversation_search_cache() -> None:
    """Clear only the transient in-memory private search cache."""
    with _SESSION_SEARCH_CACHE_LOCK:
        _SESSION_SEARCH_CACHE.clear()


def _parse_catalog_time(value: str) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def conversation_session_group_label(value: str, *, now: datetime | None = None) -> str:
    stamp = _parse_catalog_time(value)
    if stamp is None:
        return "Older conversations"
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    days = (current.date() - stamp.date()).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days <= 7:
        return "Previous 7 days"
    if days <= 30:
        return "Previous 30 days"
    return stamp.strftime("%B %Y")


def _catalog_display_title(session: Mapping[str, Any], duplicate: bool) -> str:
    title = str(session.get("title") or "New conversation")[:72]
    if not duplicate:
        return title
    stamp = _parse_catalog_time(str(session.get("created_at") or session.get("updated_at") or ""))
    date_label = stamp.strftime("%b %d, %Y") if stamp else "undated"
    suffix = str(session.get("id") or "")[-4:] or "session"
    return f"{title} · {date_label} · {suffix}"


def _conversation_session_catalog_page_unlocked(
    query: str = "",
    *,
    include_archived: bool = True,
    offset: int = 0,
    limit: int = 30,
) -> dict[str, Any]:
    """Return one stable, bounded private conversation-search page.

    Search reads local session files only. It considers titles and completed user/assistant
    text, never failed turns, operator-action bodies, raw output, provider payloads, or
    runtime receipts. Search cache entries remain process-memory-only.
    """
    phrase, terms = _search_terms(query)
    try:
        requested_offset = max(0, int(offset))
        bounded_limit = max(1, min(MAX_CONVERSATION_SEARCH_LIMIT, int(limit)))
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid conversation catalog pagination.") from error

    summaries = list_conversation_sessions(include_archived=include_archived)
    title_counts: dict[str, int] = {}
    for summary in list_conversation_sessions(include_archived=True):
        key = _normalize_search_text(str(summary.get("title") or "New conversation"))
        title_counts[key] = title_counts.get(key, 0) + 1

    scored: list[tuple[int, str, dict[str, Any]]] = []
    for summary in summaries:
        session_id = str(summary.get("id") or "")
        document = _session_search_document(session_id) if phrase else {"session": summary, "title": str(summary.get("title") or "New conversation"), "title_normalized": _normalize_search_text(str(summary.get("title") or "New conversation")), "completed_turns": []}
        session = document.get("session") if isinstance(document.get("session"), dict) else dict(summary)
        title = str(document.get("title") or session.get("title") or "New conversation")
        title_normalized = str(document.get("title_normalized") or _normalize_search_text(title))
        match_source = ""
        match_snippet = ""
        score = 0
        if not phrase:
            match_source = "recent"
            match_snippet = str(session.get("last_turn_at") or session.get("updated_at") or session.get("created_at") or "")
        elif phrase in title_normalized:
            match_source = "title"
            match_snippet = title
            score = 1000 + max(0, 100 - title_normalized.find(phrase))
        elif terms and all(term in title_normalized for term in terms):
            match_source = "title_terms"
            match_snippet = title
            score = 850
        else:
            completed_turns = list(document.get("completed_turns") or [])
            for turn in reversed(completed_turns):
                normalized = str(turn.get("normalized") or "")
                phrase_match = bool(phrase and phrase in normalized)
                token_match = bool(terms and all(term in normalized for term in terms))
                if not phrase_match and not token_match:
                    continue
                match_source = "completed_turn"
                match_snippet = _bounded_search_snippet(str(turn.get("text") or ""), phrase, terms)
                score = 650 if phrase_match else 500
                break
        if not match_source:
            continue
        public = _public_session(session, include_turns=False)
        title_key = _normalize_search_text(title)
        duplicate_title = title_counts.get(title_key, 0) > 1
        sort_stamp = str(public.get("updated_at") or public.get("last_turn_at") or public.get("created_at") or "")
        public.update({
            "match_source": match_source,
            "match_snippet": match_snippet[:240],
            "duplicate_title": duplicate_title,
            "display_title": _catalog_display_title(public, duplicate_title),
            "group_label": "Search results" if phrase else conversation_session_group_label(sort_stamp),
            "sort_timestamp": sort_stamp,
        })
        scored.append((score, sort_stamp, public))

    if phrase:
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    total = len(scored)
    if total == 0:
        normalized_offset = 0
    else:
        last_page_offset = ((total - 1) // bounded_limit) * bounded_limit
        normalized_offset = min(requested_offset, last_page_offset)
    items = [item[2] for item in scored[normalized_offset: normalized_offset + bounded_limit]]
    revision_rows = [
        {
            "id": str(item.get("id") or ""),
            "status": str(item.get("status") or "active"),
            "updated_at": str(item.get("updated_at") or ""),
            "turn_count": max(0, int(item.get("turn_count") or 0)),
        }
        for item in list_conversation_sessions(include_archived=True)
    ]
    catalog_revision = hashlib.sha256(
        json.dumps(revision_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "ok": True,
        "catalog_schema_version": CATALOG_SCHEMA_VERSION,
        "catalog_revision": catalog_revision,
        "snapshot_consistent": True,
        "query": phrase,
        "include_archived": bool(include_archived),
        "offset": normalized_offset,
        "limit": bounded_limit,
        "total": total,
        "shown": len(items),
        "has_previous": normalized_offset > 0,
        "has_next": normalized_offset + len(items) < total,
        "previous_offset": max(0, normalized_offset - bounded_limit),
        "next_offset": normalized_offset + bounded_limit if normalized_offset + len(items) < total else normalized_offset,
        "items": items,
        "private_local_search": True,
        "receipts_included": False,
    }


def conversation_session_catalog_page(
    query: str = "",
    *,
    include_archived: bool = True,
    offset: int = 0,
    limit: int = 30,
) -> dict[str, Any]:
    """Return one lock-consistent catalog page and content-free revision token."""
    with _SESSION_LOCK:
        return _conversation_session_catalog_page_unlocked(
            query, include_archived=include_archived, offset=offset, limit=limit,
        )


def conversation_session_turn_window(
    session_id: str, *, before_turn_id: str = "", limit: int = 80,
) -> dict[str, Any]:
    """Return a bounded chronological transcript window without copying text into metadata."""
    with _SESSION_LOCK:
        turns = conversation_session_turns(session_id)
        try:
            bounded_limit = max(1, min(MAX_CONVERSATION_TRANSCRIPT_WINDOW, int(limit)))
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid conversation transcript window limit.") from error
        end = len(turns)
        token = str(before_turn_id or "").strip()
        if token:
            matches = [index for index, turn in enumerate(turns) if str(turn.get("id") or "") == token]
            if not matches:
                raise ValueError("Conversation transcript anchor was not found.")
            end = matches[0]
        start = max(0, end - bounded_limit)
        window = turns[start:end]
        return {
            "ok": True,
            "session_id": _validate_session_id(session_id),
            "turns": window,
            "window_start": start,
            "window_end": end,
            "total_turns": len(turns),
            "shown": len(window),
            "has_older": start > 0,
            "oldest_turn_id": str(window[0].get("id") or "") if window else "",
            "newest_turn_id": str(window[-1].get("id") or "") if window else "",
            "content_free_metadata": True,
        }


def search_conversation_sessions(
    query: str,
    *,
    include_archived: bool = True,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Compatibility wrapper returning the first bounded private catalog page."""
    return list(conversation_session_catalog_page(
        query, include_archived=include_archived, offset=0, limit=limit,
    ).get("items") or [])


def select_conversation_session(session_id: str, *, project_id: str = "") -> dict[str, Any]:
    """Select an existing session inside its exact project conversation lane."""
    with _SESSION_LOCK:
        session = load_conversation_session(session_id, include_turns=False)
        if not session:
            raise ValueError("Conversation session not found.")
        if session.get("status") == "archived":
            raise ValueError("Archived conversation must be restored before it can be resumed.")
        bound_project = _session_project_id(session)
        expected = str(project_id or _active_project_id()).strip() or "eidolon"
        if bound_project != expected:
            raise ValueError("Conversation session belongs to a different active project.")
        pointer = _write_active_session(str(session["id"]), bound_project, reason="session_selected")
        result = dict(session)
        result["selected_at"] = pointer["selected_at"]
        return result


def _legacy_dashboard_chat_signature() -> str:
    """Fingerprint the legacy turn directory without reading any file contents."""
    if not LEGACY_DASHBOARD_CHAT_DIR.exists():
        return "absent"
    count = 0
    total = 0
    newest = 0
    try:
        with os.scandir(LEGACY_DASHBOARD_CHAT_DIR) as entries:
            for entry in entries:
                if not entry.name.endswith(".json"):
                    continue
                try:
                    stat = entry.stat()
                except OSError:
                    continue
                count += 1
                total += int(stat.st_size)
                newest = max(newest, int(stat.st_mtime_ns))
    except OSError:
        return "unreadable"
    return f"{count}:{total}:{newest}"


def migrate_legacy_dashboard_chat_turns() -> dict[str, Any]:
    """Import pre-session dashboard turns once while preserving the original files.

    Older Eidolon releases stored each dashboard exchange independently. The current
    chat UI reads conversation sessions, so leaving those records unimported makes
    intact history appear to have vanished.

    The live chat surface still writes into this directory, so the archive session's
    identity must stay stable as new turns land. Deriving it from a digest of the
    directory forked a fresh copy of the whole transcript on every new turn, and
    rewrote every turn under the global session lock while chat requests queued
    behind it.
    """
    global _LEGACY_IMPORT_SIGNATURE_SEEN
    with _SESSION_LOCK:
        signature = _legacy_dashboard_chat_signature()
        marker = _load_json(LEGACY_DASHBOARD_CHAT_IMPORT_FILE) or {}
        recorded_id = str(marker.get("session_id") or "").strip()
        try:
            recorded_exists = bool(recorded_id) and _session_path(recorded_id).is_file()
        except ValueError:
            recorded_id, recorded_exists = "", False
        unchanged = signature in {_LEGACY_IMPORT_SIGNATURE_SEEN, str(marker.get("source_signature") or "")}
        if unchanged and recorded_exists:
            _LEGACY_IMPORT_SIGNATURE_SEEN = signature
            return {
                "status": "current",
                "session_id": recorded_id,
                "source_turn_count": int(marker.get("source_turn_count") or 0),
                "imported_turn_count": 0,
            }
        paths = sorted(LEGACY_DASHBOARD_CHAT_DIR.glob("*.json")) if LEGACY_DASHBOARD_CHAT_DIR.exists() else []
        records: list[dict[str, Any]] = []
        digest = hashlib.sha256()
        for path in paths:
            try:
                raw = path.read_bytes()
                data = json.loads(raw.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict) or data.get("type") != "dashboard_chat_turn":
                continue
            turn_id = str(data.get("id") or "").strip()
            user_message = str(data.get("user_message") or "")
            assistant_response = str(data.get("eidolon_response") or data.get("assistant_response") or "")
            if not turn_id or not user_message:
                continue
            digest.update(path.name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(raw)
            records.append({
                "id": turn_id,
                "created_at": str(data.get("created_at") or ""),
                "user_message": user_message,
                "assistant_response": assistant_response,
                "error": str(data.get("error") or ""),
                "use_ai": bool(data.get("use_ai")),
            })
        if not records:
            _LEGACY_IMPORT_SIGNATURE_SEEN = signature
            return {"status": "not_needed", "source_turn_count": 0, "imported_turn_count": 0}

        records.sort(key=lambda item: (item["created_at"], item["id"]))
        first_stamp = re.sub(r"[^0-9]", "", records[0]["created_at"])[:14]
        if len(first_stamp) != 14:
            first_stamp = "19700101000000"
        source_digest = digest.hexdigest()
        session_id = recorded_id if recorded_exists else (
            f"conversation_session_{first_stamp[:8]}T{first_stamp[8:]}_{source_digest[:10]}"
        )
        session = create_conversation_session(
            "Earlier Eidolon conversations",
            source="legacy_dashboard_chat_import",
            session_id=session_id,
            select_session=False,
        )
        existing_ids = {
            str(turn.get("id") or "")
            for turn in session.get("turns", [])
            if isinstance(turn, dict)
        }
        imported = 0
        for record in records:
            if record["id"] in existing_ids:
                continue
            success = bool(record["assistant_response"]) and not bool(record["error"])
            append_conversation_turn(
                session_id,
                turn_id=record["id"],
                user_message=record["user_message"],
                assistant_response=record["assistant_response"],
                completion_state="completed" if success else "failed",
                success=success,
                provider="legacy_local_ai" if record["use_ai"] else "legacy_offline",
                failure_category="legacy_dashboard_error" if record["error"] else None,
                source="legacy_dashboard_chat_import",
                created_at=record["created_at"],
                select_session=False,
                allow_default_title_update=False,
            )
            imported += 1
        _atomic_write(LEGACY_DASHBOARD_CHAT_IMPORT_FILE, {
            "type": "legacy_dashboard_chat_import",
            "schema_version": "1",
            "session_id": session_id,
            "source_digest": source_digest,
            "source_signature": signature,
            "source_turn_count": len(records),
            "imported_at": _now_utc(),
            "originals_preserved": True,
        })
        _LEGACY_IMPORT_SIGNATURE_SEEN = signature
        return {
            "status": "imported" if imported else "reconciled",
            "session_id": session_id,
            "source_turn_count": len(records),
            "imported_turn_count": imported,
        }


def get_active_conversation_session(*, create_if_missing: bool = True) -> dict[str, Any] | None:
    with _SESSION_LOCK:
        migrate_legacy_dashboard_chat_turns()
        active_project = _active_project_id()
        pointer = _active_session_pointer()
        selected_id = str((pointer.get("projects") or {}).get(active_project) or "")
        selected = load_conversation_session(selected_id, include_turns=True) if selected_id else None
        if selected and selected.get("status") != "archived" and _session_project_id(selected) == active_project:
            return selected
        sessions = list_conversation_sessions(include_archived=False, project_id=active_project)
        if sessions:
            latest_id = str(sessions[0]["id"])
            if create_if_missing:
                select_conversation_session(latest_id, project_id=active_project)
            return load_conversation_session(latest_id, include_turns=True)
        return create_conversation_session(project_id=active_project) if create_if_missing else None


def resolve_conversation_session(session_id: str = "", *, create_if_missing: bool = True) -> dict[str, Any] | None:
    token = str(session_id or "").strip()
    if token.lower() in {"", "active", "current", "latest"}:
        return get_active_conversation_session(create_if_missing=create_if_missing)
    if token.lower() in {"new", "create"}:
        return create_conversation_session()
    session = load_conversation_session(token, include_turns=True)
    if session:
        return session
    if create_if_missing:
        raise ValueError("Conversation session not found.")
    return None


def append_conversation_turn(
    session_id: str,
    *,
    turn_id: str,
    user_message: str,
    assistant_response: str,
    completion_state: str,
    success: bool,
    provider: str = "",
    model: str = "",
    streaming: bool = False,
    failure_category: str | None = None,
    source: str = "conversation_runtime",
    created_at: str = "",
    user_memory_stored: bool = False,
    user_memory_reused: bool = False,
    assistant_memory_stored: bool = False,
    user_memory_attribution_id: str = "",
    assistant_memory_attribution_id: str = "",
    recovery_of: str = "",
    recovery_kind: str = "",
    diagnostic: Mapping[str, Any] | None = None,
    operator_action: Mapping[str, Any] | None = None,
    continuity_lane: str = "ordinary",
    relationship_memory_policy: str = "explicit_curation_only",
    select_session: bool = True,
    allow_default_title_update: bool = True,
) -> dict[str, Any]:
    """Append one operation once. Failed/partial turns remain visible but are not prompt history."""
    with _SESSION_LOCK:
        session = load_conversation_session(session_id, include_turns=True)
        if not session:
            raise ValueError("Conversation session not found.")
        turns = [dict(turn) for turn in session.get("turns", []) if isinstance(turn, dict)]
        existing = next((turn for turn in turns if str(turn.get("id")) == str(turn_id)), None)
        if existing:
            return dict(existing)
        now = created_at or _now_utc()
        turn = {
            "id": str(turn_id),
            "type": "conversation_session_turn",
            "project_id": _session_project_id(session),
            "created_at": now,
            "user_message": str(user_message or ""),
            "assistant_response": str(assistant_response or ""),
            "completion_state": str(completion_state or "failed"),
            "success": bool(success),
            "failure_category": str(failure_category or ""),
            "provider": str(provider or "")[:40],
            "model": str(model or "")[:160],
            "streaming": bool(streaming),
            "source": str(source or "conversation_runtime")[:80],
            "user_memory_stored": bool(user_memory_stored),
            "user_memory_reused": bool(user_memory_reused),
            "assistant_memory_stored": bool(assistant_memory_stored),
            "memory_commit_attribution_schema_version": "1" if (user_memory_attribution_id or assistant_memory_attribution_id) else "",
            "user_memory_attribution_id": str(user_memory_attribution_id or "")[:120],
            "assistant_memory_attribution_id": str(assistant_memory_attribution_id or "")[:120],
            "recovery_of": str(recovery_of or "")[:100],
            "recovery_kind": str(recovery_kind or "")[:40],
            "continuity_lane": (
                str(continuity_lane or "ordinary").strip().lower()
                if str(continuity_lane or "ordinary").strip().lower() in {"ordinary", "relational", "operator", "mixed"}
                else "ordinary"
            ),
            "relationship_memory_policy": (
                str(relationship_memory_policy or "explicit_curation_only").strip().lower()
                if str(relationship_memory_policy or "explicit_curation_only").strip().lower() in {"explicit_curation_only", "operator_excluded"}
                else "explicit_curation_only"
            ),
            "automatic_relationship_memory_created": False,
        }
        safe_diagnostic = _safe_turn_diagnostic(diagnostic)
        if any(value not in ("", None, False) and value != {} for key, value in safe_diagnostic.items() if key != "redacted"):
            turn["diagnostic"] = safe_diagnostic
        safe_operator_action = sanitize_action_portal_state(operator_action)
        if safe_operator_action:
            turn["operator_action"] = safe_operator_action
        turns.append(turn)
        session["turns"] = turns
        session["turn_count"] = len(turns)
        session["completed_turn_count"] = sum(1 for item in turns if item.get("success") and item.get("completion_state") == "completed")
        session["updated_at"] = now
        session["last_turn_at"] = now
        session["last_provider"] = turn["provider"]
        session["last_model"] = turn["model"]
        if allow_default_title_update and session.get("title_is_default") and str(user_message or "").strip():
            session["title"] = _title_from_message(user_message)
            session["title_is_default"] = False
        _atomic_write(_session_path(session_id), session)
        if select_session:
            _write_active_session(session_id, _session_project_id(session), reason="conversation_turn")
        return dict(turn)


def update_conversation_turn_action(
    session_id: str,
    turn_id: str,
    operator_action: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach one redacted action portal snapshot without replaying provider or command work."""
    safe_action = sanitize_action_portal_state(operator_action)
    if not safe_action:
        raise ValueError("A valid redacted action portal state is required.")
    with _SESSION_LOCK:
        session = load_conversation_session(session_id, include_turns=True)
        if not session:
            raise ValueError("Conversation session not found.")
        turns = [dict(turn) for turn in session.get("turns", []) if isinstance(turn, dict)]
        match_index = next((index for index, turn in enumerate(turns) if str(turn.get("id")) == str(turn_id)), None)
        if match_index is None:
            raise ValueError("Conversation turn not found.")
        existing = turns[match_index].get("operator_action")
        if existing == safe_action:
            return dict(turns[match_index])
        if existing and not portal_update_is_safe(existing, safe_action):
            return dict(turns[match_index])
        turns[match_index]["operator_action"] = safe_action
        session["turns"] = turns
        session["updated_at"] = _now_utc()
        _atomic_write(_session_path(session_id), session)
        return dict(turns[match_index])


def conversation_session_turns(session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    session = load_conversation_session(session_id, include_turns=True)
    if not session:
        return []
    turns = [dict(turn) for turn in session.get("turns", []) if isinstance(turn, dict)]
    return turns[-limit:] if limit else turns


def conversation_history_for_prompt(session_id: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Return complete pairs plus one bounded redacted action status, never raw receipts."""
    turns = conversation_session_turns(session_id)
    action_by_operation: dict[str, dict[str, Any]] = {}
    action_by_id: dict[str, dict[str, Any]] = {}
    try:
        from chat_action_router import lookup_chat_actions
        relevant_turns = turns[-max(16, int(limit) * 3):]
        wanted_action_ids: list[str] = []
        wanted_operations: list[str] = []
        for candidate in relevant_turns:
            portal = sanitize_action_portal_state(candidate.get("operator_action"))
            action_id = str((portal or {}).get("action_id") or "")
            if action_id:
                wanted_action_ids.append(action_id)
            turn_id = str(candidate.get("id") or "")
            if turn_id:
                wanted_operations.append(turn_id)
        governed_actions = lookup_chat_actions(
            action_ids=tuple(wanted_action_ids), deduplication_keys=tuple(wanted_operations),
        )
        action_by_operation = {
            str(action.get("deduplication_key") or ""): action
            for action in governed_actions if str(action.get("deduplication_key") or "")
        }
        action_by_id = {
            str(action.get("id") or ""): action
            for action in governed_actions if str(action.get("id") or "")
        }
    except Exception:
        action_by_operation = {}
        action_by_id = {}
    rows: list[dict[str, str]] = []
    for turn in turns:
        # Provider-generated, grounded, and governed deterministic replies are
        # all successful conversation evidence once their complete turn is
        # committed. Restricting history to the literal "completed" label made
        # grounded replies invisible to the very next turn.
        if not turn.get("success"):
            continue
        user_message = str(turn.get("user_message") or "").strip()
        assistant_response = str(turn.get("assistant_response") or "").strip()
        if not user_message or not assistant_response:
            continue
        row = {
            "user_message": user_message,
            "assistant_response": assistant_response,
            "created_at": str(turn.get("created_at") or ""),
            "continuity_lane": str(turn.get("continuity_lane") or "ordinary"),
            "relationship_memory_policy": str(turn.get("relationship_memory_policy") or "explicit_curation_only"),
            "automatic_relationship_memory_created": False,
        }
        # Preserve only bounded, content-free correction lineage needed to keep
        # stale summaries out of future prompt assembly. Raw receipts and
        # transcript rewrites remain forbidden.
        for field in (
            "corrects_summary_id",
            "supersedes_summary_id",
            "retracts_summary_id",
            "deletes_summary_id",
            "correction_target_summary_id",
        ):
            value = str(turn.get(field) or "").strip()
            if value:
                row[field] = value[:160]
        digests = turn.get("superseded_content_digests") or ()
        if isinstance(digests, (list, tuple)):
            safe_digests = [str(value)[:128] for value in digests[:16] if str(value or "").strip()]
            if safe_digests:
                row["superseded_content_digests"] = safe_digests
        operator_action = sanitize_action_portal_state(turn.get("operator_action"))
        action_id = str((operator_action or {}).get("action_id") or "")
        governed_action = action_by_id.get(action_id) or action_by_operation.get(str(turn.get("id") or ""))
        if governed_action:
            from conversation_action_portal import build_action_portal_state
            current_portal = build_action_portal_state(
                governed_action,
                governed_action.get("result") if isinstance(governed_action.get("result"), dict) else None,
            )
            if current_portal and (not operator_action or portal_update_is_safe(operator_action, current_portal)):
                operator_action = current_portal
        status_summary = action_context_summary(operator_action)
        if status_summary:
            row["action_status_summary"] = status_summary
        rows.append(row)
    return rows[-max(1, int(limit)) :]


def session_contains_private_receipt_fields(value: dict[str, Any]) -> bool:
    """Regression helper: session files must not embed runtime receipt bodies."""
    forbidden = {
        "timings_ms", "retry_count", "context_budget", "receipt_path", "raw_events", "authorization",
        "raw_response", "response_body", "prompt", "prompts", "credentials", "stack_trace", "traceback",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden & set(current):
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
