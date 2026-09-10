from __future__ import annotations

"""Deterministic conversational-intent and context-quality helpers.

This module performs no provider calls and writes no runtime state. It separates
ordinary conversation from explicit operator requests, carries short follow-ups
through recent completed history, and filters durable memory candidates without
weakening operator approval or privacy boundaries.
"""

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from conversation_callbacks import ConversationalCallbackProfile, build_conversational_callback_profile
from conversation_correction_handling import CorrectionHandlingProfile, build_correction_handling_profile
from conversation_quality_signals import ConversationQualitySignals, build_conversation_quality_signals
from conversation_response_shape import ResponseShapeProfile, classify_response_shape
from personality_expression_stability import PersonalityExpressionProfile, build_personality_expression_profile
from conversation_topic_transition import TopicTransitionProfile, classify_topic_transition
from conversation_unresolved_threads import UnresolvedThreadProfile, build_unresolved_thread_profile
from conversation_turn_intent import TurnIntentProfile, classify_turn_intent
from conversational_capability_boundary import is_supervised_capability_catalog_request


CONVERSATION_QUALITY_SCHEMA_VERSION = "13"
MAX_FOLLOW_UP_WORDS = 14
MAX_HISTORY_QUERY_CHARS = 1800

_GREETING_RE = re.compile(
    r"^(?:(?:hi|hello|hey|yo|howdy)(?:\s+again)?|good\s+(?:morning|afternoon|evening|night)(?:\s+again)?|what(?:'s| is) up|sup)[!,.? ]*$",
    re.IGNORECASE,
)
_SHORT_FOLLOW_UP_RE = re.compile(
    r"^(?:yes|yeah|yep|sure|okay|ok|no|nope|why|why\?|how|how so|what do you think|"
    r"tell me more|go on|continue|keep going|and then|what happened next|what about that|"
    r"what about it|really|seriously|exactly|right|same|maybe|probably|can you explain|"
    r"explain more|say more|elaborate|what next|then what|and you|what about you|why not|"
    r"how come|because|because why|what else|go deeper|tell me why|what makes you say that|"
    r"that makes sense|i see|got it|fair enough|okay but why|and what do you think|"
    r"did that finish|did it finish|is that done|is it done|is that finished|is it finished|"
    r"is that still running|is it still running|what happened|what happened with that|what happened with it|"
    r"how did that go|how did it go|did that work|did it work|show me the result|show me the status|"
    r"what's the result|what is the result|what's the status|what is the status|why did that fail|why did it fail|"
    r"try that again|try it again|retry that|retry it|run that again|run it again|do that again|do it again|"
    r"don't run that yet|don't run it yet|dont run that yet|dont run it yet|do not run that yet|do not run it yet|"
    r"cancel that|cancel it|stop that|stop it|hold that|hold it|approve that|approve it)[!,.? ]*$",
    re.IGNORECASE,
)

