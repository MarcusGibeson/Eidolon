from __future__ import annotations

"""Content-free lineage for operator-initiated resends of proven-unaccepted turns.

A resend lineage binds one persisted non-acceptance record to exactly one fresh
acceptance identity. The claim survives browser reloads and interrupted server
processes, and it never stores draft text, prompts, responses, provider details,
or credentials. Accepted requests are never converted into resend candidates.
"""

import hashlib
import hmac
import json
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from paths import DATA_DIR
from conversation_operations import find_operation_by_acceptance_key, load_operation_marker
from conversation_retry_evidence import list_non_acceptance_evidence, load_non_acceptance_evidence

RESEND_LINEAGE_SCHEMA_VERSION = "1"
CONVERSATION_RESEND_LINEAGE_DIR = DATA_DIR / "conversation_runtime" / "resend_lineage"
_LOCK_TIMEOUT_SECONDS = 5.0
_STALE_LOCK_SECONDS = 30.0
_SESSION_ID_PATTERN = re.compile(r"^conversation_session_[0-9]{8}T[0-9]{6}_[a-f0-9]{10}$")
_ACCEPTANCE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
_ALLOWED_STATES = {"claimed", "accepted"}


class ConversationResendLineageError(ValueError):
    pass


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_session_id(value: str) -> str:
    token = str(value or "").strip()
    if not _SESSION_ID_PATTERN.fullmatch(token):
        raise ConversationResendLineageError("Invalid conversation session identifier.")
    return token


def _validate_acceptance_key(value: str) -> str:
    token = str(value or "").strip()
    if not _ACCEPTANCE_KEY_PATTERN.fullmatch(token):
        raise ConversationResendLineageError("Invalid conversation acceptance key.")
    return token


def _lineage_path(session_id: str, source_acceptance_key: str) -> Path:
    session = _validate_session_id(session_id)
    source = _validate_acceptance_key(source_acceptance_key)
    return CONVERSATION_RESEND_LINEAGE_DIR / session / f"{source}.json"


def _lock_path(session_id: str, source_acceptance_key: str) -> Path:
    path = _lineage_path(session_id, source_acceptance_key)
    return path.with_suffix(".claim.lock")


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True), encoding="utf-8")
        for attempt in range(5):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _lineage_lock(session_id: str, source_acceptance_key: str) -> Iterator[None]:
    """Acquire a small cross-process lock for one source acceptance identity."""
    path = _lock_path(session_id, source_acceptance_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, f"{os.getpid()}\n".encode("ascii", errors="ignore"))
        except FileExistsError:
            try:
                age = max(0.0, time.time() - path.stat().st_mtime)
            except OSError:
                age = 0.0
            if age >= _STALE_LOCK_SECONDS:
                try:
                    path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise ConversationResendLineageError(
                    "This explicit resend is already being claimed by another process. Refresh before trying again."
                )
            time.sleep(0.02)
    try:
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            path.unlink()
        except OSError:
            pass


def _public_record(value: Mapping[str, Any] | None, *, duplicate_claim: bool = False) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("type") != "conversation_resend_lineage":
        return None
    state = str(value.get("state") or "claimed")
    if state not in _ALLOWED_STATES:
        state = "claimed"
    return {
        "type": "conversation_resend_lineage",
        "schema_version": RESEND_LINEAGE_SCHEMA_VERSION,
        "session_id": str(value.get("session_id") or ""),
        "source_acceptance_key": str(value.get("source_acceptance_key") or "")[:96],
        "resend_acceptance_key": str(value.get("resend_acceptance_key") or "")[:96],
        "source_evidence_token": str(value.get("source_evidence_token") or "")[:64],
        "state": state,
        "claimed_at": str(value.get("claimed_at") or "")[:40],
        "accepted_at": str(value.get("accepted_at") or "")[:40],
        "operation_id": str(value.get("operation_id") or "")[:80],
        "duplicate_claim": bool(duplicate_claim),
        "operator_initiated": True,
        "fresh_acceptance_identity": True,
        "automatic_resend": False,
        "provider_request_replayed": False,
        "resume_same_acceptance_identity": state == "claimed",
        "redacted": True,
        "content_free": True,
        "contains_message": False,
        "contains_prompt_or_response": False,
        "contains_provider_payload": False,
        "contains_credentials": False,
    }


def load_resend_lineage(session_id: str, source_acceptance_key: str) -> dict[str, Any] | None:
    try:
        value = _load_json(_lineage_path(session_id, source_acceptance_key))
    except ConversationResendLineageError:
        return None
    return _public_record(value)


def find_resend_lineage_by_acceptance_key(session_id: str, resend_acceptance_key: str) -> dict[str, Any] | None:
    session = _validate_session_id(session_id)
    resend = _validate_acceptance_key(resend_acceptance_key)
    directory = CONVERSATION_RESEND_LINEAGE_DIR / session
    if not directory.exists():
        return None
    for path in sorted(directory.glob("*.json")):
        value = _public_record(_load_json(path))
        if value and value.get("resend_acceptance_key") == resend:
            return value
    return None


