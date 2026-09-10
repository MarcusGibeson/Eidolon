from __future__ import annotations

"""v1163.0-v1163.2 governed speech foundations for an existing user turn.

This module may shape only the response already requested by the user. It cannot
initiate a new turn, expose private reflection, ramble, execute actions, mutate
memory or learning, or grant approval, authorization, installation, promotion,
or certification authority.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable

CONTRACT_VERSION = "v1163.8"
SCHEMA_VERSION = "1"
MAX_MESSAGE_CHARS = 4096
MAX_CONTEXT_ROWS = 24
MAX_PROMPT_CHARS = 1800
MAX_RESPONSE_AUDIT_CHARS = 8192
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TOKEN = re.compile(r"[^a-z0-9_:-]+")
_SUSPICIOUS_KEYS = {
    "system_prompt", "provider_prompt", "provider_payload", "private_reasoning",
    "hidden_reasoning", "chain_of_thought", "approval_granted",
    "authorization_granted", "execution_permitted", "tool_intent",
    "initiate_new_turn", "autonomous_reflection_delivery",
}
_STALE = {"stale", "retracted", "superseded", "expired", "invalid", "inactive"}
_EXPLICIT_EXPANSION_CUES = (
    "tell me more", "go deeper", "expand", "what do you notice", "your thoughts",
    "what do you think", "anything important", "what am i missing",
)
_BRIEFNESS_CUES = ("briefly", "keep it brief", "short answer", "just answer", "concise", "no extra")
_INTERRUPTION_CUES = ("stop", "enough", "do not continue", "don't continue", "no more", "leave it there")
_OPERATOR_SUPPRESSION_CONSTRAINTS = {
    "force_reactive_only", "suppress_optional_expansion", "no_optional_observation",
    "no_proactive_speech", "preserve_deliberate_silence",
}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _token(value: Any, default: str, maximum: int = 48) -> str:
    cleaned = _TOKEN.sub("_", str(value or default).lower()).strip("_")[:maximum]
    return cleaned or default


def _contains_phrase(message: str, cue: str) -> bool:
    return re.search(r"(?:^|\s)" + re.escape(cue) + r"(?:$|\s)", message) is not None


def _literal(value: Any) -> tuple[str, bool, bool]:
    raw = "" if value is None else str(value)
    bounded = raw[:MAX_MESSAGE_CHARS]
    cleaned = _CONTROL.sub("", bounded).lower()
    normalized = " ".join(re.sub(r"[^a-z0-9?' ]+", " ", cleaned).split())
    return normalized, len(raw) > len(bounded), cleaned != bounded


def _rows(value: Any) -> tuple[list[dict[str, Any]], bool, bool]:
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
        if index >= MAX_CONTEXT_ROWS:
            truncated = True
            break
        if isinstance(item, dict):
            rows.append(item)
    return rows, truncated, False


def _stale(row: dict[str, Any]) -> bool:
    return any(_token(row.get(key), "", 24) in _STALE for key in ("state", "status", "validity", "lifecycle")) or any(row.get(key) is True for key in _STALE)


def _suspicious(row: dict[str, Any]) -> bool:
    return any(str(key).lower() in _SUSPICIOUS_KEYS for key in row)


@dataclass(frozen=True)
class GovernedSpeechEvidence:
    message_present: bool
    message_truncated: bool
    control_characters_removed: bool
    response_turn_exists: bool
    response_intent: str
    continuation_posture: str
    topic_state: str
    discourse_relation: str
    explicit_expansion_requested: bool
    explicit_briefness_requested: bool
    required_clarification: bool
    topic_complete: bool
    intentional_silence_verified: bool
    correction_or_repair: bool
    repetition_risk_present: bool
    protected_constraints_present: bool
    operator_suppression_requested: bool
    interruption_requested: bool
    context_count: int
    context_truncated: bool
    context_malformed: bool
    expansion_cue_conflict: bool
    recent_expansion_count: int
    expansion_cooldown_applied: bool
    stale_records_ignored: int
    suspicious_records_ignored: int
    contradictory_state: bool
    evidence_integrity: str
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False,
            "contains_conversation_text": False,
            "contains_memory_text": False,
            "contains_reflection_text": False,
            "contains_provider_payload": False,
            "contains_private_chain_of_thought": False,
            "provider_contacted": False,
        })
        result["evidence_digest"] = _digest(result)
        return result


def build_governed_speech_evidence(
    current_message: Any,
    response_intent: dict[str, Any] | None,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    natural_follow_up_policy: dict[str, Any] | None,
    context_rows: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    message, truncated, controls_removed = _literal(current_message)
    intent = response_intent if isinstance(response_intent, dict) else {}
    canonical = conversation_policy_state if isinstance(conversation_policy_state, dict) else {}
    discourse = conversation_discourse_policy if isinstance(conversation_discourse_policy, dict) else {}
    follow_up = natural_follow_up_policy if isinstance(natural_follow_up_policy, dict) else {}
    rows, rows_truncated, malformed = _rows(context_rows)
    stale_ignored = suspicious_ignored = 0
    valid_count = 0
    for row in rows:
        if _stale(row):
            stale_ignored += 1
        elif _suspicious(row):
            suspicious_ignored += 1
        else:
            valid_count += 1
    selected_intent = _token(intent.get("selected_intent") or canonical.get("selected_intent"), "direct_answer", 40)
    posture = _token(follow_up.get("continuation_posture"), "answer_only", 48)
    topic_state = _token(follow_up.get("topic_continuity_posture"), "literal_current_request", 40)
    relation = _token(discourse.get("discourse_relation"), "respond", 32)
    explicit_expansion = any(_contains_phrase(message, cue) for cue in _EXPLICIT_EXPANSION_CUES)
    explicit_briefness = any(_contains_phrase(message, cue) for cue in _BRIEFNESS_CUES)
    interruption_requested = any(_contains_phrase(message, cue) for cue in _INTERRUPTION_CUES)
    try:
        protected_constraints = {_token(item, "", 64) for item in (protected_operator_constraints or ())}
    except TypeError:
        protected_constraints = set()
        malformed = True
    operator_suppression = bool(protected_constraints & _OPERATOR_SUPPRESSION_CONSTRAINTS)
    expansion_cue_conflict = explicit_expansion and (explicit_briefness or interruption_requested)
    recent_expansion_count = sum(
        1 for row in rows
        if not _stale(row) and not _suspicious(row)
        and _token(row.get("governed_speech_mode"), "", 48) == "bounded_user_requested_observation"
    )
    expansion_cooldown = recent_expansion_count >= 2
    required_clarification = posture == "ask_one_required_clarification" or selected_intent in {"clarification", "request_clarification"}
    topic_complete = topic_state == "complete" or posture == "briefly_acknowledge_and_close" or relation == "close"
    verified_silence = canonical.get("intentional_silence_verified") is True
    repair = posture == "repair_and_continue" or relation == "repair" or discourse.get("address_explicit_correction") is True
    repetition = any(follow_up.get(key) is True for key in (
        "avoid_repeated_acknowledgment", "avoid_repeated_explanation", "avoid_repeated_opening",
        "cue_conflict_suppressed", "low_confidence_suppressed",
    ))
    contradictory = (
        not isinstance(response_intent, dict)
        or not isinstance(conversation_policy_state, dict)
        or not isinstance(conversation_discourse_policy, dict)
        or not isinstance(natural_follow_up_policy, dict)
        or follow_up.get("may_initiate_new_turn") is True
        or follow_up.get("action_execution_permitted") is True
        or (verified_silence and required_clarification)
        or (topic_complete and posture in {"continue_current_topic", "answer_and_offer_one_relevant_next_step"})
    )
    integrity = "degraded" if malformed or suspicious_ignored or contradictory else "verified"
    return GovernedSpeechEvidence(
        message_present=bool(message), message_truncated=truncated,
        control_characters_removed=controls_removed, response_turn_exists=bool(message),
        response_intent=selected_intent, continuation_posture=posture,
        topic_state=topic_state, discourse_relation=relation,
        explicit_expansion_requested=explicit_expansion,
        explicit_briefness_requested=explicit_briefness,
        required_clarification=required_clarification, topic_complete=topic_complete,
        intentional_silence_verified=verified_silence, correction_or_repair=repair,
        repetition_risk_present=repetition,
        protected_constraints_present=bool(protected_constraints),
        operator_suppression_requested=operator_suppression,
        interruption_requested=interruption_requested,
        context_count=min(valid_count, MAX_CONTEXT_ROWS), context_truncated=rows_truncated,
        context_malformed=malformed, stale_records_ignored=stale_ignored,
        suspicious_records_ignored=suspicious_ignored, contradictory_state=contradictory,
        expansion_cue_conflict=expansion_cue_conflict,
        recent_expansion_count=min(recent_expansion_count, MAX_CONTEXT_ROWS),
        expansion_cooldown_applied=expansion_cooldown,
        evidence_integrity=integrity,
    ).public_summary()


def _valid_digest(source: dict[str, Any]) -> bool:
    supplied = source.get("evidence_digest")
    payload = dict(source)
    payload.pop("evidence_digest", None)
    return isinstance(supplied, str) and len(supplied) == 64 and _digest(payload) == supplied


def build_governed_speech_policy(evidence: dict[str, Any] | None) -> dict[str, Any]:
    source = evidence if isinstance(evidence, dict) else {}
    recovered = not isinstance(evidence, dict) or not _valid_digest(source)
    degraded = recovered or source.get("evidence_integrity") != "verified" or source.get("contradictory_state") is True
    operator_suppressed = source.get("operator_suppression_requested") is True
    interrupted = source.get("interruption_requested") is True
    mode = "reactive_answer_only"
    observation_budget = 0
    if not degraded:
        if source.get("intentional_silence_verified") is True:
            mode = "preserve_deliberate_silence"
        elif interrupted:
            mode = "brief_closure_only"
        elif source.get("required_clarification") is True:
            mode = "required_clarification_only"
        elif source.get("topic_complete") is True:
            mode = "brief_closure_only"
        elif source.get("correction_or_repair") is True:
            mode = "repair_without_expansion"
        elif source.get("explicit_expansion_requested") is True and source.get("explicit_briefness_requested") is not True and source.get("repetition_risk_present") is not True and source.get("expansion_cue_conflict") is not True and source.get("expansion_cooldown_applied") is not True and not operator_suppressed:
            mode = "bounded_user_requested_observation"
            observation_budget = 1
    policy = {
        "speech_mode": mode,
        "response_turn_only": True,
        "maximum_additional_observations": observation_budget,
        "maximum_reflection_summaries": 0,
        "maximum_expansion_sentences": 2 if observation_budget else 0,
        "maximum_expansion_paragraphs": 1 if observation_budget else 0,
        "maximum_unsolicited_topic_branches": 0,
        "rambling_permitted": False,
        "private_reflection_delivery_permitted": False,
        "deliberate_silence_preserved": mode == "preserve_deliberate_silence",
        "proactive_content_requires_literal_user_cue": True,
        "proactive_content_user_requested": source.get("explicit_expansion_requested") is True and not degraded,
        "optional_expansion_suppressed": observation_budget == 0,
        "operator_suppression_applied": operator_suppressed,
        "interruption_honored": interrupted,
        "expansion_cue_conflict_suppressed": source.get("expansion_cue_conflict") is True,
        "expansion_cooldown_applied": source.get("expansion_cooldown_applied") is True,
        "recent_expansion_count": int(source.get("recent_expansion_count") or 0),
        "stop_after_current_answer": interrupted or mode in {"brief_closure_only", "preserve_deliberate_silence"},
        "follow_up_question_budget": 0 if observation_budget or interrupted or mode in {"brief_closure_only", "preserve_deliberate_silence"} else 1,
        "answer_literal_current_request": True,
        "may_initiate_new_turn": False,
        "autonomous_new_turn_permitted": False,
        "tool_intent_selected": False,
        "action_execution_permitted": False,
        "learning_mutation_permitted": False,
        "memory_rewrite_permitted": False,
        "approval_granted": False,
        "authorization_granted": False,
        "installation_permitted": False,
        "promotion_permitted": False,
        "certification_permitted": False,
        "policy_recovered": recovered,
        "recovery_reason": "invalid_evidence_digest" if recovered else ("degraded_evidence" if degraded else ("operator_suppressed" if operator_suppressed else ("interruption_requested" if interrupted else ("conflicting_speech_cues" if source.get("expansion_cue_conflict") is True else ("expansion_cooldown" if source.get("expansion_cooldown_applied") is True else "none"))))),
        "evidence_digest": str(source.get("evidence_digest") or ""),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "contains_message_content": False,
        "contains_conversation_text": False,
        "contains_memory_text": False,
        "contains_reflection_text": False,
        "contains_provider_payload": False,
        "contains_private_chain_of_thought": False,
        "provider_contacted_for_policy": False,
    }
    policy["policy_digest"] = _digest(policy)
    policy["prompt_section"] = governed_speech_prompt_section(policy)
    return policy


def governed_speech_prompt_section(policy: dict[str, Any]) -> str:
    allowed = {key: value for key, value in policy.items() if key != "prompt_section"}
    section = '<governed_speech_policy data_only="true" authority="none">' + json.dumps(allowed, sort_keys=True, separators=(",", ":")) + '</governed_speech_policy>'
    if len(section) > MAX_PROMPT_CHARS:
        minimal_keys = (
            "speech_mode", "response_turn_only", "maximum_additional_observations",
            "maximum_reflection_summaries", "maximum_unsolicited_topic_branches",
            "maximum_expansion_sentences", "maximum_expansion_paragraphs",
            "rambling_permitted", "private_reflection_delivery_permitted",
            "may_initiate_new_turn", "action_execution_permitted", "policy_digest",
        )
        minimal = {key: allowed[key] for key in minimal_keys}
        section = '<governed_speech_policy data_only="true" authority="none">' + json.dumps(minimal, sort_keys=True, separators=(",", ":")) + '</governed_speech_policy>'
    return section


def build_governed_speech_for_turn(
    current_message: Any,
    response_intent: dict[str, Any] | None,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    natural_follow_up_policy: dict[str, Any] | None,
    context_rows: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    evidence = build_governed_speech_evidence(
        current_message, response_intent, conversation_policy_state,
        conversation_discourse_policy, natural_follow_up_policy,
        context_rows, protected_operator_constraints,
    )
    return {**build_governed_speech_policy(evidence), "evidence": evidence}


def build_governed_speech_runtime_projection(
    current_message: Any,
    response_intent: dict[str, Any] | None,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    natural_follow_up_policy: dict[str, Any] | None,
    context_rows: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    policy = build_governed_speech_for_turn(
        current_message, response_intent, conversation_policy_state,
        conversation_discourse_policy, natural_follow_up_policy,
        context_rows, protected_operator_constraints,
    )
    diagnostics = {
        "contract_version": policy.get("contract_version"),
        "schema_version": policy.get("schema_version"),
        "speech_mode": policy.get("speech_mode"),
        "response_turn_only": policy.get("response_turn_only") is True,
        "maximum_additional_observations": int(policy.get("maximum_additional_observations") or 0),
        "maximum_expansion_sentences": int(policy.get("maximum_expansion_sentences") or 0),
        "maximum_expansion_paragraphs": int(policy.get("maximum_expansion_paragraphs") or 0),
        "operator_suppression_applied": policy.get("operator_suppression_applied") is True,
        "interruption_honored": policy.get("interruption_honored") is True,
        "stop_after_current_answer": policy.get("stop_after_current_answer") is True,
        "expansion_cue_conflict_suppressed": policy.get("expansion_cue_conflict_suppressed") is True,
        "expansion_cooldown_applied": policy.get("expansion_cooldown_applied") is True,
        "recent_expansion_count": int(policy.get("recent_expansion_count") or 0),
        "rambling_permitted": policy.get("rambling_permitted") is True,
        "private_reflection_delivery_permitted": policy.get("private_reflection_delivery_permitted") is True,
        "may_initiate_new_turn": policy.get("may_initiate_new_turn") is True,
        "policy_recovered": policy.get("policy_recovered") is True,
        "recovery_reason": policy.get("recovery_reason"),
        "contains_content": False,
        "contains_private_chain_of_thought": False,
        "authority": "none",
    }
    diagnostics["diagnostics_digest"] = _digest(diagnostics)
    return {"policy": policy, "prompt_section": policy["prompt_section"], "diagnostics": diagnostics}


def verify_governed_speech_runtime_diagnostics(diagnostics: dict[str, Any] | None) -> bool:
    if not isinstance(diagnostics, dict):
        return False
    supplied = diagnostics.get("diagnostics_digest")
    payload = dict(diagnostics)
    payload.pop("diagnostics_digest", None)
    return isinstance(supplied, str) and len(supplied) == 64 and _digest(payload) == supplied


def audit_governed_speech_response_shape(response_text: Any, policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return content-free, bounded compliance evidence for a generated response."""
    raw = "" if response_text is None else str(response_text)
    bounded = _CONTROL.sub("", raw[:MAX_RESPONSE_AUDIT_CHARS]).strip()
    source = policy if isinstance(policy, dict) else {}
    paragraphs = [part for part in re.split(r"\n\s*\n", bounded) if part.strip()]
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", bounded) if part.strip()]
    question_count = bounded.count("?")
    sentence_budget = int(source.get("maximum_expansion_sentences") or 0)
    paragraph_budget = int(source.get("maximum_expansion_paragraphs") or 0)
    follow_up_budget = int(source.get("follow_up_question_budget") or 0)
    silence_expected = source.get("deliberate_silence_preserved") is True
    findings = {
        "contract_version": CONTRACT_VERSION,
        "response_present": bool(bounded),
        "response_truncated_for_audit": len(raw) > MAX_RESPONSE_AUDIT_CHARS,
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
        "question_count": question_count,
        "silence_violation": silence_expected and bool(bounded),
        "follow_up_budget_exceeded": question_count > follow_up_budget,
        "expansion_sentence_budget_exceeded": sentence_budget > 0 and len(sentences) > sentence_budget + 1,
        "expansion_paragraph_budget_exceeded": paragraph_budget > 0 and len(paragraphs) > paragraph_budget + 1,
        "contains_response_content": False,
        "contains_private_chain_of_thought": False,
        "authority": "none",
    }
    findings["compliant"] = not any(findings[key] for key in (
        "silence_violation", "follow_up_budget_exceeded",
        "expansion_sentence_budget_exceeded", "expansion_paragraph_budget_exceeded",
    ))
    findings["audit_digest"] = _digest(findings)
    return findings


def verify_governed_speech_response_audit(audit: dict[str, Any] | None) -> bool:
    if not isinstance(audit, dict):
        return False
    supplied = audit.get("audit_digest")
    payload = dict(audit)
    payload.pop("audit_digest", None)
    return isinstance(supplied, str) and len(supplied) == 64 and _digest(payload) == supplied
