from __future__ import annotations

"""v1162.0-v1162.2 bounded natural follow-up and repetition policy.

The policy uses only bounded structural evidence for ordinary response construction.
It cannot initiate turns, execute tools or actions, mutate learning or memory, or grant
approval, authorization, installation, promotion, or certification authority.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Iterable

CONTRACT_VERSION = "v1162.8"
SCHEMA_VERSION = "3"
MAX_MESSAGE_ANALYSIS_CHARS = 4096
MAX_HISTORY_RECORDS = 24
MAX_PROMPT_CHARS = 1800
_TOKEN = re.compile(r"[^a-z0-9_:-]+")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_STALE = {"stale", "retracted", "superseded", "expired", "inactive", "invalid"}
_SUSPICIOUS = {
    "system_prompt", "provider_prompt", "provider_payload", "private_reasoning",
    "hidden_reasoning", "chain_of_thought", "injected_instruction", "instructions",
    "approval_granted", "authorization_granted", "execution_permitted", "tool_intent",
}
_GENERIC_CLOSINGS = ("anything else", "let me know if", "how else can i help", "what else")
_ACK_OPENINGS = ("sure", "certainly", "absolutely", "of course", "got it", "understood")
_EXPLANATION_OPENINGS = ("the reason", "this means", "in other words", "to explain")
_CONTINUATION_CUES = ("continue", "keep going", "go on", "more", "next part", "next section")
_CLOSURE_CUES = ("thanks", "thank you", "got it", "that helps", "perfect", "done")
_SHARING_CLOSURE_CUES = (
    "i just wanted to share that", "just wanted to share that", "that's all", "thats all",
    "just thought you'd like to know", "just thought youd like to know", "anyway it felt good",
    "just sharing", "wanted you to know",
)
_QUESTION_INVITATION_PATTERNS = (
    re.compile(r"^(?:please\s+)?(?:go ahead and\s+)?ask me\b"),
    re.compile(r"^(?:you can|you may|feel free to)\s+ask(?: me)?\b"),
    re.compile(r"^(?:i want|i would like) you to ask me\b"),
    re.compile(r"^(?:do you have\s+)?any questions for me\b"),
    re.compile(r"^what would you ask me\b"),
    re.compile(r"^(?:do you\s+)?want to ask me\b"),
    re.compile(r"^ask away\b"),
)
_TOPIC_CHANGE_CUES = ("new topic", "different topic", "separately", "unrelated", "instead", "switching to")
_NEXT_STEP_CUES = ("what next", "next step", "where do we go", "what should i do next")
_NEGATED_CUE_PREFIXES = ("do not", "dont", "don\'t", "not", "never", "stop")



def _normalized_literal(value: str) -> str:
    """Bounded literal normalization for cue recognition; never returns raw content."""
    lowered = _CONTROL.sub("", value.lower())[:MAX_MESSAGE_ANALYSIS_CHARS]
    lowered = re.sub(r"[^a-z0-9?' ]+", " ", lowered)
    return " ".join(lowered.split())


def _cue_present(message: str, cues: tuple[str, ...], *, anywhere: bool = False) -> bool:
    normalized = _normalized_literal(message)
    if not normalized:
        return False
    for cue in cues:
        position = normalized.find(cue)
        if position < 0:
            continue
        prefix_words = normalized[:position].split()[-5:]
        prefix = " ".join(prefix_words)
        if any(negation in prefix for negation in _NEGATED_CUE_PREFIXES):
            continue
        if anywhere or position == 0:
            return True
    return False


def _question_invitation_present(message: str) -> bool:
    """Recognize deliberate invitations without treating complaints as permission."""
    normalized = _normalized_literal(message)
    return bool(normalized and any(pattern.search(normalized) for pattern in _QUESTION_INVITATION_PATTERNS))

def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _token(value: Any, default: str, maximum: int = 48) -> str:
    cleaned = _TOKEN.sub("_", str(value or default).lower()).strip("_")[:maximum]
    return cleaned or default


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
        if index >= MAX_HISTORY_RECORDS:
            truncated = True
            break
        if isinstance(item, dict):
            rows.append(item)
    return rows, truncated, False


def _stale(row: dict[str, Any]) -> bool:
    return any(_token(row.get(k), "", 24) in _STALE for k in ("state", "status", "lifecycle", "validity")) or any(row.get(k) is True for k in _STALE)


def _suspicious(row: dict[str, Any]) -> bool:
    return any(str(key).lower() in _SUSPICIOUS for key in row)


def _text(row: dict[str, Any]) -> str:
    return _CONTROL.sub("", str(row.get("content") or row.get("text") or row.get("message") or "")[:MAX_MESSAGE_ANALYSIS_CHARS])


@dataclass(frozen=True)
class NaturalFollowUpEvidence:
    message_present: bool
    message_truncated: bool
    control_characters_removed: bool
    current_request_answerable: bool
    prior_question_consumed: bool
    topic_state: str
    discourse_relation: str
    continuity_relation: str
    continuity_confidence: str
    explicit_correction_present: bool
    protected_constraints_present: bool
    history_count: int
    history_truncated: bool
    history_malformed: bool
    stale_records_ignored: int
    suspicious_records_ignored: int
    repeated_opening_posture: bool
    repeated_acknowledgment_pattern: bool
    repeated_prior_question_request: bool
    repeated_explanation_posture: bool
    repeated_generic_closing_behavior: bool
    repeated_question_ending_behavior: bool
    recent_question_ending_count: int
    literal_question_present: bool
    literal_continuation_cue: bool
    literal_closure_cue: bool
    literal_sharing_closure_cue: bool
    literal_question_invitation_cue: bool
    literal_topic_change_cue: bool
    literal_next_step_request: bool
    topic_transition_permitted: bool
    cue_conflict_present: bool
    low_confidence_state: bool
    contradictory_state: bool
    evidence_integrity: str
    schema_version: str = SCHEMA_VERSION
    contract_version: str = CONTRACT_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({
            "contains_message_content": False, "contains_conversation_text": False,
            "contains_memory_text": False, "contains_provider_payload": False,
            "contains_private_chain_of_thought": False, "provider_contacted": False,
        })
        result["evidence_digest"] = _digest(result)
        return result


def build_natural_follow_up_evidence(
    current_message: Any,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    natural_continuity_state: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    raw = "" if current_message is None else str(current_message)
    bounded = raw[:MAX_MESSAGE_ANALYSIS_CHARS]
    message = _CONTROL.sub("", bounded)
    canonical = conversation_policy_state if isinstance(conversation_policy_state, dict) else {}
    discourse = conversation_discourse_policy if isinstance(conversation_discourse_policy, dict) else {}
    continuity = natural_continuity_state if isinstance(natural_continuity_state, dict) else {}
    rows, truncated, malformed = _rows(conversation_history)
    valid: list[dict[str, Any]] = []
    stale_ignored = suspicious_ignored = 0
    for row in rows:
        if _stale(row):
            stale_ignored += 1
        elif _suspicious(row):
            suspicious_ignored += 1
        elif _text(row).strip():
            valid.append(row)
    assistant_texts = [_text(row).strip().lower() for row in valid[-8:] if "assistant" in _token(row.get("role") or row.get("kind"), "", 24)]
    openings = [text.split(maxsplit=1)[0] if text else "" for text in assistant_texts]
    repeated_opening = len(openings) >= 2 and openings[-1] and openings[-1] == openings[-2]
    repeated_ack = sum(any(text.startswith(prefix) for prefix in _ACK_OPENINGS) for text in assistant_texts[-4:]) >= 2
    repeated_explanation = sum(any(text.startswith(prefix) for prefix in _EXPLANATION_OPENINGS) for text in assistant_texts[-4:]) >= 2
    repeated_generic = any(any(cue in text for cue in _GENERIC_CLOSINGS) for text in assistant_texts[-3:])
    recent_question_endings = sum(text.rstrip().endswith("?") for text in assistant_texts[-3:])
    repeated_question_ending = recent_question_endings >= 2
    lowered_message = _normalized_literal(message)
    literal_question = "?" in message
    continuation_cue = _cue_present(message, _CONTINUATION_CUES, anywhere=True)
    closure_cue = _cue_present(message, _CLOSURE_CUES)
    sharing_closure_cue = _cue_present(message, _SHARING_CLOSURE_CUES, anywhere=True)
    question_invitation_cue = _question_invitation_present(message)
    topic_change_cue = _cue_present(message, _TOPIC_CHANGE_CUES, anywhere=True)
    next_step_request = _cue_present(message, _NEXT_STEP_CUES, anywhere=True)
    cue_conflict = continuation_cue and closure_cue
    relation = _token(discourse.get("discourse_relation"), "respond", 32)
    continuity_relation = _token(continuity.get("continuity_relation"), "fresh_turn", 40)
    prior_consumed = continuity.get("consume_prior_question") is True
    answerable = _token(canonical.get("selected_intent"), "direct_answer", 40) not in {"clarification", "request_clarification"}
    if canonical.get("intentional_silence_verified") is True or relation == "close" or continuity.get("close_without_reopening") is True:
        topic_state = "complete"
    elif discourse.get("address_explicit_correction") is True or relation == "repair":
        topic_state = "repaired"
    elif relation == "clarify" or not answerable:
        topic_state = "ambiguous"
    else:
        topic_state = "active"
    confidence = _token(continuity.get("continuity_confidence"), "low", 24)
    low_confidence = confidence not in {"high", "verified", "strong"}
    contradictory = (
        not isinstance(conversation_policy_state, dict) or not isinstance(conversation_discourse_policy, dict)
        or not isinstance(natural_continuity_state, dict)
        or (topic_state == "complete" and relation in {"continue", "clarify"})
        or (prior_consumed and continuity.get("avoid_reasking_answered_question") is not True)
        or canonical.get("component_conflict_present") is True
        or cue_conflict
    )
    integrity = "degraded" if malformed or suspicious_ignored or contradictory or low_confidence else "verified"
    evidence = NaturalFollowUpEvidence(
        message_present=bool(message.strip()), message_truncated=len(raw) > len(bounded),
        control_characters_removed=message != bounded, current_request_answerable=answerable,
        prior_question_consumed=prior_consumed, topic_state=topic_state,
        discourse_relation=relation, continuity_relation=continuity_relation,
        continuity_confidence=confidence,
        explicit_correction_present=discourse.get("address_explicit_correction") is True,
        protected_constraints_present=bool(tuple(protected_operator_constraints or ())),
        history_count=len(rows), history_truncated=truncated, history_malformed=malformed,
        stale_records_ignored=min(stale_ignored, MAX_HISTORY_RECORDS),
        suspicious_records_ignored=min(suspicious_ignored, MAX_HISTORY_RECORDS),
        repeated_opening_posture=repeated_opening,
        repeated_acknowledgment_pattern=repeated_ack,
        repeated_prior_question_request=prior_consumed and continuity.get("avoid_reasking_answered_question") is not True,
        repeated_explanation_posture=repeated_explanation,
        repeated_generic_closing_behavior=repeated_generic,
        repeated_question_ending_behavior=repeated_question_ending,
        recent_question_ending_count=recent_question_endings,
        literal_question_present=literal_question, literal_continuation_cue=continuation_cue,
        literal_closure_cue=closure_cue, literal_sharing_closure_cue=sharing_closure_cue,
        literal_question_invitation_cue=question_invitation_cue, literal_topic_change_cue=topic_change_cue,
        literal_next_step_request=next_step_request, topic_transition_permitted=topic_change_cue,
        cue_conflict_present=cue_conflict, low_confidence_state=low_confidence,
        contradictory_state=contradictory, evidence_integrity=integrity,
    )
    return evidence.public_summary()


def _digest_valid(source: dict[str, Any]) -> bool:
    supplied = source.get("evidence_digest")
    payload = dict(source); payload.pop("evidence_digest", None)
    return isinstance(supplied, str) and len(supplied) == 64 and _digest(payload) == supplied


def build_natural_follow_up_policy(evidence: dict[str, Any] | None) -> dict[str, Any]:
    source = evidence if isinstance(evidence, dict) else {}
    recovered = not isinstance(evidence, dict) or not _digest_valid(source)
    unsafe_evidence = (
        recovered
        or source.get("contradictory_state") is True
        or source.get("history_malformed") is True
        or int(source.get("suspicious_records_ignored") or 0) > 0
    )
    degraded = unsafe_evidence or source.get("evidence_integrity") != "verified"
    topic = _token(source.get("topic_state"), "ambiguous", 24)
    relation = _token(source.get("discourse_relation"), "respond", 24)
    answerable = source.get("current_request_answerable") is True
    prior_consumed = source.get("prior_question_consumed") is True
    repetition = any(source.get(key) is True for key in (
        "repeated_opening_posture", "repeated_acknowledgment_pattern", "repeated_prior_question_request",
        "repeated_explanation_posture", "repeated_generic_closing_behavior", "repeated_question_ending_behavior",
    ))
    posture = "answer_only"
    question_permission = "none"
    # Low continuity confidence suppresses optional questioning, but it must not
    # erase a literal user invitation or a genuinely required clarification.
    if not unsafe_evidence and (not answerable or relation == "clarify"):
        posture = "ask_one_required_clarification"
        question_permission = "required_clarification"
    elif not unsafe_evidence and source.get("literal_question_invitation_cue") is True:
        posture = "respond_and_ask_one_invited_question"
        question_permission = "user_invited"
    elif not degraded:
        if topic == "complete": posture = "briefly_acknowledge_and_close"
        elif relation == "repair" or source.get("explicit_correction_present") is True: posture = "repair_and_continue"
        elif source.get("literal_closure_cue") is True or source.get("literal_sharing_closure_cue") is True: posture = "briefly_acknowledge_and_close"
        elif relation == "continue" or source.get("literal_continuation_cue") is True or source.get("continuity_relation") in {"continue_thread", "answer_prior_question"}: posture = "continue_current_topic"
        elif topic == "active" and source.get("literal_next_step_request") is True and not repetition:
            posture = "answer_and_offer_one_relevant_next_step"
            question_permission = "optional_relevant"
    max_questions = 1 if question_permission != "none" else 0
    policy = {
        "continuation_posture": posture,
        "follow_up_relevance": (
            "required" if question_permission == "required_clarification"
            else ("optional_relevant" if question_permission in {"user_invited", "optional_relevant"} else "none")
        ),
        "question_permission": question_permission,
        "topic_continuity_posture": topic if not degraded else "literal_current_request",
        "answer_literal_current_request": True,
        "maximum_follow_up_questions": max_questions,
        "optional_follow_up_suppressed": (
            question_permission not in {"required_clarification", "user_invited"}
            and (degraded or repetition or prior_consumed or topic == "complete"
                 or source.get("literal_closure_cue") is True or source.get("literal_sharing_closure_cue") is True)
        ),
        "sharing_or_closure_cue_present": source.get("literal_closure_cue") is True or source.get("literal_sharing_closure_cue") is True,
        "repeated_question_ending_behavior": source.get("repeated_question_ending_behavior") is True,
        "recent_question_ending_count": int(source.get("recent_question_ending_count") or 0),
        "avoid_generic_closing_offer": True,
        "avoid_reasking_consumed_question": True,
        "avoid_repeating_user_request": True,
        "avoid_recap_of_completed_material": True,
        "avoid_repeated_acknowledgment": source.get("repeated_acknowledgment_pattern") is True,
        "avoid_repeated_explanation": source.get("repeated_explanation_posture") is True,
        "avoid_repeated_opening": source.get("repeated_opening_posture") is True,
        "no_topic_change_without_literal_cue": True,
        "topic_transition_permitted": source.get("topic_transition_permitted") is True and not degraded,
        "literal_continuation_cue_present": source.get("literal_continuation_cue") is True,
        "literal_next_step_request_present": source.get("literal_next_step_request") is True,
        "no_follow_up_to_prolong_conversation": True,
        "preserve_intentional_silence": topic == "complete" and source.get("discourse_relation") == "close",
        "may_initiate_new_turn": False, "tool_intent_selected": False, "action_execution_permitted": False,
        "approval_granted": False, "authorization_granted": False, "learning_mutation_permitted": False,
        "memory_rewrite_permitted": False, "policy_recovered": recovered,
        "recovery_reason": "invalid_evidence_digest" if recovered else ("degraded_evidence" if degraded else "none"),
        "cue_conflict_suppressed": source.get("cue_conflict_present") is True,
        "low_confidence_suppressed": source.get("low_confidence_state") is True,
        "evidence_digest": str(source.get("evidence_digest") or ""),
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "contains_message_content": False, "contains_conversation_text": False,
        "contains_memory_text": False, "contains_provider_payload": False,
        "contains_private_chain_of_thought": False, "provider_contacted_for_policy": False,
    }
    policy["policy_digest"] = _digest(policy)
    policy["prompt_section"] = natural_follow_up_prompt_section(policy)
    return policy


def natural_follow_up_prompt_section(policy: dict[str, Any]) -> str:
    """Return a compact model-facing contract, never a dump of policy JSON.

    The policy object remains the authoritative machine-readable receipt.  The
    model only needs the small set of behavioral consequences below.  Keeping
    those consequences at the front of the section prevents response-time
    compaction from silently cutting away the repetition controls that were
    already detected deterministically.
    """
    posture = _token(policy.get("continuation_posture"), "answer_only", 48)
    topic = _token(policy.get("topic_continuity_posture"), "literal_current_request", 48)
    max_questions = 1 if int(policy.get("maximum_follow_up_questions") or 0) > 0 else 0
    suppressions: list[str] = []
    if policy.get("avoid_repeated_opening") is True:
        suppressions.append("repeated opening")
    if policy.get("avoid_repeated_acknowledgment") is True:
        suppressions.append("repeated acknowledgment")
    if policy.get("avoid_repeated_explanation") is True:
        suppressions.append("repeated explanation")
    if policy.get("avoid_reasking_consumed_question") is True:
        suppressions.append("re-asked question")
    if policy.get("avoid_generic_closing_offer") is True:
        suppressions.append("generic help/closing offer")

    permission = _token(policy.get("question_permission"), "none", 40)
    lines = [
        "NATURAL FOLLOW-UP CONTRACT",
        f"Continue posture={posture}; topic posture={topic}.",
        "Answer the current message on its active subject. Do not reset the exchange or change topics without a clear user cue.",
    ]
    if max_questions <= 0:
        lines.append("QUESTION BOUNDARY: Ask no question in this reply. End naturally with a statement, reaction, reflection, warmth, humor, or a related thought instead.")
    elif permission == "required_clarification":
        lines.append("QUESTION BOUNDARY: One clarification question is permitted because the current request genuinely requires it. Ask no second question.")
    elif permission == "user_invited":
        lines.append("QUESTION BOUNDARY: The user explicitly invited a question. You may ask one specific relevant question, but no generic intake question.")
    else:
        lines.append("QUESTION BOUNDARY: At most one specific relevant question may advance this open topic; it is optional and must not be generic.")
    lines.append("Do not end with a generic offer to help, an intake question, or a question whose purpose is only to prolong the conversation.")
    if policy.get("optional_follow_up_suppressed") is True:
        lines.append("Optional follow-up is suppressed for this turn; finish naturally after the direct response.")
    if suppressions:
        lines.append("Suppress recent repetition: " + ", ".join(suppressions) + ".")
    if policy.get("preserve_intentional_silence") is True:
        lines.append("Preserve a genuine conversational close; do not reopen the topic.")
    lines.append("This contract grants no action, approval, memory rewrite, provider, or turn-initiation authority.")
    section = "\n".join(lines)
    return section[:MAX_PROMPT_CHARS].rstrip()


def build_natural_follow_up_for_turn(
    current_message: Any,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    natural_continuity_state: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    evidence = build_natural_follow_up_evidence(
        current_message, conversation_policy_state, conversation_discourse_policy,
        natural_continuity_state, conversation_history, protected_operator_constraints,
    )
    return {**build_natural_follow_up_policy(evidence), "evidence": evidence}


def verify_natural_follow_up_runtime_diagnostics(diagnostics: dict[str, Any] | None) -> bool:
    if not isinstance(diagnostics, dict):
        return False
    supplied = diagnostics.get("diagnostics_digest")
    payload = dict(diagnostics)
    payload.pop("diagnostics_digest", None)
    return isinstance(supplied, str) and len(supplied) == 64 and _digest(payload) == supplied


def build_natural_follow_up_runtime_projection(
    current_message: Any,
    conversation_policy_state: dict[str, Any] | None,
    conversation_discourse_policy: dict[str, Any] | None,
    natural_continuity_state: dict[str, Any] | None,
    conversation_history: Iterable[dict[str, Any]] | None = None,
    protected_operator_constraints: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Shared v1162.8 projection used by streaming and non-streaming generation."""
    policy = build_natural_follow_up_for_turn(
        current_message, conversation_policy_state, conversation_discourse_policy,
        natural_continuity_state, conversation_history, protected_operator_constraints,
    )
    diagnostics = {
        "contract_version": policy.get("contract_version"),
        "schema_version": policy.get("schema_version"),
        "continuation_posture": policy.get("continuation_posture"),
        "follow_up_relevance": policy.get("follow_up_relevance"),
        "question_permission": policy.get("question_permission"),
        "topic_continuity_posture": policy.get("topic_continuity_posture"),
        "topic_transition_permitted": policy.get("topic_transition_permitted") is True,
        "optional_follow_up_suppressed": policy.get("optional_follow_up_suppressed") is True,
        "maximum_follow_up_questions": int(policy.get("maximum_follow_up_questions") or 0),
        "sharing_or_closure_cue_present": policy.get("sharing_or_closure_cue_present") is True,
        "repeated_question_ending_behavior": policy.get("repeated_question_ending_behavior") is True,
        "recent_question_ending_count": int(policy.get("recent_question_ending_count") or 0),
        "policy_recovered": policy.get("policy_recovered") is True,
        "recovery_reason": policy.get("recovery_reason"),
        "cue_conflict_suppressed": policy.get("cue_conflict_suppressed") is True,
        "low_confidence_suppressed": policy.get("low_confidence_suppressed") is True,
        "contains_content": False,
        "contains_private_chain_of_thought": False,
        "authority": "none",
    }
    diagnostics["diagnostics_digest"] = _digest(diagnostics)
    return {"policy": policy, "prompt_section": policy["prompt_section"], "diagnostics": diagnostics}

