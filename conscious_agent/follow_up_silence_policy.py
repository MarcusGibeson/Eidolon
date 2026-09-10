from __future__ import annotations

"""v1158.0-v1158.8 bounded follow-up and intentional-silence policy.

This module decides whether an ordinary response may ask one follow-up question
or should honor an explicit silence request. It is deterministic, provider-free,
content-free in diagnostics, non-authorizing, and cannot initiate a new turn.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any

CONTRACT_VERSION = "v1158.8"
SCHEMA_VERSION = "1"
MAX_PROMPT_CHARS = 900
MAX_MESSAGE_CHARS = 4096
_ALLOWED_INTENTS = {
    "direct_answer", "explanation", "clarification", "acknowledgment", "summary",
    "correction", "follow_up", "governed_approval_request",
    "defer_insufficient_evidence", "intentional_silence",
}
_ALLOWED_FOLLOW_UP = {"none", "optional", "one_bounded_question"}
_ALLOWED_SILENCE = {"not_requested", "explicit_requested", "not_honored_runtime_boundary"}
_EXPLICIT_SILENCE = re.compile(r"\b(?:do not respond|don't respond|no reply|remain silent|say nothing)\b", re.I)
_QUESTION = re.compile(r"\?")
_EXPLICIT_CONTINUE = re.compile(r"\b(?:anything else|what else|tell me more|go on|continue|keep going)\b", re.I)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SUSPICIOUS_KEYS = {
    "system_prompt", "provider_prompt", "provider_payload", "private_reasoning",
    "hidden_reasoning", "chain_of_thought", "approval_granted",
    "authorization_granted", "execution_permitted", "injected_instruction",
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FollowUpSilenceEvidence:
    selected_intent: str
    explicit_silence_request: bool
    question_present: bool
    ambiguity_present: bool
    insufficient_evidence: bool
    correction_present: bool
    contextual_follow_up_posture: str
    contextual_conflict: bool
    literal_request_precedence: bool
    malformed_context_fallback: bool
    explicit_continue_request: bool
    follow_up_utility: str
    redundancy_risk: bool
    message_truncated: bool
    control_characters_removed: bool
    suspicious_context_rejected: bool
    multiple_question_markers: bool
    explicit_silence_verified: bool
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False,
            "contains_memory_text": False,
            "contains_provider_payload": False,
            "contains_private_chain_of_thought": False,
            "provider_contacted": False,
            "runtime_mutated": False,
        })
        result["evidence_digest"] = _digest(result)
        return result


def build_follow_up_silence_evidence(
    user_message: Any,
    response_intent: dict[str, Any] | None,
    contextual_behavior: dict[str, Any] | None,
) -> FollowUpSilenceEvidence:
    malformed = not isinstance(response_intent, dict) or not isinstance(contextual_behavior, dict)
    intent = response_intent if isinstance(response_intent, dict) else {}
    behavior = contextual_behavior if isinstance(contextual_behavior, dict) else {}
    raw_text = str(user_message or "")
    message_truncated = len(raw_text) > MAX_MESSAGE_CHARS
    bounded_text = raw_text[:MAX_MESSAGE_CHARS]
    cleaned_text = _CONTROL_CHARS.sub("", bounded_text)
    control_removed = cleaned_text != bounded_text
    text = " ".join(cleaned_text.split())
    suspicious = any(key in intent or key in behavior for key in _SUSPICIOUS_KEYS)
    if suspicious:
        malformed = True
        intent = {}
        behavior = {}
    selected = str(intent.get("selected_intent") or "direct_answer")
    if selected not in _ALLOWED_INTENTS:
        selected = "direct_answer"
        malformed = True
    evidence = intent.get("evidence") if isinstance(intent.get("evidence"), dict) else {}
    if intent.get("evidence") is not None and not isinstance(intent.get("evidence"), dict):
        malformed = True
    posture = str(behavior.get("follow_up_posture") or "none")
    if posture not in _ALLOWED_FOLLOW_UP:
        posture = "none"
        malformed = True
    return FollowUpSilenceEvidence(
        selected_intent=selected,
        explicit_silence_request=bool(_EXPLICIT_SILENCE.search(text)),
        question_present=bool(_QUESTION.search(text)) or bool(evidence.get("question_count")),
        ambiguity_present=selected == "clarification" or str(intent.get("confidence") or "") == "low",
        insufficient_evidence=selected == "defer_insufficient_evidence" or bool(evidence.get("reasoning_uncertain")),
        correction_present=selected == "correction" or bool(evidence.get("explicit_correction")),
        contextual_follow_up_posture=posture,
        contextual_conflict=bool(behavior.get("conflicting_context_suppressed")),
        literal_request_precedence=True,
        malformed_context_fallback=malformed,
        explicit_continue_request=bool(_EXPLICIT_CONTINUE.search(text)),
        follow_up_utility=(
            "required" if selected == "clarification" else
            "useful" if selected == "follow_up" or bool(_EXPLICIT_CONTINUE.search(text)) else
            "low" if posture == "optional" and selected in {"acknowledgment", "explanation"} else
            "none"
        ),
        redundancy_risk=(
            selected in {"direct_answer", "summary", "correction", "acknowledgment"}
            and posture != "one_bounded_question"
        ),
        message_truncated=message_truncated,
        control_characters_removed=control_removed,
        suspicious_context_rejected=suspicious,
        multiple_question_markers=text.count("?") > 1,
        explicit_silence_verified=bool(_EXPLICIT_SILENCE.search(text)),
    )


def select_follow_up_silence_policy(evidence: FollowUpSilenceEvidence) -> dict[str, Any]:
    silence = "explicit_requested" if evidence.explicit_silence_request else "not_requested"
    follow_up = "none"
    reason = "answer_without_follow_up"
    max_questions = 0
    output_disposition = "answer_only"
    question_scope = "none"

    if evidence.explicit_silence_verified:
        reason = "honor_explicit_silence"
        output_disposition = "intentional_silence"
    elif evidence.correction_present:
        reason = "correction_requires_direct_response"
    elif evidence.contextual_conflict:
        reason = "conflicting_context_suppresses_follow_up"
    elif evidence.malformed_context_fallback:
        reason = "malformed_context_requires_neutral_response"
    elif evidence.follow_up_utility == "required":
        follow_up = "one_bounded_question"
        max_questions = 1
        reason = "missing_information_requires_one_question"
        output_disposition = "ask_one_question"
        question_scope = "missing_information_only"
    elif evidence.follow_up_utility == "useful":
        follow_up = "one_bounded_question"
        max_questions = 1
        reason = "literal_request_supports_one_question"
        output_disposition = "answer_then_one_question"
        question_scope = "current_topic_only"
    elif evidence.insufficient_evidence and evidence.contextual_follow_up_posture == "one_bounded_question":
        follow_up = "one_bounded_question"
        max_questions = 1
        reason = "missing_information_allows_one_question"
        output_disposition = "ask_one_question"
        question_scope = "missing_information_only"
    elif evidence.follow_up_utility == "low" and not evidence.redundancy_risk:
        follow_up = "optional"
        reason = "context_allows_nonredundant_optional_follow_up"
        output_disposition = "answer_then_optional_question"
        question_scope = "current_topic_only"
    elif evidence.redundancy_risk:
        reason = "redundancy_risk_suppresses_follow_up"

    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "silence_posture": silence,
        "follow_up_posture": follow_up,
        "max_follow_up_questions": max_questions,
        "selection_reason": reason,
        "output_disposition": output_disposition,
        "question_scope": question_scope,
        "follow_up_utility": evidence.follow_up_utility,
        "redundancy_avoided": evidence.redundancy_risk and follow_up == "none",
        "generic_offer_prohibited": True,
        "emit_no_substantive_content": output_disposition == "intentional_silence",
        "explicit_silence_verified": evidence.explicit_silence_verified,
        "silence_is_explicit_only": True,
        "silence_may_be_inferred": False,
        "may_initiate_new_turn": False,
        "may_contact_provider_for_selection": False,
        "literal_request_precedence": True,
        "selected_intent_precedence": True,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "policy_recovered": evidence.malformed_context_fallback,
    }
    result["policy_digest"] = _digest(result)
    return result

def normalize_follow_up_silence_policy(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    recovered = not isinstance(value, dict)
    silence = str(source.get("silence_posture") or "not_requested")
    if silence not in _ALLOWED_SILENCE:
        silence = "not_requested"
        recovered = True
    follow_up = str(source.get("follow_up_posture") or "none")
    if follow_up not in _ALLOWED_FOLLOW_UP:
        follow_up = "none"
        recovered = True
    dispositions = {"answer_only", "ask_one_question", "answer_then_one_question", "answer_then_optional_question", "intentional_silence"}
    disposition = str(source.get("output_disposition") or "answer_only")
    if disposition not in dispositions:
        disposition = "answer_only"
        recovered = True
    scopes = {"none", "missing_information_only", "current_topic_only"}
    scope = str(source.get("question_scope") or "none")
    if scope not in scopes:
        scope = "none"
        recovered = True
    utility = str(source.get("follow_up_utility") or "none")
    if utility not in {"none", "low", "useful", "required"}:
        utility = "none"
        recovered = True
    verified_silence = source.get("explicit_silence_verified") is True
    if (silence == "explicit_requested" or disposition == "intentional_silence") and not verified_silence:
        silence = "not_requested"
        disposition = "answer_only"
        follow_up = "none"
        scope = "none"
        recovered = True
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "silence_posture": silence,
        "follow_up_posture": follow_up,
        "max_follow_up_questions": 1 if follow_up == "one_bounded_question" else 0,
        "selection_reason": re.sub(r"[^a-z0-9_:-]+", "_", str(source.get("selection_reason") or "recovered_neutral").lower())[:80].strip("_") or "recovered_neutral",
        "output_disposition": disposition,
        "question_scope": scope,
        "follow_up_utility": utility,
        "redundancy_avoided": bool(source.get("redundancy_avoided")),
        "generic_offer_prohibited": True,
        "emit_no_substantive_content": disposition == "intentional_silence",
        "explicit_silence_verified": verified_silence,
        "silence_is_explicit_only": True,
        "silence_may_be_inferred": False,
        "may_initiate_new_turn": False,
        "may_contact_provider_for_selection": False,
        "literal_request_precedence": True,
        "selected_intent_precedence": True,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "policy_recovered": recovered or bool(source.get("policy_recovered")),
    }
    if silence == "explicit_requested" or disposition == "intentional_silence":
        result["silence_posture"] = "explicit_requested"
        result["follow_up_posture"] = "none"
        result["max_follow_up_questions"] = 0
        result["output_disposition"] = "intentional_silence"
        result["question_scope"] = "none"
        result["emit_no_substantive_content"] = True
    elif result["max_follow_up_questions"] == 0:
        result["question_scope"] = "none"
        if result["output_disposition"] != "answer_only":
            result["output_disposition"] = "answer_only"
            result["policy_recovered"] = True
    result["policy_digest"] = _digest(result)
    return result

def follow_up_silence_prompt_section(policy: dict[str, Any]) -> str:
    normalized = normalize_follow_up_silence_policy(policy)
    projection = {key: normalized[key] for key in (
        "silence_posture", "follow_up_posture", "max_follow_up_questions",
        "selection_reason", "output_disposition", "question_scope", "follow_up_utility",
        "redundancy_avoided", "generic_offer_prohibited", "emit_no_substantive_content",
        "explicit_silence_verified", "silence_is_explicit_only", "silence_may_be_inferred",
        "may_initiate_new_turn", "literal_request_precedence",
        "selected_intent_precedence", "approval_granted", "authorization_granted",
        "execution_permitted",
    )}
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"))
    section = '<follow_up_silence_policy data_only="true" authority="none">' + payload + '</follow_up_silence_policy>'
    if len(section) > MAX_PROMPT_CHARS:
        raise ValueError("Follow-up and silence prompt exceeded hard bound")
    return section


def build_follow_up_silence_policy(
    user_message: Any,
    response_intent: dict[str, Any] | None,
    contextual_behavior: dict[str, Any] | None,
) -> dict[str, Any]:
    evidence = build_follow_up_silence_evidence(user_message, response_intent, contextual_behavior)
    try:
        policy = select_follow_up_silence_policy(evidence)
        prompt = follow_up_silence_prompt_section(policy)
    except Exception:
        policy = normalize_follow_up_silence_policy({})
        prompt = follow_up_silence_prompt_section(policy)
    return {**policy, "evidence": evidence.public_summary(), "prompt_section": prompt}
