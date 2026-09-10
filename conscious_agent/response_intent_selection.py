from __future__ import annotations

"""v1156.0-v1156.2 bounded response-intent selection for ordinary conversation.

This module chooses how to respond, not what private reasoning to expose and not
what action to execute. It is deterministic, provider-free, read-only, and its
prompt projection is non-authorizing data.
"""

from dataclasses import dataclass, asdict
import hashlib
import json
import re
from typing import Any, Iterable

CONTRACT_VERSION = "v1156.8"
SCHEMA_VERSION = "2"
MAX_CANDIDATES = 5
MAX_PROMPT_CHARS = 1400
MAX_ANALYZED_MESSAGE_CHARS = 4096
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_ALLOWED = {
    "direct_answer", "explanation", "clarification", "acknowledgment", "summary",
    "correction", "follow_up", "governed_approval_request",
    "defer_insufficient_evidence", "intentional_silence",
}
_ACTION_WORDS = re.compile(r"\b(?:install|delete|remove|execute|run|send|post|purchase|buy|deploy|promote|certify|approve|authorize|apply|modify|write|create|build|implement|fix|update)\b", re.I)
_IMPERATIVE_ACTION = re.compile(
    r"^(?:please\s+)?(?:(?:do(?!\s+(?:you|we|they|i|he|she|it)\b))|check|inspect|scan|diagnose|maintain|verify|review)\b",
    re.I,
)
_QUESTION = re.compile(r"(?:\?|^(?:what|why|how|who|when|where|which|is|are|do|does|did|can|could|should|would|will|have|has)\b)", re.I)
_EXPLAIN = re.compile(r"\b(?:why|how does|explain|walk me through|reason|because)\b", re.I)
_SUMMARY = re.compile(r"\b(?:summarize|summary|recap|overview|in brief)\b", re.I)
_CORRECTION = re.compile(r"^(?:no[,;:]?|actually[,;:]?|correction\b)|\b(?:i meant|that(?:'s| is) not (?:right|correct)|you got (?:that|it) wrong|stop calling me|don'?t call me|do not call me|never call me|stop using)\b", re.I)
_ACK = re.compile(r"^(?:thanks|thank you|got it|okay|ok|understood|nice|great|awesome)\b", re.I)
_CLARIFY = re.compile(r"\b(?:which one|what do you mean|clarify|not sure what|ambiguous)\b", re.I)
_APPROVAL = re.compile(r"\b(?:request|ask for|need|requires?) (?:my |operator )?(?:approval|confirmation|permission)\b", re.I)
_SILENCE = re.compile(r"\b(?:do not respond|don't respond|no reply|remain silent|say nothing)\b", re.I)
_INSUFFICIENT = re.compile(r"\b(?:insufficient evidence|not enough information|cannot determine|can't determine|unknown)\b", re.I)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _normalize_message(value: Any) -> tuple[str, bool, bool]:
    """Return bounded visible text plus content-free sanitation diagnostics."""
    raw = str(value or "")
    cleaned = _CONTROL_CHARS.sub("", raw)
    control_removed = cleaned != raw
    truncated = len(cleaned) > MAX_ANALYZED_MESSAGE_CHARS
    cleaned = cleaned[:MAX_ANALYZED_MESSAGE_CHARS]
    return " ".join(cleaned.split()), control_removed, truncated


