from __future__ import annotations

"""Explicit failed-turn recovery for private conversation sessions.

Recovery never changes providers or models, never installs or deletes models, and
never replays completed turns. It reuses the original user memory when present so
an operator retry cannot duplicate user memories. A successful recovery is linked
to the failed source operation and blocks duplicate successful replays.
"""

import hashlib
import hmac
import threading
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from conversation_runtime import ConversationRuntimeResult
from conversation_experience import retry_allowed_for_failure
from conversation_sessions import conversation_session_turns, load_conversation_session
from conversation_retry_evidence import retry_evidence_for_turn
from conversation_operations import load_operation_marker, operation_cue_token


_RECOVERY_LOCK = threading.RLock()
RECOVERY_KIND_FAILED_TURN_RETRY = "failed_turn_retry"


class ConversationRecoveryError(ValueError):
    pass


def _find_turn(session_id: str, turn_id: str) -> dict[str, Any]:
    session = load_conversation_session(session_id, include_turns=False)
    if not session:
        raise ConversationRecoveryError("Conversation session not found.")
    token = str(turn_id or "").strip()
    for turn in conversation_session_turns(session_id):
        if str(turn.get("id") or "") == token:
            return turn
    raise ConversationRecoveryError("Conversation turn not found.")


def recovery_history(session_id: str, turn_id: str) -> dict[str, Any]:
    """Return bounded content-free history derived from persisted linked turns."""
    token = str(turn_id or "").strip()
    attempts: list[dict[str, Any]] = []
    for turn in conversation_session_turns(session_id):
        if str(turn.get("recovery_of") or "") != token:
            continue
        attempts.append({
            "turn_id": str(turn.get("id") or ""),
            "created_at": str(turn.get("created_at") or ""),
            "completion_state": str(turn.get("completion_state") or "unknown"),
            "failure_category": str(turn.get("failure_category") or ""),
            "success": bool(turn.get("success")),
            "recovery_kind": str(turn.get("recovery_kind") or ""),
        })
    successful = next(
        (attempt for attempt in attempts if attempt.get("success") is True and attempt.get("completion_state") == "completed"),
        None,
    )
    latest = attempts[-1] if attempts else None
    return {
        "source_turn_id": token,
        "attempt_count": len(attempts),
        "attempts": attempts,
        "latest_recovery_turn_id": str((latest or {}).get("turn_id") or ""),
        "latest_recovery_state": str((latest or {}).get("completion_state") or "none"),
        "latest_failure_category": str((latest or {}).get("failure_category") or ""),
        "successful_recovery_turn_id": str((successful or {}).get("turn_id") or ""),
        "recovered": successful is not None,
        "redacted": True,
    }


def successful_recovery_for(session_id: str, turn_id: str) -> dict[str, Any] | None:
    successful_id = str(recovery_history(session_id, turn_id).get("successful_recovery_turn_id") or "")
    if not successful_id:
        return None
    return next(
        (turn for turn in conversation_session_turns(session_id) if str(turn.get("id") or "") == successful_id),
        None,
    )


