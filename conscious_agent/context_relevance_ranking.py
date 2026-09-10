from __future__ import annotations

"""Deterministic v1085.1 relevance ranking for eligible context records.

Ranking is local and content-safe. Raw candidate text is used only in-process to
compute bounded component scores; public evidence contains digests and codes.
"""

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Iterable, Mapping

CONTEXT_RELEVANCE_SCHEMA_VERSION = "1"
MAX_RANKED_CANDIDATES = 64
_RELATIONSHIP_TYPES = {
    "nickname", "preferred_name", "user_nickname", "preference", "user_preference",
    "relationship", "relationship_memory", "important_moment", "shared_moment",
    "commitment", "personal_fact", "user_mood", "mood",
}
_EXCLUDED_STATES = {"deleted", "retracted", "disabled", "rejected", "blocked", "expired", "stale"}


@dataclass(frozen=True)
class RankedContextCandidate:
    source_index: int
    source_kind: str
    evidence_digest: str
    lexical_score: int
    recency_score: int
    relationship_score: int
    status_score: int
    operator_curation_score: int
    importance_score: int
    total_score: int
    reason_codes: tuple[str, ...]
    relationship_relevant: bool
    operator_curated: bool
    salient: bool
    schema_version: str = CONTEXT_RELEVANCE_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        return asdict(self)


def _text(record: Mapping[str, Any]) -> str:
    for key in ("content", "thought", "summary", "text", "user_message", "assistant_response"):
        value = record.get(key)
        if value not in (None, ""):
            return " ".join(str(value).split())
    return ""


def _words(value: str) -> set[str]:
    current: list[str] = []
    result: set[str] = set()
    for char in str(value or "").casefold():
        if char.isalnum() or char in {"_", "-"}:
            current.append(char)
        elif current:
            token = "".join(current)
            if len(token) >= 3:
                result.add(token)
            current = []
    if current:
        token = "".join(current)
        if len(token) >= 3:
            result.add(token)
    return result


def _importance(record: Mapping[str, Any]) -> int:
    value = record.get("importance")
    if isinstance(value, (int, float)):
        return 4 if value >= 0.8 or value >= 3 else 2 if value >= 0.5 or value >= 2 else 0
    lowered = str(value or "").strip().casefold()
    if lowered in {"critical", "core", "high", "important"}:
        return 4
    if lowered in {"medium", "normal"}:
        return 2
    memory_type = str(record.get("type") or "").strip().casefold()
    return 4 if memory_type in {"core_memory", "identity", "identity_memory", "commitment", "goal", "long_term_goal"} else 0


def _operator_curation(record: Mapping[str, Any]) -> tuple[int, bool]:
    source = str(record.get("source") or "").strip().casefold()
    provenance = record.get("provenance") if isinstance(record.get("provenance"), Mapping) else {}
    origin = str(provenance.get("origin") or "").strip().casefold()
    curated = bool(record.get("operator_curated")) or source.startswith("operator_relationship_curation")
    retained = bool(record.get("retention_confirmed")) or str(record.get("curation_state") or "").casefold() == "retained"
    explicit = bool(record.get("operator_explicit")) or origin in {"operator_explicit", "operator_reviewed_exact_content"}
    if curated and retained:
        return 4, True
    if curated or retained:
        return 3, True
    if explicit:
        return 2, True
    return 0, False


def _status(record: Mapping[str, Any]) -> int:
    state = str(record.get("state") or record.get("status") or record.get("curation_state") or "").strip().casefold()
    if state in _EXCLUDED_STATES:
        return -8
    if state in {"active", "current", "open", "retained", "approved", "accepted"}:
        return 2
    return 1


def rank_context_records(
    records: Iterable[Mapping[str, Any]],
    query: str,
    *,
    source_kind: str = "curated_memory",
) -> list[tuple[Mapping[str, Any], RankedContextCandidate]]:
    rows = [
        record for record in records
        if isinstance(record, Mapping) and _text(record) and _status(record) >= 0
    ][:MAX_RANKED_CANDIDATES]
    query_words = _words(query)
    denominator = max(1, len(rows) - 1)
    ranked: list[tuple[Mapping[str, Any], RankedContextCandidate]] = []
    for index, record in enumerate(rows):
        text = _text(record)
        lexical = min(4, len(query_words & _words(text)))
        recency = 4 if len(rows) == 1 else int(round((index / denominator) * 4))
        memory_type = str(record.get("type") or "").strip().casefold()
        relationship_relevant = bool(record.get("relationship_relevant")) or memory_type in _RELATIONSHIP_TYPES
        relationship = 2 if relationship_relevant else 0
        status = _status(record)
        curation, operator_curated = _operator_curation(record)
        importance = _importance(record)
        total = lexical * 3 + recency * 2 + relationship * 2 + status + curation * 2 + importance * 2
        reasons: list[str] = []
        if lexical:
            reasons.append("lexical_match")
        if recency >= 3:
            reasons.append("recent")
        if relationship_relevant:
            reasons.append("relationship_relevant")
        if status >= 2:
            reasons.append("active_status")
        if operator_curated:
            reasons.append("operator_curated")
        if importance >= 4:
            reasons.append("high_importance")
        digest = hashlib.sha256(f"{source_kind}\n{memory_type}\n{text.casefold()}".encode("utf-8")).hexdigest()[:24]
        evidence = RankedContextCandidate(
            source_index=index,
            source_kind=source_kind,
            evidence_digest=digest,
            lexical_score=lexical,
            recency_score=recency,
            relationship_score=relationship,
            status_score=status,
            operator_curation_score=curation,
            importance_score=importance,
            total_score=total,
            reason_codes=tuple(reasons[:8]),
            relationship_relevant=relationship_relevant,
            operator_curated=operator_curated,
            salient=importance >= 4 or curation >= 3,
        )
        ranked.append((record, evidence))
    ranked.sort(
        key=lambda pair: (
            pair[1].total_score,
            pair[1].lexical_score,
            pair[1].operator_curation_score,
            pair[1].importance_score,
            pair[1].recency_score,
            pair[1].source_index,
        ),
        reverse=True,
    )
    return ranked


def ranking_public_summary(ranked: Iterable[tuple[Mapping[str, Any], RankedContextCandidate]]) -> dict[str, Any]:
    evidence = [row[1] for row in ranked]
    return {
        "type": "bounded_context_relevance_ranking",
        "schema_version": CONTEXT_RELEVANCE_SCHEMA_VERSION,
        "candidate_count": len(evidence),
        "top_total_score": max((row.total_score for row in evidence), default=0),
        "lexical_match_count": sum(1 for row in evidence if row.lexical_score > 0),
        "relationship_relevant_count": sum(1 for row in evidence if row.relationship_relevant),
        "operator_curated_count": sum(1 for row in evidence if row.operator_curated),
        "salient_count": sum(1 for row in evidence if row.salient),
        "evidence": [row.public_summary() for row in evidence[:12]],
        "content_free": True,
        "read_only": True,
        "provider_invoked": False,
        "writes_state": False,
    }