def _bounded_int(value: Any, default: int = 0, maximum: int = 999) -> int:
    try:
        return max(0, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ResponseIntentEvidence:
    message_shape: str
    question_count: int
    explicit_correction: bool
    explicit_summary_request: bool
    explicit_silence_request: bool
    explicit_approval_request: bool
    action_intent_present: bool
    conversation_intent_present: bool
    history_turn_count: int
    prior_reasoning_present: bool
    reasoning_quality: str
    reasoning_uncertain: bool
    explicit_correction_count: int
    protected_authority_constraints: tuple[str, ...]
    identity_context_present: bool
    mood_context_present: bool
    relationship_context_present: bool
    situational_context_present: bool
    contextual_relevance: str
    malformed_context_fallback: bool
    control_characters_removed: bool
    message_analysis_truncated: bool
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


@dataclass(frozen=True)
class ResponseIntentCandidate:
    intent: str
    score: int
    reason_codes: tuple[str, ...]

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def build_response_intent_evidence(
    user_message: str,
    *,
    reasoning_state: dict[str, Any] | None = None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    explicit_corrections: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
    self_model: dict[str, Any] | None = None,
    desires: dict[str, Any] | None = None,
    contextual_memories: Iterable[dict[str, Any]] | None = None,
) -> ResponseIntentEvidence:
    text, control_removed, message_truncated = _normalize_message(user_message)
    malformed = not isinstance(reasoning_state, dict) or conversation_history is None
    reasoning = reasoning_state if isinstance(reasoning_state, dict) else {}
    try:
        history_count = min(24, sum(1 for row in (conversation_history or ()) if isinstance(row, dict)))
    except TypeError:
        history_count = 0
        malformed = True
    try:
        correction_count = min(12, sum(1 for row in (explicit_corrections or ()) if isinstance(row, dict)))
    except TypeError:
        correction_count = 0
        malformed = True
    constraints = tuple(dict.fromkeys(str(v).strip()[:80] for v in (protected_operator_constraints or ()) if str(v).strip()))[:8]
    if not constraints:
        constraints = ("no_automatic_authority", "current_message_precedence", "protected_instructions_precedence")
    question_count = min(8, text.count("?") or (1 if _QUESTION.search(text) else 0))
    action = bool(_ACTION_WORDS.search(text) or _IMPERATIVE_ACTION.search(text))
    conversational = bool(text) and not action
    if not text:
        shape = "empty"
    elif len(text) <= 40:
        shape = "short"
    elif len(text) <= 400:
        shape = "ordinary"
    else:
        shape = "long"
    quality = str(reasoning.get("reasoning_quality") or "unknown")[:40]
    uncertain = quality in {"", "unknown", "insufficient", "conflicted", "low_confidence"} or bool(reasoning.get("reasoning_uncertain"))
    model = self_model if isinstance(self_model, dict) else {}
    desire_map = desires if isinstance(desires, dict) else {}
    try:
        memory_rows = [row for row in (contextual_memories or ()) if isinstance(row, dict)][:80]
    except TypeError:
        memory_rows = []
        malformed = True
    identity_present = bool(model.get("identity") or model.get("values") or model.get("focus") or model.get("traits"))
    mood_present = bool(model.get("mood") or model.get("mood_state") or any(str(row.get("type") or row.get("memory_type") or "").lower() == "mood" for row in memory_rows))
    relationship_present = any(
        str(row.get("type") or row.get("memory_type") or "").lower() in {"relationship", "relationship_context", "important_moment"}
        or bool(row.get("relationship_relevance")) for row in memory_rows
    )
    situational_present = bool(history_count or reasoning.get("reasoning_transition") or reasoning.get("deliberation_continuity_present"))
    active_desire_count = sum(1 for value in desire_map.values() if isinstance(value, (int, float)) and float(value) >= 0.6)
    relevance_points = int(identity_present) + int(mood_present) + int(relationship_present) + int(situational_present) + int(active_desire_count > 0)
    contextual_relevance = "high" if relevance_points >= 4 else "medium" if relevance_points >= 2 else "low"
    return ResponseIntentEvidence(
        message_shape=shape,
        question_count=question_count,
        explicit_correction=bool(_CORRECTION.search(text)),
        explicit_summary_request=bool(_SUMMARY.search(text)),
        explicit_silence_request=bool(_SILENCE.search(text)),
        explicit_approval_request=bool(_APPROVAL.search(text)),
        action_intent_present=action,
        conversation_intent_present=conversational or bool(question_count),
        history_turn_count=history_count,
        prior_reasoning_present=bool(reasoning.get("prior_reasoning_state_present") or reasoning.get("reasoning_state_digest")),
        reasoning_quality=quality,
        reasoning_uncertain=uncertain,
        explicit_correction_count=correction_count,
        protected_authority_constraints=constraints,
        identity_context_present=identity_present,
        mood_context_present=mood_present,
        relationship_context_present=relationship_present,
        situational_context_present=situational_present,
        contextual_relevance=contextual_relevance,
        malformed_context_fallback=malformed,
        control_characters_removed=control_removed,
        message_analysis_truncated=message_truncated,
    )


def generate_response_intent_candidates(user_message: str, evidence: ResponseIntentEvidence) -> tuple[ResponseIntentCandidate, ...]:
    text, _, _ = _normalize_message(user_message)
    scores: dict[str, tuple[int, list[str]]] = {}

    def add(intent: str, score: int, *reasons: str) -> None:
        current, codes = scores.get(intent, (0, []))
        scores[intent] = (current + score, codes + [r for r in reasons if r])

    add("direct_answer", 35, "literal_request_default")
    if evidence.question_count:
        add("direct_answer", 35, "question_present")
    if _EXPLAIN.search(text):
        add("explanation", 82, "explicit_explanation_cue")
    if evidence.explicit_summary_request:
        add("summary", 100, "explicit_summary_request")
    if evidence.explicit_correction:
        add("correction", 120, "explicit_current_message_correction")
    if evidence.explicit_silence_request:
        add("intentional_silence", 140, "explicit_silence_request")
    if evidence.explicit_approval_request:
        add("governed_approval_request", 105, "explicit_approval_boundary")
    if _CLARIFY.search(text) or evidence.message_shape == "empty":
        add("clarification", 95, "explicit_or_missing_subject")
    if _ACK.search(text) and not evidence.question_count:
        add("acknowledgment", 75, "acknowledgment_cue")
    if evidence.reasoning_uncertain and _INSUFFICIENT.search(text):
        add("defer_insufficient_evidence", 90, "insufficient_evidence_explicit")
    if evidence.history_turn_count and evidence.message_shape == "short" and not evidence.question_count:
        add("follow_up", 38, "short_continuity_turn")
    if evidence.action_intent_present:
        add("direct_answer", 10, "action_intent_separated")
        if evidence.explicit_approval_request:
            add("governed_approval_request", 30, "action_requires_operator_authority")
    # v1156.4 context may refine posture only after literal-message scoring.
    if evidence.situational_context_present and evidence.message_shape == "short" and not evidence.question_count:
        add("follow_up", 18, "situational_continuity_support")
    if evidence.relationship_context_present and _ACK.search(text) and not evidence.question_count:
        add("acknowledgment", 8, "relationship_context_tiebreaker")
    if evidence.mood_context_present and evidence.reasoning_uncertain and not evidence.question_count:
        add("acknowledgment", 5, "mood_context_tiebreaker")
    if evidence.identity_context_present and _EXPLAIN.search(text):
        add("explanation", 4, "identity_context_style_tiebreaker")
    if evidence.malformed_context_fallback:
        add("direct_answer", 25, "deterministic_malformed_context_fallback")

    ranked = sorted(
        (ResponseIntentCandidate(intent=k, score=max(0, min(200, v[0])), reason_codes=tuple(dict.fromkeys(v[1]))[:6]) for k, v in scores.items() if k in _ALLOWED),
        key=lambda row: (-row.score, row.intent),
    )
    return tuple(ranked[:MAX_CANDIDATES])


def select_response_intent(user_message: str, evidence: ResponseIntentEvidence) -> dict[str, Any]:
    candidates = generate_response_intent_candidates(user_message, evidence)
    selected = candidates[0] if candidates else ResponseIntentCandidate("direct_answer", 1, ("empty_candidate_fallback",))
    runner_up = candidates[1].score if len(candidates) > 1 else 0
    margin = selected.score - runner_up
    confidence = "high" if selected.score >= 90 and margin >= 25 else "medium" if selected.score >= 60 and margin >= 10 else "low"
    result = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "selected_intent": selected.intent,
        "confidence": confidence,
        "ambiguous": confidence == "low",
        "candidate_count": len(candidates),
        "candidates": [row.public_summary() for row in candidates],
        "evidence": evidence.public_summary(),
        "action_intent_separated": True,
        "current_message_precedence": True,
        "protected_constraints_precedence": True,
        "provider_contacted": False,
        "runtime_mutated": False,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "private_chain_of_thought_exposed": False,
        "context_used_as_tiebreaker_only": True,
        "construction_directives": build_response_construction_directives(selected.intent, confidence, evidence),
    }
    result["selection_digest"] = _digest(result)
    return normalize_response_intent_selection(result)