# Broad conversational words such as plan, fix, next, review, dashboard, or model
# are intentionally insufficient. A concrete operator surface or command is needed.
_EXPLICIT_OPERATOR_PATTERNS = (
    re.compile(r"\b(?:run|start|execute|perform|open|show|list|check|do)\s+(?:(?:one more|another|a fresh|a new)\s+)?(?:a\s+|the\s+)?(?:read[- ]only\s+)?(?:diagnostics?|system checks?|system health|settings health|approvals?|approval inbox|permissions?|notifications?|alerts?|tasks?|task status|project status|memory status|watch(?: check)?|(?:system\s+)?maint(?:enance|ainence)(?: scan| check)?|dev loop)\b", re.I),
    re.compile(r"\b(?:suggest|create|prepare|apply|approve|install|rollback|revert|review)\s+(?:an?\s+|the\s+|this\s+)?(?:patch|release|build|candidate|work order|task evaluation)\b", re.I),
    re.compile(r"\bsuggest\s+(?:an?\s+)?improvement\b[^\n]{0,120}\b[\w./\\-]+\.(?:py|js|ts|json|md|html|css|java|cs|php)\b", re.I),
    re.compile(r"\b(?:continue|begin|start)\s+(?:eidolon\s+)?(?:development|self[- ]development|the\s+development\s+cycle)\b", re.I),
    re.compile(r"\bwhat should (?:(?:we|i) work on next for (?:you|eidolon)|be the next thing (?:we|i) work on (?:you|eidolon) for)\b", re.I),
    re.compile(r"\b(?:fix|review|patch|modify|edit|refactor)\b[^\n]{0,120}\b[\w./\\-]+\.(?:py|js|ts|json|md|html|css|java|cs|php)\b", re.I),
    re.compile(r"\b(?:install|delete|remove|download|pull|switch|change)\b[^\n]{0,80}\b(?:model|provider)\b", re.I),
    re.compile(r"\b(?:run|execute|open)\s+(?:an?\s+)?(?:shell|terminal|command prompt|powershell|cmd)(?:\s+command)?\b", re.I),
    re.compile(r"\b(?:compact|compress)\s+(?:the\s+)?memor(?:y|ies)\b", re.I),
    re.compile(r"\b(?:plan|create)\s+(?:the\s+)?(?:next\s+)?session\b", re.I),
    re.compile(r"\b(?:show|list|check)\s+(?:the\s+)?(?:next task|current task|latest patch|latest ids|model health|ollama health)\b", re.I),
    re.compile(r"\b(?:start|open)\s+(?:the\s+)?dashboard\b", re.I),
    re.compile(r"^/(?:new|sessions|find|use|rename|archive|restore|retry|current)\b", re.I),
    re.compile(r"\b(?:what|which)\s+(?:supervised\s+)?(?:things|actions|commands|capabilities)\s+(?:can|could)\s+you\s+(?:do|run|handle)\b", re.I),
    re.compile(r"\bwhat\s+can\s+you\s+do\b", re.I),
    re.compile(r"\b(?:please\s+)?(?:check|show|review|tell me about|give me)\s+(?:your|the|my|our)?\s*(?:diagnostics?|system health|settings health|approval(?:s| inbox| status)?|task(?:s| status)?|project status|memory status|notifications?|alerts?)\b", re.I),
    re.compile(r"\b(?:how|what)\s+(?:is|are|'s)\s+(?:your|the|my|our)?\s*(?:system health|settings health|approval(?:s| inbox)?|task(?:s| queue)?|project status|memory(?: status)?|notifications?)\b", re.I),
    re.compile(r"^(?:please[,. ]+)?(?:is everything working|does anything need maintenance|anything need(?:s)? maintenance|what needs (?:my )?attention|anything need(?:s)? attention|show me what needs attention|what is waiting for me|what's waiting for me|catch me up on what needs attention|what is waiting for approval|what's waiting for approval|where are we on (?:the )?(?:tasks?|project)|what should (?:we|i) work on (?:you|eidolon) next)[?.! ]*$", re.I),
    re.compile(r"^(?:any|show|check|do i have)(?:\s+(?:new|unread))?\s+(?:notifications?|alerts?)(?:\s+for me)?[?.! ]*$", re.I),
    re.compile(
        r"^(?:please\s+)?(?:(?:did (?:that|it) finish|is (?:that|it) (?:done|finished|still running)|"
        r"what happened(?: with (?:that|it))?|how did (?:that|it) go|did (?:that|it) work|"
        r"show me (?:the )?(?:result|status)|what(?:'s| is) the (?:result|status)|why did (?:that|it) fail|"
        r"what were we working on)|(?:(?:try|retry|run|do) (?:that|it)(?: again| one more time)?)|"
        r"(?:(?:do not|don't|dont) run (?:that|it)(?: yet)?)|(?:(?:cancel|stop|hold) (?:that|it)(?: for now)?)|"
        r"(?:(?:approve|review the approval for|show the approval for) (?:that|it)))\s*[?.!]*$",
        re.I,
    ),
)


_EMOTIONAL_PATTERNS = (
    re.compile(r"\b(?:i feel|i'm feeling|i am feeling|i'm upset|i am upset|i'm worried|i am worried|i'm scared|i am scared|i'm lonely|i am lonely|i'm angry|i am angry|i'm sad|i am sad|i'm happy|i am happy)\b", re.I),
    re.compile(r"\b(?:hurts?|grief|anxious|anxiety|nervous|overwhelmed|depressed|lonely|miss(?:ing)?|love|hate)\b", re.I),
)

