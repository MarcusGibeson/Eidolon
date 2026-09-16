from __future__ import annotations

"""Bounded natural-language action understanding and registered tool grounding.

This module classifies ordinary conversation before consulting the existing
supervised chat-action router.  It never executes an action, creates an
approval, stores a proposal, mutates runtime/source state, or treats intent as
operator consent.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from chat_action_router import (
    APPROVAL,
    BLOCKED,
    DIRECT_COMMAND,
    DIRECT_FUNCTION,
    INFO,
    SUPERVISED_CAPABILITY_REGISTRY,
    is_experiment_review_question,
    propose_chat_action,
)
from bounded_action_arguments import bind_bounded_action_arguments
from structured_action_clarification import build_structured_clarification_request


ACTION_INTENT_SCHEMA_VERSION = "1"
ACTION_INTENT_CONTRACT_VERSION = "v1175.2"
MAX_ACTION_INPUT_CHARS = 12000
MAX_HISTORY_ROWS = 8
MAX_PRIOR_CANDIDATES = 4
MAX_RECEIPT_BYTES = 2048

INTENT_CATEGORIES = (
    "conversation",
    "question",
    "correction",
    "planning_request",
    "action_request",
    "ambiguous_request",
)

_CAPABILITIES = {str(row["id"]): dict(row) for row in SUPERVISED_CAPABILITY_REGISTRY}
_CAPABILITY_IDS = frozenset(_CAPABILITIES)

_ACTION_START = re.compile(
    r"^(?:please\s+)?(?:do|run|perform|execute|inspect|review|check|scan|change|modify|update|"
    r"create|make|build|develop|implement|code|fix|apply|install|delete|remove|switch|pull|start|open|show|list|find|"
    r"continue|begin|launch|test|verify|diagnose|repair)\b",
    re.I,
)
_MODAL_ACTION = re.compile(
    r"^(?:please\s+)?(?:can|could|would|will)\s+you\s+"
    r"(?:(?:please|maybe|perhaps|possibly)\s+)*"
    r"(?:run|perform|execute|inspect|review|check|scan|change|modify|update|create|make|build|fix|"
    r"apply|start|show|test|verify|diagnose|repair|develop|implement|code)\b",
    re.I,
)
_EMBEDDED_ACTION = re.compile(
    r"(?:^|[,.!?;]\s+)(?:please\s+)?(?:do|run|perform|execute|inspect|review|check|scan|change|modify|"
    r"update|create|make|build|develop|implement|code|fix|apply|install|delete|remove|switch|pull|"
    r"start|open|show|list|find|continue|begin|launch|test|verify|diagnose|repair)\b",
    re.I,
)
_DO_QUESTION = re.compile(r"^(?:please\s+)?do\s+you\b", re.I)
_QUESTION_START = re.compile(
    r"^(?:who|what|when|where|why|how|which|whose|is|are|am|was|were|does|did|has|have|had|"
    r"should|may|might|can|could|would|will)\b",
    re.I,
)
_CORRECTION = re.compile(
    r"^(?:please\s+)?(?:stop|do\s+not|don't|dont|never)\s+"
    r"(?:calling\s+me|referring\s+to\s+me|addressing\s+me|saying\s+that\s+i|telling\s+people\s+i|"
    r"using\s+(?:that|the)\s+(?:name|nickname|pronoun|title)|bringing\s+up\s+that)\b",
    re.I,
)
_CORRECTION_ALT = re.compile(
    r"^(?:that(?:'s| is)\s+not\s+right|you(?:'re| are)\s+wrong|correction\s*:|actually\s*,|"
    r"remember\s+instead\s+that|from\s+now\s+on\s*,?)\b",
    re.I,
)
_PLANNING = re.compile(
    r"^(?:please\s+)?(?:help\s+me\s+plan|make\s+(?:me\s+)?a\s+plan|create\s+a\s+plan|"
    r"plan\s+(?:out\s+)?(?:how|the|my|our)|outline\s+(?:the\s+)?steps|what\s+(?:is|are)\s+the\s+steps|"
    r"how\s+should\s+(?:i|we)|what\s+should\s+(?:i|we)\s+do)\b",
    re.I,
)
_FOLLOW_UP = re.compile(
    r"^(?:please\s+)?(?:go\s+ahead|do\s+it|do\s+that|run\s+it|run\s+that|proceed|continue|"
    r"okay\s*,?\s*(?:do\s+it|go\s+ahead)|yes\s*,?\s*(?:do\s+it|go\s+ahead))\s*[.!?]*$",
    re.I,
)
_HYPOTHETICAL = re.compile(
    r"\b(?:hypothetically|suppose|imagine|what\s+if|if\s+i\s+(?:said|asked|told\s+you)|"
    r"would\s+you\s+if|could\s+you\s+if|in\s+theory)\b",
    re.I,
)
_UNCERTAINTY = re.compile(
    r"\b(?:maybe|perhaps|possibly|i\s+think|i\s+guess|not\s+sure|uncertain|might\s+want|"
    r"could\s+probably)\b",
    re.I,
)
_QUOTED_COMMAND = re.compile(
    r"(?:^|\s)(?:[\"'`]|“|‘)(?:please\s+)?(?:do|run|perform|execute|inspect|review|check|scan|"
    r"change|modify|update|create|make|build|develop|implement|code|fix|apply|install|delete|switch|start|test|verify)\b",
    re.I,
)
_FULLY_QUOTED = re.compile(r"^\s*(?:[\"'`].*[\"'`]|“.*”|‘.*’)\s*[.!?]*$", re.S)
_PATH_HINT = re.compile(r"(?:^|\s)(?:[A-Za-z0-9_.-]+[/\\])+[A-Za-z0-9_.-]+")

_PAST_EXECUTION_CLAIM = re.compile(
    r"\b(?:i|we)\s+(?:have\s+)?(?:ran|executed|performed|completed|finished|checked|inspected|"
    r"scanned|applied|modified|updated|installed|deleted|created|built|fixed|verified|reviewed)\b|"
    r"\b(?:the\s+)?(?:diagnostics?|maintenance\s+check|scan|inspection|review|change|update|task|action)\s+"
    r"(?:is|are|was|were|has\s+been|have\s+been)\s+(?:done|complete|completed|finished|successful)\b",
    re.I,
)
_FUTURE_EXECUTION_CLAIM = re.compile(
    r"\b(?:i(?:'ll|\s+will)|we(?:'ll|\s+will)|let'?s)\s+(?:now\s+)?"
    r"(?:run|execute|perform|check|inspect|scan|apply|modify|update|install|delete|create|build|fix|"
    r"verify|review|proceed|start)\b",
    re.I,
)

_INTENT_TO_CAPABILITY = {
    "run_diagnostics": "diagnostics",
    "maintenance_scan": "maintenance",
    "settings_health": "settings_health",
    "approval_inbox": "approvals",
    "request_apply_patch": "patch_proposal",
    "request_rollback_patch": "patch_proposal",
    "request_apply_task_evaluation": "task_project",
    "task_status": "task_project",
    "next_task": "task_project",
    "project_status": "task_project",
    "memory_status": "memory",
    "manual_memory_compaction": "memory",
    "attention_center": "attention_center",
    "watch_once": "notifications",
    "notifications": "notifications",
    "plan_session": "planning",
    "review_file": "file_review",
    "suggest_patch": "patch_proposal",
    "suggest_patch_missing_file": "patch_proposal",
    "self_development_cycle": "self_development",
    "operator_approved_self_development_patch_draft": "self_development",
    "operator_approved_self_development_patch_application_trial": "self_development",
    "experiment_review_list": "experiment_review",
    "experiment_review_start": "experiment_review",
    "experiment_review_status": "experiment_review",
}


def _clean(value: Any, limit: int = MAX_ACTION_INPUT_CHARS) -> tuple[str, bool]:
    text = " ".join(str(value or "").replace("\x00", " ").split())
    oversized = len(text) > limit
    return text[:limit], oversized


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _reason(*values: str) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))[:12]


def _looks_like_action(text: str) -> bool:
    candidate = re.sub(
        r"^(?:maybe|perhaps|possibly|i\s+think|i\s+guess|not\s+sure(?:\s+but)?)[,\s]+",
        "",
        str(text or ""),
        flags=re.I,
    )
    return bool(_ACTION_START.search(candidate) or _MODAL_ACTION.search(candidate))


def _question_like(text: str) -> bool:
    return bool(text.endswith("?") or _QUESTION_START.search(text) or _DO_QUESTION.search(text))


def classify_natural_language_intent(user_text: str) -> dict[str, Any]:
    text, oversized = _clean(user_text)
    hypothetical = bool(_HYPOTHETICAL.search(text))
    uncertainty = bool(_UNCERTAINTY.search(text))
    quoted_command = bool(_QUOTED_COMMAND.search(text) or _FULLY_QUOTED.fullmatch(text))
    follow_up = bool(_FOLLOW_UP.fullmatch(text))
    correction = bool(_CORRECTION.search(text) or _CORRECTION_ALT.search(text))
    planning = bool(_PLANNING.search(text))
    action_shape = _looks_like_action(text)
    embedded_action_shape = bool(_EMBEDDED_ACTION.search(text))
    question_shape = _question_like(text)
    review_question = is_experiment_review_question(text)

    reasons: list[str]
    requires_clarification = False
    if not text:
        category = "ambiguous_request"
        confidence = 0.0
        reasons = ["empty_request", "clarification_required"]
        requires_clarification = True
    elif follow_up:
        category = "ambiguous_request"
        confidence = 0.62
        reasons = ["action_reference_without_current_target", "prior_proposal_resolution_required"]
        requires_clarification = True
    elif correction:
        category = "correction"
        confidence = 0.98
        reasons = ["direct_personal_or_factual_correction", "current_turn_precedence"]
    elif hypothetical or quoted_command:
        category = "question" if question_shape or hypothetical else "conversation"
        confidence = 0.95
        reasons = ["hypothetical_or_quoted_action_language", "no_live_action_intent"]
    elif planning:
        category = "planning_request"
        confidence = 0.94
        reasons = ["planning_language", "no_tool_execution_implied"]
    elif _DO_QUESTION.search(text):
        category = "question"
        confidence = 0.99
        reasons = ["do_you_question", "no_imperative_target"]
    elif embedded_action_shape:
        category = "action_request"
        confidence = 0.95
        reasons = ["mixed_conversation_and_action", "live_embedded_imperative", "authorization_not_implied"]
    elif _MODAL_ACTION.search(text):
        category = "action_request"
        confidence = 0.94
        reasons = ["modal_action_request", "authorization_not_implied"]
    elif action_shape:
        category = "action_request"
        confidence = 0.97
        reasons = ["natural_language_imperative", "authorization_not_implied"]
    elif review_question:
        category = "action_request"
        confidence = 0.93
        reasons = ["registered_experiment_review_question", "read_only_listing_or_status", "authorization_not_implied"]
    elif question_shape:
        category = "question"
        confidence = 0.92
        reasons = ["ordinary_question"]
    else:
        category = "conversation"
        confidence = 0.82
        reasons = ["ordinary_conversation", "no_action_cue"]

    if category == "action_request" and uncertainty:
        requires_clarification = True
        reasons.append("uncertain_action_language")
        confidence = min(confidence, 0.76)
    if oversized:
        reasons.append("input_truncated_to_contract_limit")
        if category in {"action_request", "ambiguous_request"}:
            requires_clarification = True

    result = {
        "schema_version": ACTION_INTENT_SCHEMA_VERSION,
        "contract_version": ACTION_INTENT_CONTRACT_VERSION,
        "category": category,
        "confidence": round(confidence, 2),
        "reason_codes": _reason(*reasons),
        "action_intent_present": category == "action_request",
        "question_present": category == "question",
        "correction_present": category == "correction",
        "planning_present": category == "planning_request",
        "ambiguous": category == "ambiguous_request",
        "requires_clarification": bool(requires_clarification),
        "hypothetical_language_present": hypothetical,
        "quoted_command_present": quoted_command,
        "embedded_action_present": embedded_action_shape,
        "uncertainty_present": uncertainty,
        "multi_turn_reference_present": follow_up,
        "input_truncated": oversized,
        "authorization_inferred": False,
        "approval_created": False,
        "execution_requested_but_not_authorized": category == "action_request",
        "provider_contacted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "content_free": True,
    }
    result["classification_digest"] = _digest({key: result[key] for key in result if key != "classification_digest"})
    return result


def _semantic_capability(text: str) -> str:
    lowered = text.casefold()
    development_targets = (
        "web page", "webpage", "website", "web site", "web app", "application",
        "software", "program", "codebase", "api", "desktop app", "mobile app", "text-to-speech", "text to speech", "speech system", "voice system",
    )
    development_verbs = ("make", "build", "create", "develop", "implement", "code", "fix", "repair", "update")
    if any(target in lowered for target in development_targets) and any(verb in lowered for verb in development_verbs):
        return "software_development"
    if "maintenance" in lowered or "maintainence" in lowered:
        return "maintenance"
    if any(phrase in lowered for phrase in ("diagnostic", "system health", "health check", "system check")):
        return "diagnostics"
    if "review" in lowered and (_PATH_HINT.search(text) or "file" in lowered):
        return "file_review"
    if any(phrase in lowered for phrase in ("inspect your project", "inspect the project", "project status", "active project")):
        return "task_project"
    if "dashboard" in lowered and any(word in lowered for word in ("change", "modify", "update", "background", "color", "colour")):
        return "patch_proposal"
    return ""


def _capability_for_action(text: str, action: Mapping[str, Any]) -> str:
    semantic = _semantic_capability(text)
    if semantic in _CAPABILITY_IDS:
        return semantic
    mapped = _INTENT_TO_CAPABILITY.get(str(action.get("intent") or ""), "")
    return mapped if mapped in _CAPABILITY_IDS else ""


def _authority_for(mode: str, capability_id: str, risk: str) -> tuple[str, bool]:
    if mode == APPROVAL or risk in {"medium", "high"}:
        return "separate_explicit_operator_approval", True
    if capability_id == "patch_proposal":
        return "explicit_operator_request_for_proposal_then_separate_approval_for_any_write", True
    if mode in {DIRECT_COMMAND, DIRECT_FUNCTION}:
        return "explicit_operator_execution_request_on_governed_surface", True
    return "operator_review", False


def ground_action_intent(user_text: str, intent: Mapping[str, Any]) -> dict[str, Any]:
    text, _ = _clean(user_text)
    category = str(intent.get("category") or "ambiguous_request")
    base = {
        "schema_version": ACTION_INTENT_SCHEMA_VERSION,
        "contract_version": ACTION_INTENT_CONTRACT_VERSION,
        "grounding_status": "not_applicable",
        "capability_id": "",
        "capability_registered": False,
        "candidate_count": 0,
        "risk_level": "none",
        "reversible": True,
        "required_authority": "none",
        "authority_required": False,
        "missing_information": [],
        "suggested_clarification": "",
        "execution_state": "not_executed",
        "approval_state": "not_created",
        "authorization_state": "not_granted",
        "authoritative_execution_receipt_present": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "raw_tool_arguments_included": False,
        "raw_command_included": False,
        "content_free": True,
    }
    if category not in {"action_request", "ambiguous_request"}:
        base["grounding_digest"] = _digest(base)
        return base
    if category == "ambiguous_request":
        base.update({
            "grounding_status": "ambiguous",
            "risk_level": "unknown",
            "missing_information": ["unique_action_target"],
            "suggested_clarification": "Name the exact action or registered capability you want reviewed.",
        })
        base["grounding_digest"] = _digest(base)
        return base

    action = propose_chat_action(text, save=False, save_unknown=False)
    semantic_capability = _semantic_capability(text)
    capability_id = _capability_for_action(text, action)
    mode = str(action.get("execution_mode") or BLOCKED)
    risk = str(action.get("risk_level") or "unknown")
    intent_name = str(action.get("intent") or "unknown_request")
    if semantic_capability == "patch_proposal" and capability_id == "patch_proposal":
        mode = DIRECT_FUNCTION
        risk = "medium"
        intent_name = "source_change_proposal_request"
    elif semantic_capability == "software_development" and capability_id == "software_development":
        mode = DIRECT_FUNCTION
        risk = "medium"
        intent_name = "supervised_software_development_campaign_request"
    elif semantic_capability in {"task_project", "maintenance", "diagnostics", "file_review"} and capability_id == semantic_capability:
        if mode in {BLOCKED, INFO} or intent_name == "unknown_request":
            mode = DIRECT_COMMAND
            risk = "low"
            intent_name = f"registered_{semantic_capability}_request"
    matched = bool(capability_id and capability_id in _CAPABILITY_IDS)
    unsupported = intent_name.startswith("blocked_") or (not matched and intent_name == "unknown_request")
    unavailable = bool(matched and mode == INFO and intent_name not in {"supervised_capabilities", "experiment_review_list", "experiment_review_status"})
    authority, authority_required = _authority_for(mode, capability_id, risk)

    missing: list[str] = []
    clarification = ""
    status = "matched"
    if unsupported:
        status = "unsupported"
        missing = ["supported_registered_capability"]
        clarification = "Reframe the request using a registered supervised capability."
    elif not matched:
        status = "unmatched"
        missing = ["registered_capability_match"]
        clarification = "Name the intended diagnostic, maintenance, project, software-development, file-review, planning, or proposal capability."
    elif unavailable:
        status = "unavailable"
        clarification = "Use the existing operator-controlled surface for this capability."
    elif intent.get("requires_clarification"):
        status = "ambiguous"
        missing = ["operator_confirmation_of_uncertain_request"]
        clarification = "Confirm the exact requested operation before any governed execution proposal is created."

    reversible = capability_id not in {"patch_proposal", "self_development", "software_development"} and mode != APPROVAL
    base.update({
        "grounding_status": status,
        "capability_id": capability_id if matched else "",
        "capability_registered": matched,
        "candidate_count": 1 if matched else 0,
        "risk_level": risk,
        "reversible": reversible,
        "required_authority": authority if matched else "operator_clarification",
        "authority_required": authority_required if matched else False,
        "missing_information": missing[:4],
        "suggested_clarification": clarification[:240],
        "router_intent": intent_name[:80] if matched else "",
        "router_mode": mode if matched else "",
    })
    base["grounding_digest"] = _digest(base)
    return base


def _history_candidates(history: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_ROWS:]
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in reversed(rows):
        prior_text = str(row.get("user_message") or "").strip()
        proposal_summary = " ".join(str(row.get("action_status_summary") or "").split()).casefold()
        proposal_evidence = " is proposed." in proposal_summary and "persisted evidence exists" in proposal_summary
        if not prior_text or not proposal_evidence:
            continue
        prior_intent = classify_natural_language_intent(prior_text)
        if prior_intent["category"] != "action_request":
            continue
        grounding = ground_action_intent(prior_text, prior_intent)
        capability_id = str(grounding.get("capability_id") or "")
        if (
            grounding.get("grounding_status") != "matched"
            or capability_id not in _CAPABILITY_IDS
            or capability_id in seen
            or grounding.get("risk_level") not in {"low", "none"}
        ):
            continue
        seen.add(capability_id)
        candidates.append({
            "capability_id": capability_id,
            "risk_level": grounding.get("risk_level"),
            "required_authority": grounding.get("required_authority"),
            "source": "bounded_prior_supervised_proposal",
        })
        if len(candidates) >= MAX_PRIOR_CANDIDATES:
            break
    return candidates


def _resolve_follow_up(
    intent: dict[str, Any],
    grounding: dict[str, Any],
    conversation_history: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not intent.get("multi_turn_reference_present"):
        return intent, grounding
    candidates = _history_candidates(conversation_history)
    if len(candidates) != 1:
        grounding["candidate_count"] = len(candidates)
        grounding["grounding_status"] = "ambiguous" if candidates else "unmatched"
        grounding["missing_information"] = ["unique_safe_prior_action_proposal"]
        grounding["suggested_clarification"] = "Name the prior proposed capability explicitly."
        grounding["grounding_digest"] = _digest({k: v for k, v in grounding.items() if k != "grounding_digest"})
        return intent, grounding

    candidate = candidates[0]
    capability_id = candidate["capability_id"]
    capability = _CAPABILITIES[capability_id]
    intent = dict(intent)
    intent.update({
        "category": "action_request",
        "action_intent_present": True,
        "ambiguous": False,
        "requires_clarification": False,
        "confidence": 0.88,
        "reason_codes": _reason(*intent.get("reason_codes", []), "unique_safe_prior_proposal_resolved", "authorization_not_implied"),
        "authorization_inferred": False,
        "execution_requested_but_not_authorized": True,
    })
    intent["classification_digest"] = _digest({k: v for k, v in intent.items() if k != "classification_digest"})
    authority, authority_required = _authority_for(str(capability.get("mode") or DIRECT_COMMAND), capability_id, "low")
    grounding = dict(grounding)
    grounding.update({
        "grounding_status": "matched",
        "capability_id": capability_id,
        "capability_registered": True,
        "candidate_count": 1,
        "risk_level": "low",
        "reversible": capability.get("boundary") == "allowlisted read",
        "required_authority": authority,
        "authority_required": authority_required,
        "missing_information": [],
        "suggested_clarification": "",
        "router_intent": "resolved_prior_proposal_reference",
        "router_mode": str(capability.get("mode") or DIRECT_COMMAND),
        "authorization_state": "not_granted",
        "execution_state": "not_executed",
        "approval_state": "not_created",
    })
    grounding["grounding_digest"] = _digest({k: v for k, v in grounding.items() if k != "grounding_digest"})
    return intent, grounding


def _validate_authoritative_receipts(
    receipts: Iterable[Mapping[str, Any]], capability_id: str,
) -> dict[str, Any]:
    valid: list[str] = []
    invalid = 0
    replayed = 0
    seen: set[str] = set()
    for row in list(receipts)[:16]:
        if not isinstance(row, Mapping):
            invalid += 1
            continue
        digest = str(row.get("receipt_digest") or "")
        valid_shape = (
            row.get("authoritative") is True
            and str(row.get("status") or "") == "completed"
            and str(row.get("capability_id") or "") == capability_id
            and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
            and row.get("approval_granted") in {False, None}
        )
        if not valid_shape:
            invalid += 1
            continue
        if digest in seen:
            replayed += 1
            continue
        seen.add(digest)
        valid.append(digest)
    return {
        "valid_receipt_count": len(valid),
        "invalid_receipt_count": invalid,
        "replayed_receipt_count": replayed,
        "authoritative_execution_receipt_present": bool(valid),
        "verified_receipt_digest": valid[0] if valid else "",
    }


def _prompt_section(intent: Mapping[str, Any], grounding: Mapping[str, Any]) -> str:
    category = str(intent.get("category") or "ambiguous_request")
    status = str(grounding.get("grounding_status") or "not_applicable")
    capability = str(grounding.get("capability_id") or "none")
    authority = str(grounding.get("required_authority") or "none")
    receipt = bool(grounding.get("authoritative_execution_receipt_present"))
    lines = [
        "Natural-language action and tool-intent routing (bounded, non-authoritative):",
        f"- Intent category: {category}.",
        f"- Tool grounding: {status}; registered capability: {capability}.",
        f"- Required authority: {authority}; authorization was not inferred or granted.",
        "- Intent detection is not consent. No tool, command, approval, source edit, model operation, or provider change occurred here.",
        "- Explain naturally what was understood, which registered capability may apply, and what clarification or authority is still required.",
    ]
    if not receipt:
        lines.append("- Never claim an action ran, completed, succeeded, or produced results without an authoritative existing execution receipt.")
    else:
        lines.append("- A bounded authoritative completion receipt exists for the exact registered capability; do not embellish beyond that receipt.")
    return "\n".join(lines)


def build_natural_language_action_projection(
    user_text: str,
    *,
    conversation_history: Iterable[Mapping[str, Any]] = (),
    authoritative_receipts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    intent = classify_natural_language_intent(user_text)
    grounding = ground_action_intent(user_text, intent)
    intent, grounding = _resolve_follow_up(intent, grounding, conversation_history)
    receipt_audit = _validate_authoritative_receipts(authoritative_receipts, str(grounding.get("capability_id") or ""))
    grounding.update(receipt_audit)
    grounding["grounding_digest"] = _digest({k: v for k, v in grounding.items() if k != "grounding_digest"})
    argument_binding = bind_bounded_action_arguments(user_text, grounding)

    receipt = {
        "schema_version": ACTION_INTENT_SCHEMA_VERSION,
        "contract_version": ACTION_INTENT_CONTRACT_VERSION,
        "intent_category": intent["category"],
        "classification_digest": intent["classification_digest"],
        "grounding_digest": grounding["grounding_digest"],
        "capability_id": grounding.get("capability_id", ""),
        "grounding_status": grounding.get("grounding_status", "not_applicable"),
        "authorization_state": "not_granted",
        "approval_state": "not_created",
        "execution_state": "completed" if grounding.get("authoritative_execution_receipt_present") else "not_executed",
        "authoritative_execution_receipt_present": bool(grounding.get("authoritative_execution_receipt_present")),
        "provider_contacted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "content_free": True,
        "authority_free": True,
    }
    receipt["receipt_digest"] = _digest(receipt)
    receipt_size = len(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    if receipt_size > MAX_RECEIPT_BYTES:
        raise ValueError("Natural-language action receipt exceeded its bounded size contract.")

    projection = {
        "schema_version": ACTION_INTENT_SCHEMA_VERSION,
        "contract_version": ACTION_INTENT_CONTRACT_VERSION,
        "intent": intent,
        "grounding": grounding,
        "argument_binding": argument_binding,
        "clarification_request": {},
        "receipt": receipt,
        "diagnostics": {
            "registered_capability_count": len(_CAPABILITY_IDS),
            "receipt_bytes": receipt_size,
            "receipt_bounded": receipt_size <= MAX_RECEIPT_BYTES,
            "streaming_non_streaming_shared_projection": True,
            "new_execution_path_created": False,
            "new_tool_registry_created": False,
            "existing_supervised_registry_reused": True,
            "existing_chat_action_router_reused": intent["category"] == "action_request",
            "raw_user_text_included": False,
            "raw_tool_arguments_included": False,
            "raw_command_included": False,
            "private_reasoning_included": False,
            "authorization_inferred": False,
            "approval_created": False,
            "execution_performed": False,
            "content_free": True,
        },
    }
    projection["projection_digest"] = _digest({
        "intent": intent["classification_digest"],
        "grounding": grounding["grounding_digest"],
        "argument_binding": argument_binding["binding_digest"],
        "receipt": receipt["receipt_digest"],
    })
    projection["clarification_request"] = build_structured_clarification_request(projection)
    projection["prompt_section"] = _prompt_section(intent, grounding)
    return projection


def natural_language_action_public_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    intent = dict(projection.get("intent") or {})
    grounding = dict(projection.get("grounding") or {})
    receipt = dict(projection.get("receipt") or {})
    argument_binding = dict(projection.get("argument_binding") or {})
    return {
        "schema_version": str(projection.get("schema_version") or ACTION_INTENT_SCHEMA_VERSION),
        "contract_version": str(projection.get("contract_version") or ACTION_INTENT_CONTRACT_VERSION),
        "intent": intent,
        "grounding": grounding,
        "argument_binding": argument_binding,
        "clarification_request": dict(projection.get("clarification_request") or {}),
        "receipt": receipt,
        "diagnostics": dict(projection.get("diagnostics") or {}),
        "projection_digest": str(projection.get("projection_digest") or ""),
    }


def action_projection_contains_private_fields(value: Any) -> bool:
    forbidden = {
        "prompt", "prompts", "user_text", "user_request", "request_text", "conversation", "conversation_id",
        "session_id", "memory", "memories", "provider_payload", "payload", "secret", "credential", "token",
        "command", "args", "arguments", "function_args", "path", "content", "private_reasoning", "chain_of_thought",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).casefold()
            if lowered in forbidden or lowered.endswith("_command") or lowered.endswith("_args"):
                return True
            if action_projection_contains_private_fields(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(action_projection_contains_private_fields(item) for item in value)
    return False


def bounded_action_explanation(projection: Mapping[str, Any]) -> str:
    intent = dict(projection.get("intent") or {})
    grounding = dict(projection.get("grounding") or {})
    category = str(intent.get("category") or "ambiguous_request")
    status = str(grounding.get("grounding_status") or "not_applicable")
    capability = str(grounding.get("capability_id") or "")
    authority = str(grounding.get("required_authority") or "operator clarification")
    if category == "ambiguous_request" or status == "ambiguous":
        clarification = str(grounding.get("suggested_clarification") or "Please name the exact requested operation.")
        return f"I understood this as a possible action reference, but it is not uniquely grounded. {clarification} Nothing ran and no approval was created."
    if status == "matched" and capability:
        return (
            f"I understood this as an action request that maps to the registered `{capability}` capability. "
            f"Nothing ran through this conversation turn, and authorization was not inferred. The next governed step requires {authority.replace('_', ' ')}."
        )
    if status in {"unsupported", "unmatched", "unavailable"}:
        clarification = str(grounding.get("suggested_clarification") or "No registered capability safely matches it yet.")
        return f"I understood this as an action request, but it is {status}. {clarification} Nothing ran and no approval was created."
    return "I did not identify a live action request in this turn."


def bound_unverified_action_claim(response: str, projection: Mapping[str, Any]) -> str:
    text = str(response or "")
    intent = dict(projection.get("intent") or {})
    grounding = dict(projection.get("grounding") or {})
    if not intent.get("action_intent_present"):
        return text
    if grounding.get("authoritative_execution_receipt_present"):
        return text
    if _PAST_EXECUTION_CLAIM.search(text) or _FUTURE_EXECUTION_CLAIM.search(text):
        return bounded_action_explanation(projection)
    return text
