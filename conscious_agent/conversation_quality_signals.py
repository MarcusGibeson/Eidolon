from __future__ import annotations

"""Read-only v1084.0 conversation-quality signals.

Signals are bounded structural evidence. They contain no prompt, response, memory,
provider payload, or hidden reasoning and are safe to place in redacted receipts.
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from conversation_turn_intent import TurnIntentProfile

QUALITY_SIGNAL_SCHEMA_VERSION = "1"
MAX_SIGNAL_HISTORY_ROWS = 8
_STOP = {"the", "a", "an", "and", "or", "but", "to", "of", "for", "in", "on", "at", "is", "are", "was", "were", "i", "you", "it", "that", "this", "with", "my", "your"}
_DEICTIC = re.compile(r"\b(?:that|this|it|those|these|there|then|same|again)\b", re.I)


@dataclass(frozen=True)
class ConversationQualitySignals:
    relevance_mode: str
    continuity_needed: bool
    lexical_continuity_percent: int
    clarity_risk: str
    repetition_risk: bool
    repeated_opening_runs: int
    current_question_count: int
    open_assistant_question_signals: int
    appropriateness_lane: str
    history_rows_considered: int
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = QUALITY_SIGNAL_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)

    def prompt_lines(self) -> list[str]:
        if self.relevance_mode == "recent_thread_relevant":
            relevance = "Continue the relevant recent thread without recapping it."
        elif self.relevance_mode == "operator_context_relevant":
            relevance = "Use only operator context needed for this explicit request."
        else:
            relevance = "Center the latest turn; do not force an older callback."
        lines = ["CONVERSATION QUALITY SIGNALS", relevance]
        if self.current_question_count:
            lines.append("Answer every current question explicitly.")
        if self.open_assistant_question_signals:
            lines.append("Use the prior open question only when the new wording supports it.")
        if self.clarity_risk == "ambiguous_without_context":
            lines.append("Do not invent specifics; use the narrowest reasonable interpretation.")
        elif self.clarity_risk == "multi_part":
            lines.append("Cover each distinct part.")
        if self.repetition_risk:
            lines.append("Vary the opening and avoid repeating the prior answer.")
        lines.append("Stay appropriate to the current lane; no status-report, therapy-script, or flirt escalation substitution.")
        return lines


def _words(value: Any) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", str(value or "").casefold()) if len(w) >= 3 and w not in _STOP}


def _assistant(row: Mapping[str, Any]) -> str:
    return " ".join(str(row.get("assistant_response") or row.get("assistant") or "").split())


def _user(row: Mapping[str, Any]) -> str:
    return " ".join(str(row.get("user_message") or row.get("user") or "").split())


def _opening(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.casefold())[:5])


def build_conversation_quality_signals(
    message: str,
    history: Iterable[Mapping[str, Any]],
    *,
    intent: TurnIntentProfile,
    short_follow_up: bool,
    operator_context_relevant: bool,
) -> ConversationQualitySignals:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_SIGNAL_HISTORY_ROWS:]
    latest_words = _words(message)
    recent_text = " ".join(f"{_user(row)} {_assistant(row)}" for row in rows[-3:])
    recent_words = _words(recent_text)
    overlap = int(round(100 * len(latest_words & recent_words) / max(1, len(latest_words)))) if latest_words else 0

    if operator_context_relevant:
        relevance = "operator_context_relevant"
    elif short_follow_up or overlap >= 25:
        relevance = "recent_thread_relevant"
    else:
        relevance = "current_turn_primary"

    normalized = " ".join(str(message or "").split())
    word_count = len(re.findall(r"[A-Za-z0-9']+", normalized))
    if (word_count <= 4 and _DEICTIC.search(normalized)) and not rows:
        clarity = "ambiguous_without_context"
    elif intent.question_count >= 3 or (normalized.count(";") >= 2):
        clarity = "multi_part"
    else:
        clarity = "bounded"

    openings = [_opening(_assistant(row)) for row in rows if _assistant(row)]
    repeated_runs = 0
    run = 1
    for before, after in zip(openings, openings[1:]):
        if before and before == after:
            run += 1
            if run == 3:
                repeated_runs += 1
        else:
            run = 1
    repetition = repeated_runs > 0
    if len(openings) >= 2 and openings[-1] and openings[-1] == openings[-2]:
        repetition = True

    last_assistant = _assistant(rows[-1]) if rows else ""
    open_question = int(bool(last_assistant and last_assistant.rstrip().endswith("?")))
    lane = {
        "project_instruction": "operator",
        "correction": "correction",
        "brainstorming": "brainstorming",
        "emotional_sharing": "emotional",
        "affectionate_play": "playful",
    }.get(intent.primary_intent, "ordinary")

    return ConversationQualitySignals(
        relevance_mode=relevance,
        continuity_needed=relevance == "recent_thread_relevant",
        lexical_continuity_percent=overlap,
        clarity_risk=clarity,
        repetition_risk=repetition,
        repeated_opening_runs=repeated_runs,
        current_question_count=intent.question_count,
        open_assistant_question_signals=open_question,
        appropriateness_lane=lane,
        history_rows_considered=len(rows),
    )
