from __future__ import annotations

"""Bounded public reconciliation markers for accepted conversation operations.

Markers deliberately exclude message text, generated text, prompts, partial tokens,
memories, provider payloads, credentials, receipts, and stack traces. They exist only
so ordinary chat can tell whether one already-accepted operation is running, complete,
failed, cancelled, or no longer knowable after a process restart.
"""

import hashlib
import hmac
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from paths import DATA_DIR
try:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from metadata_mutation_coordination import MetadataMutationBusy, metadata_mutation_lock


OPERATION_MARKER_SCHEMA_VERSION = "3"
OPERATION_ACKNOWLEDGEMENT_SCHEMA_VERSION = "1"
CONVERSATION_OPERATION_DIR = DATA_DIR / "conversation_runtime" / "operations"
CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR = DATA_DIR / "conversation_runtime" / "operation_acknowledgements"
CONVERSATION_ACCEPTANCE_CLAIM_DIR = DATA_DIR / "conversation_runtime" / "acceptance_claims"
_OPERATION_MARKER_LOCK = threading.RLock()
_OPERATION_ID_PATTERN = re.compile(r"^conversation_[0-9]{8}T[0-9]{6}_[a-f0-9]{12}$")
_SESSION_ID_PATTERN = re.compile(r"^conversation_session_[0-9]{8}T[0-9]{6}_[a-f0-9]{10}$")
_ACCEPTANCE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
_TERMINAL_STATES = {"completed", "failed", "cancelled", "uncertain"}
_PUBLIC_STATES = {"running", *_TERMINAL_STATES}
_ACKNOWLEDGEMENT_SOURCE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_conversation_operation_id() -> str:
    return f"conversation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:12]}"


def new_client_acceptance_key() -> str:
    return f"chat_accept_{uuid.uuid4().hex}"


def _validate_operation_id(operation_id: str) -> str:
    token = str(operation_id or "").strip()
    if not _OPERATION_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation operation identifier.")
    return token


def _validate_session_id(session_id: str) -> str:
    token = str(session_id or "").strip()
    if not _SESSION_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation session identifier.")
    return token


def _validate_acceptance_key(acceptance_key: str) -> str:
    token = str(acceptance_key or "").strip()
    if not _ACCEPTANCE_KEY_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation acceptance key.")
    return token


def _marker_path(operation_id: str) -> Path:
    return CONVERSATION_OPERATION_DIR / f"{_validate_operation_id(operation_id)}.json"


def _acknowledgement_path(operation_id: str) -> Path:
    return CONVERSATION_OPERATION_ACKNOWLEDGEMENT_DIR / f"{_validate_operation_id(operation_id)}.json"


def _acceptance_claim_path(session_id: str, acceptance_key: str) -> Path:
    session = _validate_session_id(session_id)
    key = _validate_acceptance_key(acceptance_key)
    digest = hashlib.sha256(f"{session}:{key}".encode("utf-8")).hexdigest()
    return CONVERSATION_ACCEPTANCE_CLAIM_DIR / f"{digest}.json"


