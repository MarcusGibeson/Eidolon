from __future__ import annotations

"""Deterministic, provider-free v1085.6 cross-session thread linking.

The linker never merges sessions or writes continuity state. It admits only
complete historical turns from another session when the current request names
that session/thread explicitly or contains an explicit return cue plus a strong
bounded lexical match.
"""

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "1"
MAX_SESSIONS = 24
MAX_TURNS_PER_SESSION = 12
MAX_LINKS = 2
MIN_RETURN_OVERLAP_PERCENT = 40

_STOP_WORDS = {
    "the", "and", "for", "with", "this", "that", "from", "your", "you",
    "about", "into", "have", "has", "was", "were", "are", "but", "not",
    "our", "their", "they", "then", "just", "can", "could", "would",
}
_RETURN_CUES = (
    "return to",
    "continue from",
    "go back to",
    "back to",
    "resume",
    "that other conversation",
    "other chat",
    "previous session",
)


@dataclass(frozen=True)
class CrossSessionLinkedTurn:
    turn: Mapping[str, Any]
    session_id_digest: str
    turn_offset: int
    overlap_percent: int
    evidence_kind: str
    explicit_link: bool


@dataclass(frozen=True)
class CrossSessionLinkEvidence:
    session_id_digest: str
    turn_offset: int
    overlap_percent: int
    evidence_kind: str
    explicit_link: bool

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CrossSessionLinkPlan:
    candidate_session_count: int
    candidate_turn_count: int
    linked_session_count: int
    linked_turn_count: int
    links: tuple[CrossSessionLinkEvidence, ...]
    explicit_evidence_required: bool = True
    merges_sessions: bool = False
    rewrites_history: bool = False
    writes_state: bool = False
    provider_invoked: bool = False
    contains_conversation_content: bool = False
    schema_version: str = SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result["type"] = "cross_session_thread_linking"
        result["links"] = [item.public_summary() for item in self.links]
        return result


def _words(value: Any) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9']+", str(value or "").casefold())
        if len(word) >= 3 and word not in _STOP_WORDS
    }


def _turn_text(turn: Mapping[str, Any]) -> str:
    return " ".join(
        str(turn.get(key) or "")
        for key in ("user_message", "assistant_response", "user", "assistant", "response")
    )


def _complete_turn(turn: Mapping[str, Any]) -> bool:
    user = str(turn.get("user_message") or turn.get("user") or "").strip()
    assistant = str(
        turn.get("assistant_response") or turn.get("assistant") or turn.get("response") or ""
    ).strip()
    state = str(turn.get("completion_state") or turn.get("status") or "completed").casefold()
    if state in {"failed", "cancelled", "canceled", "partial", "streaming", "pending"}:
        return False
    if turn.get("success") is False:
        return False
    return bool(user and assistant)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def _overlap_percent(left: set[str], right: set[str]) -> int:
    if not left or not right:
        return 0
    return int(round(100 * len(left & right) / max(1, min(len(left), len(right)))))


def _explicit_return_cue(message: str) -> bool:
    lowered = str(message or "").casefold()
    return any(cue in lowered for cue in _RETURN_CUES)


def link_cross_session_threads(
    message: str,
    current_session_id: str,
    sessions: Iterable[Mapping[str, Any]],
    *,
    explicit_session_id: str = "",
    explicit_thread_key: str = "",
) -> tuple[list[CrossSessionLinkedTurn], CrossSessionLinkPlan]:
    """Return at most two complete linked turns and content-free evidence."""

    query_words = _words(message)
    candidates: list[CrossSessionLinkedTurn] = []
    candidate_sessions = 0
    candidate_turns = 0
    has_return_cue = _explicit_return_cue(message)

    for session in list(sessions)[:MAX_SESSIONS]:
        if not isinstance(session, Mapping):
            continue
        session_id = str(session.get("id") or "").strip()
        status = str(session.get("status") or "active").casefold()
        if not session_id or session_id == current_session_id or status in {"deleted", "retracted"}:
            continue
        candidate_sessions += 1
        session_thread_key = str(session.get("thread_key") or "").strip()
        title_words = _words(session.get("title"))
        turns = [
            turn
            for turn in list(session.get("turns") or [])[-MAX_TURNS_PER_SESSION:]
            if isinstance(turn, Mapping) and _complete_turn(turn)
        ]
        candidate_turns += len(turns)

        for index, turn in enumerate(turns):
            turn_thread_key = str(turn.get("thread_key") or "").strip()
            explicit = bool(explicit_session_id and session_id == explicit_session_id)
            explicit = explicit or bool(
                explicit_thread_key
                and explicit_thread_key in {session_thread_key, turn_thread_key}
            )
            overlap = _overlap_percent(query_words, _words(_turn_text(turn)) | title_words)
            if explicit:
                evidence_kind = "explicit_session_or_thread_link"
            elif has_return_cue and overlap >= MIN_RETURN_OVERLAP_PERCENT:
                evidence_kind = "explicit_return_with_bounded_match"
            else:
                continue
            candidates.append(
                CrossSessionLinkedTurn(
                    turn=dict(turn),
                    session_id_digest=_digest(session_id),
                    turn_offset=len(turns) - 1 - index,
                    overlap_percent=overlap,
                    evidence_kind=evidence_kind,
                    explicit_link=explicit,
                )
            )

    candidates.sort(
        key=lambda item: (
            not item.explicit_link,
            -item.overlap_percent,
            item.turn_offset,
            item.session_id_digest,
        )
    )
    selected = candidates[:MAX_LINKS]
    evidence = tuple(
        CrossSessionLinkEvidence(
            session_id_digest=item.session_id_digest,
            turn_offset=item.turn_offset,
            overlap_percent=item.overlap_percent,
            evidence_kind=item.evidence_kind,
            explicit_link=item.explicit_link,
        )
        for item in selected
    )
    plan = CrossSessionLinkPlan(
        candidate_session_count=candidate_sessions,
        candidate_turn_count=candidate_turns,
        linked_session_count=len({item.session_id_digest for item in selected}),
        linked_turn_count=len(selected),
        links=evidence,
    )
    return selected, plan


def cross_session_evidence_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "content", "prompt", "transcript", "user_message",
        "assistant_response", "memory", "summary", "provider_payload",
        "credentials", "vector", "embedding", "reasoning",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            stack.extend(current)
    return False
