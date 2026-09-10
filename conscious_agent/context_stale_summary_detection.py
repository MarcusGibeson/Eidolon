from __future__ import annotations

"""Deterministic v1085.7 stale continuity-summary detection.

Summaries are filtered only by exact correction digests, explicit lineage, or
source records whose retraction/deletion state is known. Similar wording alone
is never treated as a correction.
"""

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "1"
SUMMARY_LINK_FIELDS = (
    "supersedes_summary_id",
    "corrects_summary_id",
    "retracts_summary_id",
    "deletes_summary_id",
    "correction_target_summary_id",
)


def content_digest(value: Any) -> str:
    normalized = " ".join(str(value or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StaleSummaryEvidence:
    summary_count: int
    eligible_count: int
    stale_count: int
    corrected_conflicts: int
    retracted_conflicts: int
    deleted_conflicts: int
    current_session_conflicts: int
    exact_digest_matches: int
    explicit_lineage_matches: int
    read_only: bool = True
    provider_invoked: bool = False
    writes_state: bool = False
    rewrites_summary: bool = False
    contains_summary_content: bool = False
    schema_version: str = SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result["type"] = "stale_summary_detection"
        return result


def _record_ids(values: Any) -> set[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        return set()
    return {str(value) for value in values if str(value or "").strip()}


def _superseded_digests(records: Iterable[Mapping[str, Any]]) -> set[str]:
    result: set[str] = set()
    for record in records:
        values = record.get("superseded_content_digests") or ()
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
            result.update(str(value) for value in values if str(value or "").strip())
    return result


def _linked_summary_ids(records: Iterable[Mapping[str, Any]]) -> set[str]:
    return {
        str(record.get(field))
        for record in records
        for field in SUMMARY_LINK_FIELDS
        if str(record.get(field) or "").strip()
    }


def filter_stale_continuity_summaries(
    summaries: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
    *,
    current_session_records: Iterable[Mapping[str, Any]] = (),
) -> tuple[list[Mapping[str, Any]], StaleSummaryEvidence]:
    """Return eligible summaries and content-free stale-summary evidence."""

    memory_records = [record for record in records if isinstance(record, Mapping)]
    session_records = [record for record in current_session_records if isinstance(record, Mapping)]
    all_evidence = [*memory_records, *session_records]
    superseded = _superseded_digests(all_evidence)
    linked_summary_ids = _linked_summary_ids(all_evidence)
    current_linked_ids = _linked_summary_ids(session_records)

    statuses_by_id = {
        str(record.get("id") or ""): str(record.get("status") or "").casefold()
        for record in memory_records
        if str(record.get("id") or "").strip()
    }

    eligible: list[Mapping[str, Any]] = []
    corrected = 0
    retracted = 0
    deleted = 0
    current_session_conflicts = 0
    exact_matches = 0
    lineage_matches = 0
    source = [summary for summary in summaries if isinstance(summary, Mapping)]

    for summary in source:
        summary_id = str(summary.get("id") or "").strip()
        digest = str(summary.get("content_digest") or "").strip() or content_digest(
            summary.get("content") or summary.get("summary") or ""
        )
        source_ids = _record_ids(summary.get("source_record_ids") or ())
        stale = False

        if digest in superseded:
            corrected += 1
            exact_matches += 1
            stale = True
        if summary_id and summary_id in linked_summary_ids:
            corrected += 1
            lineage_matches += 1
            stale = True
        if summary_id and summary_id in current_linked_ids:
            current_session_conflicts += 1
            stale = True

        source_statuses = {statuses_by_id.get(source_id, "") for source_id in source_ids}
        if "retracted" in source_statuses:
            retracted += 1
            stale = True
        if "deleted" in source_statuses:
            deleted += 1
            stale = True

        if not stale:
            eligible.append(summary)

    evidence = StaleSummaryEvidence(
        summary_count=len(source),
        eligible_count=len(eligible),
        stale_count=len(source) - len(eligible),
        corrected_conflicts=corrected,
        retracted_conflicts=retracted,
        deleted_conflicts=deleted,
        current_session_conflicts=current_session_conflicts,
        exact_digest_matches=exact_matches,
        explicit_lineage_matches=lineage_matches,
    )
    return eligible, evidence


def stale_summary_evidence_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "summary", "prompt", "transcript", "message", "memory",
        "provider_payload", "credentials", "vector", "embedding", "reasoning",
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
