from __future__ import annotations

"""Provider-neutral v1102 natural-conversation prompt foundations.

The profiles in this module consolidate already-established identity, relationship,
greeting, intent, and topic evidence into bounded prompt guidance. They inspect only
the current message and completed history supplied by the caller. They do not contact
a provider, write memory, mutate personality, infer a hidden relationship, or grant
operator authority.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


NATURAL_CONVERSATION_FOUNDATION_SCHEMA_VERSION = "1"
MAX_FOUNDATION_HISTORY_ROWS = 12
MAX_OPENING_WORDS = 5

_GREETING_RE = re.compile(
    r"^(?:(?:hi|hello|hey|yo|howdy)(?:\s+again)?|good\s+(?:morning|afternoon|evening|night)(?:\s+again)?|what(?:'s| is) up|sup)[!,.? ]*$",
    re.I,
)
_SELF_INTRO_RE = re.compile(
    r"\b(?:i am|i'm)\s+(?:eidolon|an?\s+(?:ai|assistant|local ai|language model))\b|"
    r"\bmy name is\s+eidolon\b|\bas an ai\b",
    re.I,
)
_STOCK_OPENING_RE = re.compile(
    r"^(?:hi|hello|hey|of course|certainly|absolutely|sure|i understand|i'm sorry|"
    r"that sounds|it sounds|thanks for sharing|thank you for sharing)\b",
    re.I,
)
_DEICTIC_RE = re.compile(
    r"\b(?:this|that|it|they|them|those|these|there|then|the same|what you said|your idea|"
    r"that idea|that part|that approach|that problem|that feeling)\b",
    re.I,
)


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _assistant_text(row: Mapping[str, Any]) -> str:
    for key in ("assistant_response", "assistant", "response", "assistant_text"):
        text = _normalized(row.get(key))
        if text:
            return text
    return ""


def _user_text(row: Mapping[str, Any]) -> str:
    return _normalized(row.get("user_message") or row.get("user"))


def _opening_signature(text: str) -> str:
    normalized = _normalized(text).casefold()
    stock = _STOCK_OPENING_RE.match(normalized)
    if stock:
        return "stock:" + " ".join(re.findall(r"[a-z0-9']+", stock.group(0)))
    words = re.findall(r"[A-Za-z0-9']+", normalized)[:MAX_OPENING_WORDS]
    return " ".join(words)


def _bounded_history(history: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in history if isinstance(row, Mapping)][-MAX_FOUNDATION_HISTORY_ROWS:]


@dataclass(frozen=True)
class IdentityRelationshipPromptProfile:
    configured_name: str
    interaction_lane: str
    history_available: bool
    relationship_cue_count: int
    relationship_cues_allowed: bool
    self_introduction_allowed: bool
    identity_reset_allowed: bool = False
    invented_relationship_progress_allowed: bool = False
    transcript_inference_allowed: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    schema_version: str = NATURAL_CONVERSATION_FOUNDATION_SCHEMA_VERSION

    def prompt_block(self) -> str:
        name = self.configured_name or "Eidolon"
        lines = [
            "IDENTITY AND RELATIONSHIP FOUNDATION",
            f"Speak as {name}, the same configured local AI companion across turns, reloads, and provider recovery.",
            "Treat identity as continuity, not as a reason to narrate system architecture or repeatedly explain what you are.",
            "Do not claim human embodiment, proven consciousness, hidden feelings, dependence, exclusivity, or relationship progress.",
            "Use only explicit stored relationship cues that are relevant to the latest message; never infer durable relationship facts from transcript tone.",
        ]
        if self.history_available:
            lines.append("Conversation history exists. Do not reintroduce yourself or reset the relationship unless the user explicitly asks who you are.")
        elif self.self_introduction_allowed:
            lines.append("This may be a first conversation. A name-level introduction is allowed only when it naturally answers the user, not as a mandatory opening.")
        if self.interaction_lane == "operator":
            lines.append("This turn is operator work. Keep identity present but suppress personal relationship cues and emotional progress language.")
        elif self.interaction_lane == "mixed":
            lines.append("Keep personal conversation and governed operator work distinct; neither lane may rewrite the other.")
        elif self.interaction_lane == "relational":
            lines.append("The user led a relational turn. Respond warmly and specifically without escalating intimacy or forcing stored cues into the reply.")
        else:
            lines.append("This is ordinary conversation. Let personality show through natural wording rather than identity declarations.")
        return "\n".join(lines)

    def compact_prompt_block(self) -> str:
        name = self.configured_name or "Eidolon"
        lane = (
            "Suppress relationship cues for operator work."
            if self.interaction_lane == "operator"
            else "Use only explicit relevant relationship cues; do not invent intimacy, dependence, exclusivity, or progress."
        )
        introduction = (
            "Do not reintroduce yourself unless asked."
            if self.history_available
            else "A brief name-level introduction is optional only when naturally relevant."
        )
        return "\n".join((
            "IDENTITY AND RELATIONSHIP FOUNDATION",
            f"Speak as {name}, the same configured local AI companion. {introduction}",
            f"Do not claim human embodiment or proven consciousness. {lane}",
        ))

    def public_summary(self) -> dict[str, Any]:
        return {**asdict(self), "contains_message_content": False}


@dataclass(frozen=True)
class GreetingRepetitionProfile:
    greeting_kind: str
    history_rows_considered: int
    assistant_rows_considered: int
    recent_greeting_openings: int
    repeated_opening_runs: int
    recent_self_introductions: int
    suppress_new_greeting: bool
    suppress_self_introduction: bool
    variation_required: bool
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = NATURAL_CONVERSATION_FOUNDATION_SCHEMA_VERSION

    def prompt_lines(self) -> list[str]:
        lines = ["GREETING AND REPETITION CONTROL"]
        if self.greeting_kind == "first_greeting":
            lines.append("Reply with one brief natural greeting. Do not turn it into an intake form, capabilities menu, status report, or compulsory self-introduction.")
        elif self.greeting_kind == "returning_greeting":
            lines.append("Acknowledge the greeting briefly as an ongoing conversation. Do not reintroduce yourself, restate the relationship, or ask a generic intake question.")
        elif self.greeting_kind == "repeated_greeting":
            lines.append("The greeting is repeated within an active conversation. Respond lightly without repeating the same greeting formula or resetting the exchange.")
        else:
            lines.append("The latest message is not a greeting. Start with its substance rather than adding a fresh hello or ceremonial preamble.")
        if self.suppress_self_introduction:
            lines.append("Do not say who or what you are unless the user explicitly asked.")
        if self.variation_required:
            lines.append("Recent replies share stock or repeated openings. Use a different opening structure while preserving the configured voice.")
        return lines

    def compact_prompt_lines(self) -> list[str]:
        if self.greeting_kind == "first_greeting":
            action = "Use one brief natural greeting without an intake form or mandatory self-introduction."
        elif self.greeting_kind in {"returning_greeting", "repeated_greeting"}:
            action = "Acknowledge briefly without resetting the exchange or repeating the same greeting formula."
        else:
            action = "Start with the message's substance; add no fresh greeting or ceremonial preamble."
        if self.variation_required:
            action += " Vary any recent stock opening."
        return ["GREETING AND REPETITION CONTROL", action]

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentTopicContinuityProfile:
    primary_intent: str
    topic_transition: str
    thread_mode: str
    matched_turn_offset: int | None
    deictic_follow_up: bool
    current_turn_primary: bool
    prior_thread_preserved: bool
    unrelated_thread_merge_allowed: bool = False
    recap_required: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = NATURAL_CONVERSATION_FOUNDATION_SCHEMA_VERSION

    def prompt_lines(self) -> list[str]:
        guidance = {
            "fresh": "Treat the latest message as a fresh topic and answer it without importing unrelated prior material.",
            "active": "Continue the active thread directly. Resolve pronouns and shorthand from the latest complete exchange without recapping it.",
            "resumed": "Resume the matched earlier thread with only enough orientation to answer the latest message.",
            "shifted": "Follow the new topic and leave the prior thread behind unless the user returns to it.",
            "interrupted": "Answer the bounded side question while keeping the prior thread unfinished rather than falsely completing it.",
            "ambiguous": "Center the latest wording and state uncertainty briefly only when the intended thread cannot be resolved safely.",
        }
        lines = ["INTENT AND TOPIC CONTINUITY", guidance.get(self.thread_mode, guidance["ambiguous"])]
        lines.append("Honor the current turn's primary intent before callbacks, memories, optional advice, or operator context.")
        if self.deictic_follow_up:
            lines.append("The turn uses contextual shorthand. Resolve it from the nearest relevant completed exchange; do not ask the user to repeat information already present.")
        lines.append("Do not merge unrelated conversations, repeat the previous answer, or manufacture a topic transition.")
        return lines

    def compact_prompt_lines(self) -> list[str]:
        modes = {
            "fresh": "Answer as a fresh topic without unrelated prior material.",
            "active": "Continue the active thread directly without recapping it.",
            "resumed": "Resume the matched earlier thread with minimal orientation.",
            "shifted": "Follow the new topic and leave the prior thread behind.",
            "interrupted": "Answer the side question while preserving the unfinished thread.",
            "ambiguous": "Center the latest wording and state uncertainty only when necessary.",
        }
        lines = ["INTENT AND TOPIC CONTINUITY", modes.get(self.thread_mode, modes["ambiguous"])]
        if self.deictic_follow_up:
            lines.append("Resolve contextual shorthand from the nearest relevant completed exchange.")
        lines.append("Honor the current intent first; do not merge unrelated threads or repeat the prior answer.")
        return lines

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def build_identity_relationship_prompt_profile(
    self_model: Mapping[str, Any] | None,
    continuity_profile: Any,
    relationship_context: Any,
    conversation_history: Iterable[Mapping[str, Any]],
) -> IdentityRelationshipPromptProfile:
    rows = _bounded_history(conversation_history)
    name = _normalized((self_model or {}).get("name")) or "Eidolon"
    lane = _normalized(getattr(continuity_profile, "lane", "ordinary")).lower() or "ordinary"
    cues_allowed = bool(getattr(continuity_profile, "relationship_cues_allowed", lane != "operator"))
    cue_count = int(getattr(relationship_context, "cue_count", 0) or 0)
    return IdentityRelationshipPromptProfile(
        configured_name=name[:80],
        interaction_lane=lane,
        history_available=bool(rows),
        relationship_cue_count=max(0, cue_count),
        relationship_cues_allowed=cues_allowed,
        self_introduction_allowed=not bool(rows),
    )


def build_greeting_repetition_profile(
    user_message: str,
    conversation_history: Iterable[Mapping[str, Any]],
) -> GreetingRepetitionProfile:
    rows = _bounded_history(conversation_history)
    assistants = [_assistant_text(row) for row in rows]
    assistants = [text for text in assistants if text]
    openings = [_opening_signature(text) for text in assistants]
    greetings = sum(1 for text in assistants if _GREETING_RE.match(text) or _STOCK_OPENING_RE.match(text))
    introductions = sum(1 for text in assistants if _SELF_INTRO_RE.search(text))
    repeated_runs = 0
    run = 1
    for before, after in zip(openings, openings[1:]):
        if before and before == after:
            run += 1
            if run == 2:
                repeated_runs += 1
        else:
            run = 1
    current_greeting = bool(_GREETING_RE.fullmatch(_normalized(user_message)))
    previous_user_greeting = bool(rows and _GREETING_RE.fullmatch(_user_text(rows[-1])))
    if current_greeting and previous_user_greeting:
        kind = "repeated_greeting"
    elif current_greeting and rows:
        kind = "returning_greeting"
    elif current_greeting:
        kind = "first_greeting"
    else:
        kind = "none"
    variation = bool(repeated_runs or (assistants and _STOCK_OPENING_RE.match(assistants[-1])))
    return GreetingRepetitionProfile(
        greeting_kind=kind,
        history_rows_considered=len(rows),
        assistant_rows_considered=len(assistants),
        recent_greeting_openings=greetings,
        repeated_opening_runs=repeated_runs,
        recent_self_introductions=introductions,
        suppress_new_greeting=kind == "none" or kind in {"returning_greeting", "repeated_greeting"},
        suppress_self_introduction=bool(rows) or introductions > 0,
        variation_required=variation,
    )


def build_intent_topic_continuity_profile(
    user_message: str,
    quality: Any,
) -> IntentTopicContinuityProfile:
    intent = _normalized(getattr(getattr(quality, "turn_intent", None), "primary_intent", "casual_remark")) or "casual_remark"
    transition = getattr(quality, "topic_transition", None)
    kind = _normalized(getattr(transition, "transition_kind", "no_history")) or "no_history"
    matched = getattr(transition, "matched_turn_offset", None)
    deictic = bool(getattr(transition, "deictic_follow_up", False) or _DEICTIC_RE.search(_normalized(user_message)))
    thread_mode = {
        "no_history": "fresh",
        "continuation": "active",
        "resumption": "resumed",
        "return": "resumed",
        "topic_shift": "shifted",
        "interruption": "interrupted",
        "ambiguous_transition": "ambiguous",
    }.get(kind, "ambiguous")
    return IntentTopicContinuityProfile(
        primary_intent=intent,
        topic_transition=kind,
        thread_mode=thread_mode,
        matched_turn_offset=matched if isinstance(matched, int) else None,
        deictic_follow_up=deictic,
        current_turn_primary=True,
        prior_thread_preserved=bool(getattr(transition, "preserves_prior_thread", False)),
    )