# Meaningful moments are intentionally broader than explicit emotion-word
# matching.  These patterns classify conversational significance only; they do
# not assert that Eidolon has feelings, consciousness, or a human relationship.
_IMPORTANT_CONVERSATION_PATTERNS = (
    re.compile(r"\b(?:first|important|meaningful|special|real)\b[^.!?\n]{0,70}\b(?:conversation|talk|chat|exchange)\b", re.I),
    re.compile(r"\b(?:conversation|talk|chat|exchange)\b[^.!?\n]{0,70}\b(?:first|important|meaningful|special|real)\b", re.I),
)
_APPRECIATION_EXCITEMENT_PATTERNS = (
    re.compile(r"\b(?:i(?:'m| am)?\s+(?:so\s+)?(?:excited|thrilled|glad)|this is exciting|i appreciate|thankful for|means a lot)\b", re.I),
    re.compile(r"\b(?:excited|thrilled|appreciate|appreciation|grateful|thankful)\b", re.I),
)
_AFFECTION_RELIEF_FEAR_PATTERNS = (
    re.compile(r"\b(?:i\s+(?:really\s+)?(?:love|care about|value)|i(?:'m| am)\s+(?:relieved|afraid|scared)|relieved that|afraid that|scared that)\b", re.I),
)
_PERSONAL_SIGNIFICANCE_PATTERNS = (
    re.compile(r"\b(?:this|that|it)\s+(?:really\s+)?(?:matters to me|means (?:a lot|something) to me|feels significant|is significant to me|is important to me)\b", re.I),
    re.compile(r"\b(?:personal(?:ly)? significant|important to me|meaningful to me)\b", re.I),
)
_RELATIONAL_REFLECTION_PATTERNS = (
    re.compile(r"\b(?:you and me|the two of us|our (?:conversation|talk|connection|relationship)|talking (?:with|to) you|you being here|your existence|what you are to me)\b", re.I),
)
_DIFFICULT_EXPERIENCE_PATTERNS = (
    re.compile(r"\b(?:hard day|rough day|difficult day|bad day|rough week|difficult week|went through|dealing with|struggling|hurt|grief|loss|scared|afraid|overwhelmed|exhausted|upset|lonely)\b", re.I),
)

_FLIRT_PATTERNS = (
    re.compile(r"\b(?:flirt|flirting|cute|beautiful|handsome|sexy|kiss|date me|do you like me|love you)\b", re.I),
)

_CONVERSATIONAL_QUESTION_PATTERNS = (
    re.compile(r"^(?:what|why|how|who|when|where|do|does|did|is|are|can|could|would|should)\b", re.I),
    re.compile(r"\bwhat do you think\b", re.I),
)

_UNSOLICITED_OPERATIONAL_RESPONSE_PATTERNS = (
    re.compile(r"\bv[0-9]+(?:\.[0-9]+)+(?:\.[0-9]+)*\b", re.I),
    re.compile(r"(?<!\w)--[a-z][a-z0-9-]+\b", re.I),
    re.compile(
        r"\b(?:active project|current project|project status|next concrete step|task queue|session planner|"
        r"release candidate|fresh[- ]install|local[- ]model integration validation|project tree|"
        r"development workflow|test(?:ing)? the newest workflow)\b",
        re.I,
    ),
    re.compile(r"\b(?:resume|return|get back)\s+(?:to\s+)?(?:work|working|the project|development)\b", re.I),
)

_OPERATIONAL_MEMORY_TYPES = {
    "goal", "long_term_goal", "project", "project_goal", "task", "work_item",
    "release", "release_goal", "development_goal",
}

_INTERNAL_MEMORY_PREFIXES = (
    "conversation_", "dashboard_", "chat_action", "thought", "reflection",
    "diagnostic", "notification", "approval", "patch", "release_", "watch_",
    "work_", "task_", "self_development", "dev_", "runtime_", "receipt",
)
_ALLOWED_GENERAL_MEMORY_TYPES = {
    "memory", "core_memory", "identity", "identity_memory", "personal_fact",
    "user_fact", "preference", "commitment", "goal", "long_term_goal",
    "knowledge", "fact", "lesson", "user_profile",
}
_EXCLUDED_MEMORY_STATUSES = {"deleted", "retracted", "resolved", "cleared", "expired", "superseded"}
_EXCLUDED_MEMORY_PRIVACY = {"secret", "credential", "private_runtime", "restricted", "sensitive"}