_QUESTION_FREE_FALLBACKS = (
    "I’m glad you shared that with me.",
    "That feels worth simply acknowledging.",
    "I’m taking that in with you.",
    "That lands as something worth holding onto for a moment.",
)


def _bounded_question_free_fallback(policy: dict[str, Any], original_response: str) -> str:
    """Last-resort local fallback when a provider returned only disallowed questions.

    This never performs another provider request.  The prompt contract is expected
    to prevent this path in normal use; the fallback only keeps the visible/committed
    reply compliant when a small model ignores the zero-question boundary entirely.
    """
    seed = f"{policy.get('evidence_digest')}|{policy.get('continuation_posture')}|{original_response}".encode("utf-8", errors="ignore")
    index = int(hashlib.sha256(seed).hexdigest()[:8], 16) % len(_QUESTION_FREE_FALLBACKS)
    return _QUESTION_FREE_FALLBACKS[index]


def _response_units(value: str) -> list[str]:
    """Split response into punctuation-bounded units while preserving whitespace."""
    text = str(value or "")
    if not text:
        return []
    units: list[str] = []
    start = 0
    i = 0
    closers = '"\'’”)]}'
    while i < len(text):
        ch = text[i]
        if ch in ".!?\n":
            end = i + 1
            while end < len(text) and text[end] in closers:
                end += 1
            while end < len(text) and text[end].isspace():
                end += 1
            units.append(text[start:end])
            start = end
            i = end
            continue
        i += 1
    if start < len(text):
        units.append(text[start:])
    return units