def claim_operation_acceptance(session_id: str, acceptance_key: str, operation_id: str) -> dict[str, Any]:
    """Bind one acceptance identity to one operation across processes.

    The claim contains only opaque identifiers. Repeated claims converge on the
    original operation and never authorize a second provider execution.
    """
    session = _validate_session_id(session_id)
    key = _validate_acceptance_key(acceptance_key)
    operation = _validate_operation_id(operation_id)
    path = _acceptance_claim_path(session, key)
    path.parent.mkdir(parents=True, exist_ok=True)

    def duplicate(existing: dict[str, Any]) -> dict[str, Any]:
        return {
            "claimed": False,
            "duplicate_acceptance": True,
            "operation_id": str(existing.get("operation_id") or ""),
            "session_id": session,
            "acceptance_key": key,
            "content_free": True,
        }

    existing = load_json_file(path, None, expected_type=dict)
    if existing:
        return duplicate(existing)

    try:
        lock = metadata_mutation_lock(path, timeout_seconds=5.0)
        with lock:
            existing = load_json_file(path, None, expected_type=dict)
            if existing:
                return duplicate(existing)
            value = {
                "type": "conversation_acceptance_claim",
                "schema_version": "1",
                "operation_id": operation,
                "session_id": session,
                "acceptance_key": key,
                "claimed_at": _now_utc(),
                "content_free": True,
            }
            write_json_atomic(path, value, expected_type=dict, sort_keys=True, coordinate=False)
    except MetadataMutationBusy:
        # The claim is immutable. A competing winner may have persisted it even
        # when Windows lock cleanup has not completed yet.
        existing = load_json_file(path, None, expected_type=dict)
        if existing:
            return duplicate(existing)
        raise
    return {
        "claimed": True,
        "duplicate_acceptance": False,
        "operation_id": operation,
        "session_id": session,
        "acceptance_key": key,
        "content_free": True,
    }


def operation_id_for_acceptance_key(session_id: str, acceptance_key: str) -> str:
    try:
        value = load_json_file(_acceptance_claim_path(session_id, acceptance_key), None, expected_type=dict)
    except ValueError:
        return ""
    return str((value or {}).get("operation_id") or "")


def _load_json(path: Path) -> dict[str, Any] | None:
    return load_json_file(path, None, expected_type=dict)


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    write_json_atomic(path, value, expected_type=dict, sort_keys=True)


def _public_marker(value: dict[str, Any]) -> dict[str, Any]:
    state = str(value.get("public_state") or "running")
    if state not in _PUBLIC_STATES:
        state = "uncertain"
    return {
        "type": "conversation_operation_marker",
        "schema_version": OPERATION_MARKER_SCHEMA_VERSION,
        "operation_id": str(value.get("operation_id") or ""),
        "session_id": str(value.get("session_id") or ""),
        "project_id": str(value.get("project_id") or "eidolon"),
        "accepted_at": str(value.get("accepted_at") or ""),
        "updated_at": str(value.get("updated_at") or ""),
        "completed_at": str(value.get("completed_at") or ""),
        "public_state": state,
        "failure_category": str(value.get("failure_category") or "")[:80],
        "cancellation_requested": bool(value.get("cancellation_requested")),
        "cancellation_requested_at": str(value.get("cancellation_requested_at") or ""),
        "late_result_ignored_count": max(0, int(value.get("late_result_ignored_count") or 0)),
        "last_late_completion_state": str(value.get("last_late_completion_state") or "")[:40],
        "retry_of_operation_id": str(value.get("retry_of_operation_id") or ""),
        "explicit_retry_operation_id": str(value.get("explicit_retry_operation_id") or ""),
        "final_session_turn_recorded": bool(value.get("final_session_turn_recorded")),
        "client_disconnected": bool(value.get("client_disconnected")),
        "reconciled_late": bool(value.get("reconciled_late")),
        "reconciled_at": str(value.get("reconciled_at") or ""),
        "streaming": bool(value.get("streaming", True)),
        "acceptance_key": str(value.get("acceptance_key") or "")[:96],
        "redacted": True,
    }


