from __future__ import annotations

"""Explicit cancellation-first generation steering for v1086.3.

Steering never mutates the accepted request, never appends redirect text to the
running provider call, and never submits a replacement automatically.  It asks
for cancellation of one exact operation and returns bounded evidence requiring a
fresh acceptance identity for any redirected user turn.
"""

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from conversation_operations import load_operation_marker, operation_cue_token

MAX_STEERING_MESSAGE_CHARS = 4_000
STEERING_SCHEMA_VERSION = "1"


class ConversationSteeringError(ValueError):
    pass


@dataclass(frozen=True)
class GenerationSteeringPlan:
    schema_version: str
    session_id: str
    operation_id: str
    operation_state: str
    cancellation_requested: bool
    redirect_present: bool
    redirect_digest: str
    redirect_length: int
    steering_allowed: bool
    reason: str
    fresh_acceptance_identity_required: bool = True
    automatic_resend: bool = False
    accepted_request_replay: bool = False
    partial_response_committed: bool = False
    assistant_memory_committed_by_steering: bool = False
    provider_invoked_by_planner: bool = False
    writes_redirect_content: bool = False
    preserves_original_operation: bool = True
    redacted: bool = True

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def _digest(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def build_generation_steering_plan(
    session_id: str,
    operation_id: str,
    redirect_message: str = "",
    *,
    marker: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    session_token = str(session_id or "").strip()
    operation_token = str(operation_id or "").strip()
    redirect = str(redirect_message or "").strip()
    if len(redirect) > MAX_STEERING_MESSAGE_CHARS:
        raise ConversationSteeringError(
            f"Steering message exceeds {MAX_STEERING_MESSAGE_CHARS} characters."
        )
    persisted = dict(marker) if isinstance(marker, Mapping) else load_operation_marker(operation_token)
    if not persisted:
        state = "not_found"
        allowed = False
        reason = "operation_not_found"
        cancellation_requested = False
    elif str(persisted.get("session_id") or "") != session_token:
        state = str(persisted.get("public_state") or "unknown")
        allowed = False
        reason = "session_mismatch"
        cancellation_requested = bool(persisted.get("cancellation_requested"))
    else:
        state = str(persisted.get("public_state") or "unknown")
        cancellation_requested = bool(persisted.get("cancellation_requested"))
        allowed = state == "running" and bool(redirect)
        if not redirect:
            reason = "redirect_required"
        elif state != "running":
            reason = "operation_terminal"
        elif cancellation_requested:
            reason = "cancellation_already_requested"
        else:
            reason = "explicit_cancel_then_fresh_send"
    plan = GenerationSteeringPlan(
        schema_version=STEERING_SCHEMA_VERSION,
        session_id=session_token,
        operation_id=operation_token,
        operation_state=state,
        cancellation_requested=cancellation_requested,
        redirect_present=bool(redirect),
        redirect_digest=_digest(redirect) if redirect else "",
        redirect_length=len(redirect),
        steering_allowed=allowed,
        reason=reason,
    ).public_summary()
    plan["operation_cue_token"] = operation_cue_token(persisted) if persisted else ""
    return plan


def request_generation_steering(
    session_id: str,
    operation_id: str,
    redirect_message: str,
) -> dict[str, Any]:
    """Request cancellation for one exact operation without submitting redirect text."""
    plan = build_generation_steering_plan(session_id, operation_id, redirect_message)
    if plan.get("reason") == "session_mismatch":
        raise ConversationSteeringError("The active operation belongs to another conversation session.")
    if plan.get("reason") == "operation_not_found":
        raise ConversationSteeringError("Conversation operation was not found.")
    if not plan.get("redirect_present"):
        raise ConversationSteeringError("A non-empty redirect message is required for steering.")
    if str(plan.get("operation_state") or "") != "running":
        raise ConversationSteeringError("Only a running conversation operation can be steered.")

    # Lazy import avoids coupling the runtime module back into the evidence builder.
    from dashboard_chat_console import cancel_dashboard_chat_operation

    cancellation = cancel_dashboard_chat_operation(operation_id)
    status = str(cancellation.get("status") or "")
    if not cancellation.get("ok") and status not in {"cancellation_requested", "cancelled"}:
        raise ConversationSteeringError(
            str(cancellation.get("message") or "The running operation could not be cancelled for steering.")
        )
    result = dict(plan)
    result.update({
        "ok": True,
        "status": "awaiting_terminal_cancellation",
        "cancellation": cancellation,
        "cancellation_requested": True,
        "redirect_submitted": False,
        "fresh_acceptance_identity_required": True,
        "next_action": "wait_for_cancelled_then_submit_redirect_explicitly",
    })
    return result


def steering_evidence_contains_private_fields(value: Mapping[str, Any]) -> bool:
    forbidden = {
        "redirect_message", "message", "prompt", "response", "assistant_response",
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