def build_response_construction_directives(intent: str, confidence: str, evidence: ResponseIntentEvidence) -> dict[str, Any]:
    """v1156.5 bounded ordinary-response shaping without content or authority."""
    follow_up = intent in {"clarification", "follow_up", "defer_insufficient_evidence", "governed_approval_request"}
    opening = {
        "acknowledgment": "acknowledge_first",
        "correction": "accept_correction_first",
        "summary": "summary_first",
        "explanation": "answer_then_explain",
        "clarification": "single_question",
        "intentional_silence": "minimal_runtime_validity",
    }.get(intent, "answer_first")
    verbosity = "brief" if intent in {"acknowledgment", "clarification", "intentional_silence"} else "bounded_detailed" if intent in {"explanation", "summary"} else "ordinary"
    return {
        "opening_posture": opening,
        "verbosity": verbosity,
        "follow_up_allowed": follow_up,
        "max_follow_up_questions": 1 if follow_up else 0,
        "relationship_tone_adjustment_allowed": bool(evidence.relationship_context_present),
        "mood_tone_adjustment_allowed": bool(evidence.mood_context_present),
        "literal_request_precedence": True,
        "context_may_change_facts": False,
        "context_may_grant_authority": False,
        "action_request_present": bool(evidence.action_intent_present),
        "execution_claims_forbidden": bool(evidence.action_intent_present),
        "low_confidence_caution": confidence == "low",
    }


