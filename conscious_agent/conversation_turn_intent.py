from __future__ import annotations

"""Deterministic v1084.1 turn-intent alignment.

The classifier reads only the current message and bounded flags supplied by the
conversation quality layer. It performs no provider calls, writes no state, and
never treats an ordinary ambiguous sentence as a correction or operator action.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any

TURN_INTENT_SCHEMA_VERSION = "1"

_CORRECTION_PATTERNS = (
    re.compile(r"^(?:no[,;:]\s+|actually[,;:]?\s+|correction\s*[:,-]\s*)", re.I),
    re.compile(r"\b(?:i meant|what i meant was|that(?:'s| is) not (?:right|correct)|you (?:got|have) (?:that|it) wrong|please correct that)\b", re.I),
    re.compile(r"\bnot\s+[^,.!?]{1,60}\b(?:but|rather)\b", re.I),
)
_BRAINSTORM_PATTERNS = (
    re.compile(r"\bbrainstorm\b", re.I),
    re.compile(r"\b(?:give me|suggest|explore|think through)\s+(?:some\s+)?(?:ideas|options|approaches|possibilities)\b", re.I),
    re.compile(r"\bwhat if (?:we|i)\b", re.I),
)
_REQUEST_PATTERNS = (
    re.compile(r"^(?:please\s+)?(?:help|explain|show|tell|give|write|draft|make|create|compare|review|summarize|outline|list|find|check|continue|start|build|implement|add|fix|update)\b", re.I),
    re.compile(r"\b(?:can|could|would|will) you\b", re.I),
    re.compile(r"\bi (?:want|need|would like) you to\b", re.I),
)
_QUESTION_START = re.compile(r"^(?:what|why|how|who|when|where|which|do|does|did|is|are|am|can|could|would|should|will|have|has)\b", re.I)


@dataclass(frozen=True)
class TurnIntentProfile:
    primary_intent: str
    flags: tuple[str, ...]
    question_count: int
    explicit_correction: bool
    explicit_brainstorming: bool
    explicit_request: bool
    project_instruction: bool
    emotional_sharing: bool
    ambiguous_correction_inferred: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    schema_version: str = TURN_INTENT_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return {**asdict(self), "contains_message_content": False}

    def prompt_lines(self) -> list[str]:
        guidance = {
            "project_instruction": "Address the explicit supervised project instruction directly while preserving approval and release boundaries.",
            "correction": "Acknowledge the explicit correction once, use the corrected meaning, and do not repeat or defend the stale claim.",
            "brainstorming": "Offer distinct useful possibilities before converging; do not present ideas as completed actions.",
            "emotional_sharing": "Respond first to the specific feeling; do not manufacture a task.",
            "request": "Fulfill the concrete request directly and state real limitations briefly.",
            "question": "Answer the actual question before optional context.",
            "greeting": "Return a natural greeting, not an intake form or status report.",
            "affectionate_play": "Match playfulness without inventing exclusivity, dependence, or relationship progress.",
            "casual_remark": "Respond as conversation; do not manufacture a task, diagnosis, or project transition.",
        }
        lines = ["TURN INTENT ALIGNMENT", guidance.get(self.primary_intent, guidance["casual_remark"])]
        if self.question_count > 1:
            lines.append("Multiple questions are present; cover each without silently dropping one.")
        if self.emotional_sharing and self.primary_intent != "emotional_sharing":
            lines.append("Also acknowledge the emotional context.")
        return lines


def classify_turn_intent(
    message: str,
    *,
    explicit_operator_request: bool = False,
    greeting: bool = False,
    emotional: bool = False,
    flirting: bool = False,
) -> TurnIntentProfile:
    text = " ".join(str(message or "").split())
    question_count = text.count("?")
    if question_count == 0 and _QUESTION_START.search(text):
        question_count = 1
    correction = bool(text and any(pattern.search(text) for pattern in _CORRECTION_PATTERNS))
    brainstorming = bool(text and any(pattern.search(text) for pattern in _BRAINSTORM_PATTERNS))
    request = bool(text and any(pattern.search(text) for pattern in _REQUEST_PATTERNS))

    flags: list[str] = []
    if explicit_operator_request:
        flags.append("project_instruction")
    if correction:
        flags.append("correction")
    if brainstorming:
        flags.append("brainstorming")
    if emotional:
        flags.append("emotional_sharing")
    if request:
        flags.append("request")
    if question_count:
        flags.append("question")
    if greeting:
        flags.append("greeting")
    if flirting:
        flags.append("affectionate_play")
    if not flags:
        flags.append("casual_remark")

    if explicit_operator_request:
        primary = "project_instruction"
    elif correction:
        primary = "correction"
    elif brainstorming:
        primary = "brainstorming"
    elif emotional:
        primary = "emotional_sharing"
    elif request:
        primary = "request"
    elif question_count:
        primary = "question"
    elif greeting:
        primary = "greeting"
    elif flirting:
        primary = "affectionate_play"
    else:
        primary = "casual_remark"

    return TurnIntentProfile(
        primary_intent=primary,
        flags=tuple(dict.fromkeys(flags)),
        question_count=question_count,
        explicit_correction=correction,
        explicit_brainstorming=brainstorming,
        explicit_request=request,
        project_instruction=explicit_operator_request,
        emotional_sharing=emotional,
    )
