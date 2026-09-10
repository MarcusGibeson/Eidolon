from __future__ import annotations

"""Read-only long-session personality stability evidence.

The guard inspects bounded completed conversation history already supplied to prompt
construction. It writes nothing, promotes no memory, infers no hidden traits, and
never changes the configured personality. The recent 12-turn window preserves the
established v1083 contract while a separate 48-turn horizon detects slow drift that
short windows miss.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


PERSONALITY_STABILITY_SCHEMA_VERSION = "2"
MAX_STABILITY_HISTORY_ROWS = 12
MAX_LONG_STABILITY_HISTORY_ROWS = 48
MAX_OPENING_WORDS = 5

_IDENTITY_RESET_PATTERNS = (
    re.compile(r"\bas an ai\b", re.I),
    re.compile(r"\bi (?:do not|don't) (?:have|retain) memor(?:y|ies)\b", re.I),
    re.compile(r"\bi am not eidolon\b", re.I),
    re.compile(r"\bi have no (?:identity|personality|continuity)\b", re.I),
)
_OPERATOR_BLEED_RE = re.compile(
    r"\b(?:release candidate|verification profile|current milestone|task queue|operator dashboard|source manifest|approval packet)\b",
    re.I,
)
_AFFECTION_INFLATION_RE = re.compile(
    r"\b(?:only need me|always be yours|you belong to me|never leave me|our love is growing|more than anyone)\b",
    re.I,
)
_STOCK_EMOTIONAL_OPENING_RE = re.compile(
    r"^(?:that sounds really|i hear how|your feelings are valid|i'm here with you|that must be hard)\b",
    re.I,
)


@dataclass(frozen=True)
class PersonalityStabilitySnapshot:
    history_rows_considered: int
    assistant_rows_considered: int
    continuity_lane_changes: int
    repeated_opening_runs: int
    identity_reset_signals: int
    repetition_guard_active: bool
    identity_continuity_guard_active: bool
    tone_matching_guard_active: bool
    long_history_rows_considered: int = 0
    long_assistant_rows_considered: int = 0
    opening_diversity_percent: int = 100
    repeated_opening_percent: int = 0
    operator_bleed_signals: int = 0
    affection_inflation_signals: int = 0
    stock_emotional_opening_signals: int = 0
    tone_monoculture_risk: bool = False
    lane_adaptation_stable: bool = True
    long_horizon_guard_active: bool = True
    writes_state: bool = False
    mutates_personality: bool = False
    infers_hidden_traits: bool = False
    contains_message_content: bool = False
    schema_version: str = PERSONALITY_STABILITY_SCHEMA_VERSION

    @property
    def drift_risk(self) -> str:
        if self.identity_reset_signals:
            return "identity_reset_risk"
        if self.affection_inflation_signals:
            return "relationship_inflation_risk"
        if self.operator_bleed_signals:
            return "operator_lane_bleed_risk"
        if self.repeated_opening_runs >= 2 or self.tone_monoculture_risk or not self.lane_adaptation_stable:
            return "repetition_or_tone_drift_risk"
        return "bounded"

    def to_prompt_lines(self) -> list[str]:
        lines = [
            "LONG-SESSION PERSONALITY STABILITY",
            "Keep Eidolon's configured identity and grounded conversational voice stable across long sessions, reloads, retries, and provider recovery.",
            "Do not reset identity, disclaim existing continuity, or imitate a different persona unless the operator explicitly changes the configured personality.",
            "Respond to the latest user message naturally; do not repeat stock openings or cadence, and do not turn continuity facts into a mechanical recap.",
            "Match the user's current tone without copying hostility, escalating intimacy, or carrying operator-work language into ordinary conversation.",
        ]
        if self.identity_reset_signals:
            lines.append("Recent completed output showed identity-reset language. Preserve continuity without mentioning this diagnostic.")
        if self.repeated_opening_runs or self.tone_monoculture_risk:
            lines.append("Recent and long-horizon structure showed repeated openings or cadence. Vary phrasing while preserving the same personality and meaning.")
        if self.operator_bleed_signals:
            lines.append("Long-horizon evidence shows operator-language bleed. Exclude project/release language unless the latest turn explicitly requests operator work.")
        if self.affection_inflation_signals:
            lines.append("Long-horizon evidence shows affection inflation. Keep warmth user-led, bounded, and free of dependence or relationship-progress claims.")
        if not self.lane_adaptation_stable:
            lines.append("Adapt to the current conversational lane without carrying the prior lane's mannerisms forward or acting like a different identity.")
        return lines

    def compact_prompt_lines(self) -> list[str]:
        risks: list[str] = []
        if self.identity_reset_signals: risks.append("identity reset")
        if self.repeated_opening_runs or self.tone_monoculture_risk: risks.append("repeated cadence")
        if self.operator_bleed_signals: risks.append("operator bleed")
        if self.affection_inflation_signals: risks.append("affection inflation")
        suffix = f" Correct recent {', '.join(risks)} risk." if risks else ""
        return [
            "LONG-SESSION PERSONALITY STABILITY",
            "Preserve the configured identity and voice; vary phrasing, match the current lane, and invent no intimacy or hidden traits." + suffix,
        ]

    def public_summary(self) -> dict[str, Any]:
        return {**asdict(self), "drift_risk": self.drift_risk, "contains_message_content": False}

    def receipt_metrics(self) -> dict[str, Any]:
        return self.public_summary()


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _assistant_text(row: Mapping[str, Any]) -> str:
    for key in ("assistant_response", "assistant", "response", "assistant_text"):
        value = _normalized(row.get(key))
        if value:
            return value
    return ""


def _opening_signature(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9']+", text.casefold())[:MAX_OPENING_WORDS]
    return " ".join(words)


def _repeated_opening_runs(openings: list[str]) -> int:
    repeated_runs = 0
    run = 1
    for before, after in zip(openings, openings[1:]):
        if before == after:
            run += 1
            if run == 3:
                repeated_runs += 1
        else:
            run = 1
    return repeated_runs


def build_personality_stability_snapshot(
    conversation_history: Iterable[Mapping[str, Any]],
) -> PersonalityStabilitySnapshot:
    all_rows = [row for row in conversation_history if isinstance(row, Mapping)][-MAX_LONG_STABILITY_HISTORY_ROWS:]
    recent_rows = all_rows[-MAX_STABILITY_HISTORY_ROWS:]
    recent_assistants = [_assistant_text(row) for row in recent_rows]
    recent_assistants = [text for text in recent_assistants if text]
    long_assistants = [_assistant_text(row) for row in all_rows]
    long_assistants = [text for text in long_assistants if text]

    recent_lanes = [str(row.get("continuity_lane") or "").strip().lower() for row in recent_rows]
    recent_lanes = [lane for lane in recent_lanes if lane]
    lane_changes = sum(1 for before, after in zip(recent_lanes, recent_lanes[1:]) if before != after)

    recent_openings = [_opening_signature(text) for text in recent_assistants]
    recent_openings = [opening for opening in recent_openings if opening]
    long_openings = [_opening_signature(text) for text in long_assistants]
    long_openings = [opening for opening in long_openings if opening]
    repeated_runs = _repeated_opening_runs(recent_openings)
    repeated_pairs = sum(1 for before, after in zip(long_openings, long_openings[1:]) if before == after)
    comparison_count = max(1, len(long_openings) - 1)
    repeated_percent = round(repeated_pairs * 100 / comparison_count) if long_openings else 0
    diversity_percent = round(len(set(long_openings)) * 100 / len(long_openings)) if long_openings else 100

    identity_resets = sum(1 for text in long_assistants if any(pattern.search(text) for pattern in _IDENTITY_RESET_PATTERNS))
    operator_bleed = 0
    affection_inflation = 0
    stock_emotional = 0
    lane_mismatches = 0
    for row in all_rows:
        text = _assistant_text(row)
        if not text:
            continue
        lane = str(row.get("continuity_lane") or "ordinary").strip().lower()
        if lane not in {"operator", "mixed"} and _OPERATOR_BLEED_RE.search(text):
            operator_bleed += 1
            lane_mismatches += 1
        if _AFFECTION_INFLATION_RE.search(text):
            affection_inflation += 1
        if _STOCK_EMOTIONAL_OPENING_RE.search(text):
            stock_emotional += 1
            if lane not in {"relational", "emotional", "mixed"}:
                lane_mismatches += 1

    unique_opening_count = len(set(long_openings))
    tone_monoculture = bool(
        len(long_assistants) >= 12
        and (
            unique_opening_count <= 3
            or repeated_percent >= 35
            or stock_emotional >= max(4, len(long_assistants) // 3)
        )
    )
    lane_adaptation_stable = lane_mismatches <= max(1, len(long_assistants) // 8)

    return PersonalityStabilitySnapshot(
        history_rows_considered=len(recent_rows),
        assistant_rows_considered=len(recent_assistants),
        continuity_lane_changes=lane_changes,
        repeated_opening_runs=repeated_runs,
        identity_reset_signals=identity_resets,
        repetition_guard_active=True,
        identity_continuity_guard_active=True,
        tone_matching_guard_active=True,
        long_history_rows_considered=len(all_rows),
        long_assistant_rows_considered=len(long_assistants),
        opening_diversity_percent=diversity_percent,
        repeated_opening_percent=repeated_percent,
        operator_bleed_signals=operator_bleed,
        affection_inflation_signals=affection_inflation,
        stock_emotional_opening_signals=stock_emotional,
        tone_monoculture_risk=tone_monoculture,
        lane_adaptation_stable=lane_adaptation_stable,
    )