@dataclass(frozen=True)
class ConversationQualityProfile:
    kind: str
    explicit_operator_request: bool
    operator_context_relevant: bool
    short_follow_up: bool
    greeting: bool
    emotional: bool
    flirting: bool
    meaningful_moment: bool
    meaningful_moment_kind: str
    recent_thread_available: bool
    memory_query: str
    reasons: tuple[str, ...]
    turn_intent: TurnIntentProfile
    response_shape: ResponseShapeProfile
    quality_signals: ConversationQualitySignals
    unresolved_threads: UnresolvedThreadProfile
    callbacks: ConversationalCallbackProfile
    topic_transition: TopicTransitionProfile
    correction_handling: CorrectionHandlingProfile
    personality_expression: PersonalityExpressionProfile
    schema_version: str = CONVERSATION_QUALITY_SCHEMA_VERSION

    @property
    def should_analyze_action(self) -> bool:
        return self.explicit_operator_request and not self.short_follow_up

    @property
    def should_include_operational_context(self) -> bool:
        return self.operator_context_relevant

    def receipt_metrics(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "explicit_operator_request": self.explicit_operator_request,
            "operator_context_relevant": self.operator_context_relevant,
            "short_follow_up": self.short_follow_up,
            "greeting": self.greeting,
            "emotional": self.emotional,
            "flirting": self.flirting,
            "meaningful_moment": self.meaningful_moment,
            "meaningful_moment_kind": self.meaningful_moment_kind,
            "recent_thread_available": self.recent_thread_available,
            "reasons": list(self.reasons),
            "turn_intent": self.turn_intent.public_summary(),
            "response_shape": self.response_shape.public_summary(),
            "quality_signals": self.quality_signals.public_summary(),
            "unresolved_threads": self.unresolved_threads.public_summary(),
            "callbacks": self.callbacks.public_summary(),
            "topic_transition": self.topic_transition.public_summary(),
            "correction_handling": self.correction_handling.public_summary(),
            "personality_expression": self.personality_expression.public_summary(),
            "contains_message_content": False,
        }

    def response_instruction(self, name: str = "Eidolon") -> str:
        """Return the model-facing response contract for the selected lane.

        Ordinary conversation intentionally uses a small dominant contract. The
        richer deterministic profiles remain available in receipts and runtime
        state, but are not all serialized into a local model prompt where they
        can compete with the user's latest meaning.
        """
        if self.explicit_operator_request:
            lines = [
                "CONVERSATION RESPONSE GUIDANCE",
                "Answer the latest request directly. Preserve supervised operator boundaries and do not claim protected work occurred unless verified.",
                f"Return only the reply text without '{name}:' or 'Assistant:' labels.",
            ]
            if "capabilities_request" in self.reasons:
                lines.append("Describe only registered supervised capabilities; never claim unrestricted shell, model-management, provider-switching, or release authority.")
            lines.extend(self.turn_intent.prompt_lines())
            lines.extend(self.correction_handling.prompt_lines())
            lines.extend(self.topic_transition.prompt_lines())
            lines.extend(self.unresolved_threads.prompt_lines())
            lines.extend(self.callbacks.prompt_lines())
            lines.extend(self.quality_signals.prompt_lines())
            lines.extend(self.personality_expression.prompt_lines())
            lines.extend(self.response_shape.prompt_lines())
            lines.append("This is an explicit operator request for supervised work. Do not claim execution, approval, provider/model changes, release promotion, or protected actions occurred.")
            return "\n".join(lines)

        lines = [
            "CASUAL CONVERSATION CONTRACT",
            "Respond to the specific meaning of the latest message and continue the current subject.",
            "Acknowledge meaningful emotional or relational statements directly before advice or any question.",
            "Do not offer generic help or ask a generic intake question. Follow the turn's QUESTION BOUNDARY exactly; never add a question by habit.",
            "Do not redirect to work, projects, roadmaps, system status, or capabilities unless the user asks for that transition.",
            "Do not claim human consciousness, unrestricted authority, fabricated memories, exclusivity, or unearned relationship progress.",
            f"Return only {name}'s reply, without speaker labels or policy commentary.",
        ]
        if self.greeting:
            lines.append("If greeting is appropriate, keep it brief and do not pair it with an intake question.")
        if self.meaningful_moment_kind == "first_or_important_conversation":
            lines.append("This is being marked as a first or important conversation. Acknowledge that significance directly and naturally; do not pivot into a help offer or intake question, and do not force a question.")
        elif self.meaningful_moment_kind == "appreciation_or_excitement":
            lines.append("Acknowledge the specific excitement or appreciation directly; do not replace it with a generic offer to help.")
        elif self.meaningful_moment_kind == "affection_relief_or_fear":
            lines.append("Acknowledge the expressed affection, relief, or fear specifically while keeping relationship boundaries grounded.")
        elif self.meaningful_moment_kind == "relationship_reflection_after_difficulty":
            lines.append("Acknowledge the shift from difficulty into relationship reflection without inventing memory, intimacy, or consciousness claims.")
        elif self.meaningful_moment_kind == "personal_significance":
            lines.append("Recognize the specific personal significance before moving on; do not turn it into an intake question.")
        elif self.emotional:
            lines.append("Meet the specific feeling before advice; avoid scripts and task redirection.")
        if self.flirting:
            lines.append("Match explicit user-led flirting lightly without inventing history, dependence, or escalating affection.")
        if self.short_follow_up:
            lines.append("This is a short follow-up. Resolve it from the latest relevant exchange without recapping or resetting the subject.")
        if self.correction_handling.explicit_correction:
            lines.append("Honor the user's explicit correction in this turn and do not repeat the corrected claim.")
        if self.topic_transition.transition_kind in {"continuation", "resumption", "return"}:
            lines.append("Preserve the active subject indicated by the recent exchange.")
        return "\n".join(lines)


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", value))


