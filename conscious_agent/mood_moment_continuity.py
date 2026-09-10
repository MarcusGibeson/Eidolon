from __future__ import annotations

"""Temporal continuity for explicit mood records and important moments.

This module is provider-neutral and read-only. It uses only explicit durable
memories plus the existing self-model expression state. It never mines session
transcripts, promotes memories, changes personality, or writes runtime state.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


MOOD_MOMENT_SCHEMA_VERSION = "1"
DEFAULT_MOOD_FRESHNESS_HOURS = 72
MAX_IMPORTANT_MOMENTS = 3
MAX_TEMPORAL_CUE_CHARACTERS = 240

_MOOD_TYPES = {"user_mood", "mood"}
_MOMENT_TYPES = {"important_moment", "shared_moment"}
_EXCLUDED_STATUSES = {"rejected", "retracted", "stale", "expired", "deleted", "blocked"}
_EXCLUDED_PRIVACY = {"sensitive", "secret", "restricted"}
_RESOLVED_STATES = {"resolved", "closed", "complete", "completed", "dismissed"}
_CLEARED_MOOD_STATES = {"cleared", "resolved", "expired", "inactive"}
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "our", "are", "was", "were", "have", "has", "had", "about", "today", "feel",
}


@dataclass(frozen=True)
class TemporalContinuityCue:
    category: str
    text: str
    recorded_at: str
    freshness: str
    importance: int
    relevance: int
    continuity_state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MoodMomentContinuitySnapshot:
    user_mood: TemporalContinuityCue | None
    important_moments: tuple[TemporalContinuityCue, ...]
    mood_candidates: int
    stale_moods_omitted: int
    current_mood_conflicts_omitted: int
    moment_candidates: int
    resolved_moments_omitted: int
    moment_limit_omitted: int
    eidolon_mood_label: str
    eidolon_energy_band: str
    eidolon_focus_band: str
    schema_version: str = MOOD_MOMENT_SCHEMA_VERSION

    @property
    def cue_count(self) -> int:
        return (1 if self.user_mood is not None else 0) + len(self.important_moments)

    @property
    def categories(self) -> tuple[str, ...]:
        categories: list[str] = []
        if self.user_mood is not None:
            categories.append("user_mood")
        if self.important_moments:
            categories.append("important_moment")
        return tuple(categories)

    def to_prompt_lines(self) -> list[str]:
        lines = [
            "MOOD AND IMPORTANT-MOMENT CONTINUITY",
            "Use these explicit temporal cues only when relevant. Do not assume an old mood is still current, dramatize a moment, or force a follow-up.",
            "Eidolon's current expression state is a configurable self-model state, not proof of feelings or consciousness.",
            (
                "Eidolon expression state: "
                f"mood={self.eidolon_mood_label}; energy={self.eidolon_energy_band}; focus={self.eidolon_focus_band}."
            ),
        ]
        if self.user_mood is not None:
            lines.append(
                f"- Current explicitly recorded user mood ({self.user_mood.freshness}): {self.user_mood.text}"
            )
        for moment in self.important_moments:
            lines.append(f"- Open important moment ({moment.freshness}): {moment.text}")
        if self.user_mood is None and not self.important_moments:
            lines.append("- No current explicit user mood or open important moment is available.")
        return lines

    def public_summary(self, *, include_content: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "user_mood_current": self.user_mood is not None,
            "important_moment_count": len(self.important_moments),
            "categories": list(self.categories),
            "eidolon_mood_label": self.eidolon_mood_label,
            "eidolon_energy_band": self.eidolon_energy_band,
            "eidolon_focus_band": self.eidolon_focus_band,
            "inferred_from_transcript": False,
            "writes_memory": False,
            "mutates_personality": False,
            "claims_sentience": False,
            "current_mood_conflicts_omitted": self.current_mood_conflicts_omitted,
        }
        if include_content:
            result["user_mood"] = self.user_mood.to_dict() if self.user_mood else None
            result["important_moments"] = [moment.to_dict() for moment in self.important_moments]
        return result

    def receipt_metrics(self, *, included: bool) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mood_candidates": self.mood_candidates,
            "current_user_mood_included": bool(included and self.user_mood is not None),
            "stale_moods_omitted": self.stale_moods_omitted,
            "current_mood_conflicts_omitted": self.current_mood_conflicts_omitted,
            "important_moment_candidates": self.moment_candidates,
            "important_moments_included": len(self.important_moments) if included else 0,
            "resolved_moments_omitted": self.resolved_moments_omitted,
            "moment_limit_omitted": self.moment_limit_omitted,
            "contains_cue_content": False,
            "inferred_from_transcript": False,
        }


def _clean_text(memory: dict[str, Any]) -> str:
    value = memory.get("content")
    if value in {None, ""}:
        value = memory.get("thought")
    if value in {None, ""}:
        value = memory.get("summary")
    text = " ".join(str(value or "").split())
    if len(text) > MAX_TEMPORAL_CUE_CHARACTERS:
        text = text[: MAX_TEMPORAL_CUE_CHARACTERS - 1].rstrip() + "…"
    return text


def _eligible(memory: dict[str, Any]) -> bool:
    if not isinstance(memory, dict):
        return False
    memory_type = str(memory.get("type") or "").strip().lower()
    if memory_type not in _MOOD_TYPES | _MOMENT_TYPES:
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
    return bool(_clean_text(memory))


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _recorded_at(memory: dict[str, Any]) -> datetime | None:
    for field in ("observed_at", "occurred_at", "updated_at", "created_at", "timestamp"):
        parsed = _parse_time(memory.get(field))
        if parsed is not None:
            return parsed
    return None


def _importance(memory: dict[str, Any]) -> int:
    value = memory.get("importance")
    if isinstance(value, (int, float)):
        return 3 if value >= 0.8 else 2 if value >= 0.5 else 1
    lowered = str(value or "").strip().lower()
    if lowered in {"critical", "core", "high", "important"}:
        return 3
    if lowered in {"medium", "normal"}:
        return 2
    return 1


def _words(text: str) -> set[str]:
    current: list[str] = []
    result: set[str] = set()
    for char in str(text or "").lower():
        if char.isalnum():
            current.append(char)
        elif current:
            word = "".join(current)
            if len(word) >= 3 and word not in _STOPWORDS:
                result.add(word)
            current = []
    if current:
        word = "".join(current)
        if len(word) >= 3 and word not in _STOPWORDS:
            result.add(word)
    return result


def _relevance(text: str, user_message: str) -> int:
    return len(_words(text) & _words(user_message))


def _freshness(recorded_at: datetime | None, now: datetime) -> str:
    if recorded_at is None:
        return "time not recorded"
    age = max(timedelta(0), now - recorded_at)
    if age <= timedelta(hours=24):
        return "today"
    if age <= timedelta(days=7):
        return "recent"
    if age <= timedelta(days=30):
        return "this month"
    return "older"


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


def build_mood_moment_continuity_snapshot(
    memories: Iterable[dict[str, Any]],
    self_model: dict[str, Any],
    *,
    user_message: str = "",
    now: datetime | None = None,
    mood_freshness_hours: int = DEFAULT_MOOD_FRESHNESS_HOURS,
    max_important_moments: int = MAX_IMPORTANT_MOMENTS,
) -> MoodMomentContinuitySnapshot:
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    reference = reference.astimezone(timezone.utc)

    mood_rows: list[tuple[datetime | None, int, dict[str, Any]]] = []
    moment_rows: list[tuple[int, int, datetime | None, int, dict[str, Any]]] = []
    mood_candidates = 0
    moment_candidates = 0
    stale_moods_omitted = 0
    resolved_moments_omitted = 0

    for index, memory in enumerate(memories):
        if not _eligible(memory):
            continue
        memory_type = str(memory.get("type") or "").strip().lower()
        recorded = _recorded_at(memory)
        if memory_type in _MOOD_TYPES:
            mood_candidates += 1
            mood_state = str(memory.get("mood_state") or memory.get("temporal_state") or "").strip().lower()
            if mood_state in _CLEARED_MOOD_STATES:
                stale_moods_omitted += 1
                continue
            explicitly_current = mood_state == "current"
            fresh = recorded is not None and reference - recorded <= timedelta(hours=max(1, mood_freshness_hours))
            if not explicitly_current and not fresh:
                stale_moods_omitted += 1
                continue
            mood_rows.append((recorded, index, memory))
        elif memory_type in _MOMENT_TYPES:
            moment_candidates += 1
            moment_state = str(memory.get("moment_state") or memory.get("temporal_state") or "open").strip().lower()
            if moment_state in _RESOLVED_STATES:
                resolved_moments_omitted += 1
                continue
            moment_rows.append((
                _relevance(_clean_text(memory), user_message),
                _importance(memory),
                recorded,
                -index,
                memory,
            ))

    mood_rows.sort(key=lambda row: (row[0] or datetime.min.replace(tzinfo=timezone.utc), row[1]), reverse=True)
    user_mood: TemporalContinuityCue | None = None
    if mood_rows:
        recorded, _index, memory = mood_rows[0]
        user_mood = TemporalContinuityCue(
            category="user_mood",
            text=_clean_text(memory),
            recorded_at=recorded.isoformat(timespec="seconds") if recorded else "",
            freshness=_freshness(recorded, reference),
            importance=_importance(memory),
            relevance=_relevance(_clean_text(memory), user_message),
            continuity_state="current",
        )

    moment_rows.sort(
        key=lambda row: (
            row[0],
            row[1],
            row[2] or datetime.min.replace(tzinfo=timezone.utc),
            row[3],
        ),
        reverse=True,
    )
    limit = max(0, min(MAX_IMPORTANT_MOMENTS, int(max_important_moments)))
    selected_moments: list[TemporalContinuityCue] = []
    seen: set[str] = set()
    for relevance, importance, recorded, _index, memory in moment_rows:
        text = _clean_text(memory)
        fingerprint = " ".join(text.casefold().split())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        if len(selected_moments) >= limit:
            continue
        selected_moments.append(TemporalContinuityCue(
            category="important_moment",
            text=text,
            recorded_at=recorded.isoformat(timespec="seconds") if recorded else "",
            freshness=_freshness(recorded, reference),
            importance=importance,
            relevance=relevance,
            continuity_state="open",
        ))

    state = self_model.get("current_state") if isinstance(self_model, dict) else {}
    state = state if isinstance(state, dict) else {}
    eidolon_mood = " ".join(str(state.get("mood_label") or "neutral").split())[:40] or "neutral"
    return MoodMomentContinuitySnapshot(
        user_mood=user_mood,
        important_moments=tuple(selected_moments),
        mood_candidates=mood_candidates,
        stale_moods_omitted=stale_moods_omitted,
        current_mood_conflicts_omitted=max(0, len(mood_rows) - 1),
        moment_candidates=moment_candidates,
        resolved_moments_omitted=resolved_moments_omitted,
        moment_limit_omitted=max(0, len(moment_rows) - len(selected_moments)),
        eidolon_mood_label=eidolon_mood,
        eidolon_energy_band=_band(state.get("energy")),
        eidolon_focus_band=_band(state.get("focus")),
    )
