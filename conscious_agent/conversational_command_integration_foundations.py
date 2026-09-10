from __future__ import annotations

"""v1259.0-v1259.2 conversational command integration foundations.

This layer classifies the *speech act* of an ordinary conversation turn without
executing it.  It deliberately separates discussion, hypotheticals,
information requests, development requests, corrections, cancellations, and
authorization-shaped language.  Classification never grants proposal approval,
execution, application, installation, release, or independent authority.
"""

import hashlib
import json
import re
from typing import Any, Mapping

from natural_conversation_command_distinction import distinguish_natural_conversation_and_command

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1259.2"
MAX_TURN_CHARS = 12000

DENIED_AUTHORITY = {
    "authority_granted": False,
    "approval_granted": False,
    "authorization_granted": False,
    "execution_authorized": False,
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "project_mutation_authorized": False,
    "application_authorized": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "certification_authorized": False,
    "release_authorized": False,
    "permanent_approval_granted": False,
    "independent_authority_granted": False,
}

ACT_KINDS = (
    "discussion",
    "hypothetical",
    "information_request",
    "planning_request",
    "action_request",
    "authorization",
    "correction",
    "cancellation",
    "ambiguous_action",
)

_EXACT_PROPOSAL_APPROVAL = re.compile(
    r"^(?:i\s+)?approve\s+(?:the\s+)?(?:development\s+)?proposal\s+"
    r"devc_[a-f0-9]{24}\s+revision\s+[1-9][0-9]*[.!?]*$",
    re.I,
)
_EXACT_PROPOSAL_REJECTION = re.compile(
    r"^(?:i\s+)?reject\s+(?:the\s+)?(?:development\s+)?proposal\s+"
    r"devc_[a-f0-9]{24}\s+revision\s+[1-9][0-9]*[.!?]*$",
    re.I,
)
_EXACT_PROPOSAL_CANCELLATION = re.compile(
    r"^(?:please\s+)?cancel\s+(?:the\s+)?(?:development\s+)?proposal\s+"
    r"devc_[a-f0-9]{24}\s+revision\s+[1-9][0-9]*[.!?]*$",
    re.I,
)
_EXACT_GOVERNED_AUTHORITY = re.compile(
    r"^(?:authorize|approve|apply|rollback)\b.{0,220}\b(?:devc_[a-f0-9]{24}|cdr_[a-f0-9]{24}|"
    r"request\s+[a-f0-9]{16,64}|packet\s+[a-f0-9]{16,64}|revision\s+[1-9][0-9]*|digest\s+[a-f0-9]{16,64})\b",
    re.I,
)
_GENERIC_AUTHORIZATION = re.compile(
    r"^(?:yes[,.!?\s]+)?(?:go\s+ahead|do\s+it|do\s+that|proceed|continue|start\s+it|run\s+it|"
    r"you\s+have\s+my\s+(?:approval|permission)|i\s+(?:approve|authorize)\s+(?:it|that))\s*[.!?]*$",
    re.I,
)
_CANCELLATION = re.compile(
    r"^(?:please\s+)?(?:cancel|abort|stop)\b|^(?:never\s*mind|nevermind)\b|"
    r"^(?:please\s+)?(?:do\s+not|don['’]?t)\s+(?:do|run|build|create|implement|continue|proceed|apply)\b",
    re.I,
)
_CORRECTION = re.compile(
    r"^(?:actually\b|correction\s*:|instead\b|change\s+that\b|make\s+it\b|"
    r"i\s+meant\b|not\s+that\b|rather\b|revise\s+that\b|update\s+that\b)",
    re.I,
)
_DEVELOPMENT_CORRECTION = re.compile(
    r"^(?:(?:actually|instead|rather)\b[,:]?\s*|correction\s*:\s*|i\s+meant\b[,:]?\s*)?"
    r"(?:please\s+)?(?:make|use|change|add|remove|replace|update|rename|build|implement|create|fix|"
    r"modify|edit|set|switch|keep|include|exclude|move|put|delete|revise)\b",
    re.I,
)
_NON_DEVELOPMENT_STOP = re.compile(
    r"^(?:please\s+)?stop\s+(?:calling|referring\s+to|addressing|saying|telling)\b",
    re.I,
)
_HYPOTHETICAL = re.compile(
    r"\b(?:hypothetically|suppose|imagine|what\s+if|if\s+i\s+(?:said|asked|told\s+you)|"
    r"in\s+theory|would\s+you\s+if|could\s+you\s+if)\b",
    re.I,
)
_WISH_OR_SUGGESTION = re.compile(
    r"^(?:i\s+(?:wish|hope)|it\s+would\s+be\s+(?:nice|cool|great|useful)|"
    r"wouldn['’]?t\s+it\s+be\s+(?:nice|cool|great)|maybe|perhaps|"
    r"you\s+(?:could|might|should)|we\s+(?:could|might|should))\b",
    re.I,
)
_INFORMATION = re.compile(
    r"^(?:who|what|when|where|why|how|which|is|are|am|was|were|does|did|has|have|had|"
    r"can\s+you\s+(?:explain|tell|describe|show\s+me\s+how)|could\s+you\s+(?:explain|tell|describe)|"
    r"would\s+you\s+(?:explain|tell|describe)|explain|tell\s+me|describe)\b",
    re.I,
)
_PLANNING = re.compile(
    r"^(?:please\s+)?(?:help\s+me\s+plan|make\s+(?:me\s+)?a\s+plan|create\s+a\s+plan|"
    r"plan\s+(?:out\s+)?(?:how|the|my|our)|outline\s+(?:the\s+)?steps|"
    r"how\s+should\s+(?:i|we)|what\s+should\s+(?:i|we)\s+do)\b",
    re.I,
)
_QUOTED_ONLY = re.compile(r"^\s*(?:[\"'`].*[\"'`]|“.*”|‘.*’)\s*[.!?]*$", re.S)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _clean(value: Any) -> tuple[str, bool]:
    text = " ".join(str(value or "").replace("\x00", " ").split())
    oversized = len(text) > MAX_TURN_CHARS
    return text[:MAX_TURN_CHARS], oversized