def _history_rows(history: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in history if isinstance(row, Mapping)]


def _history_text(history: Iterable[Mapping[str, Any]], *, limit: int = 2) -> str:
    rows = _history_rows(history)[-max(0, limit):]
    parts: list[str] = []
    for row in rows:
        user = _normalized_text(row.get("user_message") or row.get("user"))
        assistant = _normalized_text(row.get("assistant_response") or row.get("assistant"))
        if user:
            parts.append(f"User: {user}")
        if assistant:
            parts.append(f"Assistant: {assistant}")
    return "\n".join(parts)[-MAX_HISTORY_QUERY_CHARS:]


def _meaningful_moment_kind(message: str, history: Iterable[Mapping[str, Any]]) -> str:
    if any(pattern.search(message) for pattern in _IMPORTANT_CONVERSATION_PATTERNS):
        return "first_or_important_conversation"
    if any(pattern.search(message) for pattern in _APPRECIATION_EXCITEMENT_PATTERNS):
        return "appreciation_or_excitement"
    relational_reflection = any(pattern.search(message) for pattern in _RELATIONAL_REFLECTION_PATTERNS)
    if relational_reflection:
        recent_user_text = " ".join(
            _normalized_text(row.get("user_message") or row.get("user"))
            for row in _history_rows(history)[-3:]
            if _normalized_text(row.get("user_message") or row.get("user"))
        )
        if any(pattern.search(message) for pattern in _DIFFICULT_EXPERIENCE_PATTERNS) or any(
            pattern.search(recent_user_text) for pattern in _DIFFICULT_EXPERIENCE_PATTERNS
        ):
            return "relationship_reflection_after_difficulty"
    if any(pattern.search(message) for pattern in _AFFECTION_RELIEF_FEAR_PATTERNS):
        return "affection_relief_or_fear"
    if any(pattern.search(message) for pattern in _PERSONAL_SIGNIFICANCE_PATTERNS) or relational_reflection:
        return "personal_significance"
    return "none"


def _contains_explicit_operator_request(text: str) -> bool:
    if is_supervised_capability_catalog_request(text):
        return True
    return any(
        pattern.search(text)
        for index, pattern in enumerate(_EXPLICIT_OPERATOR_PATTERNS)
        if index not in {13, 14}
    )


