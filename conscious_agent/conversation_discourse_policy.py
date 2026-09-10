from __future__ import annotations

"""v1160.0-v1160.2 bounded conversation-policy foundations.

This module derives a structural discourse policy for the current ordinary turn.
It does not expose conversation text, contact a provider, initiate another turn,
or grant approval, authorization, execution, installation, promotion, or
certification authority.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable

CONTRACT_VERSION = "v1160.8"
SCHEMA_VERSION = "1"
MAX_MESSAGE_ANALYSIS_CHARS = 4096
MAX_HISTORY_RECORDS = 24
MAX_PROMPT_CHARS = 1600
MAX_CORRECTION_RECORDS = 24
MAX_REPAIR_LOOP_SIGNALS = 3
_TOKEN = re.compile(r"[^a-z0-9_:-]+")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SUSPICIOUS_KEYS = {
    "system_prompt", "provider_prompt", "provider_payload", "private_reasoning",
    "hidden_reasoning", "chain_of_thought", "injected_instruction", "instructions",
    "approval_granted", "authorization_granted", "execution_permitted",
}
_STALE_VALUES = {"stale", "retracted", "superseded", "expired", "inactive", "invalid"}

_CONTINUATION_CUES = (
    "continue", "keep going", "go on", "more detail", "expand", "elaborate",
    "what about", "and then", "next", "also",
)
_CORRECTION_CUES = (
    "that's wrong", "that is wrong", "not what i", "i meant", "correction",
    "actually", "you misunderstood", "don't", "do not",
)
_CLOSING_CUES = (
    "thanks", "thank you", "got it", "understood", "that helps", "perfect",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _token(value: Any, default: str, maximum: int = 48) -> str:
    cleaned = _TOKEN.sub("_", str(value or default).lower()).strip("_")[:maximum]
    return cleaned or default


def _bounded_records(value: Any, limit: int) -> tuple[list[dict[str, Any]], bool, bool]:
    if value is None:
        return [], False, False
    if isinstance(value, (str, bytes, dict)):
        return [], False, True
    try:
        iterator = iter(value)
    except TypeError:
        return [], False, True
    rows: list[dict[str, Any]] = []
    truncated = False
    for index, item in enumerate(iterator):
        if index >= limit:
            truncated = True
            break
        if isinstance(item, dict):
            rows.append(item)
    return rows, truncated, False


def _role(row: dict[str, Any]) -> str:
    return _token(row.get("role") or row.get("kind") or row.get("memory_type"), "unknown", 32)


def _record_is_stale(row: dict[str, Any]) -> bool:
    for key in ("state", "status", "lifecycle", "validity"):
        if _token(row.get(key), "", 24) in _STALE_VALUES:
            return True
    return any(row.get(key) is True for key in ("stale", "retracted", "superseded", "expired", "inactive", "invalid"))


def _record_is_suspicious(row: dict[str, Any]) -> bool:
    return any(str(key).lower() in _SUSPICIOUS_KEYS for key in row)


def _content_shape(row: dict[str, Any]) -> tuple[bool, bool, bool, bool]:
    text = str(row.get("content") or row.get("text") or row.get("message") or "")[:MAX_MESSAGE_ANALYSIS_CHARS]
    cleaned = _CONTROL_CHARS.sub("", text)
    lowered = cleaned.lower()
    return bool(cleaned.strip()), "?" in cleaned, any(cue in lowered for cue in _CLOSING_CUES), cleaned != text


@dataclass(frozen=True)
class ConversationDiscourseEvidence:
    message_present: bool
    message_truncated: bool
    message_control_characters_removed: bool
    message_has_question: bool
    contradictory_literal_cues: bool
    literal_continuation_cue: bool
    literal_correction_cue: bool
    literal_closing_cue: bool
    history_available: bool
    history_count: int
    history_truncated: bool
    history_malformed: bool
    stale_history_records_ignored: int
    suspicious_history_records_ignored: int
    prior_assistant_turn_present: bool
    prior_assistant_question_present: bool
    prior_user_turn_present: bool
    explicit_correction_present: bool
    repeated_repair_loop_present: bool
    selected_intent: str
    output_disposition: str
    context_conflict_present: bool
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False,
            "contains_conversation_text": False,
            "contains_memory_text": False,
            "contains_provider_payload": False,
            "contains_private_chain_of_thought": False,
            "provider_contacted": False,
        })
        result["evidence_digest"] = _digest(result)
        return result


@dataclass(frozen=True)
class ConversationDiscoursePolicy:
    discourse_relation: str
    primary_obligation: str
    continuity_mode: str
    grounding_mode: str
    repetition_policy: str
    closure_policy: str
    answer_current_request: bool
    address_explicit_correction: bool
    resolve_prior_question_only_if_relevant: bool
    preserve_current_topic: bool
    avoid_unearned_continuity_claims: bool
    avoid_repeating_completed_content: bool
    may_reference_prior_turn: bool
    opening_move: str
    prior_context_use: str
    repair_sequence: str
    completion_shape: str
    maximum_prior_turn_references: int
    maximum_recap_sentences: int
    generic_closing_offer_allowed: bool
    context_integrity: str
    contradictory_cues_suppressed: bool
    repeated_repair_loop_suppressed: bool
    may_initiate_new_turn: bool
    approval_granted: bool
    authorization_granted: bool
    execution_permitted: bool
    policy_recovered: bool
    evidence_digest: str
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False,
            "contains_conversation_text": False,
            "contains_memory_text": False,
            "contains_provider_payload": False,
            "contains_private_chain_of_thought": False,
            "provider_contacted_for_policy": False,
        })
        result["policy_digest"] = _digest(result)
        return result


def build_conversation_discourse_evidence(
    current_message: Any,
    conversation_policy_state: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    explicit_corrections: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    raw = "" if current_message is None else str(current_message)
    raw_bounded = raw[:MAX_MESSAGE_ANALYSIS_CHARS]
    bounded = _CONTROL_CHARS.sub("", raw_bounded)
    lowered = bounded.lower()
    history, history_truncated, history_malformed = _bounded_records(conversation_history, MAX_HISTORY_RECORDS)
    corrections, corrections_truncated, corrections_malformed = _bounded_records(explicit_corrections, MAX_CORRECTION_RECORDS)
    policy = conversation_policy_state if isinstance(conversation_policy_state, dict) else {}

    prior_assistant = False
    prior_assistant_question = False
    prior_user = False
    stale_ignored = 0
    suspicious_ignored = 0
    repair_signals = 0
    for row in reversed(history):
        if _record_is_stale(row):
            stale_ignored += 1
            continue
        if _record_is_suspicious(row):
            suspicious_ignored += 1
            continue
        role = _role(row)
        present, has_question, _, _ = _content_shape(row)
        if not present:
            continue
        lowered_row = str(row.get("content") or row.get("text") or row.get("message") or "").lower()[:MAX_MESSAGE_ANALYSIS_CHARS]
        if any(cue in lowered_row for cue in _CORRECTION_CUES):
            repair_signals += 1
        if not prior_assistant and "assistant" in role:
            prior_assistant = True
            prior_assistant_question = has_question
        if not prior_user and "user" in role:
            prior_user = True

    evidence = ConversationDiscourseEvidence(
        message_present=bool(bounded.strip()),
        message_truncated=len(raw) > len(raw_bounded),
        message_control_characters_removed=bounded != raw_bounded,
        message_has_question="?" in bounded,
        contradictory_literal_cues=(any(cue in lowered for cue in _CONTINUATION_CUES) and any(cue in lowered for cue in _CLOSING_CUES)) or (any(cue in lowered for cue in _CORRECTION_CUES) and any(cue in lowered for cue in _CLOSING_CUES)),
        literal_continuation_cue=any(cue in lowered for cue in _CONTINUATION_CUES),
        literal_correction_cue=any(cue in lowered for cue in _CORRECTION_CUES),
        literal_closing_cue=any(cue in lowered for cue in _CLOSING_CUES),
        history_available=bool(history),
        history_count=len(history),
        history_truncated=history_truncated or corrections_truncated,
        history_malformed=history_malformed or corrections_malformed,
        stale_history_records_ignored=min(stale_ignored, MAX_HISTORY_RECORDS),
        suspicious_history_records_ignored=min(suspicious_ignored, MAX_HISTORY_RECORDS),
        prior_assistant_turn_present=prior_assistant,
        prior_assistant_question_present=prior_assistant_question,
        prior_user_turn_present=prior_user,
        explicit_correction_present=bool(corrections) or bool(policy.get("selected_intent") == "correction"),
        repeated_repair_loop_present=repair_signals >= MAX_REPAIR_LOOP_SIGNALS,
        selected_intent=_token(policy.get("selected_intent"), "direct_answer", 40),
        output_disposition=_token(policy.get("output_disposition"), "answer_only", 40),
        context_conflict_present=policy.get("component_conflict_present") is True,
    )
    return evidence.public_summary()


def build_conversation_discourse_policy(evidence: dict[str, Any] | None) -> dict[str, Any]:
    source = evidence if isinstance(evidence, dict) else {}
    recovered = not isinstance(evidence, dict) or source.get("history_malformed") is True
    selected = _token(source.get("selected_intent"), "direct_answer", 40)
    disposition = _token(source.get("output_disposition"), "answer_only", 40)
    correction = source.get("explicit_correction_present") is True or source.get("literal_correction_cue") is True
    continuation = source.get("literal_continuation_cue") is True
    closing = source.get("literal_closing_cue") is True
    prior_turn = source.get("prior_assistant_turn_present") is True
    conflict = source.get("context_conflict_present") is True
    contradictory = source.get("contradictory_literal_cues") is True
    repeated_repair = source.get("repeated_repair_loop_present") is True
    suspicious_ignored = int(source.get("suspicious_history_records_ignored") or 0) if str(source.get("suspicious_history_records_ignored") or "0").isdigit() else 0
    integrity_degraded = recovered or contradictory or repeated_repair or suspicious_ignored > 0

    if disposition == "intentional_silence":
        relation = "close"
        obligation = "honor_explicit_silence"
        continuity = "none"
        grounding = "literal_current_turn"
        closure = "silent_completion"
    elif correction or selected == "correction":
        relation = "repair"
        obligation = "address_correction_first"
        continuity = "implicit" if prior_turn else "none"
        grounding = "literal_current_turn"
        closure = "complete_current_turn"
    elif continuation:
        relation = "continue"
        obligation = "continue_current_topic"
        continuity = "brief_explicit" if prior_turn and not conflict else "implicit"
        grounding = "current_and_prior_turn"
        closure = "complete_current_turn"
    elif selected == "clarification" or disposition == "ask_one_question":
        relation = "clarify"
        obligation = "request_missing_information"
        continuity = "implicit" if prior_turn else "none"
        grounding = "literal_current_turn"
        closure = "await_bounded_reply"
    elif closing and selected in {"acknowledgment", "direct_answer"}:
        relation = "close"
        obligation = "acknowledge_without_reopening"
        continuity = "none"
        grounding = "literal_current_turn"
        closure = "do_not_reopen"
    else:
        relation = "respond"
        obligation = "answer_current_request"
        continuity = "implicit" if prior_turn and not conflict else "none"
        grounding = "current_turn_primary"
        closure = "complete_current_turn"

    if contradictory:
        relation = "respond"
        obligation = "answer_current_request"
        continuity = "none"
        grounding = "literal_current_turn"
        closure = "complete_current_turn"
        correction = False

    if conflict or repeated_repair:
        continuity = "none"

    if relation == "repair":
        opening_move = "acknowledge_correction_then_replace"
        prior_context_use = "one_brief_reference" if prior_turn else "none"
        repair_sequence = "acknowledge_correct_answer"
        completion_shape = "complete_without_offer"
        max_prior_refs = 1 if prior_turn else 0
        max_recap = 0
    elif relation == "continue":
        opening_move = "continue_without_recap"
        prior_context_use = "one_brief_reference" if continuity == "brief_explicit" else ("implicit_only" if continuity == "implicit" else "none")
        repair_sequence = "none"
        completion_shape = "complete_without_offer"
        max_prior_refs = 1 if continuity != "none" else 0
        max_recap = 0
    elif relation == "clarify":
        opening_move = "ask_missing_information_directly"
        prior_context_use = "implicit_only" if continuity == "implicit" else "none"
        repair_sequence = "none"
        completion_shape = "await_required_reply"
        max_prior_refs = 0
        max_recap = 0
    elif obligation == "honor_explicit_silence":
        opening_move = "no_substantive_content"
        prior_context_use = "none"
        repair_sequence = "none"
        completion_shape = "silent_completion"
        max_prior_refs = 0
        max_recap = 0
    elif relation == "close":
        opening_move = "brief_acknowledgment"
        prior_context_use = "none"
        repair_sequence = "none"
        completion_shape = "close_without_offer"
        max_prior_refs = 0
        max_recap = 0
    else:
        opening_move = "answer_current_request_first"
        prior_context_use = "implicit_only" if continuity == "implicit" else "none"
        repair_sequence = "none"
        completion_shape = "complete_without_offer"
        max_prior_refs = 0
        max_recap = 1 if selected == "summary" else 0

    if conflict or integrity_degraded:
        prior_context_use = "none"
        max_prior_refs = 0
    if repeated_repair:
        opening_move = "answer_current_request_first"
        repair_sequence = "none"
        max_recap = 0

    policy = ConversationDiscoursePolicy(
        discourse_relation=relation,
        primary_obligation=obligation,
        continuity_mode=continuity,
        grounding_mode=grounding,
        repetition_policy="avoid_completed_content_repetition",
        closure_policy=closure,
        answer_current_request=disposition != "intentional_silence",
        address_explicit_correction=correction,
        resolve_prior_question_only_if_relevant=True,
        preserve_current_topic=True,
        avoid_unearned_continuity_claims=True,
        avoid_repeating_completed_content=True,
        may_reference_prior_turn=continuity != "none" and not recovered,
        opening_move=opening_move,
        prior_context_use=prior_context_use,
        repair_sequence=repair_sequence,
        completion_shape=completion_shape,
        maximum_prior_turn_references=max_prior_refs,
        maximum_recap_sentences=max_recap,
        generic_closing_offer_allowed=False,
        context_integrity="degraded" if integrity_degraded else "verified",
        contradictory_cues_suppressed=contradictory,
        repeated_repair_loop_suppressed=repeated_repair,
        may_initiate_new_turn=False,
        approval_granted=False,
        authorization_granted=False,
        execution_permitted=False,
        policy_recovered=recovered,
        evidence_digest=str(source.get("evidence_digest") or _digest({"malformed": True})),
    )
    public = policy.public_summary()
    public["prompt_section"] = conversation_discourse_prompt_section(public)
    return public


def conversation_discourse_prompt_section(policy: dict[str, Any]) -> str:
    keys = (
        "discourse_relation", "primary_obligation", "continuity_mode", "grounding_mode",
        "repetition_policy", "closure_policy", "answer_current_request",
        "address_explicit_correction", "resolve_prior_question_only_if_relevant",
        "preserve_current_topic", "avoid_unearned_continuity_claims",
        "avoid_repeating_completed_content", "may_reference_prior_turn",
        "opening_move", "prior_context_use", "repair_sequence",
        "completion_shape", "maximum_prior_turn_references",
        "maximum_recap_sentences", "generic_closing_offer_allowed",
        "context_integrity", "contradictory_cues_suppressed",
        "repeated_repair_loop_suppressed", "may_initiate_new_turn", "approval_granted", "authorization_granted",
        "execution_permitted",
    )
    projection = {key: policy.get(key) for key in keys}
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"))
    section = '<conversation_discourse_policy data_only="true" authority="none">' + payload + '</conversation_discourse_policy>'
    if len(section) > MAX_PROMPT_CHARS:
        raise ValueError("Conversation discourse policy prompt exceeded hard bound")
    return section


def build_conversation_discourse_policy_for_turn(
    current_message: Any,
    conversation_policy_state: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    explicit_corrections: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = build_conversation_discourse_evidence(
        current_message,
        conversation_policy_state,
        conversation_history=conversation_history,
        explicit_corrections=explicit_corrections,
    )
    policy = build_conversation_discourse_policy(evidence)
    policy["evidence"] = evidence
    return policy
