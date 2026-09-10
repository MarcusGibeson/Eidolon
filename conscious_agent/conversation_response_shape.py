from __future__ import annotations

"""Deterministic v1084.2 response length and depth matching."""

import re
from dataclasses import asdict, dataclass
from typing import Any

from conversation_turn_intent import TurnIntentProfile

RESPONSE_SHAPE_SCHEMA_VERSION = "1"

_BRIEF = re.compile(r"\b(?:briefly|short answer|keep it short|be concise|concise answer|in one sentence|quick answer|just the answer)\b", re.I)
_DETAILED = re.compile(r"\b(?:in detail|detailed|thorough|comprehensive|deep dive|go deep|explain fully|step[- ]by[- ]step|walk me through|all the details)\b", re.I)
_STRUCTURE = re.compile(r"\b(?:compare|options|pros and cons|steps|roadmap|plan|checklist|break(?: it)? down|list)\b", re.I)


@dataclass(frozen=True)
class ResponseShapeProfile:
    length_mode: str
    depth_mode: str
    target_min_words: int
    target_max_words: int
    structured: bool
    explicit_length_cue: bool
    reasons: tuple[str, ...]
    mutates_personality: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    schema_version: str = RESPONSE_SHAPE_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return {**asdict(self), "contains_message_content": False}

    def prompt_lines(self) -> list[str]:
        lines = [
            "RESPONSE LENGTH AND DEPTH",
            f"Use a {self.length_mode} response with {self.depth_mode.replace('_', ' ')} depth, roughly {self.target_min_words}-{self.target_max_words} words when suitable.",
            "This temporary response-shape instruction applies only to the current request and does not modify personality or future defaults.",
        ]
        if self.structured:
            lines.append("Use light structure only when it improves scanning.")
        else:
            lines.append("Prefer natural prose without decorative headings or lists.")
        return lines


def classify_response_shape(message: str, intent: TurnIntentProfile, *, short_follow_up: bool = False) -> ResponseShapeProfile:
    text = " ".join(str(message or "").split())
    words = re.findall(r"[A-Za-z0-9']+", text)
    count = len(words)
    brief = bool(_BRIEF.search(text))
    detailed = bool(_DETAILED.search(text))
    structured = bool(_STRUCTURE.search(text)) or intent.question_count >= 3
    reasons: list[str] = []

    if brief:
        mode, depth, low, high = "brief", "answer_only", 10, 80
        reasons.append("explicit_brief_cue")
    elif detailed:
        mode, depth, low, high = "deep", "structured", 160, 500
        structured = True
        reasons.append("explicit_detail_cue")
    elif intent.primary_intent in {"greeting", "affectionate_play"}:
        mode, depth, low, high = "brief", "light_explanation", 8, 70
        reasons.append("light_conversation")
    elif short_follow_up:
        mode, depth, low, high = "concise", "light_explanation", 20, 120
        reasons.append("short_follow_up")
    elif intent.primary_intent == "correction":
        mode, depth, low, high = "concise", "answer_only", 20, 120
        reasons.append("explicit_correction")
    elif intent.primary_intent == "emotional_sharing" and not intent.explicit_request:
        mode, depth, low, high = "balanced", "light_explanation", 35, 180
        reasons.append("emotional_presence")
    elif intent.primary_intent == "brainstorming":
        mode, depth, low, high = "detailed", "structured", 100, 360
        structured = True
        reasons.append("brainstorming")
    elif intent.primary_intent == "project_instruction" or count >= 80 or intent.question_count >= 3:
        mode, depth, low, high = "detailed", "structured", 120, 420
        structured = True
        reasons.append("complex_or_operator_turn")
    elif intent.primary_intent == "question" and count <= 24:
        mode, depth, low, high = "concise", "reasoned", 30, 160
        reasons.append("focused_question")
    elif intent.primary_intent == "casual_remark" and count <= 18:
        mode, depth, low, high = "concise", "light_explanation", 15, 110
        reasons.append("short_casual_turn")
    else:
        mode, depth, low, high = "balanced", "reasoned", 50, 240
        reasons.append("default_balanced")

    return ResponseShapeProfile(
        length_mode=mode,
        depth_mode=depth,
        target_min_words=low,
        target_max_words=high,
        structured=structured,
        explicit_length_cue=brief or detailed,
        reasons=tuple(reasons),
    )