def enforce_natural_follow_up_output(
    response: Any,
    policy: dict[str, Any] | None,
    *,
    casual_fast_path: bool,
) -> tuple[str, dict[str, Any]]:
    """Enforce the authoritative question budget before a reply is committed.

    Operator/governed lanes are intentionally untouched.  For casual turns, whole
    question-bearing units beyond the policy budget are omitted before visibility
    or commit; no second generation request is made.
    """
    text = str(response or "")
    source = policy if isinstance(policy, dict) else {}
    maximum = max(0, min(1, int(source.get("maximum_follow_up_questions") or 0)))
    if not casual_fast_path:
        diagnostics = {
            "applied": False, "reason": "governed_operator_lane",
            "maximum_follow_up_questions": maximum, "input_question_units": 0,
            "output_question_units": 0, "suppressed_question_units": 0,
            "fallback_used": False, "content_free": True, "provider_request_added": False,
        }
        diagnostics["diagnostics_digest"] = _digest(diagnostics)
        return text, diagnostics

    kept: list[str] = []
    input_questions = output_questions = suppressed = 0
    for unit in _response_units(text):
        has_question = "?" in unit
        if has_question:
            input_questions += 1
            if output_questions >= maximum:
                suppressed += 1
                continue
            output_questions += 1
        kept.append(unit)
    filtered = "".join(kept).strip()
    fallback_used = False
    if text.strip() and not filtered:
        filtered = _bounded_question_free_fallback(source, text)
        fallback_used = True
    diagnostics = {
        "applied": True,
        "reason": "casual_follow_up_question_budget",
        "maximum_follow_up_questions": maximum,
        "question_permission": _token(source.get("question_permission"), "none", 40),
        "input_question_units": input_questions,
        "output_question_units": output_questions if not fallback_used else 0,
        "suppressed_question_units": suppressed,
        "fallback_used": fallback_used,
        "sharing_or_closure_cue_present": source.get("sharing_or_closure_cue_present") is True,
        "repeated_question_ending_behavior": source.get("repeated_question_ending_behavior") is True,
        "content_free": True,
        "provider_request_added": False,
    }
    diagnostics["diagnostics_digest"] = _digest(diagnostics)
    return filtered, diagnostics