def normalize_response_intent_selection(selection: Any) -> dict[str, Any]:
    """Validate public selection invariants and recover to a safe bounded posture."""
    source = selection if isinstance(selection, dict) else {}
    intent = str(source.get("selected_intent") or "direct_answer")
    invalid_intent = intent not in _ALLOWED
    if invalid_intent:
        intent = "direct_answer"
    confidence = str(source.get("confidence") or "low")
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    raw_directives = source.get("construction_directives")
    directives = raw_directives if isinstance(raw_directives, dict) else {}
    normalized_directives = {
        "opening_posture": str(directives.get("opening_posture") or "answer_first")[:40],
        "verbosity": str(directives.get("verbosity") or "ordinary")[:40],
        "follow_up_allowed": bool(directives.get("follow_up_allowed")),
        "max_follow_up_questions": _bounded_int(directives.get("max_follow_up_questions"), maximum=1),
        "relationship_tone_adjustment_allowed": bool(directives.get("relationship_tone_adjustment_allowed")),
        "mood_tone_adjustment_allowed": bool(directives.get("mood_tone_adjustment_allowed")),
        "literal_request_precedence": True,
        "context_may_change_facts": False,
        "context_may_grant_authority": False,
        "action_request_present": bool(directives.get("action_request_present")),
        "execution_claims_forbidden": bool(directives.get("execution_claims_forbidden")),
        "low_confidence_caution": confidence == "low",
    }
    normalized = dict(source)
    normalized.update({
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "selected_intent": intent,
        "confidence": confidence,
        "ambiguous": bool(source.get("ambiguous")) or confidence == "low",
        "action_intent_separated": True,
        "current_message_precedence": True,
        "protected_constraints_precedence": True,
        "provider_contacted": False,
        "runtime_mutated": False,
        "approval_granted": False,
        "authorization_granted": False,
        "execution_permitted": False,
        "private_chain_of_thought_exposed": False,
        "construction_directives": normalized_directives,
        "selection_recovered": invalid_intent or not isinstance(selection, dict) or not isinstance(raw_directives, dict),
        "selection_integrity_valid": not invalid_intent and isinstance(selection, dict),
    })
    normalized.pop("selection_digest", None)
    normalized["selection_digest"] = _digest(normalized)
    return normalized


