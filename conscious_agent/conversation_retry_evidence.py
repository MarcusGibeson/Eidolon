from __future__ import annotations

"""Redacted evidence for explicit conversation retry and resend boundaries.

Accepted operations are never described as unaccepted and are never automatically
replayed. A fresh client acceptance identity is permitted only when a bounded
persisted record proves that the earlier submission was not accepted.
"""

import hashlib
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from paths import DATA_DIR
from conversation_operations import find_operation_by_acceptance_key, load_operation_marker

RETRY_EVIDENCE_SCHEMA_VERSION = "1"
CONVERSATION_RETRY_EVIDENCE_DIR = DATA_DIR / "conversation_runtime" / "retry_evidence"
_LOCK = threading.RLock()
_SESSION_ID_PATTERN = re.compile(r"^conversation_session_[0-9]{8}T[0-9]{6}_[a-f0-9]{10}$")
_ACCEPTANCE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,96}$")
_ALLOWED_REASONS = {"acceptance_rejected", "acceptance_validation_failed", "acceptance_internal_failure"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_session_id(value: str) -> str:
    token = str(value or "").strip()
    if not _SESSION_ID_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation session identifier.")
    return token


def _validate_acceptance_key(value: str) -> str:
    token = str(value or "").strip()
    if not _ACCEPTANCE_KEY_PATTERN.fullmatch(token):
        raise ValueError("Invalid conversation acceptance key.")
    return token


def _evidence_path(session_id: str, acceptance_key: str) -> Path:
    session = _validate_session_id(session_id)
    key = _validate_acceptance_key(acceptance_key)
    return CONVERSATION_RETRY_EVIDENCE_DIR / session / f"{key}.json"


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(dict(value), indent=2, sort_keys=True), encoding="utf-8")
        for attempt in range(5):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)



def _evidence_token(value: Mapping[str, Any]) -> str:
    payload = "|".join((
        "eidolon-non-acceptance-v1",
        str(value.get("session_id") or ""),
        str(value.get("acceptance_key") or ""),
        str(value.get("recorded_at") or ""),
        str(value.get("reason") or "acceptance_internal_failure"),
    ))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _public_record(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or value.get("type") != "conversation_non_acceptance_evidence":
        return None
    reason = str(value.get("reason") or "acceptance_internal_failure")
    if reason not in _ALLOWED_REASONS:
        reason = "acceptance_internal_failure"
    return {
        "type": "conversation_non_acceptance_evidence",
        "schema_version": RETRY_EVIDENCE_SCHEMA_VERSION,
        "session_id": str(value.get("session_id") or ""),
        "acceptance_key": str(value.get("acceptance_key") or "")[:96],
        "recorded_at": str(value.get("recorded_at") or "")[:40],
        "reason": reason,
        "evidence_token": _evidence_token(value),
        "acceptance_proven": False,
        "non_acceptance_proven": True,
        "resend_allowed": True,
        "fresh_acceptance_identity_required": True,
        "automatic_resend": False,
        "provider_request_replayed": False,
        "redacted": True,
        "contains_message": False,
        "contains_prompt_or_response": False,
        "contains_provider_payload": False,
        "contains_credentials": False,
    }


def load_non_acceptance_evidence(session_id: str, acceptance_key: str) -> dict[str, Any] | None:
    try:
        path = _evidence_path(session_id, acceptance_key)
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, json.JSONDecodeError):
        return None
    return _public_record(raw)


def persist_non_acceptance_evidence(
    session_id: str,
    acceptance_key: str,
    *,
    reason: str = "acceptance_internal_failure",
) -> dict[str, Any]:
    """Persist proof only after rechecking that no accepted operation exists."""
    with _LOCK:
        session = _validate_session_id(session_id)
        key = _validate_acceptance_key(acceptance_key)
        accepted = find_operation_by_acceptance_key(session, key)
        if accepted:
            raise ValueError("Non-acceptance evidence cannot be recorded for an accepted operation.")
        existing = load_non_acceptance_evidence(session, key)
        if existing:
            return existing
        normalized_reason = str(reason or "acceptance_internal_failure")
        if normalized_reason not in _ALLOWED_REASONS:
            normalized_reason = "acceptance_internal_failure"
        record = {
            "type": "conversation_non_acceptance_evidence",
            "schema_version": RETRY_EVIDENCE_SCHEMA_VERSION,
            "session_id": session,
            "acceptance_key": key,
            "recorded_at": _now_utc(),
            "reason": normalized_reason,
        }
        _atomic_write(_evidence_path(session, key), record)
        return _public_record(record) or record



def list_non_acceptance_evidence(session_id: str) -> list[dict[str, Any]]:
    """List bounded evidence newest-first without exposing draft or provider content."""
    try:
        session = _validate_session_id(session_id)
    except ValueError:
        return []
    directory = CONVERSATION_RETRY_EVIDENCE_DIR / session
    if not directory.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in directory.glob("*.json"):
        public = _public_record(_load_json_file(path))
        if public:
            rows.append(public)
    return sorted(rows, key=lambda item: (str(item.get("recorded_at") or ""), str(item.get("acceptance_key") or "")), reverse=True)


def _load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None

def retry_evidence_for_turn(session_id: str, turn_id: str) -> dict[str, Any]:
    """Classify one persisted turn using its exact operation marker."""
    marker = load_operation_marker(str(turn_id or ""))
    marker_matches = bool(marker and str(marker.get("session_id") or "") == str(session_id or ""))
    accepted = bool(marker_matches and marker.get("accepted_at"))
    state = str((marker or {}).get("public_state") or "unknown")
    terminal = state in {"completed", "failed", "cancelled", "uncertain"}
    return {
        "session_id": str(session_id or ""),
        "turn_id": str(turn_id or ""),
        "acceptance_proven": accepted,
        "accepted_at": str((marker or {}).get("accepted_at") or ""),
        "operation_state": state,
        "terminal_evidence": terminal,
        "linked_recovery_allowed": bool(accepted and terminal and state != "completed"),
        "resend_allowed": False,
        "fresh_acceptance_identity_required": False,
        "automatic_retry": False,
        "automatic_resend": False,
        "redacted": True,
    }


def resend_evidence(session_id: str, acceptance_key: str) -> dict[str, Any]:
    """Return resend eligibility without creating a new acceptance identity."""
    accepted = find_operation_by_acceptance_key(session_id, acceptance_key)
    if accepted:
        return {
            "acceptance_proven": True,
            "non_acceptance_proven": False,
            "resend_allowed": False,
            "fresh_acceptance_identity_required": False,
            "operation_id": str(accepted.get("operation_id") or ""),
            "operation_state": str(accepted.get("public_state") or "running"),
            "automatic_resend": False,
            "redacted": True,
        }
    evidence = load_non_acceptance_evidence(session_id, acceptance_key)
    return evidence or {
        "acceptance_proven": False,
        "non_acceptance_proven": False,
        "resend_allowed": False,
        "fresh_acceptance_identity_required": False,
        "automatic_resend": False,
        "redacted": True,
    }