class NaturalFollowUpStreamGate:
    """Sentence-bounded stream gate that never retracts an already visible question.

    The gate is active only for casual_fast turns.  When the question budget is
    zero it buffers the current punctuation unit, exposing declarative units as
    soon as they complete while withholding disallowed question units.
    """

    def __init__(self, policy: dict[str, Any] | None, *, casual_fast_path: bool) -> None:
        self.policy = policy if isinstance(policy, dict) else {}
        self.casual_fast_path = bool(casual_fast_path)
        self.maximum = max(0, min(1, int(self.policy.get("maximum_follow_up_questions") or 0)))
        self.buffer = ""
        self.raw_seen = ""
        self.visible = ""
        self.input_question_units = 0
        self.output_question_units = 0
        self.suppressed_question_units = 0
        self.fallback_used = False

    def _admit_unit(self, unit: str) -> str:
        if not self.casual_fast_path:
            self.visible += unit
            return unit
        if "?" in unit:
            self.input_question_units += 1
            if self.output_question_units >= self.maximum:
                self.suppressed_question_units += 1
                return ""
            self.output_question_units += 1
        self.visible += unit
        return unit

    def feed(self, value: Any) -> str:
        text = str(value or "")
        self.raw_seen += text
        if not self.casual_fast_path:
            self.visible += text
            return text
        self.buffer += text
        units = _response_units(self.buffer)
        if not units:
            return ""
        # Keep an unterminated final unit buffered.  Every preceding unit ended in
        # punctuation/newline and can be admitted safely without future retraction.
        last_terminated = bool(re.search(r"[.!?][\"'’”\)\]\}]*\s*$", self.buffer)) or self.buffer.endswith("\n")
        if not last_terminated:
            pending = units.pop() if units else ""
        else:
            pending = ""
        emitted = "".join(self._admit_unit(unit) for unit in units)
        self.buffer = pending
        return emitted

    def finish(self) -> str:
        tail = self._admit_unit(self.buffer) if self.buffer else ""
        self.buffer = ""
        if not self.visible.strip() and self.casual_fast_path:
            fallback = _bounded_question_free_fallback(self.policy, self.raw_seen or "question_only_provider_output")
            self.visible = fallback
            self.fallback_used = True
            return fallback
        return tail

    def diagnostics(self) -> dict[str, Any]:
        diagnostics = {
            "applied": self.casual_fast_path,
            "reason": "casual_stream_question_budget" if self.casual_fast_path else "governed_operator_lane",
            "maximum_follow_up_questions": self.maximum,
            "question_permission": _token(self.policy.get("question_permission"), "none", 40),
            "input_question_units": self.input_question_units,
            "output_question_units": self.output_question_units if not self.fallback_used else 0,
            "suppressed_question_units": self.suppressed_question_units,
            "fallback_used": self.fallback_used,
            "buffered_before_visibility": self.casual_fast_path,
            "content_free": True,
            "provider_request_added": False,
        }
        diagnostics["diagnostics_digest"] = _digest(diagnostics)
        return diagnostics
