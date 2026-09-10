from __future__ import annotations

"""v1085.5 deterministic correction-aware retrieval.

Stale records are suppressed only by exact superseded-content digests or explicit
lineage/linkage fields. Lexical similarity alone is never correction evidence.
"""

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

CORRECTION_RETRIEVAL_SCHEMA_VERSION = "1"
MAX_CORRECTION_RECORDS = 128
_LINK_FIELDS = ("superseded_by", "replaced_by", "corrected_by", "correction_target_id")
_GROUP_FIELDS = ("correction_group_id", "fact_key", "fact_identity")


@dataclass(frozen=True)
class CorrectionRetrievalEvidence:
    input_count: int
    eligible_count: int
    exact_digest_suppressed: int
    explicit_link_suppressed: int
    ambiguous_similarity_suppressed: int
    correction_record_count: int
    explicit_group_count: int
    suppression_digests: tuple[str, ...]
    read_only: bool = True
    provider_invoked: bool = False
    writes_state: bool = False
    rewrites_transcript: bool = False
    lexical_inference_used: bool = False
    schema_version: str = CORRECTION_RETRIEVAL_SCHEMA_VERSION

    def public_summary(self) -> dict[str, Any]:
        result = asdict(self)
        result["type"] = "correction_aware_context_retrieval"
        result["content_free"] = True
        return result


def _text(record: Mapping[str, Any]) -> str:
    for key in ("content", "thought", "summary", "text"):
        if record.get(key) not in (None, ""):
            return " ".join(str(record.get(key)).split())
    return ""


def content_digest(value: str) -> str:
    return hashlib.sha256(" ".join(str(value or "").split()).encode("utf-8")).hexdigest()


def normalized_fact_fingerprint(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", " ".join(str(value or "").casefold().split())).strip()


def _explicit_correction_records(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for record in records:
        lineage = record.get("correction_lineage") if isinstance(record.get("correction_lineage"), list) else []
        if any(isinstance(row, Mapping) and row.get("operator_explicit") is True for row in lineage):
            result.append(record)
    return result


def filter_correction_aware_records(
    records: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], CorrectionRetrievalEvidence]:
    rows = [record for record in records if isinstance(record, Mapping)][:MAX_CORRECTION_RECORDS]
    corrections = _explicit_correction_records(rows)
    superseded_digests: set[str] = set()
    corrected_ids: set[str] = set()
    corrected_groups: set[tuple[str, str]] = set()
    for record in rows:
        for value in record.get("superseded_content_digests") or ():
            if value:
                superseded_digests.add(str(value))
    for record in corrections:
        record_id = str(record.get("id") or "").strip()
        if record_id:
            corrected_ids.add(record_id)
        for lineage in record.get("correction_lineage") or ():
            if isinstance(lineage, Mapping) and lineage.get("operator_explicit") is True:
                digest = str(lineage.get("previous_content_digest") or "")
                if digest:
                    superseded_digests.add(digest)
        for field in _GROUP_FIELDS:
            value = str(record.get(field) or "").strip()
            if value:
                corrected_groups.add((field, value))

    eligible: list[dict[str, Any]] = []
    exact_suppressed = 0
    link_suppressed = 0
    suppression_digests: list[str] = []
    for record in rows:
        text = _text(record)
        digest = content_digest(text) if text else ""
        if digest and digest in superseded_digests:
            exact_suppressed += 1
            suppression_digests.append(hashlib.sha256(f"exact:{digest}".encode()).hexdigest()[:20])
            continue
        explicit_link = any(str(record.get(field) or "").strip() in corrected_ids for field in _LINK_FIELDS)
        explicit_group = any(
            (field, str(record.get(field) or "").strip()) in corrected_groups
            and str(record.get(field) or "").strip()
            and record not in corrections
            for field in _GROUP_FIELDS
        )
        if explicit_link or explicit_group:
            link_suppressed += 1
            material = "|".join(str(record.get(field) or "") for field in (*_LINK_FIELDS, *_GROUP_FIELDS))
            suppression_digests.append(hashlib.sha256(f"link:{material}".encode()).hexdigest()[:20])
            continue
        eligible.append(dict(record))

    evidence = CorrectionRetrievalEvidence(
        input_count=len(rows),
        eligible_count=len(eligible),
        exact_digest_suppressed=exact_suppressed,
        explicit_link_suppressed=link_suppressed,
        ambiguous_similarity_suppressed=0,
        correction_record_count=len(corrections),
        explicit_group_count=len(corrected_groups),
        suppression_digests=tuple(suppression_digests[:24]),
    )
    return eligible, evidence


def candidate_reintroduces_superseded_fact(
    candidate: Mapping[str, Any],
    existing_records: Iterable[Mapping[str, Any]],
) -> tuple[bool, str]:
    rows = [dict(record) for record in existing_records if isinstance(record, Mapping)]
    combined = [*rows, dict(candidate)]
    eligible, evidence = filter_correction_aware_records(combined)
    candidate_id = str(candidate.get("id") or "")
    retained = any(
        (candidate_id and str(row.get("id") or "") == candidate_id)
        or (not candidate_id and _text(row) == _text(candidate))
        for row in eligible
    )
    if retained:
        return False, "no_explicit_supersession_evidence"
    reason = "exact_superseded_digest" if evidence.exact_digest_suppressed else "explicit_lineage_link"
    return True, reason


def correction_retrieval_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "message", "user_message", "assistant_response", "content", "thought", "summary", "text", "prompt",
        "transcript", "memory", "previous_content", "provider_payload", "credentials", "vector", "embedding",
        "receipt", "chain_of_thought", "reasoning_trace",
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