def create_operation_marker(
    operation_id: str,
    session_id: str,
    *,
    accepted_at: str = "",
    streaming: bool = True,
    acceptance_key: str = "",
) -> dict[str, Any]:
    """Create one marker once; duplicate acceptance returns the existing marker."""
    with _OPERATION_MARKER_LOCK:
        operation_token = _validate_operation_id(operation_id)
        session_token = _validate_session_id(session_id)
        existing = _load_json(_marker_path(operation_token))
        if existing:
            return _public_marker(existing)
        now = accepted_at or _now_utc()
        try:
            from conversation_sessions import load_conversation_session, _session_project_id
            session_record = load_conversation_session(session_token, include_turns=False)
            project_id = _session_project_id(session_record)
        except Exception:
            project_id = "eidolon"
        marker = {
            "type": "conversation_operation_marker",
            "schema_version": OPERATION_MARKER_SCHEMA_VERSION,
            "operation_id": operation_token,
            "session_id": session_token,
            "project_id": project_id,
            "accepted_at": now,
            "updated_at": now,
            "completed_at": "",
            "public_state": "running",
            "failure_category": "",
            "cancellation_requested": False,
            "cancellation_requested_at": "",
            "late_result_ignored_count": 0,
            "last_late_completion_state": "",
            "retry_of_operation_id": "",
            "explicit_retry_operation_id": "",
            "final_session_turn_recorded": False,
            "client_disconnected": False,
            "reconciled_late": False,
            "reconciled_at": "",
            "streaming": bool(streaming),
            "acceptance_key": _validate_acceptance_key(acceptance_key),
            "redacted": True,
        }
        _atomic_write(_marker_path(operation_token), marker)
        return _public_marker(marker)


def load_operation_marker(operation_id: str) -> dict[str, Any] | None:
    try:
        path = _marker_path(operation_id)
    except ValueError:
        return None
    value = _load_json(path)
    return _public_marker(value) if value else None


def list_operation_markers(*, session_id: str = "") -> list[dict[str, Any]]:
    if not CONVERSATION_OPERATION_DIR.exists():
        return []
    session_token = str(session_id or "").strip()
    rows: list[dict[str, Any]] = []
    for path in CONVERSATION_OPERATION_DIR.glob("conversation_*.json"):
        value = _load_json(path)
        if not value:
            continue
        public = _public_marker(value)
        if session_token and public.get("session_id") != session_token:
            continue
        rows.append(public)
    return sorted(
        rows,
        key=lambda item: (str(item.get("accepted_at") or ""), str(item.get("operation_id") or "")),
        reverse=True,
    )


def find_operation_by_acceptance_key(session_id: str, acceptance_key: str) -> dict[str, Any] | None:
    session = _validate_session_id(session_id)
    key = _validate_acceptance_key(acceptance_key)
    claimed_operation = operation_id_for_acceptance_key(session, key)
    if claimed_operation:
        marker = load_operation_marker(claimed_operation)
        if marker:
            return marker
    return next(
        (
            marker
            for marker in list_operation_markers(session_id=session)
            if marker.get("acceptance_key") == key
        ),
        None,
    )


def latest_operation_marker(session_id: str, *, states: Iterable[str] | None = None) -> dict[str, Any] | None:
    allowed = {str(item) for item in states} if states is not None else None
    for marker in list_operation_markers(session_id=_validate_session_id(session_id)):
        if allowed is None or marker.get("public_state") in allowed:
            return marker
    return None


def _mutate_marker(operation_id: str, mutator: Any) -> dict[str, Any] | None:
    with _OPERATION_MARKER_LOCK:
        try:
            path = _marker_path(operation_id)
        except ValueError:
            return None
        marker = _load_json(path)
        if not marker:
            return None
        changed = bool(mutator(marker))
        if changed:
            marker["updated_at"] = _now_utc()
            _atomic_write(path, marker)
        return _public_marker(marker)


def mark_operation_client_disconnected(operation_id: str) -> dict[str, Any] | None:
    def mutate(marker: dict[str, Any]) -> bool:
        changed = False
        if not marker.get("client_disconnected"):
            marker["client_disconnected"] = True
            changed = True
        if str(marker.get("public_state") or "") == "completed" and not marker.get("reconciled_late"):
            marker["reconciled_late"] = True
            changed = True
        return changed

    return _mutate_marker(operation_id, mutate)


