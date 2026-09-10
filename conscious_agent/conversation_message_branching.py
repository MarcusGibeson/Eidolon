from __future__ import annotations

"""Explicit message editing by branch creation for v1086.5.

The source transcript is immutable. Editing an earlier user message creates a new
private conversation with a copied prefix and a draft containing the edited user
message. Nothing is sent until the operator explicitly submits that new draft.
"""

import hashlib
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from conversation_sessions import create_conversation_branch_from_turn

MESSAGE_BRANCH_SCHEMA_VERSION = "1"
MAX_EDITED_MESSAGE_CHARS = 20_000


class ConversationBranchError(ValueError):
    pass


@dataclass(frozen=True)
class MessageBranchPlan:
    schema_version: str
    source_session_id: str
    source_turn_id: str
    edited_message_digest: str
    edited_message_length: int
    branch_request_digest: str
    branch_allowed: bool
    original_session_preserved: bool = True
    original_turn_preserved: bool = True
    raw_transcript_rewritten: bool = False
    provider_invoked: bool = False
    message_submitted: bool = False
    automatic_branch_creation: bool = False
    explicit_operator_action_required: bool = True
    fresh_acceptance_required_to_send: bool = True
    redacted: bool = True

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def build_message_branch_plan(
    session_id: str, turn_id: str, edited_user_message: str, branch_request_id: str,
) -> dict[str, Any]:
    text = str(edited_user_message or "").strip()
    request_token = str(branch_request_id or "").strip()
    if len(text) > MAX_EDITED_MESSAGE_CHARS:
        raise ConversationBranchError(f"Edited message exceeds {MAX_EDITED_MESSAGE_CHARS} characters.")
    return MessageBranchPlan(
        schema_version=MESSAGE_BRANCH_SCHEMA_VERSION,
        source_session_id=str(session_id or "").strip(),
        source_turn_id=str(turn_id or "").strip(),
        edited_message_digest=hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        edited_message_length=len(text),
        branch_request_digest=hashlib.sha256(request_token.encode("utf-8")).hexdigest() if request_token else "",
        branch_allowed=bool(
            str(session_id or "").strip() and str(turn_id or "").strip() and text
            and 8 <= len(request_token) <= 96
        ),
    ).public_summary()


def create_message_edit_branch(
    session_id: str,
    turn_id: str,
    edited_user_message: str,
    *,
    branch_request_id: str,
    title: str = "",
    select_session: bool = True,
) -> dict[str, Any]:
    plan = build_message_branch_plan(session_id, turn_id, edited_user_message, branch_request_id)
    if not plan.get("branch_allowed"):
        raise ConversationBranchError(
            "A source session, source turn, non-empty edited message, and explicit branch request identifier are required."
        )
    branch = create_conversation_branch_from_turn(
        session_id,
        turn_id,
        edited_user_message,
        branch_request_id=branch_request_id,
        title=title,
        select_session=select_session,
    )
    return {
        "ok": True,
        "plan": plan,
        "branch": branch,
        "message_submitted": False,
        "provider_invoked": False,
        "fresh_acceptance_required_to_send": True,
        "original_preserved": True,
    }


def message_branch_evidence_contains_private_fields(value: Mapping[str, Any]) -> bool:
    forbidden = {
        "edited_user_message", "user_message", "message", "prompt", "response",
        "assistant_response", "provider_payload", "credentials", "receipt", "memory", "memories",
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