def recovery_cue_token(session_id: str, turn_id: str) -> str:
    """Fingerprint the exact source operation and current linked recovery history."""
    marker = load_operation_marker(str(turn_id or ""))
    if not marker or str(marker.get("session_id") or "") != str(session_id or ""):
        return ""
    source_cue = operation_cue_token(marker)
    history = recovery_history(session_id, turn_id)
    attempt_parts = [
        "|".join((
            str(attempt.get("turn_id") or ""),
            str(attempt.get("completion_state") or ""),
            "1" if attempt.get("success") else "0",
        ))
        for attempt in history.get("attempts", [])
        if isinstance(attempt, dict)
    ]
    payload = "|".join(("eidolon-recovery-cue-v1", source_cue, *attempt_parts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_recovery_cue(session_id: str, turn_id: str, expected_recovery_cue: str) -> str:
    """Require an exact current recovery fingerprint before a mutable recovery action."""
    expected = str(expected_recovery_cue or "").strip()
    if not expected:
        raise ConversationRecoveryError(
            "This recovery control has no persisted state token. Refresh the conversation before trying again."
        )
    current = recovery_cue_token(session_id, turn_id)
    if not current or not hmac.compare_digest(expected, current):
        raise ConversationRecoveryError(
            "This recovery control is stale because the failed turn changed. Refresh the conversation before trying again."
        )
    return current


def recovery_state(session_id: str, turn_id: str) -> dict[str, Any]:
    turn = _find_turn(session_id, turn_id)
    completed = turn.get("success") is True and str(turn.get("completion_state") or "") == "completed"
    history = recovery_history(session_id, turn_id)
    recovered_turn_id = str(history.get("successful_recovery_turn_id") or "")
    recovered = next(
        (candidate for candidate in conversation_session_turns(session_id) if str(candidate.get("id") or "") == recovered_turn_id),
        None,
    ) if recovered_turn_id else None
    evidence = retry_evidence_for_turn(session_id, str(turn.get("id") or ""))
    retryable = (
        bool(str(turn.get("user_message") or "").strip())
        and not completed
        and recovered is None
        and retry_allowed_for_failure(turn.get("failure_category") or turn.get("completion_state"))
        and evidence.get("linked_recovery_allowed") is True
    )
    return {
        "session_id": session_id,
        "turn_id": str(turn.get("id") or ""),
        "retryable": retryable,
        "completion_state": str(turn.get("completion_state") or ""),
        "failure_category": str(turn.get("failure_category") or ""),
        "successful_recovery_turn_id": str((recovered or {}).get("id") or ""),
        "recovery_attempt_count": int(history.get("attempt_count") or 0),
        "latest_recovery_turn_id": str(history.get("latest_recovery_turn_id") or ""),
        "latest_recovery_state": str(history.get("latest_recovery_state") or "none"),
        "latest_recovery_failure_category": str(history.get("latest_failure_category") or ""),
        "recovery_history": list(history.get("attempts") or []),
        "recovery_cue_token": recovery_cue_token(session_id, str(turn.get("id") or "")),
        "completed_turn_replay_blocked": completed,
        "acceptance_proven": bool(evidence.get("acceptance_proven")),
        "accepted_at": str(evidence.get("accepted_at") or ""),
        "operation_state": str(evidence.get("operation_state") or "unknown"),
        "linked_recovery_allowed": bool(evidence.get("linked_recovery_allowed")),
        "resend_allowed": False,
        "fresh_acceptance_identity_required": False,
        "automatic_retry": False,
        "automatic_resend": False,
    }


def retry_failed_conversation_turn(
    session_id: str,
    turn_id: str,
    *,
    use_ai: bool = True,
    source: str = "conversation_recovery",
    expected_recovery_cue: str = "",
) -> ConversationRuntimeResult:
    """Run one explicit linked recovery for an accepted failed turn."""
    with _RECOVERY_LOCK:
        turn = _find_turn(session_id, turn_id)
        if expected_recovery_cue:
            validate_recovery_cue(session_id, str(turn.get("id") or ""), expected_recovery_cue)
        evidence = retry_evidence_for_turn(session_id, str(turn.get("id") or ""))
        if not evidence.get("acceptance_proven"):
            raise ConversationRecoveryError("This failed turn has no persisted acceptance proof and cannot use accepted-turn recovery.")
        if not evidence.get("linked_recovery_allowed"):
            raise ConversationRecoveryError("Persisted operation evidence does not allow a linked recovery for this turn.")
        if turn.get("success") is True and str(turn.get("completion_state") or "") == "completed":
            raise ConversationRecoveryError(
                "Completed turns cannot be regenerated by this recovery control because their assistant memory is already committed."
            )
        existing = successful_recovery_for(session_id, turn_id)
        if existing:
            raise ConversationRecoveryError("This failed turn already has a successful recovery.")
        message = str(turn.get("user_message") or "").strip()
        if not message:
            raise ConversationRecoveryError("The failed turn has no user message to retry.")
        from conversation_runtime import run_conversation_turn
        return run_conversation_turn(
            message,
            source=source,
            use_ai=use_ai,
            session_id=session_id,
            recovery_of=str(turn.get("id") or ""),
            recovery_kind=RECOVERY_KIND_FAILED_TURN_RETRY,
        )