def request_operation_cancellation(operation_id: str, *, expected_project_id: str = "") -> dict[str, Any] | None:
    expected = str(expected_project_id or "").strip().lower()
    marker = load_operation_marker(operation_id)
    if not marker:
        return None
    marker_project = str(marker.get("project_id") or "eidolon").strip().lower()
    if expected and expected != marker_project:
        rejected = dict(marker)
        rejected.update({
            "cancellation_rejected": True,
            "cancellation_rejection": "project_mismatch",
            "expected_project_id": expected,
        })
        return rejected

    def mutate(value: dict[str, Any]) -> bool:
        if str(value.get("public_state") or "running") in _TERMINAL_STATES:
            return False
        if value.get("cancellation_requested"):
            return False
        value["cancellation_requested"] = True
        value["cancellation_requested_at"] = _now_utc()
        return True

    return _mutate_marker(operation_id, mutate)


def finalize_operation_marker(
    operation_id: str,
    *,
    completion_state: str,
    success: bool,
    failure_category: str = "",
    final_session_turn_recorded: bool = False,
    completed_at: str = "",
) -> dict[str, Any] | None:
    """Finalize once. A terminal result cannot be overwritten by late packets or cancellation."""
    def mutate(marker: dict[str, Any]) -> bool:
        current = str(marker.get("public_state") or "running")
        state_token = str(completion_state or "").strip().lower()
        if current in _TERMINAL_STATES:
            changed = False
            if final_session_turn_recorded and not marker.get("final_session_turn_recorded"):
                marker["final_session_turn_recorded"] = True
                changed = True
            incoming_public = "completed" if bool(success) else ("cancelled" if state_token == "cancelled" else ("uncertain" if state_token in {"consumer_disconnected", "uncertain"} else "failed"))
            if incoming_public != current:
                marker["late_result_ignored_count"] = max(0, int(marker.get("late_result_ignored_count") or 0)) + 1
                marker["last_late_completion_state"] = incoming_public
                changed = True
            return changed
        if bool(success):
            public_state = "completed"
        elif state_token == "cancelled":
            public_state = "cancelled"
        elif state_token in {"consumer_disconnected", "uncertain"}:
            public_state = "uncertain"
        else:
            public_state = "failed"
        marker["public_state"] = public_state
        marker["failure_category"] = str(failure_category or ("" if public_state == "completed" else state_token))[:80]
        marker["completed_at"] = completed_at or _now_utc()
        marker["final_session_turn_recorded"] = bool(final_session_turn_recorded)
        if marker.get("client_disconnected"):
            marker["reconciled_late"] = True
        return True

    return _mutate_marker(operation_id, mutate)



def link_explicit_retry(original_operation_id: str, retry_operation_id: str) -> dict[str, Any]:
    """Bind one operator-triggered retry to one terminal operation without replaying it."""
    original = _validate_operation_id(original_operation_id)
    retry = _validate_operation_id(retry_operation_id)
    if original == retry:
        raise ValueError("Retry operation must differ from the original operation.")
    original_marker = load_operation_marker(original)
    retry_marker = load_operation_marker(retry)
    if not original_marker or not retry_marker:
        raise ValueError("Both conversation operations must exist before retry linkage.")
    if str(original_marker.get("session_id") or "") != str(retry_marker.get("session_id") or ""):
        raise ValueError("Retry operation must belong to the same conversation session.")
    if str(original_marker.get("public_state") or "running") not in {"failed", "cancelled", "uncertain"}:
        raise ValueError("Only a terminal recoverable operation may be retried explicitly.")

    def mutate_original(value: dict[str, Any]) -> bool:
        existing = str(value.get("explicit_retry_operation_id") or "")
        if existing and existing != retry:
            return False
        if existing == retry:
            return False
        value["explicit_retry_operation_id"] = retry
        return True

    def mutate_retry(value: dict[str, Any]) -> bool:
        existing = str(value.get("retry_of_operation_id") or "")
        if existing and existing != original:
            return False
        if existing == original:
            return False
        value["retry_of_operation_id"] = original
        return True

    linked_original = _mutate_marker(original, mutate_original)
    linked_retry = _mutate_marker(retry, mutate_retry)
    return {
        "ok": bool(linked_original and linked_retry),
        "original_operation": linked_original,
        "retry_operation": linked_retry,
        "automatic_retry": False,
        "content_free": True,
    }


