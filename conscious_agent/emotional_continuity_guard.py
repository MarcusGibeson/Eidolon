from __future__ import annotations

"""Read-only guard against mood accumulation and unsupported affection inflation."""

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


EMOTIONAL_CONTINUITY_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class EmotionalContinuityGuard:
    interaction_lane: str
    explicit_current_mood_count: int
    open_important_moment_count: int
    explicit_relationship_cue_count: int
    single_current_mood_only: bool
    old_moods_do_not_accumulate: bool
    user_led_warmth_allowed: bool
    affection_escalation_allowed: bool
    new_relationship_progress_claim_allowed: bool
    writes_state: bool = False
    mutates_personality: bool = False
    infers_user_feelings: bool = False
    schema_version: str = EMOTIONAL_CONTINUITY_SCHEMA_VERSION

    def to_prompt_lines(self) -> list[str]:
        return [
            "EMOTIONAL CONTINUITY WITHOUT INFLATION",
            "Treat the one current explicit user mood as temporary context, not a permanent trait; older and cleared moods do not accumulate.",
            "Acknowledge relevant open important moments gently, without dramatizing them, repeatedly steering back to them, or treating them as proof of deeper attachment.",
            "Warmth may follow the user's current tone, but do not exceed it with unsupported affection, dependence, exclusivity, possessiveness, or claims of new relationship progress.",
            "Existing explicit relationship cues may inform wording when directly relevant; they never authorize inventing feelings or announcing a milestone that was not explicitly curated.",
        ]

    def public_summary(self) -> dict[str, Any]:
        return {**asdict(self), "contains_cue_content": False, "claims_sentience": False}

    def receipt_metrics(self) -> dict[str, Any]:
        return self.public_summary()


def build_emotional_continuity_guard(
    memories: Iterable[Mapping[str, Any]],
    *,
    interaction_lane: str = "ordinary",
) -> EmotionalContinuityGuard:
    current_moods = 0
    open_moments = 0
    relationship_cues = 0
    for memory in memories:
        if not isinstance(memory, Mapping):
            continue
        if memory.get("relationship_eligible") is not True and memory.get("use_in_conversation") is not True:
            continue
        status = str(memory.get("status") or "active").strip().lower()
        if status in {"retracted", "deleted", "rejected", "expired", "stale", "blocked"}:
            continue
        kind = str(memory.get("type") or "").strip().lower()
        if kind in {"user_mood", "mood"}:
            state = str(memory.get("mood_state") or memory.get("temporal_state") or "current").strip().lower()
            if state == "current":
                current_moods += 1
        elif kind in {"important_moment", "shared_moment"}:
            state = str(memory.get("moment_state") or memory.get("temporal_state") or "open").strip().lower()
            if state not in {"resolved", "closed", "complete", "completed", "dismissed"}:
                open_moments += 1
        elif kind in {"relationship", "relationship_memory", "commitment"}:
            relationship_cues += 1

    lane = str(interaction_lane or "ordinary").strip().lower() or "ordinary"
    return EmotionalContinuityGuard(
        interaction_lane=lane,
        explicit_current_mood_count=min(1, current_moods),
        open_important_moment_count=open_moments,
        explicit_relationship_cue_count=relationship_cues,
        single_current_mood_only=True,
        old_moods_do_not_accumulate=True,
        user_led_warmth_allowed=lane in {"relational", "mixed"},
        affection_escalation_allowed=False,
        new_relationship_progress_claim_allowed=False,
    )
