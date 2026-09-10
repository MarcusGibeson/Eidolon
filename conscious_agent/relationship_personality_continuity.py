from __future__ import annotations

"""Deterministic relationship/personality continuity policy for conversation turns.

The profile classifies only the interaction lane needed to keep operator work,
ordinary conversation, and user-led relational dialogue from bleeding into one
another. It performs no provider calls, transcript mining, memory promotion,
personality mutation, or runtime writes.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from conversation_quality import ConversationQualityProfile, classify_conversation_quality
from personality_stability import PersonalityStabilitySnapshot, build_personality_stability_snapshot


RELATIONSHIP_PERSONALITY_CONTINUITY_SCHEMA_VERSION = "1"
MAX_HISTORY_ROWS = 3

_RELATIONAL_PATTERNS = (
    re.compile(
        r"\b(?:remember when|we talked about|you remember|between us|our relationship|our friendship|"
        r"you and me|how do you feel about me|what do you think of me|do you care about me|"
        r"call me|my nickname|my preference|i prefer|i appreciate you|i trust you|i missed you|"
        r"i miss you|love you|like you|need comfort|need support|stay with me)\b",
        re.I,
    ),
    re.compile(r"\b(?:relationship|companionship|affection|nickname|shared moment|important moment)\b", re.I),
)


@dataclass(frozen=True)
class RelationshipPersonalityContinuityProfile:
    lane: str
    explicit_operator_request: bool
    operator_context_relevant: bool
    relational_signal: bool
    relationship_cues_allowed: bool
    relationship_memory_policy: str
    reasons: tuple[str, ...]
    personality_stability: PersonalityStabilitySnapshot | None = None
    schema_version: str = RELATIONSHIP_PERSONALITY_CONTINUITY_SCHEMA_VERSION

    @property
    def operator_only(self) -> bool:
        return self.lane == "operator"

    @property
    def mixed(self) -> bool:
        return self.lane == "mixed"

    def to_prompt_block(self) -> str:
        lines = [
            "PERSONALITY AND RELATIONSHIP CONTINUITY",
            f"Interaction lane: {self.lane}.",
            "Keep the same grounded conversational voice across reloads, conversation switches, retries, and provider recovery.",
            "Do not invent feelings, dependence, exclusivity, shared history, or relationship progress.",
            "Action success, failure, approval, maintenance, and project work never create affection or relationship progress.",
            "Automatic transcript memories are not relationship memories; durable relationship cues require explicit operator curation.",
        ]
        if self.personality_stability is not None:
            lines.extend(self.personality_stability.to_prompt_lines())
        if self.lane == "operator":
            lines.append(
                "This is operator-only context. Keep the reply conversational but do not use personal continuity cues or turn system work into emotional intimacy."
            )
        elif self.lane == "mixed":
            lines.append(
                "This message mixes personal conversation and operator work. Address the personal part naturally, keep governed action claims separate, and do not let either part rewrite the other."
            )
        elif self.lane == "relational":
            lines.append(
                "This is user-led relational or emotional conversation. Use relevant explicit cues gently without escalating intimacy, parroting facts, or forcing follow-up."
            )
        else:
            lines.append(
                "This is ordinary conversation. Stay consistent and natural; use explicit relationship cues only when they genuinely help the latest message."
            )
        return "\n".join(lines)

    def receipt_metrics(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "lane": self.lane,
            "explicit_operator_request": self.explicit_operator_request,
            "operator_context_relevant": self.operator_context_relevant,
            "relational_signal": self.relational_signal,
            "relationship_cues_allowed": self.relationship_cues_allowed,
            "relationship_memory_policy": self.relationship_memory_policy,
            "reasons": list(self.reasons),
            "contains_message_content": False,
            "writes_memory": False,
            "mutates_personality": False,
            "personality_stability": (self.personality_stability.receipt_metrics() if self.personality_stability is not None else {}),
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _has_relational_signal(text: str) -> bool:
    return bool(text and any(pattern.search(text) for pattern in _RELATIONAL_PATTERNS))


def _recent_relational_lane(history: Iterable[Mapping[str, Any]]) -> bool:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_HISTORY_ROWS:]
    for row in reversed(rows):
        lane = str(row.get("continuity_lane") or "").strip().lower()
        if lane in {"relational", "mixed"}:
            return True
        user = _normalized(row.get("user_message") or row.get("user"))
        if user:
            return _has_relational_signal(user)
    return False


def classify_relationship_personality_continuity(
    user_message: str,
    conversation_history: Iterable[Mapping[str, Any]] = (),
    *,
    quality: ConversationQualityProfile | None = None,
) -> RelationshipPersonalityContinuityProfile:
    """Classify one turn without persisting or inferring durable relationship facts."""
    history_rows = [row for row in conversation_history if isinstance(row, Mapping)]
    current_quality = quality or classify_conversation_quality(user_message, history_rows)
    message = _normalized(user_message)
    direct_relational = bool(
        current_quality.emotional
        or current_quality.flirting
        or _has_relational_signal(message)
    )
    inherited_relational = bool(
        current_quality.short_follow_up
        and not current_quality.explicit_operator_request
        and _recent_relational_lane(history_rows)
    )
    relational = direct_relational or inherited_relational
    operator = bool(current_quality.operator_context_relevant)

    if operator and relational:
        lane = "mixed"
    elif operator:
        lane = "operator"
    elif relational:
        lane = "relational"
    else:
        lane = "ordinary"

    reasons: list[str] = []
    if current_quality.explicit_operator_request:
        reasons.append("explicit_operator_request")
    elif current_quality.operator_context_relevant:
        reasons.append("operator_thread_continuation")
    if direct_relational:
        reasons.append("direct_relational_signal")
    elif inherited_relational:
        reasons.append("relational_thread_continuation")
    if not reasons:
        reasons.append("ordinary_conversation")

    stability = build_personality_stability_snapshot(history_rows)

    return RelationshipPersonalityContinuityProfile(
        lane=lane,
        explicit_operator_request=current_quality.explicit_operator_request,
        operator_context_relevant=current_quality.operator_context_relevant,
        relational_signal=relational,
        relationship_cues_allowed=lane != "operator",
        relationship_memory_policy=("operator_excluded" if lane == "operator" else "explicit_curation_only"),
        reasons=tuple(reasons),
        personality_stability=stability,
    )
