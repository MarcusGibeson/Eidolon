from __future__ import annotations

"""Canonical content-free recovery presentation for one conversation session."""

from typing import Any

from conversation_operations import latest_operation_marker
from conversation_recovery import recovery_state
from conversation_resend_lineage import resend_candidate_for_session
from provider_recovery_evidence import provider_resume_cue

RECOVERY_CONTRACT_SCHEMA_VERSION = "1"


def _contract(
    session_id: str,
    state: str,
    label: str,
    detail: str,
    *,
    action: str = "none",
    operation_id: str = "",
    provider_state: str = "unknown",
    acceptance_proven: bool = False,
    explicit_resend: bool = False,
) -> dict[str, Any]:
    return {
        "type": "conversation_recovery_contract",
        "schema_version": RECOVERY_CONTRACT_SCHEMA_VERSION,
        "session_id": str(session_id or ""),
        "state": state,
        "label": label,
        "detail": detail,
        "action": action,
        "operation_id": str(operation_id or ""),
        "provider_state": str(provider_state or "unknown"),
        "acceptance_proven": bool(acceptance_proven),
        "explicit_resend": bool(explicit_resend),
        "automatic_retry": False,
        "automatic_resend": False,
        "provider_request_replayed": False,
        "redacted": True,
        "content_free": True,
    }


def conversation_recovery_contract(session_id: str) -> dict[str, Any]:
    """Return one canonical recovery state without mutating provider or conversation data."""
    session = str(session_id or "").strip()
    provider = provider_resume_cue()
    provider_state = str(provider.get("state") or "unknown")
    marker = None
    try:
        marker = latest_operation_marker(session) if session else None
    except ValueError:
        marker = None
    if marker:
        operation_id = str(marker.get("operation_id") or "")
        operation_state = str(marker.get("public_state") or "unknown")
        if operation_state == "running":
            return _contract(
                session, "accepted_reconciling", "Accepted turn is reconciling",
                "The request was accepted. Eidolon is checking the exact persisted operation without replaying it.",
                action="reconcile", operation_id=operation_id, provider_state=provider_state, acceptance_proven=True,
            )
        if operation_state in {"failed", "cancelled", "uncertain"} and marker.get("final_session_turn_recorded"):
            try:
                recovery = recovery_state(session, operation_id)
            except ValueError:
                recovery = None
            if recovery and recovery.get("successful_recovery_turn_id"):
                return _contract(
                    session, "accepted_recovered", "Accepted turn recovered",
                    "A linked recovery completed for the accepted failed turn. The original provider request was not replayed.",
                    action="review_history", operation_id=operation_id, provider_state=provider_state, acceptance_proven=True,
                )
            if recovery and recovery.get("retryable"):
                return _contract(
                    session, "accepted_recovery_available", "Accepted turn needs explicit recovery",
                    "Persisted evidence proves acceptance. A linked recovery is available, but it will run only after an explicit operator action.",
                    action="linked_recovery", operation_id=operation_id, provider_state=provider_state, acceptance_proven=True,
                )
            return _contract(
                session, "accepted_terminal", "Accepted turn reached a terminal state",
                "The accepted operation will not be resent automatically. Review its persisted state before taking another action.",
                action="review_history", operation_id=operation_id, provider_state=provider_state, acceptance_proven=True,
            )
    candidate = None
    try:
        candidate = resend_candidate_for_session(session) if session else None
    except ValueError:
        candidate = None
    if candidate:
        if candidate.get("claim_pending"):
            return _contract(
                session, "explicit_resend_claimed", "Explicit resend claim preserved",
                "The original submission was proven unaccepted. Resume the same claimed acceptance identity only by pressing Send explicitly.",
                action="review_draft", provider_state=provider_state, explicit_resend=True,
            )
        return _contract(
            session, "explicit_resend_available", "Draft is eligible for explicit resend",
            "Persisted evidence proves the earlier submission was not accepted. Review the draft and press Send to create one new acceptance identity.",
            action="review_draft", provider_state=provider_state, explicit_resend=True,
        )
    if provider.get("visible") and not provider.get("can_resume_composition"):
        label = str(provider.get("label") or "Provider unavailable")
        detail = str(provider.get("detail") or "Provider-backed generation is unavailable. Local conversation history and drafts remain available.")
        return _contract(
            session, "provider_unavailable", label, detail,
            action="check_provider", provider_state=provider_state,
        )
    if provider.get("visible") and provider.get("can_resume_composition"):
        return _contract(
            session, "provider_recovered", "Configured provider recovery verified",
            "A persisted readiness result confirms provider-backed composition may resume. No accepted request was replayed.",
            action="resume_composition", provider_state=provider_state,
        )
    return _contract(
        session, "ready", "Conversation ready",
        "No persisted recovery action currently needs attention.",
        provider_state=provider_state,
    )


def recovery_contract_contains_private_fields(value: dict[str, Any]) -> bool:
    forbidden = {
        "message", "message_text", "user_message", "assistant_response", "prompt", "response",
        "provider_payload", "credentials", "endpoint", "model", "draft", "draft_content", "raw_response",
        "command_output", "receipt_payload",
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
