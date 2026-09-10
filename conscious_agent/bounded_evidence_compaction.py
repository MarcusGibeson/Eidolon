from __future__ import annotations

"""v1192.0-v1192.2 bounded, content-free evidence compaction foundations."""

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_VERSION = "v1192.2"
SCHEMA = (
    "evidence_id", "sequence", "previous_evidence_digest", "snapshot_digest",
    "context_digest", "artifact_digest", "receipt_digest", "domain",
    "evidence_kind", "outcome", "uncertainty_code", "approval_state",
    "rollback_state", "authority_state", "evidence_digest",
)
ALLOWED_DOMAINS = {"conversation", "cognition", "reasoning", "planning", "campaign", "approval", "action", "result", "learning"}
ALLOWED_KINDS = {"observation", "decision", "transition", "result", "learning"}
ALLOWED_OUTCOMES = {"retained", "revised", "suspended", "completed", "failed", "blocked", "cancelled", "superseded"}
ALLOWED_UNCERTAINTY = {"none", "bounded", "unresolved", "conflicted"}
ALLOWED_APPROVAL = {"not_required", "review_required", "approved", "rejected", "deferred"}
ALLOWED_ROLLBACK = {"not_applicable", "available", "verified", "unavailable"}
PRIVATE_KEYS = {"prompt", "conversation", "memory", "secret", "raw_source", "patch", "stdout", "stderr", "provider_payload", "private_reasoning", "content", "text"}


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _is_digest(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(ch in "0123456789abcdef" for ch in token)


def create_evidence_record(*, evidence_id: str, sequence: int, previous_evidence_digest: str,
                           snapshot_digest: str, context_digest: str, artifact_digest: str,
                           receipt_digest: str, domain: str, evidence_kind: str, outcome: str,
                           uncertainty_code: str, approval_state: str, rollback_state: str) -> dict[str, Any]:
    row = {
        "evidence_id": str(evidence_id), "sequence": int(sequence),
        "previous_evidence_digest": str(previous_evidence_digest),
        "snapshot_digest": str(snapshot_digest), "context_digest": str(context_digest),
        "artifact_digest": str(artifact_digest), "receipt_digest": str(receipt_digest),
        "domain": str(domain), "evidence_kind": str(evidence_kind), "outcome": str(outcome),
        "uncertainty_code": str(uncertainty_code), "approval_state": str(approval_state),
        "rollback_state": str(rollback_state), "authority_state": "separate_not_granted",
    }
    row["evidence_digest"] = _digest(row)
    return row


def validate_evidence_records(records: Sequence[Mapping[str, Any]], *, snapshot_digest: str,
                              context_digest: str, max_records: int = 64) -> list[str]:
    errors: list[str] = []
    rows = [dict(row) for row in records]
    if not rows: errors.append("empty_evidence")
    if len(rows) > max_records: errors.append("oversized_evidence")
    ids: list[str] = []; sequences: list[int] = []; previous = ""
    for index, row in enumerate(rows):
        lower = {str(key).lower() for key in row}
        if lower & PRIVATE_KEYS: errors.append("private_field")
        if set(row) != set(SCHEMA): errors.append("malformed_evidence_schema")
        ids.append(str(row.get("evidence_id") or ""))
        try: seq = int(row.get("sequence"))
        except (TypeError, ValueError): seq = -1
        sequences.append(seq)
        if seq != index: errors.append("non_contiguous_sequence")
        if row.get("previous_evidence_digest") != previous: errors.append("broken_lineage")
        if row.get("snapshot_digest") != snapshot_digest: errors.append("stale_snapshot")
        if row.get("context_digest") != context_digest: errors.append("stale_context")
        for key in ("snapshot_digest", "context_digest", "artifact_digest", "receipt_digest", "evidence_digest"):
            if not _is_digest(row.get(key)): errors.append("malformed_digest")
        if row.get("domain") not in ALLOWED_DOMAINS: errors.append("unsupported_domain")
        if row.get("evidence_kind") not in ALLOWED_KINDS: errors.append("unsupported_evidence_kind")
        if row.get("outcome") not in ALLOWED_OUTCOMES: errors.append("unsupported_outcome")
        if row.get("uncertainty_code") not in ALLOWED_UNCERTAINTY: errors.append("unsupported_uncertainty")
        if row.get("approval_state") not in ALLOWED_APPROVAL: errors.append("unsupported_approval_state")
        if row.get("rollback_state") not in ALLOWED_ROLLBACK: errors.append("unsupported_rollback_state")
        if row.get("authority_state") != "separate_not_granted": errors.append("authority_expansion")
        candidate = dict(row); claimed = candidate.pop("evidence_digest", "")
        if claimed != _digest(candidate): errors.append("evidence_tamper")
        previous = str(row.get("evidence_digest") or "")
    if len(ids) != len(set(ids)): errors.append("duplicate_evidence_id")
    if len(sequences) != len(set(sequences)): errors.append("duplicate_sequence")
    return sorted(set(errors))


def compact_evidence(records: Sequence[Mapping[str, Any]], *, snapshot_digest: str,
                     context_digest: str, max_records: int = 64) -> dict[str, Any]:
    rows = [dict(row) for row in records]
    errors = validate_evidence_records(rows, snapshot_digest=snapshot_digest, context_digest=context_digest, max_records=max_records)
    compact_rows = [[row.get(field) for field in SCHEMA] for row in rows] if not errors else []
    body = {
        "schema": list(SCHEMA), "rows": compact_rows, "snapshot_digest": snapshot_digest,
        "context_digest": context_digest, "record_count": len(rows),
        "first_sequence": rows[0].get("sequence") if rows else None,
        "last_sequence": rows[-1].get("sequence") if rows else None,
        "terminal_evidence_digest": rows[-1].get("evidence_digest") if rows else "",
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "compacted" if not errors else "blocked",
        "errors": errors, "error_count": len(errors),
        "compaction": body if not errors else {},
        "compaction_digest": _digest(body) if not errors else "",
        "content_free": True, "lossless_claim": not errors,
        "execution_invoked": False, "approval_consumed": False,
        "rollback_invoked": False, "authority_granted": False,
    }


def expand_compaction(report: Mapping[str, Any], *, expected_snapshot_digest: str,
                      expected_context_digest: str) -> dict[str, Any]:
    errors: list[str] = []
    if report.get("status") != "compacted": errors.append("compaction_not_available")
    body = dict(report.get("compaction") or {})
    if report.get("compaction_digest") != _digest(body): errors.append("compaction_tamper")
    if body.get("snapshot_digest") != expected_snapshot_digest: errors.append("stale_compaction_snapshot")
    if body.get("context_digest") != expected_context_digest: errors.append("stale_compaction_context")
    if tuple(body.get("schema") or ()) != SCHEMA: errors.append("unsupported_compaction_schema")
    rows: list[dict[str, Any]] = []
    if not errors:
        for values in body.get("rows") or []:
            if not isinstance(values, list) or len(values) != len(SCHEMA):
                errors.append("malformed_compact_row"); continue
            rows.append(dict(zip(SCHEMA, values)))
        errors.extend(validate_evidence_records(rows, snapshot_digest=expected_snapshot_digest, context_digest=expected_context_digest))
        if len(rows) != body.get("record_count"): errors.append("record_count_mismatch")
        if rows and rows[-1].get("evidence_digest") != body.get("terminal_evidence_digest"): errors.append("terminal_digest_mismatch")
    return {
        "status": "expanded" if not errors else "blocked", "errors": sorted(set(errors)),
        "records": rows if not errors else [], "record_count": len(rows) if not errors else 0,
        "content_free": True, "execution_invoked": False, "authority_granted": False,
    }


def verify_compaction_equivalence(records: Sequence[Mapping[str, Any]], report: Mapping[str, Any], *,
                                  snapshot_digest: str, context_digest: str) -> dict[str, Any]:
    expanded = expand_compaction(report, expected_snapshot_digest=snapshot_digest, expected_context_digest=context_digest)
    original = [dict(row) for row in records]
    equivalent = expanded.get("status") == "expanded" and expanded.get("records") == original
    return {
        "status": "equivalent" if equivalent else "blocked",
        "equivalent": equivalent, "original_digest": _digest(original),
        "expanded_digest": _digest(expanded.get("records") or []),
        "record_count": len(original), "errors": expanded.get("errors", []),
        "content_free": True, "historical_truth_preserved": equivalent,
        "approval_truth_preserved": equivalent, "rollback_truth_preserved": equivalent,
        "uncertainty_truth_preserved": equivalent, "authority_separation_preserved": equivalent,
        "execution_invoked": False, "authority_granted": False,
    }


def public_compaction_summary(report: Mapping[str, Any], equivalence: Mapping[str, Any]) -> dict[str, Any]:
    body = report.get("compaction") or {}
    return {
        "contract_version": CONTRACT_VERSION, "status": report.get("status"),
        "record_count": body.get("record_count", 0), "first_sequence": body.get("first_sequence"),
        "last_sequence": body.get("last_sequence"), "equivalent": equivalence.get("equivalent") is True,
        "historical_truth_preserved": equivalence.get("historical_truth_preserved") is True,
        "approval_truth_preserved": equivalence.get("approval_truth_preserved") is True,
        "rollback_truth_preserved": equivalence.get("rollback_truth_preserved") is True,
        "uncertainty_truth_preserved": equivalence.get("uncertainty_truth_preserved") is True,
        "authority_separation_preserved": equivalence.get("authority_separation_preserved") is True,
        "content_free": True, "execution_invoked": False, "authority_granted": False,
    }
