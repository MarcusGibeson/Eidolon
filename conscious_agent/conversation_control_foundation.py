from __future__ import annotations

"""Bounded v1086.0 conversation-control contract.

This module defines session-local controls without granting provider, model,
release, approval, shell, retry-replay, or branch-mutation authority.
"""

from dataclasses import asdict, dataclass
from typing import Any, Mapping

CONTROL_SCHEMA_VERSION = "1"
RESPONSE_MODES = ("default", "concise", "detailed", "technical", "casual", "brainstorming")
RESPONSE_FORMATS = ("default", "prose", "bullets", "steps")
TEMPORARY_INSTRUCTION_SCOPES = ("current_turn", "current_topic", "current_session", "until_cleared")
PINNED_CONTEXT_KINDS = ("note", "goal", "project_constraint", "reference_fact")
PINNED_CONTEXT_SCOPES = ("current_topic", "current_session", "until_cleared")
OFFLINE_INTENT_KINDS = ("send_current_draft", "retry_failed_turn", "regenerate_completed_turn", "resend_user_turn", "open_branch_draft")
RETRY_POLICIES = ("safe_transient_only", "explicit_only", "disabled")
BRANCH_POLICIES = ("preserve_original", "disabled")


@dataclass(frozen=True)
class ConversationControlFoundation:
    response_modes: tuple[str, ...] = RESPONSE_MODES
    response_formats: tuple[str, ...] = RESPONSE_FORMATS
    temporary_instruction_scopes: tuple[str, ...] = TEMPORARY_INSTRUCTION_SCOPES
    pinned_context_kinds: tuple[str, ...] = PINNED_CONTEXT_KINDS
    pinned_context_scopes: tuple[str, ...] = PINNED_CONTEXT_SCOPES
    offline_intent_kinds: tuple[str, ...] = OFFLINE_INTENT_KINDS
    retry_policies: tuple[str, ...] = RETRY_POLICIES
    branch_policies: tuple[str, ...] = BRANCH_POLICIES
    default_retry_policy: str = "safe_transient_only"
    default_branch_policy: str = "preserve_original"
    session_local_only: bool = True
    explicit_post_required_for_persisted_changes: bool = True
    current_turn_instruction_is_transient: bool = True
    accepted_request_replay_allowed: bool = False
    automatic_resend_allowed: bool = False
    automatic_branch_creation_allowed: bool = False
    mutates_global_personality: bool = False
    changes_provider_or_model: bool = False
    grants_release_or_approval_authority: bool = False
    unrestricted_shell_allowed: bool = False
    pinned_context_is_session_local: bool = True
    queued_offline_intent_executes_automatically: bool = False
    provider_invoked: bool = False
    writes_state: bool = False
    schema_version: str = CONTROL_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def default_conversation_control_state(session_id: str = "") -> dict[str, Any]:
    return {
        "type": "conversation_control_state",
        "schema_version": CONTROL_SCHEMA_VERSION,
        "session_id": str(session_id or ""),
        "revision": 0,
        "updated_at": "",
        "response_preferences": {
            "mode": "default",
            "format": "default",
            "revision": 0,
            "updated_at": "",
            "source": "default",
        },
        "temporary_instruction": None,
        "pinned_context": [],
        "queued_operator_intent": None,
        "retry_policy": "safe_transient_only",
        "branch_policy": "preserve_original",
    }


def normalize_conversation_control_state(value: Mapping[str, Any] | None, *, session_id: str = "") -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    state = default_conversation_control_state(session_id)
    state["revision"] = max(0, int(raw.get("revision") or 0))
    state["updated_at"] = str(raw.get("updated_at") or "")[:40]
    retry = str(raw.get("retry_policy") or state["retry_policy"]).strip().lower()
    branch = str(raw.get("branch_policy") or state["branch_policy"]).strip().lower()
    state["retry_policy"] = retry if retry in RETRY_POLICIES else "safe_transient_only"
    state["branch_policy"] = branch if branch in BRANCH_POLICIES else "preserve_original"
    if isinstance(raw.get("response_preferences"), Mapping):
        state["response_preferences"] = dict(raw["response_preferences"])
    if isinstance(raw.get("temporary_instruction"), Mapping):
        state["temporary_instruction"] = dict(raw["temporary_instruction"])
    if isinstance(raw.get("pinned_context"), (list, tuple)):
        state["pinned_context"] = [dict(item) for item in list(raw.get("pinned_context") or [])[:8] if isinstance(item, Mapping)]
    if isinstance(raw.get("queued_operator_intent"), Mapping):
        state["queued_operator_intent"] = dict(raw["queued_operator_intent"])
    return state


def build_conversation_control_foundation() -> dict[str, Any]:
    return ConversationControlFoundation().public_summary()
