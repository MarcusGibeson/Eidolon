from __future__ import annotations

"""v1161.0-v1161.8 bounded natural-conversation continuity foundations, integration, and reliability.

This module converts structural turn adjacency into content-free continuity guidance.
It never exposes conversation text, contacts a provider, initiates a turn, or grants
approval, authorization, execution, installation, promotion, or certification.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable

CONTRACT_VERSION = "v1161.8"
SCHEMA_VERSION = "1"
MAX_MESSAGE_ANALYSIS_CHARS = 4096
MAX_HISTORY_RECORDS = 24
MAX_PROMPT_CHARS = 1650
_TOKEN = re.compile(r"[^a-z0-9_:-]+")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_STALE = {"stale", "retracted", "superseded", "expired", "inactive", "invalid"}
_SUSPICIOUS = {
    "system_prompt", "provider_prompt", "provider_payload", "private_reasoning",
    "hidden_reasoning", "chain_of_thought", "injected_instruction", "instructions",
    "approval_granted", "authorization_granted", "execution_permitted",
}
_SHORT_REPLY = {"yes", "no", "okay", "ok", "sure", "correct", "right", "exactly", "thanks", "thank_you"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _token(value: Any, default: str, maximum: int = 48) -> str:
    cleaned = _TOKEN.sub("_", str(value or default).lower()).strip("_")[:maximum]
    return cleaned or default


def _bounded_rows(value: Any) -> tuple[list[dict[str, Any]], bool, bool]:
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
        if index >= MAX_HISTORY_RECORDS:
            truncated = True
            break
        if isinstance(item, dict):
            rows.append(item)
    return rows, truncated, False


def _stale(row: dict[str, Any]) -> bool:
    for key in ("state", "status", "lifecycle", "validity"):
        if _token(row.get(key), "", 24) in _STALE:
            return True
    return any(row.get(key) is True for key in _STALE)


def _suspicious(row: dict[str, Any]) -> bool:
    return any(str(key).lower() in _SUSPICIOUS for key in row)


def _text(row: dict[str, Any]) -> str:
    return _CONTROL.sub("", str(row.get("content") or row.get("text") or row.get("message") or "")[:MAX_MESSAGE_ANALYSIS_CHARS])


@dataclass(frozen=True)
class NaturalContinuityEvidence:
    message_present: bool
    message_truncated: bool
    control_characters_removed: bool
    message_is_short_reply: bool
    history_count: int
    history_truncated: bool
    history_malformed: bool
    stale_records_ignored: int
    suspicious_records_ignored: int
    latest_valid_role: str
    latest_assistant_turn_present: bool
    latest_assistant_asked_question: bool
    adjacent_user_assistant_pair_present: bool
    duplicate_recent_assistant_questions: int
    prior_question_ambiguous: bool
    contradictory_linkage_cues: bool
    evidence_integrity: str
    discourse_relation: str
    discourse_context_integrity: str
    selected_intent: str
    explicit_correction_present: bool
    verified_silence_present: bool
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
class NaturalContinuityPolicy:
    continuity_relation: str
    thread_posture: str
    reference_posture: str
    maximum_prior_turn_references: int
    maximum_recap_sentences: int
    answer_prior_question_directly: bool
    continue_without_restart: bool
    repair_without_replaying_history: bool
    close_without_reopening: bool
    use_current_message_as_primary_grounding: bool
    avoid_false_shared_memory_claims: bool
    avoid_repeating_completed_content: bool
    continuity_confidence: str
    linkage_target: str
    opening_move: str
    response_progression: str
    consume_prior_question: bool
    resume_at_next_unfinished_point: bool
    replace_only_corrected_element: bool
    avoid_reasking_answered_question: bool
    avoid_repeating_prior_answer: bool
    maximum_bridge_sentences: int
    prior_question_ambiguity_suppressed: bool
    contradictory_linkage_suppressed: bool
    evidence_integrity: str
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


def build_natural_continuity_evidence(
    current_message: Any,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    raw = "" if current_message is None else str(current_message)
    bounded_raw = raw[:MAX_MESSAGE_ANALYSIS_CHARS]
    message = _CONTROL.sub("", bounded_raw)
    compact = _token(message, "", 64)
    rows, truncated, malformed = _bounded_rows(conversation_history)
    valid: list[dict[str, Any]] = []
    stale_ignored = suspicious_ignored = 0
    for row in rows:
        if _stale(row):
            stale_ignored += 1
        elif _suspicious(row):
            suspicious_ignored += 1
        elif _text(row).strip():
            valid.append(row)
    latest = valid[-1] if valid else {}
    latest_role = _token(latest.get("role") or latest.get("kind"), "none", 24)
    latest_assistant = "assistant" in latest_role
    latest_question = latest_assistant and "?" in _text(latest)
    adjacent_pair = len(valid) >= 2 and "user" in _token(valid[-2].get("role"), "", 24) and latest_assistant
    recent_question_digests: list[str] = []
    for row in valid[-8:]:
        role = _token(row.get("role") or row.get("kind"), "none", 24)
        text = _text(row).strip()
        if "assistant" in role and "?" in text:
            recent_question_digests.append(_digest({"question": text}))
    duplicate_questions = 0
    if latest_question and recent_question_digests:
        duplicate_questions = max(0, recent_question_digests.count(recent_question_digests[-1]) - 1)
    canonical = conversation_policy_state if isinstance(conversation_policy_state, dict) else {}
    discourse = conversation_discourse_policy if isinstance(conversation_discourse_policy, dict) else {}
    relation = _token(discourse.get("discourse_relation"), "respond", 32)
    correction = discourse.get("address_explicit_correction") is True
    silence = canonical.get("intentional_silence_verified") is True
    contradictory_linkage = (correction and relation in {"continue", "close"}) or (silence and relation not in {"close"})
    evidence_integrity = "degraded" if malformed or suspicious_ignored or contradictory_linkage else "verified"
    evidence = NaturalContinuityEvidence(
        message_present=bool(message.strip()),
        message_truncated=len(raw) > len(bounded_raw),
        control_characters_removed=message != bounded_raw,
        message_is_short_reply=compact in _SHORT_REPLY or (0 < len(message.split()) <= 3 and not "?" in message),
        history_count=len(rows),
        history_truncated=truncated,
        history_malformed=malformed,
        stale_records_ignored=min(stale_ignored, MAX_HISTORY_RECORDS),
        suspicious_records_ignored=min(suspicious_ignored, MAX_HISTORY_RECORDS),
        latest_valid_role=latest_role,
        latest_assistant_turn_present=latest_assistant,
        latest_assistant_asked_question=latest_question,
        adjacent_user_assistant_pair_present=adjacent_pair,
        duplicate_recent_assistant_questions=min(duplicate_questions, MAX_HISTORY_RECORDS),
        prior_question_ambiguous=duplicate_questions > 0,
        contradictory_linkage_cues=contradictory_linkage,
        evidence_integrity=evidence_integrity,
        discourse_relation=relation,
        discourse_context_integrity=_token(discourse.get("context_integrity"), "degraded", 24),
        selected_intent=_token(canonical.get("selected_intent"), "direct_answer", 40),
        explicit_correction_present=discourse.get("address_explicit_correction") is True,
        verified_silence_present=canonical.get("intentional_silence_verified") is True,
    )
    return evidence.public_summary()


def _evidence_digest_valid(source: dict[str, Any]) -> bool:
    supplied = source.get("evidence_digest")
    if not isinstance(supplied, str) or len(supplied) != 64:
        return False
    payload = dict(source)
    payload.pop("evidence_digest", None)
    return _digest(payload) == supplied


def build_natural_continuity_policy(evidence: dict[str, Any] | None) -> dict[str, Any]:
    source = evidence if isinstance(evidence, dict) else {}
    digest_valid = _evidence_digest_valid(source) if isinstance(evidence, dict) else False
    recovered = not isinstance(evidence, dict) or source.get("history_malformed") is True or not digest_valid
    contradictory = source.get("contradictory_linkage_cues") is True
    ambiguous_question = source.get("prior_question_ambiguous") is True
    integrity = (
        source.get("discourse_context_integrity") == "verified"
        and source.get("evidence_integrity") == "verified"
        and not recovered
        and not contradictory
        and int(source.get("suspicious_records_ignored") or 0) == 0
    )
    relation = _token(source.get("discourse_relation"), "respond", 32)
    prior = source.get("latest_assistant_turn_present") is True
    prior_question = source.get("latest_assistant_asked_question") is True
    short_reply = source.get("message_is_short_reply") is True
    correction = source.get("explicit_correction_present") is True
    silence = source.get("verified_silence_present") is True

    if silence:
        continuity_relation = "close_thread"
        posture = "silent_completion"
    elif contradictory:
        continuity_relation = "fresh_turn"
        posture = "current_turn_primary"
    elif correction or relation == "repair":
        continuity_relation = "repair_thread"
        posture = "current_turn_repair"
    elif relation == "continue" and prior and integrity:
        continuity_relation = "continue_thread"
        posture = "adjacent_continuation"
    elif prior_question and short_reply and integrity and not ambiguous_question:
        continuity_relation = "answer_prior_question"
        posture = "adjacent_answer"
    elif relation == "close":
        continuity_relation = "close_thread"
        posture = "bounded_closure"
    else:
        continuity_relation = "fresh_turn" if not prior or not integrity else "adjacent_turn"
        posture = "current_turn_primary"

    may_reference = continuity_relation in {"continue_thread", "answer_prior_question", "repair_thread", "adjacent_turn"} and prior and integrity
    reference_posture = "one_brief_reference" if continuity_relation in {"continue_thread", "repair_thread"} and may_reference else ("implicit_only" if may_reference else "none")
    max_refs = 1 if may_reference else 0
    max_recap = 0
    confidence = "high" if integrity and continuity_relation != "fresh_turn" else ("medium" if not recovered else "low")

    if continuity_relation == "answer_prior_question":
        linkage_target = "latest_assistant_question"
        opening_move = "answer_directly"
        progression = "consume_question_then_continue_current_topic"
    elif continuity_relation == "continue_thread":
        linkage_target = "current_thread"
        opening_move = "resume_in_place"
        progression = "continue_from_next_unfinished_point"
    elif continuity_relation == "repair_thread":
        linkage_target = "latest_corrected_element"
        opening_move = "acknowledge_correction_once"
        progression = "replace_corrected_element_then_continue"
    elif continuity_relation == "close_thread":
        linkage_target = "none"
        opening_move = "minimal_closure"
        progression = "close_without_reopening"
    elif continuity_relation == "adjacent_turn":
        linkage_target = "current_thread"
        opening_move = "answer_current_turn"
        progression = "use_prior_context_only_if_needed"
    else:
        linkage_target = "none"
        opening_move = "answer_current_turn"
        progression = "treat_as_fresh_turn"

    policy = NaturalContinuityPolicy(
        continuity_relation=continuity_relation,
        thread_posture=posture,
        reference_posture=reference_posture,
        maximum_prior_turn_references=max_refs,
        maximum_recap_sentences=max_recap,
        answer_prior_question_directly=continuity_relation == "answer_prior_question",
        continue_without_restart=continuity_relation == "continue_thread",
        repair_without_replaying_history=continuity_relation == "repair_thread",
        close_without_reopening=continuity_relation == "close_thread",
        use_current_message_as_primary_grounding=True,
        avoid_false_shared_memory_claims=True,
        avoid_repeating_completed_content=True,
        continuity_confidence=confidence,
        linkage_target=linkage_target,
        opening_move=opening_move,
        response_progression=progression,
        consume_prior_question=continuity_relation == "answer_prior_question",
        resume_at_next_unfinished_point=continuity_relation == "continue_thread",
        replace_only_corrected_element=continuity_relation == "repair_thread",
        avoid_reasking_answered_question=True,
        avoid_repeating_prior_answer=True,
        maximum_bridge_sentences=1 if may_reference and continuity_relation in {"continue_thread", "repair_thread"} else 0,
        prior_question_ambiguity_suppressed=ambiguous_question,
        contradictory_linkage_suppressed=contradictory,
        evidence_integrity="verified" if integrity else "degraded",
        may_initiate_new_turn=False,
        approval_granted=False,
        authorization_granted=False,
        execution_permitted=False,
        policy_recovered=recovered,
        evidence_digest=str(source.get("evidence_digest") or _digest({"malformed": True})),
    )
    public = policy.public_summary()
    public["prompt_section"] = natural_continuity_prompt_section(public)
    return public


def natural_continuity_prompt_section(policy: dict[str, Any]) -> str:
    keys = (
        "continuity_relation", "thread_posture", "reference_posture",
        "maximum_prior_turn_references", "maximum_recap_sentences",
        "answer_prior_question_directly", "continue_without_restart",
        "repair_without_replaying_history", "close_without_reopening",
        "use_current_message_as_primary_grounding", "avoid_false_shared_memory_claims",
        "avoid_repeating_completed_content", "continuity_confidence",
        "linkage_target", "opening_move", "response_progression",
        "consume_prior_question", "resume_at_next_unfinished_point",
        "replace_only_corrected_element", "avoid_reasking_answered_question",
        "avoid_repeating_prior_answer", "maximum_bridge_sentences",
        "prior_question_ambiguity_suppressed", "contradictory_linkage_suppressed",
        "evidence_integrity", "may_initiate_new_turn", "approval_granted", "authorization_granted", "execution_permitted",
    )
    payload = json.dumps({key: policy.get(key) for key in keys}, sort_keys=True, separators=(",", ":"))
    section = '<natural_conversation_continuity data_only="true" authority="none">' + payload + '</natural_conversation_continuity>'
    if len(section) > MAX_PROMPT_CHARS:
        raise ValueError("Natural conversation continuity prompt exceeded hard bound")
    return section


def build_natural_continuity_for_turn(
    current_message: Any,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = build_natural_continuity_evidence(
        current_message, conversation_policy_state, conversation_discourse_policy,
        conversation_history=conversation_history,
    )
    policy = build_natural_continuity_policy(evidence)
    policy["evidence"] = evidence
    return policy