def claim_explicit_resend(
    session_id: str,
    source_acceptance_key: str,
    resend_acceptance_key: str,
    *,
    source_evidence_token: str,
) -> dict[str, Any]:
    """Bind one proven-unaccepted source to one fresh acceptance identity."""
    session = _validate_session_id(session_id)
    source = _validate_acceptance_key(source_acceptance_key)
    resend = _validate_acceptance_key(resend_acceptance_key)
    if source == resend:
        raise ConversationResendLineageError("An explicit resend must use a fresh acceptance identity.")
    evidence = load_non_acceptance_evidence(session, source)
    supplied_token = str(source_evidence_token or "").strip()
    current_token = str((evidence or {}).get("evidence_token") or "")
    if not evidence or not supplied_token or not current_token or not hmac.compare_digest(supplied_token, current_token):
        raise ConversationResendLineageError(
            "The non-acceptance evidence changed or is missing. Refresh the conversation before resending."
        )
    if find_operation_by_acceptance_key(session, source):
        raise ConversationResendLineageError("The original request is accepted and cannot be resent.")
    with _lineage_lock(session, source):
        existing_raw = _load_json(_lineage_path(session, source))
        existing = _public_record(existing_raw)
        if existing:
            if existing.get("resend_acceptance_key") != resend:
                raise ConversationResendLineageError(
                    "This original submission is already bound to another resend identity. Refresh and resume that exact claim."
                )
            return _public_record(existing_raw, duplicate_claim=True) or existing
        if find_operation_by_acceptance_key(session, resend):
            raise ConversationResendLineageError(
                "The proposed resend identity is already accepted without matching lineage evidence. Refresh before continuing."
            )
        record = {
            "type": "conversation_resend_lineage",
            "schema_version": RESEND_LINEAGE_SCHEMA_VERSION,
            "session_id": session,
            "source_acceptance_key": source,
            "resend_acceptance_key": resend,
            "source_evidence_token": current_token,
            "state": "claimed",
            "claimed_at": _now_utc(),
            "accepted_at": "",
            "operation_id": "",
        }
        _atomic_write(_lineage_path(session, source), record)
        return _public_record(record) or record


def finalize_explicit_resend(
    session_id: str,
    source_acceptance_key: str,
    resend_acceptance_key: str,
    operation_id: str,
) -> dict[str, Any]:
    session = _validate_session_id(session_id)
    source = _validate_acceptance_key(source_acceptance_key)
    resend = _validate_acceptance_key(resend_acceptance_key)
    with _lineage_lock(session, source):
        path = _lineage_path(session, source)
        record = _load_json(path)
        public = _public_record(record)
        if not record or not public:
            raise ConversationResendLineageError("Explicit resend lineage was not claimed.")
        if public.get("resend_acceptance_key") != resend:
            raise ConversationResendLineageError("Explicit resend lineage belongs to another acceptance identity.")
        marker = load_operation_marker(operation_id)
        if not marker or marker.get("session_id") != session or marker.get("acceptance_key") != resend:
            raise ConversationResendLineageError("The accepted operation does not match the claimed resend lineage.")
        if str(record.get("state") or "claimed") != "accepted":
            record["state"] = "accepted"
            record["accepted_at"] = str(marker.get("accepted_at") or _now_utc())
            record["operation_id"] = str(marker.get("operation_id") or "")
            _atomic_write(path, record)
        return _public_record(record) or record


def resend_candidate_for_session(session_id: str) -> dict[str, Any] | None:
    """Return the newest unresolved proven-unaccepted source for explicit review."""
    session = _validate_session_id(session_id)
    for evidence in list_non_acceptance_evidence(session):
        source = str(evidence.get("acceptance_key") or "")
        if not source or find_operation_by_acceptance_key(session, source):
            continue
        lineage = load_resend_lineage(session, source)
        if lineage and lineage.get("state") == "accepted":
            continue
        return {
            "type": "conversation_explicit_resend_candidate",
            "schema_version": RESEND_LINEAGE_SCHEMA_VERSION,
            "session_id": session,
            "source_acceptance_key": source,
            "source_evidence_token": str(evidence.get("evidence_token") or ""),
            "evidence_recorded_at": str(evidence.get("recorded_at") or ""),
            "reason": str(evidence.get("reason") or "acceptance_internal_failure"),
            "resend_acceptance_key": str((lineage or {}).get("resend_acceptance_key") or ""),
            "claim_state": str((lineage or {}).get("state") or "unclaimed"),
            "claim_pending": bool(lineage and lineage.get("state") == "claimed"),
            "resend_allowed": True,
            "fresh_acceptance_identity_required": not bool(lineage),
            "resume_same_acceptance_identity": bool(lineage and lineage.get("state") == "claimed"),
            "operator_initiated": True,
            "automatic_resend": False,
            "redacted": True,
            "content_free": True,
        }
    return None


def resend_lineage_contains_private_fields(value: Mapping[str, Any]) -> bool:
    forbidden = {
        "content", "text", "message", "message_text", "user_message", "assistant_response",
        "prompt", "prompts", "partial", "partial_tokens", "memory", "memories", "provider",
        "model", "endpoint", "credentials", "secret", "raw_response", "draft", "draft_content",
        "command_output", "receipt_payload",
    }
    stack: list[Any] = [dict(value)]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
