from __future__ import annotations

"""Canonical, content-free conversation turn presentation.

This module deliberately separates persisted operation truth from browser wording.
It never creates model text, retries a provider request, mutates memory, or treats an
unknown acceptance outcome as permission to resend.
"""

from typing import Any, Mapping

TURN_PRESENTATION_SCHEMA_VERSION = "1"


def _clean(value: Any, limit: int = 240) -> str:
    return " ".join(str(value or "").split())[: max(0, int(limit))]


def _result(
    state: str,
    label: str,
    detail: str,
    *,
    accepted: bool = False,
    terminal: bool = False,
    action: str = "none",
    memory_commit_allowed: bool = False,
    draft_preserved: bool = False,
    explicit_resend_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "type": "conversation_turn_presentation",
        "schema_version": TURN_PRESENTATION_SCHEMA_VERSION,
        "state": state,
        "label": label,
        "detail": detail,
        "action": action,
        "accepted": bool(accepted),
        "terminal": bool(terminal),
        "memory_commit_allowed": bool(memory_commit_allowed),
        "draft_preserved": bool(draft_preserved),
        "explicit_resend_allowed": bool(explicit_resend_allowed),
        "automatic_retry": False,
        "automatic_resend": False,
        "provider_request_replayed": False,
        "synthetic_assistant_response": False,
        "redacted": True,
        "content_free": True,
    }


def build_turn_presentation(
    marker: Mapping[str, Any] | None = None,
    *,
    turn: Mapping[str, Any] | None = None,
    recovery: Mapping[str, Any] | None = None,
    non_acceptance: Mapping[str, Any] | None = None,
    resend_lineage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one canonical state for live, restored, and failed-turn surfaces."""
    marker = marker if isinstance(marker, Mapping) else {}
    turn = turn if isinstance(turn, Mapping) else {}
    recovery = recovery if isinstance(recovery, Mapping) else {}
    non_acceptance = non_acceptance if isinstance(non_acceptance, Mapping) else {}
    resend_lineage = resend_lineage if isinstance(resend_lineage, Mapping) else {}

    accepted = bool(marker.get("accepted_at") or marker.get("operation_id"))
    public_state = _clean(marker.get("public_state") or "", 40).lower()
    completion_state = _clean(turn.get("completion_state") or "", 40).lower()

    if not accepted and non_acceptance.get("non_acceptance_proven") is True:
        claimed = bool(resend_lineage.get("resend_acceptance_key"))
        return _result(
            "proven_unaccepted_claimed" if claimed else "proven_unaccepted",
            "Explicit resend preserved" if claimed else "Submission was not accepted",
            (
                "Persisted evidence proves the earlier submission was not accepted. "
                + (
                    "The same explicit resend identity is preserved for operator-controlled resume."
                    if claimed
                    else "Review the preserved draft before explicitly sending it with a new acceptance identity."
                )
            ),
            terminal=True,
            action="review_draft",
            draft_preserved=True,
            explicit_resend_allowed=True,
        )

    if public_state == "running":
        if marker.get("cancellation_requested"):
            return _result(
                "accepted_cancelling",
                "Cancellation requested",
                "The turn was accepted and cancellation was requested for that exact operation. No retry or resend was started.",
                accepted=True,
                action="reconcile",
            )
        return _result(
            "accepted_running",
            "Accepted and responding",
            "The turn was accepted. Eidolon is reconciling the exact persisted operation without replaying it.",
            accepted=True,
            action="reconcile",
        )

    successful_recovery = bool(recovery.get("successful_recovery_turn_id"))
    recovery_available = bool(recovery.get("retryable") and recovery.get("acceptance_proven"))
    if successful_recovery:
        return _result(
            "accepted_recovered",
            "Recovery completed",
            "A linked recovery completed once for the accepted failed turn. The original request was not replayed.",
            accepted=True,
            terminal=True,
            action="review_history",
            memory_commit_allowed=True,
        )

    if public_state == "completed" or (turn.get("success") is True and completion_state == "completed"):
        late = bool(marker.get("client_disconnected") or marker.get("reconciled_late"))
        return _result(
            "accepted_completed_late" if late else "accepted_completed",
            "Reply restored" if late else "Reply completed",
            (
                "The accepted reply completed while the viewer was away and was attached once."
                if late
                else "The accepted reply completed and was persisted once."
            ),
            accepted=True,
            terminal=True,
            action="none",
            memory_commit_allowed=True,
        )

    if public_state == "cancelled" or completion_state == "cancelled":
        return _result(
            "accepted_cancelled",
            "Cancelled",
            "The accepted turn was cancelled safely. Partial assistant output is not eligible for memory or continuity.",
            accepted=True,
            terminal=True,
            action="review_history",
        )

    if public_state == "failed" or completion_state == "failed":
        if recovery_available:
            return _result(
                "accepted_recovery_available",
                "Accepted turn needs explicit recovery",
                "The request was accepted and failed. A linked recovery is available only through an explicit operator action.",
                accepted=True,
                terminal=True,
                action="linked_recovery",
            )
        return _result(
            "accepted_failed",
            "Accepted turn failed",
            "The accepted operation failed and will not be retried or resent automatically.",
            accepted=True,
            terminal=True,
            action="review_history",
        )

    if public_state == "uncertain" or completion_state in {"uncertain", "interrupted"}:
        return _result(
            "accepted_uncertain" if accepted else "acceptance_unknown",
            "Completion uncertain" if accepted else "Acceptance not proven",
            (
                "The request was accepted, but terminal completion is not yet proven. Reconcile the persisted operation; do not resend it."
                if accepted
                else "Acceptance could not be proven. Keep the draft and check persisted evidence before any explicit resend."
            ),
            accepted=accepted,
            terminal=True,
            action="reconcile" if accepted else "review_draft",
            draft_preserved=not accepted,
        )

    return _result(
        "idle",
        "Conversation ready",
        "No persisted turn currently needs cancellation, recovery, retry, or resend attention.",
    )


def turn_presentation_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "user_message", "assistant_response", "prompt", "response",
        "provider_payload", "credentials", "endpoint", "model", "draft_content",
        "raw_response", "command_output", "receipt_payload",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return False