def _authorization_kind(text: str) -> tuple[bool, bool]:
    exact = bool(_EXACT_PROPOSAL_APPROVAL.fullmatch(text) or _EXACT_GOVERNED_AUTHORITY.search(text))
    generic = bool(_GENERIC_AUTHORIZATION.fullmatch(text))
    return exact, generic


def classify_conversational_command_turn(user_text: str) -> dict[str, Any]:
    text, oversized = _clean(user_text)
    distinction = distinguish_natural_conversation_and_command(text)
    exact_authorization, generic_authorization = _authorization_kind(text)
    exact_cancellation = bool(_EXACT_PROPOSAL_CANCELLATION.fullmatch(text))
    exact_rejection = bool(_EXACT_PROPOSAL_REJECTION.fullmatch(text))
    non_development_stop = bool(_NON_DEVELOPMENT_STOP.search(text))
    cancellation = (bool(_CANCELLATION.search(text)) and not non_development_stop) or exact_cancellation or exact_rejection
    correction = bool(_CORRECTION.search(text)) or non_development_stop
    development_correction_shape = bool(correction and _DEVELOPMENT_CORRECTION.search(text))
    hypothetical = bool(_HYPOTHETICAL.search(text))
    quoted_only = bool(_QUOTED_ONLY.fullmatch(text))
    planning = bool(_PLANNING.search(text))
    legacy_live_count = int(distinction.get("live_action_clause_count") or 0)
    explicit_information = bool(_INFORMATION.search(text))
    information = explicit_information or (text.endswith("?") and not exact_authorization and legacy_live_count == 0)
    effective_live_count = 0 if explicit_information else legacy_live_count
    multiple_actions = bool((distinction.get("requires_clarification") or legacy_live_count > 1) and not explicit_information)
    action_text = str(distinction.get("action_text") or "").strip()

    reason_codes: list[str] = []
    exact_control = False
    target_reference_required = False
    requires_clarification = False

    if not text:
        kind = "ambiguous_action"
        reason_codes = ["empty_turn", "clarification_required"]
        requires_clarification = True
    elif exact_cancellation or exact_rejection:
        kind = "cancellation"
        exact_control = True
        reason_codes = ["exact_development_proposal_terminal_control", "authority_not_expanded"]
    elif cancellation:
        kind = "cancellation"
        target_reference_required = True
        reason_codes = ["explicit_stop_or_cancel_language", "target_must_resolve_uniquely"]
    elif exact_authorization:
        kind = "authorization"
        exact_control = True
        reason_codes = ["exact_governed_authority_shape", "existing_authority_contract_must_validate"]
    elif generic_authorization:
        kind = "authorization"
        target_reference_required = True
        reason_codes = ["generic_authorization_language", "exact_authorization_must_not_be_inferred"]
    elif correction:
        kind = "correction"
        target_reference_required = development_correction_shape
        reason_codes = (
            ["explicit_development_correction_language", "current_pending_target_required"]
            if development_correction_shape
            else ["conversational_correction_language", "development_target_not_inferred"]
        )
    elif hypothetical:
        kind = "hypothetical"
        reason_codes = ["hypothetical_frame", "no_live_action_from_hypothetical"]
    elif quoted_only:
        kind = "discussion"
        reason_codes = ["quoted_language_only", "quoted_command_not_live"]
    elif planning and legacy_live_count == 0:
        kind = "planning_request"
        reason_codes = ["planning_only", "execution_not_requested"]
    elif explicit_information:
        kind = "information_request"
        reason_codes = ["explicit_information_seeking_language", "embedded_action_words_not_live"]
    elif multiple_actions:
        kind = "ambiguous_action"
        requires_clarification = True
        reason_codes = ["multiple_live_actions", "single_bounded_action_required"]
    elif effective_live_count == 1:
        kind = "action_request"
        reason_codes = ["one_live_action_clause", "request_is_not_authorization"]
    elif information:
        kind = "information_request"
        reason_codes = ["information_seeking_language", "no_live_action_clause"]
    elif _WISH_OR_SUGGESTION.search(text):
        kind = "discussion"
        reason_codes = ["wish_or_suggestion", "no_live_action_clause"]
    else:
        kind = "discussion"
        reason_codes = ["ordinary_conversation", "no_live_action_clause"]

    if oversized:
        reason_codes.append("turn_truncated_to_contract_limit")
        if kind in {"action_request", "authorization", "correction", "cancellation"}:
            requires_clarification = True

    routing_mode = {
        "action_request": "route_live_action_clause",
        "authorization": "pass_exact_control" if exact_control else "require_exact_authorization",
        "correction": "resolve_pending_development_target" if development_correction_shape else "conversation_only",
        "cancellation": "pass_exact_control" if exact_control else "resolve_pending_development_target",
        "ambiguous_action": "clarification_only",
    }.get(kind, "conversation_only")

    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "primary_act": kind,
        "act_supported": kind in ACT_KINDS,
        "reason_codes": reason_codes[:12],
        "live_action_clause_count": effective_live_count,
        "legacy_live_action_clause_count": legacy_live_count,
        "conversation_clause_count": int(distinction.get("conversation_clause_count") or 0),
        "mixed_turn": bool(distinction.get("mixed_turn")),
        "multiple_live_actions": multiple_actions,
        "requires_clarification": bool(requires_clarification),
        "target_reference_required": target_reference_required,
        "exact_control_shape": exact_control,
        "generic_authorization_shape": generic_authorization,
        "development_correction_shape": development_correction_shape,
        "non_development_stop_shape": non_development_stop,
        "routing_mode": routing_mode,
        "action_text": action_text if kind == "action_request" else "",
        "conversation_text": str(distinction.get("conversation_text") or "").strip(),
        "private_turn_text_present": bool(text),
        "content_minimized_public_projection_available": True,
        "quoted_command_live": False if quoted_only else None,
        "provider_contacted": False,
        "commands_executed": False,
        "project_modified": False,
        **DENIED_AUTHORITY,
    }
    row["turn_classification_digest"] = _digest({k: v for k, v in row.items() if k not in {"action_text", "turn_classification_digest"}})
    return row


def public_conversational_command_turn(value: Mapping[str, Any]) -> dict[str, Any]:
    hidden = {"action_text", "conversation_text", "private_turn_text_present"}
    row = {k: v for k, v in dict(value or {}).items() if k not in hidden}
    row["private_turn_text_exposed"] = False
    row["raw_command_exposed"] = False
    row["conversation_clause_exposed"] = False
    row["raw_authorization_phrase_exposed"] = False
    return row


__all__ = [
    "ACT_KINDS",
    "CONTRACT_VERSION",
    "DENIED_AUTHORITY",
    "classify_conversational_command_turn",
    "public_conversational_command_turn",
]
