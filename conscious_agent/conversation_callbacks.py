from __future__ import annotations

"""Deterministic v1084.4 natural conversational callback selection."""

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from conversation_topic_transition import TopicTransitionProfile
from conversation_unresolved_threads import UnresolvedThreadProfile

CALLBACK_SCHEMA_VERSION = "1"
MAX_CALLBACK_HISTORY_ROWS = 8
MAX_CALLBACKS = 2

_CALLBACK_RE = re.compile(r"\b(?:that|this|it|earlier|before|again|same|remember|as we discussed|what you said|back to)\b", re.I)
_STOP = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for", "in", "on", "at", "is", "are", "was", "were",
    "i", "you", "it", "that", "this", "with", "my", "your", "we", "our", "be", "as", "do", "did", "does",
    "how", "what", "why", "when", "where", "who", "which", "much", "many", "need", "needs",
}


@dataclass(frozen=True)
class CallbackCandidate:
    source_role: str
    turn_offset: int
    reason: str
    relevance_percent: int
    evidence_digest: str

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConversationalCallbackProfile:
    candidates: tuple[CallbackCandidate, ...]
    candidate_count: int
    selected_count: int
    explicit_callback_cue: bool
    recap_allowed: bool = False
    forced_emotional_significance: bool = False
    stale_callback_allowed: bool = False
    writes_state: bool = False
    contacts_provider: bool = False
    contains_message_content: bool = False
    schema_version: str = CALLBACK_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        data = asdict(self)
        data["candidates"] = [candidate.public_summary() for candidate in self.candidates]
        return data

    def prompt_lines(self) -> list[str]:
        if not self.selected_count:
            return []
        lines = ["NATURAL CONVERSATIONAL CALLBACKS"]
        if self.selected_count:
            offsets = ", ".join(str(candidate.turn_offset) for candidate in self.candidates)
            lines.append(f"Relevant recent callback evidence exists at bounded turn offsets {offsets}; reference only the minimum detail needed.")
            lines.append("Do not recap the prior exchange, announce retrieval, or repeat a fact merely to prove continuity.")
        lines.append("Do not assign emotional importance, relationship progress, or permanence that the user did not provide.")
        return lines


def _normalized(value: Any) -> str:
    return " ".join(str(value or "").split())


def _words(value: Any) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9']+", _normalized(value).casefold())
        if len(word) >= 3 and word not in _STOP
    }


def _overlap(message: str, source: str) -> int:
    current = _words(message)
    earlier = _words(source)
    if not current or not earlier:
        return 0
    return int(round(100 * len(current & earlier) / max(1, len(current))))


def _digest(role: str, text: str) -> str:
    return hashlib.sha256(f"{role}\n{text.casefold()}".encode("utf-8")).hexdigest()[:20]


def build_conversational_callback_profile(
    message: str,
    history: Iterable[Mapping[str, Any]],
    *,
    topic_transition: TopicTransitionProfile,
    unresolved_threads: UnresolvedThreadProfile,
    explicit_correction: bool = False,
) -> ConversationalCallbackProfile:
    rows = [row for row in history if isinstance(row, Mapping)][-MAX_CALLBACK_HISTORY_ROWS:]
    explicit_cue = bool(_CALLBACK_RE.search(message))
    if topic_transition.transition_kind in {"topic_shift", "interruption"}:
        return ConversationalCallbackProfile((), 0, 0, explicit_cue)

    scored: list[tuple[int, int, str, str, int]] = []
    for absolute_index, row in enumerate(rows):
        offset = len(rows) - 1 - absolute_index
        if offset > 5:
            continue
        user = _normalized(row.get("user_message") or row.get("user"))
        assistant = _normalized(row.get("assistant_response") or row.get("assistant"))
        for role, text in (("user", user), ("assistant", assistant)):
            if not text:
                continue
            if explicit_correction and role == "assistant":
                continue
            relevance = _overlap(message, text)
            matched_transition = topic_transition.matched_turn_offset == offset and topic_transition.transition_kind in {"resumption", "return"}
            latest_deictic = offset == 0 and explicit_cue
            unresolved_match = any(item.turn_offset == offset and item.current_turn_match for item in unresolved_threads.items)
            if relevance >= 30:
                reason = "lexical_relevance"
            elif matched_transition:
                reason = "topic_resumption"
            elif unresolved_match:
                reason = "unresolved_thread_match"
            elif latest_deictic:
                reason = "explicit_recent_callback"
            else:
                continue
            priority = relevance + (35 if matched_transition else 0) + (25 if unresolved_match else 0) + (15 if latest_deictic else 0)
            scored.append((priority, -offset, role, text, relevance))

    scored.sort(reverse=True)
    selected: list[CallbackCandidate] = []
    seen_offsets: set[tuple[str, int]] = set()
    for _priority, negative_offset, role, text, relevance in scored:
        offset = -negative_offset
        key = (role, offset)
        if key in seen_offsets:
            continue
        seen_offsets.add(key)
        selected.append(
            CallbackCandidate(
                source_role=role,
                turn_offset=offset,
                reason=(
                    "topic_resumption" if topic_transition.matched_turn_offset == offset and topic_transition.transition_kind in {"resumption", "return"}
                    else "unresolved_thread_match" if any(item.turn_offset == offset and item.current_turn_match for item in unresolved_threads.items)
                    else "explicit_recent_callback" if offset == 0 and explicit_cue and relevance < 30
                    else "lexical_relevance"
                ),
                relevance_percent=relevance,
                evidence_digest=_digest(role, text),
            )
        )
        if len(selected) >= MAX_CALLBACKS:
            break

    return ConversationalCallbackProfile(
        candidates=tuple(selected),
        candidate_count=len(scored),
        selected_count=len(selected),
        explicit_callback_cue=explicit_cue,
    )
