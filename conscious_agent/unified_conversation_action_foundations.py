from __future__ import annotations

"""v1287.0-v1287.2 unified conversation/action foundations.

This module produces one deterministic, non-executing turn contract over the
existing conversational-command distinction.  It does not replace ordinary
chat, the action router, development campaigns, operator experience, or any
exact authorization owner.
"""

import hashlib
import json
import re
from typing import Any, Mapping

from conversational_command_integration_foundations import (
    DENIED_AUTHORITY,
    classify_conversational_command_turn,
    public_conversational_command_turn,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1287.2"
MAX_TURN_CHARS = 12000

TURN_MODES = (
    "companionship",
    "discussion",
    "question",
    "planning",
    "development_request",
    "progress_request",
    "correction",
    "cancellation",
    "authorization_control",
    "ambiguous_action",
)

_PROGRESS = re.compile(
    r"^(?:please\s+)?(?:what(?:'s| is) (?:the )?(?:status|progress)|"
    r"how(?:'s| is) (?:it|that|the work) (?:going|progressing)|"
    r"how far (?:are you|did you get)|what are you working on|"
    r"where are we(?: at)?|did (?:it|that) finish|is (?:it|that) (?:done|finished|still running)|"
    r"what happened(?: with (?:it|that))?|show me (?:the )?(?:status|progress|result)|"
    r"why did (?:it|that) fail|what remains|what(?:'s| is) left)\s*[?.!]*$",
    re.I,
)

_COMPANION = re.compile(
    r"^(?:hi|hello|hey|good morning|good afternoon|good evening|good night|thanks|thank you|"
    r"how are you|how(?:'s| is) your day|i(?:'m| am) (?:glad|happy|sad|upset|tired|lonely)|"
    r"i just wanted to talk|can we talk)\b",
    re.I,
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


def _clean(value: Any) -> tuple[str, bool]:
    text = " ".join(str(value or "").replace("\x00", " ").split())
    oversized = len(text) > MAX_TURN_CHARS
    return text[:MAX_TURN_CHARS], oversized


def _mode_for(text: str, command: Mapping[str, Any]) -> tuple[str, list[str]]:
    act = str(command.get("primary_act") or "discussion")
    if _PROGRESS.fullmatch(text):
        return "progress_request", ["explicit_progress_request", "progress_is_read_only_projection"]
    if _COMPANION.search(text) and act in {"discussion", "information_request"}:
        return "companionship", ["social_or_companion_turn", "foreground_conversation_preserved"]
    if act == "action_request":
        return "development_request", ["one_live_action_clause", "request_is_not_execution_authority"]
    if act == "planning_request":
        return "planning", ["planning_request", "planning_is_not_execution"]
    if act == "information_request":
        return "question", ["information_request", "question_does_not_create_action"]
    if act == "correction":
        return "correction", ["correction_uses_existing_target_semantics"]
    if act == "cancellation":
        return "cancellation", ["cancellation_uses_existing_target_semantics"]
    if act == "authorization":
        return "authorization_control", ["authorization_shape_detected", "existing_exact_authority_owner_required"]
    if act == "ambiguous_action":
        return "ambiguous_action", ["ambiguous_action", "clarification_required"]
    return "discussion", ["ordinary_discussion", "foreground_conversation_preserved"]


def classify_unified_conversation_action_turn(user_text: str) -> dict[str, Any]:
    text, oversized = _clean(user_text)
    command = classify_conversational_command_turn(text)
    mode, reasons = _mode_for(text, command)
    if oversized:
        reasons.append("turn_truncated_to_contract_limit")
    requires_clarification = bool(command.get("requires_clarification")) or mode == "ambiguous_action"
    exact_control = bool(command.get("exact_control_shape"))
    generic_authorization = bool(command.get("generic_authorization_shape"))

    route_owner = {
        "companionship": "ordinary_conversation_generation",
        "discussion": "ordinary_conversation_generation",
        "question": "ordinary_conversation_generation",
        "planning": "ordinary_conversation_generation",
        "development_request": "existing_ordinary_chat_action_and_development_pipeline",
        "progress_request": "existing_operator_and_action_progress_projection",
        "correction": "existing_conversational_command_integration",
        "cancellation": "existing_conversational_command_integration",
        "authorization_control": "existing_exact_authorization_owner" if exact_control else "exact_authorization_required",
        "ambiguous_action": "clarification_only",
    }[mode]

    response_obligations = {
        "companionship": ["respond_conversationally", "do_not_invent_work"],
        "discussion": ["respond_conversationally", "do_not_invent_work"],
        "question": ["answer_question", "do_not_turn_question_into_action"],
        "planning": ["discuss_plan", "do_not_execute_plan"],
        "development_request": ["acknowledge_request", "use_existing_supervised_development_path"],
        "progress_request": ["report_known_progress_only", "separate_unknown_from_failed"],
        "correction": ["apply_existing_correction_target_rules", "preserve_unrelated_completed_work"],
        "cancellation": ["apply_existing_cancel_target_rules", "do_not_start_replacement_work"],
        "authorization_control": ["validate_with_existing_exact_authority_contract", "never_infer_from_generic_approval"],
        "ambiguous_action": ["request_one_bounded_action", "execute_nothing"],
    }[mode]

    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "turn_mode": mode,
        "turn_mode_supported": mode in TURN_MODES,
        "reason_codes": reasons[:12],
        "route_owner": route_owner,
        "response_obligations": response_obligations,
        "requires_clarification": requires_clarification,
        "exact_control_shape": exact_control,
        "generic_authorization_shape": generic_authorization,
        "mixed_turn": bool(command.get("mixed_turn")),
        "live_action_clause_count": int(command.get("live_action_clause_count") or 0),
        "command_classification": public_conversational_command_turn(command),
        "foreground_conversation_preserved": True,
        "parallel_execution_engine_created": False,
        "progress_request_executes_work": False,
        "planning_executes_work": False,
        "question_creates_work": False,
        "raw_turn_text_exposed": False,
        "provider_contacted": False,
        "commands_executed": False,
        "project_modified": False,
        **DENIED_AUTHORITY,
    }
    row["turn_digest"] = _digest({k: v for k, v in row.items() if k != "turn_digest"})
    return row


def public_unified_conversation_action_turn(value: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(value or {})
    row.pop("private_turn_text", None)
    row["raw_turn_text_exposed"] = False
    row["raw_authorization_phrase_exposed"] = False
    return row


__all__ = [
    "CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TURN_MODES",
    "classify_unified_conversation_action_turn",
    "public_unified_conversation_action_turn",
]
