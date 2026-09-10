from __future__ import annotations

"""Deterministic v1084.3 unresolved-thread continuity.

The classifier examines only a bounded suffix of completed conversation turns.
It performs no provider calls, writes no state, and treats structural signals as
possible unresolved threads rather than proof that an obligation exists.
"""

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

UNRESOLVED_THREAD_SCHEMA_VERSION = "1"
MAX_THREAD_HISTORY_ROWS = 8
MAX_THREAD_ITEMS = 6

_PROMISE_RE = re.compile(r"\b(?:i(?:'ll| will)|we(?:'ll| will)|next[, ]+(?:i|we)(?:'ll| will))\b", re.I)
_BLOCKER_RE = re.compile(
    r"\b(?:blocked|blocking|cannot continue|can't continue|unable to continue|waiting (?:for|on)|"
    r"unavailable|failed because|cannot proceed|can't proceed|need(?:s)? .{0,50} before)\b",
    re.I,
)
_UNFINISHED_RE = re.compile(
    r"\b(?:still need(?:s)?|not finished|unfinished|remaining work|come back to|return to|"
    r"continue later|pick this back up|next step|not done yet|left to do)\b",
    re.I,
)
_COMPLETION_RE = re.compile(r"\b(?:completed|finished|done|resolved|unblocked|now available|succeeded|passed)\b", re.I)
_CONTINUE_RE = re.compile(r"\b(?:continue|keep going|pick (?:it|that|this) back up|resume|what next|then what|still|that|it)\b", re.I)
_UNRELATED_TRANSITION_RE = re.compile(r"\b(?:new topic|different topic|switching gears|quick question|side question|before we continue|unrelated)\b", re.I)
_STOP = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for", "in", "on", "at", "is", "are", "was", "were",
    "i", "you", "it", "that", "this", "with", "my", "your", "we", "our", "be", "as", "do", "did", "does",
}


@dataclass(frozen=True)
class UnresolvedThreadItem:
    kind: str
    source_role: str
    turn_offset: int
    current_turn_match: bool
    evidence_level: str
    evidence_digest: str

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UnresolvedThreadProfile:
    items: tuple[UnresolvedThreadItem, ...]
    unresolved_question_count: int
    assistant_commitment_signal_count: int
    blocker_count: int
    unfinished_subject_count: int
    matching_item_count: int
    history_rows_considered: int
    bounded: bool = True
    obligations_inferred: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = UNRESOLVED_THREAD_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        data = asdict(self)
        data["items"] = [item.public_summary() for item in self.items]
        return data

    def prompt_lines(self) -> list[str]:
        if not self.items:
            return []
        lines = ["UNRESOLVED THREAD CONTINUITY"]
        if self.matching_item_count:
            kinds = sorted({item.kind for item in self.items if item.current_turn_match})
            lines.append(
                "The latest message appears to resume bounded recent thread evidence: "
                + ", ".join(kind.replace("_", " ") for kind in kinds)
                + ". Continue only the relevant thread without a recap."
            )
        elif self.items:
            lines.append("Recent unresolved-thread signals exist, but do not force them into an unrelated current topic.")
        if self.assistant_commitment_signal_count:
            lines.append("A prior assistant commitment signal is not proof of execution or a durable obligation; do not claim completion without current evidence.")
        if self.blocker_count:
            lines.append("Treat a blocker as current only when the latest wording still supports it.")
        lines.append("Do not invent promises, obligations, blockers, or unfinished work.")
        return lines


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _words(value: Any) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9']+", _normalized(value).casefold())
        if len(word) >= 3 and word not in _STOP
    }


def _sentences(value: Any) -> list[str]:
    text = _normalized(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _digest(kind: str, role: str, sentence: str) -> str:
    material = f"{kind}\n{role}\n{sentence.casefold()}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:20]


def _overlap_percent(left: Any, right: Any) -> int:
    current = _words(left)
    prior = _words(right)
    if not current or not prior:
        return 0
    return int(round(100 * len(current & prior) / max(1, len(current))))


def _current_matches(message: str, sentence: str, *, turn_offset: int) -> bool:
    words = re.findall(r"[A-Za-z0-9']+", _normalized(message))
    overlap = _overlap_percent(message, sentence)
    if _UNRELATED_TRANSITION_RE.search(message):
        return False
    if overlap >= 30:
        return True
    return bool(turn_offset == 0 and len(words) <= 14 and _CONTINUE_RE.search(message))


def build_unresolved_thread_profile(
    message: str,
    history: Iterable[Mapping[str, Any]],
) -> UnresolvedThreadProfile:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_THREAD_HISTORY_ROWS:]
    candidates: list[tuple[str, str, int, str]] = []

    for absolute_index, row in enumerate(rows):
        turn_offset = len(rows) - 1 - absolute_index
        user = _normalized(row.get("user_message") or row.get("user"))
        assistant = _normalized(row.get("assistant_response") or row.get("assistant"))

        for sentence in _sentences(user):
            if _BLOCKER_RE.search(sentence) and not _COMPLETION_RE.search(sentence):
                candidates.append(("blocker", "user", turn_offset, sentence))
            if _UNFINISHED_RE.search(sentence) and not _COMPLETION_RE.search(sentence):
                candidates.append(("unfinished_subject", "user", turn_offset, sentence))

        for sentence in _sentences(assistant):
            if sentence.rstrip().endswith("?") and turn_offset == 0:
                candidates.append(("unresolved_question", "assistant", turn_offset, sentence))
            if _PROMISE_RE.search(sentence) and not _COMPLETION_RE.search(sentence) and turn_offset <= 2:
                candidates.append(("assistant_commitment_signal", "assistant", turn_offset, sentence))
            if _BLOCKER_RE.search(sentence) and not _COMPLETION_RE.search(sentence):
                candidates.append(("blocker", "assistant", turn_offset, sentence))
            if _UNFINISHED_RE.search(sentence) and not _COMPLETION_RE.search(sentence):
                candidates.append(("unfinished_subject", "assistant", turn_offset, sentence))

    seen: set[tuple[str, str]] = set()
    items: list[UnresolvedThreadItem] = []
    for kind, role, offset, sentence in sorted(candidates, key=lambda row: row[2]):
        digest = _digest(kind, role, sentence)
        key = (kind, digest)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            UnresolvedThreadItem(
                kind=kind,
                source_role=role,
                turn_offset=offset,
                current_turn_match=_current_matches(message, sentence, turn_offset=offset),
                evidence_level="explicit_bounded_pattern",
                evidence_digest=digest,
            )
        )
        if len(items) >= MAX_THREAD_ITEMS:
            break

    count = lambda kind: sum(1 for item in items if item.kind == kind)
    return UnresolvedThreadProfile(
        items=tuple(items),
        unresolved_question_count=count("unresolved_question"),
        assistant_commitment_signal_count=count("assistant_commitment_signal"),
        blocker_count=count("blocker"),
        unfinished_subject_count=count("unfinished_subject"),
        matching_item_count=sum(1 for item in items if item.current_turn_match),
        history_rows_considered=len(rows),
    )
