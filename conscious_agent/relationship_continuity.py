from __future__ import annotations

"""Provider-neutral relationship continuity derived from explicit durable state.

This module reads already-stored durable memories and Eidolon's current self-state.
It does not infer facts from raw conversation transcripts, promote memories, mutate
personality, write runtime state, or contact a model/provider.
"""

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from mood_moment_continuity import (
    MoodMomentContinuitySnapshot,
    build_mood_moment_continuity_snapshot,
)
from relationship_personality_continuity import RelationshipPersonalityContinuityProfile
from emotional_continuity_guard import EmotionalContinuityGuard, build_emotional_continuity_guard


RELATIONSHIP_CONTINUITY_SCHEMA_VERSION = "1"
MAX_RELATIONSHIP_CUES = 8
MAX_CUES_PER_CATEGORY = 2
MAX_CUE_CHARACTERS = 220

RELATIONSHIP_MEMORY_CATEGORIES: dict[str, str] = {
    "nickname": "nickname",
    "preferred_name": "nickname",
    "user_nickname": "nickname",
    "preference": "preference",
    "user_preference": "preference",
    "relationship": "relationship",
    "relationship_memory": "relationship",
    "important_moment": "important_moment",
    "shared_moment": "important_moment",
    "commitment": "commitment",
    "personal_fact": "personal_fact",
    "user_mood": "user_mood",
    "mood": "user_mood",
}

_CATEGORY_LABELS = {
    "nickname": "Preferred name or nickname",
    "preference": "Established preference",
    "relationship": "Relationship continuity",
    "important_moment": "Important shared moment",
    "commitment": "Established commitment",
    "personal_fact": "Relevant personal fact",
    "user_mood": "Explicitly stored user mood",
}

_EXCLUDED_STATUSES = {"rejected", "retracted", "stale", "expired", "deleted", "blocked"}
_EXCLUDED_PRIVACY = {"sensitive", "secret", "restricted"}
_RELEVANCE_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "our", "are", "was", "were", "have", "has", "had", "please", "keep", "about",
}


@dataclass(frozen=True)
class RelationshipCue:
    category: str
    label: str
    text: str
    importance: int
    relevance: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelationshipContinuitySnapshot:
    cues: tuple[RelationshipCue, ...]
    cue_candidates: int
    cue_duplicates_omitted: int
    cue_limit_omitted: int
    mood_label: str
    energy_band: str
    focus_band: str
    mood_moment: MoodMomentContinuitySnapshot
    emotional_guard: EmotionalContinuityGuard
    interaction_lane: str = "ordinary"
    relationship_cues_suppressed: int = 0
    singleton_conflicts_omitted: int = 0
    personality_guard_active: bool = True
    schema_version: str = RELATIONSHIP_CONTINUITY_SCHEMA_VERSION

    @property
    def cue_count(self) -> int:
        return len(self.cues) + self.mood_moment.cue_count

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys([*(cue.category for cue in self.cues), *self.mood_moment.categories]))

    def to_prompt_block(self) -> str:
        lines = [
            "RELATIONSHIP CONTINUITY",
            "Use only these explicitly stored continuity cues, and only when relevant to the latest message.",
            "Do not mention memory machinery, invent relationship progress, infer unstated feelings, or force a nickname.",
        ]
        for cue in self.cues:
            lines.append(f"- {cue.label}: {cue.text}")
        lines.extend(self.mood_moment.to_prompt_lines())
        lines.extend(self.emotional_guard.to_prompt_lines())
        return "\n".join(lines)

    def public_summary(self, *, include_cues: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "cue_count": self.cue_count,
            "categories": list(self.categories),
            "mood_label": self.mood_label,
            "energy_band": self.energy_band,
            "focus_band": self.focus_band,
            "inferred_from_transcript": False,
            "writes_memory": False,
            "mutates_personality": False,
            "interaction_lane": self.interaction_lane,
            "relationship_cues_suppressed": self.relationship_cues_suppressed,
            "singleton_conflicts_omitted": self.singleton_conflicts_omitted,
            "personality_guard_active": self.personality_guard_active,
            "emotional_guard": self.emotional_guard.receipt_metrics(),
        }
        result["mood_moment"] = self.mood_moment.public_summary(include_content=include_cues)
        result["emotional_guard"] = self.emotional_guard.public_summary()
        if include_cues:
            cues = [cue.to_dict() for cue in self.cues]
            if self.mood_moment.user_mood is not None:
                mood = self.mood_moment.user_mood.to_dict()
                mood["label"] = "Current explicit user mood"
                cues.append(mood)
            for moment in self.mood_moment.important_moments:
                row = moment.to_dict()
                row["label"] = "Open important moment"
                cues.append(row)
            result["cues"] = cues
        return result

    def receipt_metrics(self, *, included: bool) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "cue_candidates": self.cue_candidates,
            "cue_count": self.cue_count if included else 0,
            "cues_omitted": self.cue_candidates - (self.cue_count if included else 0),
            "categories": list(self.categories) if included else [],
            "mood_included": bool(included),
            "temporal_continuity": self.mood_moment.receipt_metrics(included=included),
            "contains_cue_content": False,
            "inferred_from_transcript": False,
            "interaction_lane": self.interaction_lane,
            "relationship_cues_suppressed": self.relationship_cues_suppressed if included else 0,
            "singleton_conflicts_omitted": self.singleton_conflicts_omitted,
            "personality_guard_active": self.personality_guard_active,
            "emotional_guard": self.emotional_guard.receipt_metrics(),
        }


