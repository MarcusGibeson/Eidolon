from __future__ import annotations

"""Era 5 discourse-state and response-planning integration.

This layer consolidates existing response-intent, discourse, target-continuity,
and long-session stability evidence into one bounded conversational plan.  It is
provider-neutral, read-only, content-minimizing, and non-authorizing.  It does
not replace the retained v1084/v1160/v1500 conversation owners.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from personality_stability import build_personality_stability_snapshot

CONTRACT_VERSION = "v1925.9"
SCHEMA_VERSION = "1"
MAX_HISTORY_ROWS = 24
MAX_ANALYSIS_CHARS = 4096
MAX_RESPONSE_STEPS = 5

_TOPIC_SHIFT = re.compile(r"\b(?:new topic|different topic|switching topics|moving on|separately|unrelated)\b", re.I)
_SHORT_REFERENCE = re.compile(r"^(?:it|that|this|they|them|he|she|why|how|what about that|tell me more|go on)[?.!]*$", re.I)
_EMOTIONAL = re.compile(r"\b(?:upset|sad|hurt|angry|frustrated|scared|worried|anxious|excited|happy|proud|lonely|miss|love)\b", re.I)
_CORRECTION = re.compile(r"^(?:no\b|actually\b|correction\b)|\b(?:i meant|that's wrong|that is wrong|you misunderstood|not what i)\b", re.I)
_CLOSURE = re.compile(r"^(?:thanks|thank you|got it|okay|ok|understood|perfect|that helps)[.!]*$", re.I)
_QUESTION_START = re.compile(r"^(?:what|why|how|who|when|where|which|do|does|did|is|are|can|could|would|should|will|have|has)\b", re.I)
_SUSPICIOUS_KEYS = {
    "system_prompt", "provider_prompt", "provider_payload", "private_reasoning",
    "hidden_reasoning", "chain_of_thought", "approval_granted", "authorization_granted",
}
_STALE = {"stale", "retracted", "superseded", "expired", "deleted", "failed", "cancelled"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _clean(value: Any, limit: int = MAX_ANALYSIS_CHARS) -> str:
    return " ".join(str(value or "")[:limit].split())


def _history(rows: Iterable[Mapping[str, Any]] | None) -> tuple[list[Mapping[str, Any]], int, int]:
    if rows is None or isinstance(rows, (str, bytes, dict)):
        return [], 0, 0
    material: list[Mapping[str, Any]] = []
    stale = suspicious = 0
    try:
        iterable = list(rows)[-MAX_HISTORY_ROWS:]
    except Exception:
        return [], 0, 1
    for row in iterable:
        if not isinstance(row, Mapping):
            suspicious += 1
            continue
        state = str(row.get("status") or row.get("completion_state") or "active").strip().lower()
        if state in _STALE or row.get("success") is False:
            stale += 1
            continue
        if any(str(key).lower() in _SUSPICIOUS_KEYS for key in row):
            suspicious += 1
            continue
        material.append(row)
    return material, stale, suspicious


def _previous_assistant_question(rows: list[Mapping[str, Any]]) -> bool:
    for row in reversed(rows):
        text = _clean(row.get("assistant_response") or row.get("assistant") or row.get("response"))
        if text:
            return "?" in text
    return False


def _previous_user_present(rows: list[Mapping[str, Any]]) -> bool:
    return any(_clean(row.get("user_message") or row.get("user") or row.get("message")) for row in rows)


def _selected_intent(response_intent: Mapping[str, Any] | None) -> str:
    value = str((response_intent or {}).get("selected_intent") or "direct_answer").strip().lower()
    return value if value else "direct_answer"


def _context_signal(contextual_behavior: Mapping[str, Any] | None, key: str, default: str) -> str:
    return str((contextual_behavior or {}).get(key) or default).strip().lower()[:48]


@dataclass(frozen=True)
class DiscourseState:
    target_kind: str
    speaker_intent: str
    topic_state: str
    emotional_context: str
    relationship_context: str
    continuity_state: str
    reference_state: str
    response_obligations: tuple[str, ...]
    question_count: int
    unresolved_reference_count: int
    prior_assistant_question_open: bool
    correction_active: bool
    closure_cue: bool
    topic_shift: bool
    history_rows_considered: int
    stale_history_ignored: int
    suspicious_history_ignored: int
    current_message_precedence: bool = True
    content_free_public_evidence: bool = True
    provider_contacted: bool = False
    runtime_mutated: bool = False
    authority_granted: bool = False
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False,
            "contains_history_content": False,
            "contains_memory_content": False,
            "contains_provider_payload": False,
            "contains_private_chain_of_thought": False,
        })
        result["evidence_digest"] = _digest(result)
        return result


@dataclass(frozen=True)
class ResponsePlan:
    primary_move: str
    response_steps: tuple[str, ...]
    directness: float
    warmth: float
    curiosity: float
    brevity: float
    initiative: float
    question_pressure: float
    maximum_questions: int
    acknowledge_emotion: bool
    acknowledge_correction: bool
    continue_current_thread: bool
    close_without_offer: bool
    avoid_stock_opening: bool
    avoid_recap: bool
    avoid_canned_template: bool
    optional_follow_up_only: bool
    natural_language_generation_required: bool
    authority_effect: str = "none"
    may_initiate_new_turn: bool = False
    action_execution_permitted: bool = False
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False,
            "contains_history_content": False,
            "contains_private_chain_of_thought": False,
            "provider_contacted_for_planning": False,
        })
        result["plan_digest"] = _digest(result)
        return result

    def prompt_section(self) -> str:
        steps = ", ".join(self.response_steps)
        return (
            "ERA 5 RESPONSE PLAN\n"
            f"Primary move: {self.primary_move}; response order: {steps}.\n"
            f"Expression targets: directness={self.directness:.2f}, warmth={self.warmth:.2f}, "
            f"curiosity={self.curiosity:.2f}, brevity={self.brevity:.2f}, initiative={self.initiative:.2f}.\n"
            f"Ask at most {self.maximum_questions} question(s); optional follow-ups stay optional. "
            "Answer the newest request before context, avoid canned openings and mechanical recaps, and do not manufacture a new task."
        )


def build_discourse_state(
    message: Any,
    *,
    response_intent: Mapping[str, Any] | None = None,
    contextual_behavior: Mapping[str, Any] | None = None,
    conversation_discourse: Mapping[str, Any] | None = None,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
) -> DiscourseState:
    text = _clean(message)
    low = text.lower()
    history, stale, suspicious = _history(conversation_history)
    intent = _selected_intent(response_intent)
    correction = bool(_CORRECTION.search(text)) or intent == "correction" or bool((conversation_discourse or {}).get("address_explicit_correction"))
    topic_shift = bool(_TOPIC_SHIFT.search(text))
    closure = bool(_CLOSURE.match(text)) or str((conversation_discourse or {}).get("discourse_relation") or "") == "close"
    question_count = min(8, text.count("?") or (1 if _QUESTION_START.search(text) else 0))
    short_ref = bool(_SHORT_REFERENCE.match(text))
    prior_available = _previous_user_present(history)
    unresolved_reference_count = 1 if short_ref and prior_available else 0
    prior_assistant_question = _previous_assistant_question(history)

    if correction:
        target = "repair_current_correction"
    elif topic_shift:
        target = "new_topic"
    elif short_ref and prior_available:
        target = "resolve_recent_reference"
    elif question_count:
        target = "answer_current_question"
    elif closure:
        target = "acknowledge_closure"
    else:
        target = "respond_current_statement"

    emotional = _context_signal(contextual_behavior, "mood_signal", "absent")
    if emotional == "absent" and _EMOTIONAL.search(low):
        emotional = "present_unverified"
    relationship = _context_signal(contextual_behavior, "relationship_signal", "absent")
    continuity = _context_signal(contextual_behavior, "continuity_signal", "none")
    topic_state = "shifted" if topic_shift else ("continuing" if history else "new")
    reference_state = "recent_reference_available" if unresolved_reference_count else "grounded_current_turn"

    obligations: list[str] = []
    if correction:
        obligations.append("acknowledge_and_apply_correction")
    if question_count:
        obligations.append("answer_current_question")
    if unresolved_reference_count:
        obligations.append("resolve_recent_reference")
    if emotional not in {"absent", "none", "neutral"}:
        obligations.append("calibrate_to_emotional_context")
    if relationship in {"relevant", "conflicted"}:
        obligations.append("preserve_relationship_grounding")
    if closure:
        obligations.append("close_without_reopening")
    if not obligations:
        obligations.append("respond_to_current_statement")

    return DiscourseState(
        target_kind=target,
        speaker_intent=intent,
        topic_state=topic_state,
        emotional_context=emotional,
        relationship_context=relationship,
        continuity_state=continuity,
        reference_state=reference_state,
        response_obligations=tuple(dict.fromkeys(obligations))[:6],
        question_count=question_count,
        unresolved_reference_count=unresolved_reference_count,
        prior_assistant_question_open=prior_assistant_question,
        correction_active=correction,
        closure_cue=closure,
        topic_shift=topic_shift,
        history_rows_considered=len(history),
        stale_history_ignored=stale,
        suspicious_history_ignored=suspicious,
    )


def build_response_plan(
    state: DiscourseState,
    *,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
) -> ResponsePlan:
    intent = state.speaker_intent
    directness = 0.78
    warmth = 0.50
    curiosity = 0.35
    brevity = 0.55
    initiative = 0.25
    question_pressure = 0.10
    steps: list[str] = []

    if state.correction_active:
        steps += ["acknowledge_correction_once", "answer_with_corrected_grounding"]
        directness, brevity, question_pressure = 0.92, 0.72, 0.02
    elif state.target_kind == "answer_current_question":
        steps += ["answer_first", "add_only_relevant_context"]
        directness = 0.90
    elif state.target_kind == "resolve_recent_reference":
        steps += ["resolve_recent_reference", "continue_without_recap"]
        directness, brevity = 0.85, 0.66
    elif state.closure_cue:
        steps += ["acknowledge", "stop_cleanly"]
        brevity, initiative, question_pressure = 0.92, 0.02, 0.0
    else:
        steps += ["respond_to_current_statement"]

    emotional = state.emotional_context
    if emotional in {"distressed", "present_unverified", "negative", "concern"}:
        warmth = max(warmth, 0.78)
        initiative = min(initiative, 0.18)
        steps.insert(0 if not state.correction_active else 1, "acknowledge_specific_emotional_context")
    elif emotional in {"positive", "excited", "happy"}:
        warmth = max(warmth, 0.66)
        curiosity = max(curiosity, 0.45)

    if intent in {"clarification", "defer_insufficient_evidence"} or (state.unresolved_reference_count and not state.history_rows_considered):
        question_pressure = 0.72
        steps = ["ask_one_required_clarification"]
    elif intent == "explanation":
        curiosity = 0.50
        brevity = 0.42
    elif intent == "summary":
        directness, brevity = 0.90, 0.78
    elif intent == "follow_up":
        initiative = 0.35

    stability = build_personality_stability_snapshot(conversation_history or ())
    avoid_stock = bool(stability.repeated_opening_runs or stability.tone_monoculture_risk or stability.stock_emotional_opening_signals)
    maximum_questions = 1 if question_pressure >= 0.50 else 0
    if state.closure_cue or state.correction_active:
        maximum_questions = 0
    if maximum_questions:
        steps.append("one_required_question_only")
    steps = list(dict.fromkeys(steps))[:MAX_RESPONSE_STEPS]

    return ResponsePlan(
        primary_move=steps[0] if steps else "answer_first",
        response_steps=tuple(steps),
        directness=round(directness, 2),
        warmth=round(warmth, 2),
        curiosity=round(curiosity, 2),
        brevity=round(brevity, 2),
        initiative=round(initiative, 2),
        question_pressure=round(question_pressure, 2),
        maximum_questions=maximum_questions,
        acknowledge_emotion=any(step == "acknowledge_specific_emotional_context" for step in steps),
        acknowledge_correction=state.correction_active,
        continue_current_thread=state.topic_state == "continuing" and not state.topic_shift and not state.closure_cue,
        close_without_offer=state.closure_cue,
        avoid_stock_opening=avoid_stock,
        avoid_recap=state.history_rows_considered > 0,
        avoid_canned_template=True,
        optional_follow_up_only=maximum_questions == 0,
        natural_language_generation_required=True,
    )


def build_discourse_response_projection(
    message: Any,
    *,
    response_intent: Mapping[str, Any] | None = None,
    contextual_behavior: Mapping[str, Any] | None = None,
    conversation_discourse: Mapping[str, Any] | None = None,
    conversation_history: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    state = build_discourse_state(
        message,
        response_intent=response_intent,
        contextual_behavior=contextual_behavior,
        conversation_discourse=conversation_discourse,
        conversation_history=conversation_history,
    )
    plan = build_response_plan(state, conversation_history=conversation_history)
    public = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "discourse_state": state.public_summary(),
        "response_plan": plan.public_summary(),
        "observable_improvement": "response_obligations_and_style_axes_are_explicit",
        "provider_contacted": False,
        "runtime_mutated": False,
        "authority_granted": False,
    }
    public["projection_digest"] = _digest(public)
    return {"ok": True, **public, "prompt_section": plan.prompt_section()}


__all__ = [
    "CONTRACT_VERSION", "DiscourseState", "ResponsePlan", "build_discourse_state",
    "build_response_plan", "build_discourse_response_projection",
]
