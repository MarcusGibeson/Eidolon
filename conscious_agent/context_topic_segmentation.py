from __future__ import annotations

"""Deterministic v1085.3 topic segmentation for bounded conversation context.

The segmenter groups complete turns using local lexical continuity and selects one
active segment from explicit transition evidence. Public evidence contains only
counts, offsets, scores, and digests. It never writes state or contacts a provider.
"""

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

TOPIC_SEGMENTATION_SCHEMA_VERSION = "1"
MAX_SEGMENT_HISTORY_ROWS = 32
MAX_SEGMENTS = 12
_MIN_CONTINUITY_PERCENT = 12
_MIN_QUERY_MATCH_PERCENT = 24
_STOP = {
    "the", "a", "an", "and", "or", "but", "to", "of", "for", "in", "on", "at", "is", "are", "was", "were",
    "i", "you", "it", "that", "this", "with", "my", "your", "we", "our", "be", "as", "do", "did", "does",
    "how", "what", "why", "when", "where", "who", "which", "much", "many", "have", "has", "had", "can",
    "could", "would", "should", "will", "just", "about", "from", "into", "then", "than", "also", "really", "topic",
}


@dataclass(frozen=True)
class TopicSegmentEvidence:
    segment_id: str
    start_offset: int
    end_offset: int
    turn_count: int
    query_overlap_percent: int
    latest_segment: bool

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TopicSegmentationPlan:
    segment_count: int
    active_segment_id: str
    active_turn_indices: tuple[int, ...]
    active_turn_offsets: tuple[int, ...]
    active_turn_count: int
    unrelated_turns_excluded: int
    selection_reason: str
    transition_kind: str
    query_overlap_percent: int
    segments: tuple[TopicSegmentEvidence, ...]
    bounded_history_rows: int
    read_only: bool = True
    provider_invoked: bool = False
    writes_state: bool = False
    rewrites_transcript: bool = False
    contains_context_content: bool = False
    schema_version: str = TOPIC_SEGMENTATION_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result["type"] = "conversation_topic_segmentation"
        result["active_turn_indices"] = list(self.active_turn_indices)
        result["active_turn_offsets"] = list(self.active_turn_offsets)
        result["segments"] = [segment.public_summary() for segment in self.segments]
        return result


def _text(row: Mapping[str, Any]) -> str:
    user = " ".join(str(row.get("user_message") or row.get("user") or "").split())
    assistant = " ".join(str(row.get("assistant_response") or row.get("assistant") or row.get("response") or "").split())
    return " ".join(part for part in (user, assistant) if part)


def _words(value: Any) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9']+", str(value or "").casefold())
        if len(word) >= 3 and word not in _STOP
    }


def _overlap_percent(left: set[str], right: set[str]) -> int:
    if not left or not right:
        return 0
    return int(round(100 * len(left & right) / max(1, min(len(left), len(right)))))


def _segment_digest(indices: Sequence[int], token_union: set[str]) -> str:
    material = f"{','.join(map(str, indices))}\n{' '.join(sorted(token_union))}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _matched_index_from_offset(row_count: int, offset: Any) -> int | None:
    if not isinstance(offset, int) or offset < 0 or offset >= row_count:
        return None
    return row_count - 1 - offset


def segment_conversation_topics(
    message: str,
    history: Iterable[Mapping[str, Any]],
    *,
    transition: Any = None,
) -> tuple[list[Mapping[str, Any]], TopicSegmentationPlan]:
    source_rows = [row for row in history if isinstance(row, Mapping) and _text(row)]
    rows = source_rows[-MAX_SEGMENT_HISTORY_ROWS:]
    if not rows:
        plan = TopicSegmentationPlan(0, "", (), (), 0, 0, "no_history", "no_history", 0, (), 0)
        return [], plan

    segments: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        tokens = _words(_text(row))
        if not segments:
            segments.append({"indices": [index], "tokens": set(tokens)})
            continue
        current = segments[-1]
        previous_tokens = _words(_text(rows[index - 1]))
        continuity = max(_overlap_percent(tokens, previous_tokens), _overlap_percent(tokens, current["tokens"]))
        if continuity >= _MIN_CONTINUITY_PERCENT:
            current["indices"].append(index)
            current["tokens"].update(tokens)
        elif len(segments) < MAX_SEGMENTS:
            segments.append({"indices": [index], "tokens": set(tokens)})
        else:
            segments[-1]["indices"].append(index)
            segments[-1]["tokens"].update(tokens)

    query_words = _words(message)
    transition_kind = str(getattr(transition, "transition_kind", "") or "ambiguous_transition")
    matched_index = _matched_index_from_offset(len(rows), getattr(transition, "matched_turn_offset", None))
    active_index: int | None = None
    selection_reason = "latest_segment_default"

    if transition_kind == "topic_shift":
        active_index = None
        selection_reason = "explicit_or_bounded_topic_shift"
    elif transition_kind in {"resumption", "return"} and matched_index is not None:
        active_index = next((i for i, segment in enumerate(segments) if matched_index in segment["indices"]), None)
        selection_reason = "matched_prior_segment"
    elif transition_kind in {"continuation", "interruption"}:
        active_index = len(segments) - 1
        selection_reason = "latest_segment_continuity"
    else:
        scores = [_overlap_percent(query_words, segment["tokens"]) for segment in segments]
        best = max(range(len(scores)), key=scores.__getitem__) if scores else None
        if best is not None and scores[best] >= _MIN_QUERY_MATCH_PERCENT:
            active_index = best
            selection_reason = "bounded_query_match"
        else:
            active_index = len(segments) - 1
            selection_reason = "latest_segment_default"

    public_segments: list[TopicSegmentEvidence] = []
    for index, segment in enumerate(segments):
        indices = tuple(segment["indices"])
        offsets = [len(rows) - 1 - item for item in indices]
        public_segments.append(TopicSegmentEvidence(
            segment_id=_segment_digest(indices, segment["tokens"]),
            start_offset=max(offsets),
            end_offset=min(offsets),
            turn_count=len(indices),
            query_overlap_percent=_overlap_percent(query_words, segment["tokens"]),
            latest_segment=index == len(segments) - 1,
        ))

    active_indices = tuple(segments[active_index]["indices"]) if active_index is not None else ()
    active_rows = [rows[index] for index in active_indices]
    active_offsets = tuple(len(rows) - 1 - index for index in active_indices)
    active_segment_id = public_segments[active_index].segment_id if active_index is not None else ""
    query_overlap = public_segments[active_index].query_overlap_percent if active_index is not None else 0
    plan = TopicSegmentationPlan(
        segment_count=len(segments),
        active_segment_id=active_segment_id,
        active_turn_indices=active_indices,
        active_turn_offsets=active_offsets,
        active_turn_count=len(active_rows),
        unrelated_turns_excluded=max(0, len(rows) - len(active_rows)),
        selection_reason=selection_reason,
        transition_kind=transition_kind,
        query_overlap_percent=query_overlap,
        segments=tuple(public_segments),
        bounded_history_rows=len(rows),
    )
    return active_rows, plan


def topic_segmentation_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "messages", "user_message", "assistant_response", "content", "thought", "summary", "text",
        "prompt", "transcript", "memory", "provider_payload", "credentials", "vector", "embedding", "receipt",
        "chain_of_thought", "reasoning_trace",
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