def operation_cue_token(marker: dict[str, Any], *, public_state: str = "") -> str:
    """Return a content-free exact-operation fingerprint for stale-click rejection."""
    operation_id = _validate_operation_id(str(marker.get("operation_id") or ""))
    session_id = _validate_session_id(str(marker.get("session_id") or ""))
    state = str(public_state or marker.get("public_state") or "").strip().lower()
    if state not in _PUBLIC_STATES:
        raise ValueError("Invalid conversation operation public state.")
    payload = "|".join((
        "eidolon-conversation-cue-v1",
        operation_id,
        session_id,
        str(marker.get("accepted_at") or ""),
        state,
    ))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _public_acknowledgement(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "conversation_operation_acknowledgement",
        "schema_version": OPERATION_ACKNOWLEDGEMENT_SCHEMA_VERSION,
        "operation_id": str(value.get("operation_id") or ""),
        "session_id": str(value.get("session_id") or ""),
        "acknowledged_at": str(value.get("acknowledged_at") or ""),
        "acknowledged_public_state": str(value.get("acknowledged_public_state") or ""),
        "source": str(value.get("source") or "")[:80],
        "local_private": True,
        "redacted": True,
    }


def load_operation_acknowledgement(operation_id: str) -> dict[str, Any] | None:
    try:
        value = _load_json(_acknowledgement_path(operation_id))
    except ValueError:
        return None
    if not value or value.get("type") != "conversation_operation_acknowledgement":
        return None
    return _public_acknowledgement(value)


def acknowledge_operation_marker(
    operation_id: str,
    session_id: str,
    *,
    public_state: str,
    source: str = "dashboard_chat_session_cue",
) -> dict[str, Any]:
    """Persist one exact terminal-cue acknowledgement without mutating operation truth."""
    with _OPERATION_MARKER_LOCK:
        operation_token = _validate_operation_id(operation_id)
        session_token = _validate_session_id(session_id)
        state = str(public_state or "").strip().lower()
        if state not in _TERMINAL_STATES:
            raise ValueError("Only terminal conversation cues may be acknowledged.")
        source_token = str(source or "dashboard_chat_session_cue").strip()
        if not _ACKNOWLEDGEMENT_SOURCE_PATTERN.fullmatch(source_token):
            raise ValueError("Invalid conversation acknowledgement source.")
        marker = _load_json(_marker_path(operation_token))
        if not marker:
            raise ValueError("Conversation operation was not found.")
        if str(marker.get("session_id") or "") != session_token:
            raise ValueError("Conversation operation does not belong to this session.")
        persisted_state = str(marker.get("public_state") or "running")
        if persisted_state != state and not (persisted_state == "running" and state == "uncertain"):
            raise ValueError("Conversation cue changed before it could be acknowledged.")
        existing = _load_json(_acknowledgement_path(operation_token))
        if existing:
            result = _public_acknowledgement(existing)
            result.update({"changed": False, "already_acknowledged": True})
            return result
        record = {
            "type": "conversation_operation_acknowledgement",
            "schema_version": OPERATION_ACKNOWLEDGEMENT_SCHEMA_VERSION,
            "operation_id": operation_token,
            "session_id": session_token,
            "acknowledged_at": _now_utc(),
            "acknowledged_public_state": state,
            "source": source_token,
            "local_private": True,
            "redacted": True,
        }
        _atomic_write(_acknowledgement_path(operation_token), record)
        result = _public_acknowledgement(record)
        result.update({"changed": True, "already_acknowledged": False})
        return result


def operation_marker_is_acknowledged(operation_id: str) -> bool:
    return load_operation_acknowledgement(operation_id) is not None

def operation_marker_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden_keys = {
        "user_message", "message", "prompt", "prompts", "response", "display_message",
        "assistant_response", "partial", "partial_tokens", "raw_events", "raw_response",
        "response_body", "credentials", "receipt", "receipt_path", "stack_trace", "traceback",
        "memory", "memories", "provider_payload", "request_payload",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden_keys & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