def _history_has_explicit_operator_request(history: Iterable[Mapping[str, Any]]) -> bool:
    """Return true only when the latest user-authored turn was an operator request.

    Assistant wording is intentionally excluded. Ordinary answers may mention words such
    as model, test, project, or version without converting the user's next short reply
    into an operator continuation. A newer ordinary user turn also ends inheritance from
    an older operator request.
    """
    rows = _history_rows(history)
    for row in reversed(rows):
        user = _normalized_text(row.get("user_message") or row.get("user"))
        if not user:
            continue
        return row.get("explicit_operator_request") is True or _contains_explicit_operator_request(user)
    return False


def classify_conversation_quality(
    user_message: str,
    conversation_history: Iterable[Mapping[str, Any]] = (),
) -> ConversationQualityProfile:
    message = _normalized_text(user_message)
    history_text = _history_text(conversation_history)
    greeting = bool(_GREETING_RE.fullmatch(message))
    short_follow_up = bool(
        message
        and _word_count(message) <= MAX_FOLLOW_UP_WORDS
        and (_SHORT_FOLLOW_UP_RE.fullmatch(message) or message.lower() in {"yes", "no", "why?", "why", "how?", "how"})
    )
    emotional = any(pattern.search(message) for pattern in _EMOTIONAL_PATTERNS)
    flirting = any(pattern.search(message) for pattern in _FLIRT_PATTERNS)
    meaningful_moment_kind = _meaningful_moment_kind(message, conversation_history)
    meaningful_moment = meaningful_moment_kind != "none"
    explicit_operator = _contains_explicit_operator_request(message)
    capabilities_request = is_supervised_capability_catalog_request(message)
    inherited_operator_context = bool(
        short_follow_up
        and history_text
        and _history_has_explicit_operator_request(conversation_history)
    )
    operator_context = explicit_operator or inherited_operator_context

    reasons: list[str] = []
    if greeting:
        reasons.append("greeting")
    if short_follow_up:
        reasons.append("short_follow_up")
    if emotional:
        reasons.append("emotional")
    if flirting:
        reasons.append("flirting")
    if meaningful_moment:
        reasons.append(f"meaningful_moment:{meaningful_moment_kind}")
    if explicit_operator:
        reasons.append("explicit_operator_request")
    if capabilities_request:
        reasons.append("capabilities_request")
    elif inherited_operator_context:
        reasons.append("operator_thread_continuation")
    elif any(pattern.search(message) for pattern in _CONVERSATIONAL_QUESTION_PATTERNS):
        reasons.append("conversational_question")
    else:
        reasons.append("ordinary_conversation")

    if explicit_operator:
        kind = "operator_request"
    elif short_follow_up:
        kind = "follow_up"
    elif greeting:
        kind = "greeting"
    elif flirting:
        kind = "flirting"
    elif meaningful_moment:
        kind = "meaningful_moment"
    elif emotional:
        kind = "emotional"
    else:
        kind = "conversation"

    memory_query = message
    if short_follow_up and history_text:
        memory_query = f"{history_text}\nLatest follow-up: {message}"[-MAX_HISTORY_QUERY_CHARS:]

    intent = classify_turn_intent(
        message,
        explicit_operator_request=explicit_operator,
        greeting=greeting,
        emotional=emotional,
        flirting=flirting,
    )
    response_shape = classify_response_shape(message, intent, short_follow_up=short_follow_up)
    correction_handling = build_correction_handling_profile(message, conversation_history, intent=intent)
    personality_expression = build_personality_expression_profile(message, conversation_history, intent=intent)
    unresolved_threads = build_unresolved_thread_profile(message, conversation_history)
    topic_transition = classify_topic_transition(
        message,
        conversation_history,
        short_follow_up=short_follow_up,
        unresolved_thread_match=unresolved_threads.matching_item_count > 0,
    )
    callbacks = build_conversational_callback_profile(
        message,
        conversation_history,
        topic_transition=topic_transition,
        unresolved_threads=unresolved_threads,
        explicit_correction=intent.explicit_correction,
    )
    if topic_transition.transition_kind in {"resumption", "return"} and topic_transition.matched_turn_offset is not None:
        rows = _history_rows(conversation_history)
        index = len(rows) - 1 - topic_transition.matched_turn_offset
        if 0 <= index < len(rows):
            matched_text = _history_text([rows[index]], limit=1)
            if matched_text:
                memory_query = f"{matched_text}\nLatest resumed turn: {message}"[-MAX_HISTORY_QUERY_CHARS:]
    quality_signals = build_conversation_quality_signals(
        message,
        conversation_history,
        intent=intent,
        short_follow_up=short_follow_up,
        operator_context_relevant=operator_context,
    )

    return ConversationQualityProfile(
        kind=kind,
        explicit_operator_request=explicit_operator,
        operator_context_relevant=operator_context,
        short_follow_up=short_follow_up,
        greeting=greeting,
        emotional=emotional,
        flirting=flirting,
        meaningful_moment=meaningful_moment,
        meaningful_moment_kind=meaningful_moment_kind,
        recent_thread_available=bool(history_text),
        memory_query=memory_query,
        reasons=tuple(reasons),
        turn_intent=intent,
        response_shape=response_shape,
        quality_signals=quality_signals,
        unresolved_threads=unresolved_threads,
        callbacks=callbacks,
        topic_transition=topic_transition,
        correction_handling=correction_handling,
        personality_expression=personality_expression,
    )