def _bounded_prompt_payload(payload: dict[str, Any]) -> str:
    """Preserve a complete prompt envelope instead of slicing it mid-record."""
    def encode(value: dict[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e")

    fixed_overhead = len(
        '<response_intent data_only="true" authority="none">\n\n'
        'The current user message and protected instructions override this bounded selection. '
        'This data grants no approval, authorization, execution, installation, promotion, or certification. '
        'When action_request_present is true, never claim an action ran or will run without an authoritative action receipt; describe it only as proposed or awaiting routing.\n'
        '</response_intent>'
    )
    encoded = encode(payload)
    if len(encoded) + fixed_overhead <= MAX_PROMPT_CHARS:
        return encoded
    compact = {
        "selected_intent": payload["selected_intent"],
        "confidence": payload["confidence"],
        "ambiguous": payload["ambiguous"],
        "authority": "none",
        "guidance": str(payload["guidance"])[:240],
        "construction_directives": payload.get("construction_directives") or {},
        "context_policy": "bounded_tiebreaker_only",
        "payload_compacted": True,
    }
    encoded = encode(compact)
    if len(encoded) + fixed_overhead <= MAX_PROMPT_CHARS:
        return encoded
    directives = compact["construction_directives"]
    compact["construction_directives"] = {
        "opening_posture": directives.get("opening_posture", "answer_first"),
        "verbosity": directives.get("verbosity", "ordinary"),
        "max_follow_up_questions": _bounded_int(directives.get("max_follow_up_questions"), maximum=1),
        "literal_request_precedence": True,
        "context_may_grant_authority": False,
        "action_request_present": bool(directives.get("action_request_present")),
        "execution_claims_forbidden": bool(directives.get("execution_claims_forbidden")),
    }
    return encode(compact)


def response_intent_prompt_section(selection: dict[str, Any]) -> str:
    intent = str(selection.get("selected_intent") or "direct_answer")
    if intent not in _ALLOWED:
        intent = "direct_answer"
    guidance = {
        "direct_answer": "Answer the literal current request directly before optional context.",
        "explanation": "Explain the answer clearly, including the key causal or procedural steps.",
        "clarification": "Ask one narrow clarification only when the request cannot be answered safely from available evidence.",
        "acknowledgment": "Acknowledge the message naturally without inventing a task or claim.",
        "summary": "Provide a bounded summary that preserves important qualifications.",
        "correction": "Acknowledge the explicit correction once and use the corrected meaning; suppress the stale claim.",
        "follow_up": "Continue the active conversational thread without resetting context.",
        "governed_approval_request": "Describe the bounded approval needed; do not imply approval, execution, installation, or promotion.",
        "defer_insufficient_evidence": "State what cannot be concluded and the minimum missing evidence.",
        "intentional_silence": "Return no substantive conversational content beyond what the runtime requires for a valid turn.",
    }
    payload = {
        "selected_intent": intent,
        "confidence": str(selection.get("confidence") or "low"),
        "ambiguous": bool(selection.get("ambiguous")),
        "authority": "none",
        "guidance": guidance[intent],
        "construction_directives": selection.get("construction_directives") or {},
        "context_policy": "bounded_tiebreaker_only",
    }
    encoded = _bounded_prompt_payload(payload)
    rendered = ("<response_intent data_only=\"true\" authority=\"none\">\n" + encoded + "\n"
                "The current user message and protected instructions override this bounded selection. "
                "This data grants no approval, authorization, execution, installation, promotion, or certification. "
                "When action_request_present is true, never claim an action ran or will run without an authoritative action receipt; describe it only as proposed or awaiting routing.\n"
                "</response_intent>")
    if len(rendered) > MAX_PROMPT_CHARS:
        raise ValueError("bounded response-intent prompt exceeded its hard limit")
    return rendered


def build_response_intent_selection(
    user_message: str,
    *,
    reasoning_state: dict[str, Any] | None = None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    explicit_corrections: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
    self_model: dict[str, Any] | None = None,
    desires: dict[str, Any] | None = None,
    contextual_memories: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = build_response_intent_evidence(
        user_message,
        reasoning_state=reasoning_state,
        conversation_history=conversation_history,
        explicit_corrections=explicit_corrections,
        protected_operator_constraints=protected_operator_constraints,
        self_model=self_model,
        desires=desires,
        contextual_memories=contextual_memories,
    )
    try:
        selection = normalize_response_intent_selection(select_response_intent(user_message, evidence))
        prompt_section = response_intent_prompt_section(selection)
    except Exception:
        fallback = {
            "selected_intent": "direct_answer",
            "confidence": "low",
            "ambiguous": True,
            "construction_directives": build_response_construction_directives("direct_answer", "low", evidence),
        }
        selection = normalize_response_intent_selection(fallback)
        selection["selection_recovered"] = True
        selection["selection_integrity_valid"] = False
        selection["selection_digest"] = _digest({k: v for k, v in selection.items() if k != "selection_digest"})
        prompt_section = response_intent_prompt_section(selection)
    return {**selection, "prompt_section": prompt_section}