def relationship_memory_type(memory: dict[str, Any]) -> str:
    return RELATIONSHIP_MEMORY_CATEGORIES.get(str(memory.get("type") or "").strip().lower(), "")


def is_relationship_memory(memory: dict[str, Any]) -> bool:
    return bool(relationship_memory_type(memory))


def _memory_text(memory: dict[str, Any]) -> str:
    value = memory.get("content")
    if value in {None, ""}:
        value = memory.get("thought")
    if value in {None, ""}:
        value = memory.get("summary")
    text = " ".join(str(value or "").split())
    if len(text) > MAX_CUE_CHARACTERS:
        text = text[: MAX_CUE_CHARACTERS - 1].rstrip() + "â€¦"
    return text


def _importance(memory: dict[str, Any]) -> int:
    value = memory.get("importance")
    if isinstance(value, (int, float)):
        if value >= 0.8:
            return 3
        if value >= 0.5:
            return 2
        return 1
    lowered = str(value or "").strip().lower()
    if lowered in {"critical", "core", "high", "important"}:
        return 3
    if lowered in {"medium", "normal"}:
        return 2
    return 1


def _normalize_word(word: str) -> str:
    value = word.lower().strip()
    if len(value) > 4 and value.endswith("s") and not value.endswith("ss"):
        value = value[:-1]
    return value


def _words(text: str) -> set[str]:
    current: list[str] = []
    result: set[str] = set()
    for char in str(text or "").lower():
        if char.isalnum():
            current.append(char)
        elif current:
            word = _normalize_word("".join(current))
            if len(word) >= 3 and word not in _RELEVANCE_STOPWORDS:
                result.add(word)
            current = []
    if current:
        word = _normalize_word("".join(current))
        if len(word) >= 3 and word not in _RELEVANCE_STOPWORDS:
            result.add(word)
    return result


def _relevance(text: str, user_message: str, category: str = "") -> int:
    query = _words(user_message)
    if not query:
        return 0
    score = len(query & _words(text))
    category_words = _words(category.replace("_", " "))
    if query & category_words:
        score += 1
    return score


def _eligible(memory: dict[str, Any]) -> bool:
    if not isinstance(memory, dict) or not is_relationship_memory(memory):
        return False
    if memory.get("relationship_eligible") is False or memory.get("use_in_conversation") is False:
        return False
    if memory.get("relationship_eligible") is not True and memory.get("use_in_conversation") is not True:
        return False
    if str(memory.get("status") or "").strip().lower() in _EXCLUDED_STATUSES:
        return False
    privacy = str(memory.get("privacy") or memory.get("sensitivity") or "").strip().lower()
    if privacy in _EXCLUDED_PRIVACY or memory.get("sensitive") is True:
        return False
    return bool(_memory_text(memory))


def _band(value: Any, *, default: str = "steady") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number >= 0.75:
        return "high"
    if number >= 0.4:
        return "steady"
    return "low"


