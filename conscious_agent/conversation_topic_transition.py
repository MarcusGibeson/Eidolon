from __future__ import annotations

"""Deterministic v1084.5 topic-transition quality."""

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

TOPIC_TRANSITION_SCHEMA_VERSION = "3"
MAX_TOPIC_HISTORY_ROWS = 8

_SHIFT_RE = re.compile(r"\b(?:new topic|different topic|different subject|switching gears|unrelated|anyway[,;:]|another thing)\b", re.I)
_INTERRUPT_RE = re.compile(r"\b(?:quick question|side question|before we continue|one thing first|brief interruption|pause that)\b", re.I)
_RESUME_RE = re.compile(r"\b(?:resume|continue with|pick (?:this|that|it) back up|where were we|keep going with)\b", re.I)
_RETURN_RE = re.compile(r"\b(?:back to|return to|returning to|go back to|about .{0,60} again)\b", re.I)
_DEICTIC_RE = re.compile(r"\b(?:this|that|it|they|them|those|these|there|then|the same|what you said|your idea|that idea|that part|that approach|that problem|that feeling)\b", re.I)
_REFERENTIAL_STATUS_RE = re.compile(
    r"^(?:well[, ]+)?(?:the|this|that|my|our|your)\b[^.!?\n]{0,100}\b(?:finally|still|now|again|worked|working|fixed|finished|done|better|worse|smoothly)\b",
    re.I,
)
_STOP = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for", "in", "on", "at", "is", "are", "was", "were",
    "i", "you", "it", "that", "this", "with", "my", "your", "we", "our", "be", "as", "do", "did", "does",
    "how", "what", "why", "when", "where", "who", "which", "much", "many", "need", "needs",
}


@dataclass(frozen=True)
class TopicTransitionProfile:
    transition_kind: str
    confidence: str
    latest_turn_overlap_percent: int
    best_earlier_overlap_percent: int
    matched_turn_offset: int | None
    preserves_prior_thread: bool
    explicit_transition_cue: bool
    deictic_follow_up: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = TOPIC_TRANSITION_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)

    def prompt_lines(self) -> list[str]:
        if self.transition_kind in {"no_history", "ambiguous_transition"}:
            return []
        lines = ["TOPIC TRANSITION QUALITY"]
        guidance = {
            "no_history": "Treat this as a fresh topic without inventing prior context.",
            "continuation": "Continue the active topic directly without reintroducing it.",
            "topic_shift": "Follow the new topic; do not drag the previous subject into the reply.",
            "resumption": "Resume the matching earlier topic with only the minimum orientation needed.",
            "return": "Return to the earlier topic naturally without replaying the whole discussion.",
            "interruption": "Answer the side question while preserving, but not falsely completing, the prior thread.",
            "ambiguous_transition": "Center the latest wording and avoid assuming a topic relationship that is not supported.",
        }
        lines.append(guidance.get(self.transition_kind, guidance["ambiguous_transition"]))
        lines.append("Do not merge unrelated conversations or invent continuity.")
        return lines


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _words(value: Any) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9']+", _normalized(value).casefold())
        if len(word) >= 3 and word not in _STOP
    }


def _overlap(message: str, prior: str) -> int:
    current = _words(message)
    earlier = _words(prior)
    if not current or not earlier:
        return 0
    return int(round(100 * len(current & earlier) / max(1, len(current))))


def classify_topic_transition(
    message: str,
    history: Iterable[Mapping[str, Any]],
    *,
    short_follow_up: bool = False,
    unresolved_thread_match: bool = False,
) -> TopicTransitionProfile:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_TOPIC_HISTORY_ROWS:]
    users = [_normalized(row.get("user_message") or row.get("user")) for row in rows]
    users = [text for text in users if text]
    if not users:
        return TopicTransitionProfile("no_history", "high", 0, 0, None, False, False)

    latest_overlap = _overlap(message, users[-1])
    earlier_scores: list[tuple[int, int]] = []
    for index, text in enumerate(reversed(users[:-1]), start=1):
        earlier_scores.append((_overlap(message, text), index))
    best_earlier, best_offset = max(earlier_scores, default=(0, 0))
    explicit_shift = bool(_SHIFT_RE.search(message))
    explicit_interrupt = bool(_INTERRUPT_RE.search(message))
    explicit_resume = bool(_RESUME_RE.search(message))
    explicit_return = bool(_RETURN_RE.search(message))
    explicit = explicit_shift or explicit_interrupt or explicit_resume or explicit_return
    message_word_count = len(re.findall(r"[A-Za-z0-9']+", _normalized(message)))
    deictic_follow_up = bool(_DEICTIC_RE.search(message) and message_word_count <= 18 and not explicit_shift)
    referential_status_follow_up = bool(_REFERENTIAL_STATUS_RE.search(_normalized(message)) and message_word_count <= 18 and not explicit)

    if explicit_interrupt:
        kind, confidence, matched, preserves = "interruption", "high", 0, True
    elif explicit_return:
        kind, confidence, matched, preserves = "return", "high", (best_offset or 0), False
    elif explicit_resume:
        kind, confidence, matched, preserves = "resumption", "high", (best_offset or 0), False
    elif explicit_shift:
        kind, confidence, matched, preserves = "topic_shift", "high", None, False
    elif unresolved_thread_match:
        kind, confidence, matched, preserves = "continuation", "high", 0, False
    elif deictic_follow_up or referential_status_follow_up:
        kind, confidence, matched, preserves = "continuation", "high", 0, False
    elif short_follow_up or latest_overlap >= 25:
        kind, confidence, matched, preserves = "continuation", "high" if latest_overlap >= 40 else "medium", 0, False
    elif best_earlier >= 30 and best_earlier >= latest_overlap + 15:
        kind, confidence, matched, preserves = "resumption", "medium", best_offset, False
    elif len(_words(message)) >= 8 and message_word_count >= 10 and latest_overlap <= 10 and best_earlier < 25:
        kind, confidence, matched, preserves = "topic_shift", "medium", None, False
    else:
        kind, confidence, matched, preserves = "ambiguous_transition", "low", None, False

    return TopicTransitionProfile(
        transition_kind=kind,
        confidence=confidence,
        latest_turn_overlap_percent=latest_overlap,
        best_earlier_overlap_percent=best_earlier,
        matched_turn_offset=matched,
        preserves_prior_thread=preserves,
        explicit_transition_cue=explicit,
        deictic_follow_up=deictic_follow_up,
    )
