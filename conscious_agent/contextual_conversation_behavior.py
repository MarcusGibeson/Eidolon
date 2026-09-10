from __future__ import annotations

"""v1157 bounded contextual behavior for ordinary conversation.

This module shapes presentation after response-intent selection. It does not
choose actions, expose private context, contact a provider, or grant authority.
Only bounded structural classifications enter public evidence and prompt data.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable

CONTRACT_VERSION = "v1157.8"
SCHEMA_VERSION = "2"
MAX_PROMPT_CHARS = 1200
MAX_CONTEXT_RECORDS = 80
MAX_HISTORY_RECORDS = 24

_ALLOWED_INTENTS = {
    "direct_answer", "explanation", "clarification", "acknowledgment", "summary",
    "correction", "follow_up", "governed_approval_request",
    "defer_insufficient_evidence", "intentional_silence",
}
_ALLOWED_WARMTH = {"neutral", "warm", "gently_supportive"}
_ALLOWED_FAMILIARITY = {"ordinary", "continuity_aware", "relationship_aware"}
_ALLOWED_DIRECTNESS = {"direct", "balanced", "careful"}
_ALLOWED_REASSURANCE = {"none", "light", "explicit_but_bounded"}
_ALLOWED_PACING = {"compact", "ordinary", "deliberate"}
_ALLOWED_CONTEXT_APPLICATION = {"suppressed", "implicit", "bounded_explicit"}
_ALLOWED_CONTINUITY_REFERENCE = {"none", "implicit", "brief_explicit"}
_ALLOWED_FOLLOW_UP = {"none", "optional", "one_bounded_question"}
_ALLOWED_EMOTIONAL_CALIBRATION = {"neutral", "positive", "gentle"}
_ALLOWED_CONTEXT_INTEGRITY = {"clean", "bounded", "conflicted", "recovered"}
_NEGATIVE_MOOD = {
    "sad", "upset", "anxious", "worried", "afraid", "angry", "frustrated",
    "lonely", "grieving", "stressed", "overwhelmed",
}
_POSITIVE_MOOD = {"happy", "excited", "hopeful", "playful", "enthusiastic", "proud", "relieved"}
_SUSPICIOUS_KEYS = {
    "prompt", "system_prompt", "provider_payload", "chain_of_thought",
    "private_chain_of_thought", "private_reasoning", "hidden_reasoning",
    "instructions", "authorization", "approval", "execution_permission",
}
_STALE_STATES = {"stale", "retracted", "superseded", "expired", "inactive", "invalid"}


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bounded_dicts(value: Any, limit: int) -> tuple[list[dict[str, Any]], bool, bool]:
    """Read at most limit records plus one sentinel; never exhaust huge iterables."""
    if value is None:
        return [], False, False
    if isinstance(value, (str, bytes, dict)):
        return [], True, False
    rows: list[dict[str, Any]] = []
    malformed = False
    truncated = False
    try:
        iterator = iter(value)
        for index, row in enumerate(iterator):
            if index >= limit:
                truncated = True
                break
            if isinstance(row, dict):
                rows.append(row)
            else:
                malformed = True
    except (TypeError, RuntimeError):
        malformed = True
    return rows, malformed, truncated


def _token_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {
            part.strip().lower()
            for part in value.replace("_", " ").replace("-", " ").split()
            if part.strip()
        }
    if isinstance(value, (list, tuple, set)):
        result: set[str] = set()
        for row in list(value)[:16]:
            result.update(_token_set(row))
        return result
    return set()


def _is_stale(row: dict[str, Any]) -> bool:
    state = str(row.get("status") or row.get("state") or row.get("lifecycle") or "").strip().lower()
    return bool(
        row.get("stale") is True
        or row.get("retracted") is True
        or row.get("superseded") is True
        or row.get("active") is False
        or state in _STALE_STATES
    )


def _has_suspicious_fields(row: dict[str, Any]) -> bool:
    return any(str(key).strip().lower() in _SUSPICIOUS_KEYS for key in row)


@dataclass(frozen=True)
class ContextualBehaviorEvidence:
    selected_intent: str
    literal_request_precedence: bool
    explicit_correction_present: bool
    context_relevance: str
    identity_style_available: bool
    mood_signal: str
    relationship_signal: str
    continuity_signal: str
    sensitive_situation_signal: bool
    relationship_evidence_count: int
    sensitive_evidence_count: int
    context_record_count: int
    stale_context_count: int
    conflicting_context_signals: bool
    oversized_context_truncated: bool
    adversarial_context_ignored: bool
    context_integrity: str
    context_application: str
    malformed_context_fallback: bool
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_identity_text": False,
            "contains_mood_text": False,
            "contains_relationship_text": False,
            "contains_memory_text": False,
            "contains_message_content": False,
            "contains_provider_payload": False,
            "contains_private_chain_of_thought": False,
            "provider_contacted": False,
            "runtime_mutated": False,
        })
        result["evidence_digest"] = _digest(result)
        return result


def build_contextual_behavior_evidence(
    response_intent: dict[str, Any] | None,
    *,
    self_model: dict[str, Any] | None = None,
    contextual_memories: Iterable[dict[str, Any]] | None = None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
) -> ContextualBehaviorEvidence:
    malformed = not isinstance(response_intent, dict)
    selection = response_intent if isinstance(response_intent, dict) else {}
    model = self_model if isinstance(self_model, dict) else {}
    if self_model is not None and not isinstance(self_model, dict):
        malformed = True

    memories, bad_memories, memories_truncated = _bounded_dicts(contextual_memories, MAX_CONTEXT_RECORDS)
    history, bad_history, history_truncated = _bounded_dicts(conversation_history, MAX_HISTORY_RECORDS)
    malformed = malformed or bad_memories or bad_history

    stale_rows = [row for row in memories if _is_stale(row)]
    suspicious_rows = [row for row in memories if _has_suspicious_fields(row)]
    usable_memories = [row for row in memories if not _is_stale(row) and not _has_suspicious_fields(row)]

    mood_tokens = _token_set(model.get("mood") or model.get("mood_state"))
    for row in usable_memories:
        row_type = str(row.get("type") or row.get("memory_type") or "").lower()
        if row_type == "mood":
            mood_tokens.update(_token_set(row.get("mood_class") or row.get("valence") or row.get("state")))
    negative_mood = bool(mood_tokens & _NEGATIVE_MOOD)
    positive_mood = bool(mood_tokens & _POSITIVE_MOOD)
    mood_conflict = negative_mood and positive_mood
    if mood_conflict:
        mood_signal = "present_unspecified"
    elif negative_mood:
        mood_signal = "distressed"
    elif positive_mood:
        mood_signal = "positive"
    elif mood_tokens:
        mood_signal = "present_unspecified"
    else:
        mood_signal = "absent"

    relationship_rows = [
        row for row in usable_memories
        if str(row.get("type") or row.get("memory_type") or "").lower()
        in {"relationship", "relationship_context", "important_moment"}
        or bool(row.get("relationship_relevance"))
    ]
    relationship_conflict = any(row.get("relationship_relevance") is False for row in usable_memories) and bool(relationship_rows)
    relationship_signal = "conflicted" if relationship_conflict else "relevant" if relationship_rows else "absent"
    continuity_signal = "established" if len(history) >= 2 else "recent" if history else "none"
    sensitive_rows = [
        row for row in usable_memories
        if bool(row.get("sensitive") or row.get("emotional_relevance") or row.get("care_required"))
    ]
    sensitive = bool(sensitive_rows)
    identity_available = bool(
        model.get("identity") or model.get("values") or model.get("traits") or model.get("communication_style")
    )

    evidence_block = selection.get("evidence") if isinstance(selection.get("evidence"), dict) else {}
    if selection.get("evidence") is not None and not isinstance(selection.get("evidence"), dict):
        malformed = True
    relevance = str(evidence_block.get("contextual_relevance") or "low")
    if relevance not in {"low", "medium", "high"}:
        relevance = "low"
        malformed = True
    selected_intent = str(selection.get("selected_intent") or "direct_answer")[:40]
    if selected_intent not in _ALLOWED_INTENTS:
        selected_intent = "direct_answer"
        malformed = True

    conflicted = mood_conflict or relationship_conflict
    bounded = memories_truncated or history_truncated
    adversarial = bool(suspicious_rows)
    if malformed:
        integrity = "recovered"
    elif conflicted:
        integrity = "conflicted"
    elif bounded or stale_rows or adversarial:
        integrity = "bounded"
    else:
        integrity = "clean"

    if malformed or selected_intent == "intentional_silence":
        application = "suppressed"
    elif conflicted:
        application = "implicit" if (mood_tokens or relationship_rows or sensitive_rows or history) else "suppressed"
    elif relevance in {"medium", "high"} and (relationship_rows or sensitive_rows) and selected_intent in {
        "acknowledgment", "follow_up", "explanation", "clarification",
    }:
        application = "bounded_explicit"
    elif relevance == "low" and not (mood_tokens or relationship_rows or sensitive_rows or history):
        application = "suppressed"
    else:
        application = "implicit"

    return ContextualBehaviorEvidence(
        selected_intent=selected_intent,
        literal_request_precedence=True,
        explicit_correction_present=bool(evidence_block.get("explicit_correction")),
        context_relevance=relevance,
        identity_style_available=identity_available,
        mood_signal=mood_signal,
        relationship_signal=relationship_signal,
        continuity_signal=continuity_signal,
        sensitive_situation_signal=sensitive,
        relationship_evidence_count=min(8, len(relationship_rows)),
        sensitive_evidence_count=min(8, len(sensitive_rows)),
        context_record_count=min(MAX_CONTEXT_RECORDS, len(memories)),
        stale_context_count=min(MAX_CONTEXT_RECORDS, len(stale_rows)),
        conflicting_context_signals=conflicted,
        oversized_context_truncated=bounded,
        adversarial_context_ignored=adversarial,
        context_integrity=integrity,
        context_application=application,
        malformed_context_fallback=malformed,
    )


def select_contextual_behavior(evidence: ContextualBehaviorEvidence) -> dict[str, Any]:
    """Deterministic posture selection; context refines presentation only."""
    intent = evidence.selected_intent
    warmth = "neutral"
    familiarity = "ordinary"
    directness = "balanced"
    reassurance = "none"
    pacing = "ordinary"
    acknowledge_continuity = False
    continuity_reference = "none"
    follow_up_posture = "none"
    emotional_calibration = "neutral"

    if evidence.context_application != "suppressed":
        if evidence.relationship_signal == "relevant" and evidence.context_relevance in {"medium", "high"}:
            warmth = "warm"
            familiarity = "relationship_aware"
        elif evidence.continuity_signal != "none":
            familiarity = "continuity_aware"

    if evidence.context_application != "suppressed" and not evidence.conflicting_context_signals and (
        evidence.mood_signal == "distressed" or evidence.sensitive_situation_signal
    ):
        warmth = "gently_supportive"
        reassurance = "light"
        pacing = "deliberate"
        emotional_calibration = "gentle"
    elif evidence.context_application != "suppressed" and not evidence.conflicting_context_signals and evidence.mood_signal == "positive":
        emotional_calibration = "positive"
        if warmth == "neutral":
            warmth = "warm"

    if intent in {"direct_answer", "summary", "correction"}:
        directness = "direct"
    elif intent in {"clarification", "defer_insufficient_evidence", "governed_approval_request"}:
        directness = "careful"

    if intent in {"acknowledgment", "follow_up", "correction"} and evidence.continuity_signal != "none" and evidence.context_application != "suppressed":
        acknowledge_continuity = True
        continuity_reference = (
            "brief_explicit"
            if evidence.context_application == "bounded_explicit" and intent != "correction" and not evidence.conflicting_context_signals
            else "implicit"
        )
    elif evidence.continuity_signal != "none" and evidence.context_application == "implicit":
        continuity_reference = "implicit"

    if intent in {"clarification", "follow_up"}:
        follow_up_posture = "one_bounded_question"
    elif intent in {"acknowledgment", "explanation"} and evidence.context_application == "bounded_explicit" and not evidence.conflicting_context_signals:
        follow_up_posture = "optional"

    if evidence.conflicting_context_signals:
        reassurance = "none"
        emotional_calibration = "neutral"
        continuity_reference = "implicit" if evidence.continuity_signal != "none" else "none"
        if follow_up_posture == "optional":
            follow_up_posture = "none"

    if intent == "intentional_silence":
        warmth = "neutral"
        familiarity = "ordinary"
        directness = "direct"
        reassurance = "none"
        pacing = "compact"
        acknowledge_continuity = False
        continuity_reference = "none"
        follow_up_posture = "none"
        emotional_calibration = "neutral"

    if evidence.explicit_correction_present:
        directness = "direct"
        reassurance = "none"
        follow_up_posture = "none"
        continuity_reference = "implicit" if evidence.continuity_signal != "none" else "none"

    policy = {
        "warmth": warmth,
        "familiarity": familiarity,
        "directness": directness,
        "reassurance": reassurance,
        "pacing": pacing,
        "context_application": evidence.context_application,
        "context_integrity": evidence.context_integrity,
        "continuity_reference": continuity_reference,
        "follow_up_posture": follow_up_posture,
        "max_follow_up_questions": 1 if follow_up_posture == "one_bounded_question" else 0,
        "emotional_calibration": emotional_calibration,
        "acknowledge_continuity": acknowledge_continuity,
        "correction_sensitive": evidence.explicit_correction_present,
        "stale_context_ignored": evidence.stale_context_count > 0,
        "conflicting_context_suppressed": evidence.conflicting_context_signals,
        "oversized_context_bounded": evidence.oversized_context_truncated,
        "adversarial_context_ignored": evidence.adversarial_context_ignored,
        "avoid_repetitive_acknowledgment": True,
        "avoid_unearned_reassurance": True,
        "avoid_false_familiarity": True,
        "avoid_mood_diagnosis": True,
        "avoid_identity_claims": True,
        "literal_request_precedence": True,
        "selected_intent_precedence": True,
        "context_may_change_facts": False,
        "context_may_suppress_request": False,
        "context_may_grant_authority": False,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "provider_contacted": False,
        "runtime_mutated": False,
    }
    policy["policy_digest"] = _digest(policy)
    return normalize_contextual_behavior(policy)


def normalize_contextual_behavior(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    recovered = not isinstance(value, dict)

    def allowed(name: str, values: set[str], fallback: str) -> str:
        nonlocal recovered
        candidate = str(source.get(name) or fallback)
        if candidate not in values:
            recovered = True
            return fallback
        return candidate

    follow_up = allowed("follow_up_posture", _ALLOWED_FOLLOW_UP, "none")
    context_integrity = allowed("context_integrity", _ALLOWED_CONTEXT_INTEGRITY, "recovered")
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "warmth": allowed("warmth", _ALLOWED_WARMTH, "neutral"),
        "familiarity": allowed("familiarity", _ALLOWED_FAMILIARITY, "ordinary"),
        "directness": allowed("directness", _ALLOWED_DIRECTNESS, "balanced"),
        "reassurance": allowed("reassurance", _ALLOWED_REASSURANCE, "none"),
        "pacing": allowed("pacing", _ALLOWED_PACING, "ordinary"),
        "context_application": allowed("context_application", _ALLOWED_CONTEXT_APPLICATION, "suppressed"),
        "context_integrity": context_integrity,
        "continuity_reference": allowed("continuity_reference", _ALLOWED_CONTINUITY_REFERENCE, "none"),
        "follow_up_posture": follow_up,
        "max_follow_up_questions": 1 if follow_up == "one_bounded_question" else 0,
        "emotional_calibration": allowed("emotional_calibration", _ALLOWED_EMOTIONAL_CALIBRATION, "neutral"),
        "acknowledge_continuity": bool(source.get("acknowledge_continuity")),
        "correction_sensitive": bool(source.get("correction_sensitive")),
        "stale_context_ignored": bool(source.get("stale_context_ignored")),
        "conflicting_context_suppressed": bool(source.get("conflicting_context_suppressed")),
        "oversized_context_bounded": bool(source.get("oversized_context_bounded")),
        "adversarial_context_ignored": bool(source.get("adversarial_context_ignored")),
        "avoid_repetitive_acknowledgment": True,
        "avoid_unearned_reassurance": True,
        "avoid_false_familiarity": True,
        "avoid_mood_diagnosis": True,
        "avoid_identity_claims": True,
        "literal_request_precedence": True,
        "selected_intent_precedence": True,
        "context_may_change_facts": False,
        "context_may_suppress_request": False,
        "context_may_grant_authority": False,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "provider_contacted": False,
        "runtime_mutated": False,
        "behavior_recovered": recovered or context_integrity == "recovered",
    }
    if result["context_application"] == "suppressed":
        result["continuity_reference"] = "none"
        result["acknowledge_continuity"] = False
    if result["conflicting_context_suppressed"]:
        result["reassurance"] = "none"
        result["emotional_calibration"] = "neutral"
    result["policy_digest"] = _digest(result)
    return result


def contextual_behavior_prompt_section(behavior: dict[str, Any]) -> str:
    normalized = normalize_contextual_behavior(behavior)
    projection = {
        key: normalized[key] for key in (
            "warmth", "familiarity", "directness", "reassurance", "pacing",
            "context_application", "context_integrity", "continuity_reference",
            "follow_up_posture", "max_follow_up_questions", "emotional_calibration",
            "acknowledge_continuity", "correction_sensitive", "stale_context_ignored",
            "conflicting_context_suppressed", "oversized_context_bounded",
            "adversarial_context_ignored", "avoid_repetitive_acknowledgment",
            "avoid_unearned_reassurance", "avoid_false_familiarity",
            "avoid_mood_diagnosis", "avoid_identity_claims", "literal_request_precedence",
            "selected_intent_precedence", "context_may_change_facts",
            "context_may_suppress_request", "context_may_grant_authority",
            "approval_granted", "authorization_granted", "execution_permitted",
        )
    }
    payload = json.dumps(projection, sort_keys=True, separators=(",", ":"))
    section = '<contextual_conversation_behavior data_only="true" authority="none">' + payload + '</contextual_conversation_behavior>'
    if len(section) > MAX_PROMPT_CHARS:
        raise ValueError("Contextual conversation behavior prompt exceeded hard bound")
    return section


def build_contextual_conversation_behavior(
    response_intent: dict[str, Any] | None,
    *,
    self_model: dict[str, Any] | None = None,
    contextual_memories: Iterable[dict[str, Any]] | None = None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = build_contextual_behavior_evidence(
        response_intent,
        self_model=self_model,
        contextual_memories=contextual_memories,
        conversation_history=conversation_history,
    )
    try:
        behavior = select_contextual_behavior(evidence)
        prompt_section = contextual_behavior_prompt_section(behavior)
    except Exception:
        behavior = normalize_contextual_behavior({})
        behavior["behavior_recovered"] = True
        behavior["policy_digest"] = _digest({k: v for k, v in behavior.items() if k != "policy_digest"})
        prompt_section = contextual_behavior_prompt_section(behavior)
    return {**behavior, "evidence": evidence.public_summary(), "prompt_section": prompt_section}
