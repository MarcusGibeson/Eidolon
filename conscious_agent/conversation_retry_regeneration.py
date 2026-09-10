from __future__ import annotations

"""Explicitly distinguish failed retry, completed regeneration, and resend.

No action is automatic.  Completed-response regeneration preserves the original
turn and reuses its accepted user-memory identity when available.  Explicit
resend is a new user turn with a fresh operation identity.  Failed retry remains
bound to the existing persisted recovery cue and recovery implementation.
"""

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from conversation_operations import load_operation_marker, new_conversation_operation_id
from conversation_recovery import retry_failed_conversation_turn, recovery_state
from conversation_runtime import ConversationRuntimeResult, run_conversation_turn
from conversation_sessions import conversation_session_turns, load_conversation_session

RETRY_REGENERATION_SCHEMA_VERSION = "1"
ACTION_FAILED_RETRY = "failed_retry"
ACTION_REGENERATE = "regenerate_completed_response"
ACTION_RESEND = "explicit_resend"
ACTION_TYPES = (ACTION_FAILED_RETRY, ACTION_REGENERATE, ACTION_RESEND)


class ConversationTurnActionError(ValueError):
    pass


@dataclass(frozen=True)
class ConversationTurnActionPlan:
    schema_version: str
    session_id: str
    source_turn_id: str
    source_completion_state: str
    source_success: bool
    failed_retry_allowed: bool
    regeneration_allowed: bool
    explicit_resend_allowed: bool
    failed_retry_reuses_acceptance: bool
    regeneration_reuses_user_memory: bool
    resend_creates_new_user_turn: bool
    original_turn_preserved: bool = True
    automatic_retry: bool = False
    automatic_regeneration: bool = False
    automatic_resend: bool = False
    fresh_acceptance_required_for_regeneration: bool = True
    fresh_acceptance_required_for_resend: bool = True
    provider_invoked_by_planner: bool = False
    writes_state_by_planner: bool = False
    redacted: bool = True

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def _find_turn(session_id: str, turn_id: str) -> dict[str, Any]:
    session = load_conversation_session(session_id, include_turns=False)
    if not session:
        raise ConversationTurnActionError("Conversation session not found.")
    token = str(turn_id or "").strip()
    for turn in conversation_session_turns(session_id):
        if str(turn.get("id") or "") == token:
            return dict(turn)
    raise ConversationTurnActionError("Conversation turn not found.")


def build_turn_action_plan(session_id: str, turn_id: str) -> dict[str, Any]:
    turn = _find_turn(session_id, turn_id)
    completed = bool(turn.get("success")) and str(turn.get("completion_state") or "") == "completed"
    message_present = bool(str(turn.get("user_message") or "").strip())
    retry = recovery_state(session_id, turn_id)
    return ConversationTurnActionPlan(
        schema_version=RETRY_REGENERATION_SCHEMA_VERSION,
        session_id=str(session_id or ""),
        source_turn_id=str(turn_id or ""),
        source_completion_state=str(turn.get("completion_state") or "unknown"),
        source_success=bool(turn.get("success")),
        failed_retry_allowed=bool(retry.get("retryable")),
        regeneration_allowed=completed and message_present and bool(str(turn.get("assistant_response") or "").strip()),
        explicit_resend_allowed=message_present,
        failed_retry_reuses_acceptance=True,
        regeneration_reuses_user_memory=True,
        resend_creates_new_user_turn=True,
    ).public_summary()


def _fresh_operation_id(operation_id: str = "") -> str:
    token = str(operation_id or "").strip()
    if not token:
        raise ConversationTurnActionError("A fresh explicit operation identifier is required.")
    if load_operation_marker(token) is not None:
        raise ConversationTurnActionError("This fresh operation identity has already been accepted.")
    return token


def regenerate_completed_conversation_turn(
    session_id: str,
    turn_id: str,
    *,
    use_ai: bool = True,
    source: str = "conversation_regeneration",
    operation_id: str = "",
) -> ConversationRuntimeResult:
    turn = _find_turn(session_id, turn_id)
    plan = build_turn_action_plan(session_id, turn_id)
    if not plan.get("regeneration_allowed"):
        raise ConversationTurnActionError("Only a completed response with a user message can be regenerated.")
    fresh_id = _fresh_operation_id(operation_id)
    return run_conversation_turn(
        str(turn.get("user_message") or ""),
        source=source,
        use_ai=use_ai,
        session_id=session_id,
        recovery_of=str(turn_id),
        recovery_kind="completed_turn_regeneration",
        operation_id=fresh_id,
    )


def explicitly_resend_conversation_turn(
    session_id: str,
    turn_id: str,
    *,
    use_ai: bool = True,
    source: str = "conversation_explicit_resend",
    operation_id: str = "",
) -> ConversationRuntimeResult:
    turn = _find_turn(session_id, turn_id)
    if not str(turn.get("user_message") or "").strip():
        raise ConversationTurnActionError("The source turn has no user message to resend.")
    fresh_id = _fresh_operation_id(operation_id)
    return run_conversation_turn(
        str(turn.get("user_message") or ""),
        source=source,
        use_ai=use_ai,
        session_id=session_id,
        recovery_of="",
        recovery_kind="explicit_user_resend",
        operation_id=fresh_id,
    )


def execute_turn_action(
    session_id: str,
    turn_id: str,
    action: str,
    *,
    use_ai: bool = True,
    expected_recovery_cue: str = "",
    operation_id: str = "",
) -> ConversationRuntimeResult:
    token = str(action or "").strip().lower()
    if token == ACTION_FAILED_RETRY:
        return retry_failed_conversation_turn(
            session_id,
            turn_id,
            use_ai=use_ai,
            source="conversation_failed_retry",
            expected_recovery_cue=expected_recovery_cue,
        )
    if token == ACTION_REGENERATE:
        return regenerate_completed_conversation_turn(
            session_id, turn_id, use_ai=use_ai, operation_id=operation_id,
        )
    if token == ACTION_RESEND:
        return explicitly_resend_conversation_turn(
            session_id, turn_id, use_ai=use_ai, operation_id=operation_id,
        )
    raise ConversationTurnActionError("Unknown conversation turn action.")


def turn_action_evidence_contains_private_fields(value: Mapping[str, Any]) -> bool:
    forbidden = {
        "user_message", "message", "prompt", "response", "assistant_response",
        "provider_payload", "request_payload", "credentials", "receipt", "memory", "memories",
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