def should_analyze_chat_action(
    user_message: str,
    conversation_history: Iterable[Mapping[str, Any]] = (),
) -> bool:
    from release_self_knowledge import is_grouped_release_inspection
    if is_grouped_release_inspection(user_message):
        return True
    return classify_conversation_quality(user_message, conversation_history).should_analyze_action


def assistant_response_has_unsolicited_operational_content(
    assistant_response: Any,
    *,
    user_message: Any = "",
) -> bool:
    """Detect old off-topic work narration without classifying broad technical words."""
    if _contains_explicit_operator_request(_normalized_text(user_message)):
        return False
    response = _normalized_text(assistant_response)
    return bool(response and any(pattern.search(response) for pattern in _UNSOLICITED_OPERATIONAL_RESPONSE_PATTERNS))


def general_memory_is_operational(memory: Mapping[str, Any]) -> bool:
    memory_type = str(memory.get("type") or "").strip().lower()
    if memory_type in _OPERATIONAL_MEMORY_TYPES:
        return True
    content = _normalized_text(memory.get("content") or memory.get("thought") or memory.get("summary"))
    return bool(content and any(pattern.search(content) for pattern in _UNSOLICITED_OPERATIONAL_RESPONSE_PATTERNS))


def general_memory_is_conversation_eligible(memory: Mapping[str, Any]) -> bool:
    if not isinstance(memory, Mapping):
        return False
    if memory.get("use_in_conversation") is False or memory.get("conversation_eligible") is False:
        return False
    status = str(memory.get("status") or "").strip().lower()
    if status in _EXCLUDED_MEMORY_STATUSES:
        return False
    privacy = str(memory.get("privacy") or memory.get("sensitivity") or "").strip().lower()
    if privacy in _EXCLUDED_MEMORY_PRIVACY or memory.get("sensitive") is True:
        return False
    memory_type = str(memory.get("type") or "memory").strip().lower()
    if memory.get("use_in_conversation") is True or memory.get("conversation_eligible") is True:
        return bool(_normalized_text(memory.get("content") or memory.get("thought") or memory.get("summary")))
    if memory_type.startswith(_INTERNAL_MEMORY_PREFIXES):
        return False
    return memory_type in _ALLOWED_GENERAL_MEMORY_TYPES


def filter_general_conversation_memories(memories: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(memory) for memory in memories if general_memory_is_conversation_eligible(memory)]


def normalized_content_fingerprint(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _normalized_text(value).lower()).strip()


def memory_duplicates_recent_history(memory_text: str, recent_history_text: str) -> bool:
    memory_fingerprint = normalized_content_fingerprint(memory_text)
    history_fingerprint = normalized_content_fingerprint(recent_history_text)
    if not memory_fingerprint or not history_fingerprint:
        return False
    if memory_fingerprint in history_fingerprint:
        return True
    memory_words = set(memory_fingerprint.split())
    history_words = set(history_fingerprint.split())
    if len(memory_words) < 5:
        return False
    return len(memory_words & history_words) / max(1, len(memory_words)) >= 0.8