def build_relationship_continuity_snapshot(
    memories: Iterable[dict[str, Any]],
    self_model: dict[str, Any],
    *,
    user_message: str = "",
    max_cues: int = MAX_RELATIONSHIP_CUES,
    interaction_profile: RelationshipPersonalityContinuityProfile | None = None,
) -> RelationshipContinuitySnapshot:
    """Build a bounded continuity snapshot without reading or writing session transcripts."""
    memory_rows = [memory for memory in memories if isinstance(memory, dict)]
    full_mood_moment = build_mood_moment_continuity_snapshot(
        memory_rows, self_model, user_message=user_message,
    )
    cues_allowed = interaction_profile is None or interaction_profile.relationship_cues_allowed
    interaction_lane = str(getattr(interaction_profile, "lane", "ordinary") or "ordinary")
    singleton_conflicts_omitted = int(full_mood_moment.current_mood_conflicts_omitted or 0)

    eligible_rows: list[tuple[int, dict[str, Any], str]] = []
    nickname_rows: list[tuple[int, dict[str, Any], str]] = []
    for index, memory in enumerate(memory_rows):
        if not _eligible(memory):
            continue
        category = relationship_memory_type(memory)
        row = (index, memory, category)
        if category == "nickname":
            nickname_rows.append(row)
        else:
            eligible_rows.append(row)
    if nickname_rows:
        nickname_rows.sort(
            key=lambda row: (str(row[1].get("updated_at") or row[1].get("created_at") or ""), row[0]),
            reverse=True,
        )
        eligible_rows.append(nickname_rows[0])
        singleton_conflicts_omitted += max(0, len(nickname_rows) - 1)

    if cues_allowed:
        mood_moment = full_mood_moment
    else:
        mood_moment = MoodMomentContinuitySnapshot(
            user_mood=None,
            important_moments=(),
            mood_candidates=full_mood_moment.mood_candidates,
            stale_moods_omitted=full_mood_moment.stale_moods_omitted,
            current_mood_conflicts_omitted=full_mood_moment.current_mood_conflicts_omitted,
            moment_candidates=full_mood_moment.moment_candidates,
            resolved_moments_omitted=full_mood_moment.resolved_moments_omitted,
            moment_limit_omitted=full_mood_moment.moment_limit_omitted,
            eidolon_mood_label=full_mood_moment.eidolon_mood_label,
            eidolon_energy_band=full_mood_moment.eidolon_energy_band,
            eidolon_focus_band=full_mood_moment.eidolon_focus_band,
        )

    candidates: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for index, memory, category in eligible_rows:
        if category in {"important_moment", "user_mood"}:
            continue
        text = _memory_text(memory)
        category_priority = {
            "nickname": 6,
            "preference": 5,
            "relationship": 5,
            "commitment": 4,
            "important_moment": 4,
            "personal_fact": 3,
            "user_mood": 2,
        }.get(category, 1)
        candidates.append((
            _relevance(text, user_message, category),
            _importance(memory),
            category_priority,
            str(memory.get("created_at") or ""),
            {"memory": memory, "category": category, "text": text, "index": index},
        ))

    candidates.sort(key=lambda row: (row[0], row[1], row[2], row[3], -row[4]["index"]), reverse=True)
    non_temporal_candidate_count = len(candidates)
    relationship_cues_suppressed = 0
    if not cues_allowed:
        relationship_cues_suppressed = non_temporal_candidate_count + full_mood_moment.cue_count
        candidates = []
    seen_text: set[str] = set()
    category_counts: dict[str, int] = {}
    cues: list[RelationshipCue] = []
    duplicates_omitted = 0
    limit_omitted = 0
    limit = max(0, min(MAX_RELATIONSHIP_CUES, int(max_cues)))

    for relevance, importance, _priority, created_at, payload in candidates:
        category = payload["category"]
        text = payload["text"]
        fingerprint = " ".join(text.lower().split())
        if fingerprint in seen_text:
            duplicates_omitted += 1
            continue
        if category_counts.get(category, 0) >= MAX_CUES_PER_CATEGORY or len(cues) >= limit:
            limit_omitted += 1
            continue
        seen_text.add(fingerprint)
        category_counts[category] = category_counts.get(category, 0) + 1
        cues.append(RelationshipCue(
            category=category,
            label=_CATEGORY_LABELS[category],
            text=text,
            importance=importance,
            relevance=relevance,
            created_at=created_at,
        ))

    emotional_guard = build_emotional_continuity_guard(memory_rows, interaction_lane=interaction_lane)

    return RelationshipContinuitySnapshot(
        cues=tuple(cues),
        cue_candidates=non_temporal_candidate_count + full_mood_moment.mood_candidates + full_mood_moment.moment_candidates,
        cue_duplicates_omitted=duplicates_omitted,
        cue_limit_omitted=(
            limit_omitted
            + mood_moment.stale_moods_omitted
            + mood_moment.resolved_moments_omitted
            + mood_moment.moment_limit_omitted
        ),
        mood_label=mood_moment.eidolon_mood_label,
        energy_band=mood_moment.eidolon_energy_band,
        focus_band=mood_moment.eidolon_focus_band,
        mood_moment=mood_moment,
        emotional_guard=emotional_guard,
        interaction_lane=interaction_lane,
        relationship_cues_suppressed=relationship_cues_suppressed,
        singleton_conflicts_omitted=singleton_conflicts_omitted,
        personality_guard_active=True,
    )



# v1436 roadmap adapter. The established runtime API above remains authoritative.
VERSION = "1436.9"
TITLE = "Relationship Continuity"
PHASE = "unified_conversation_action_companion"
IMPLEMENTATION = "unified_companion_developer.update_relationship_continuity"


def evaluate(*args: Any, **kwargs: Any):
    from unified_companion_developer import update_relationship_continuity

    kwargs.setdefault("version", VERSION)
    return update_relationship_continuity(*args, **kwargs)


def inspect(project_state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = dict(project_state or {})
    row = dict(state.get("relationship_continuity") or {})
    return {
        "active": True,
        "ok": bool(row),
        "status": "relationship_continuity_found" if row else "relationship_continuity_missing",
        "record": row,
        "action_executed": False,
        "source_mutation_authorized": False,
        "project_mutation_authorized": False,
        "release_authorized": False,
        "independent_authority_granted": False,
    }

