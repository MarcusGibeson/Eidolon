from __future__ import annotations

"""v1090.4 bounded descriptive comparison of registered repair candidates."""

from typing import Any, Iterable, Mapping
import hashlib
import json

from conversation_evaluation_finding import EvaluationFindingError
from repair_candidate_registration import build_repair_candidate_registrations, load_registered_repair_candidate_private
from repair_candidate_review import build_repair_candidate_review
from repair_candidate_verification_evidence import build_repair_candidate_verification_evidence

REPAIR_CANDIDATE_COMPARISON_SCHEMA_VERSION = "1"
MIN_REPAIR_CANDIDATES_FOR_COMPARISON = 2
MAX_REPAIR_CANDIDATES_FOR_COMPARISON = 8


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _normalize(candidate_ids: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for raw in candidate_ids:
        token = str(raw or "").strip()
        if token and token not in normalized:
            normalized.append(token)
    if len(normalized) < MIN_REPAIR_CANDIDATES_FOR_COMPARISON:
        raise EvaluationFindingError("At least two distinct repair candidates are required for comparison.")
    if len(normalized) > MAX_REPAIR_CANDIDATES_FOR_COMPARISON:
        raise EvaluationFindingError(
            f"At most {MAX_REPAIR_CANDIDATES_FOR_COMPARISON} repair candidates may be compared."
        )
    return normalized


def _row(finding_id: str, candidate_id: str) -> dict[str, Any]:
    _, candidate = load_registered_repair_candidate_private(finding_id, candidate_id)
    review = build_repair_candidate_review(finding_id, candidate_id)
    verification = build_repair_candidate_verification_evidence(finding_id, candidate_id)
    counts = dict(verification.get("result_counts") or {})
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "artifact_sha256": str(candidate.get("artifact_sha256") or ""),
        "source_manifest_sha256": str(candidate.get("source_manifest_sha256") or ""),
        "registration_evidence_digest": str(candidate.get("evidence_digest") or ""),
        "review_state": str(candidate.get("review_state") or "registered"),
        "reproducibility_status_at_registration": str(
            candidate.get("reproducibility_status_at_registration") or "not_reviewed"
        ),
        "review_event_count": max(0, int(review.get("review_event_count") or 0)),
        "verification_evidence_count": max(0, int(verification.get("verification_evidence_count") or 0)),
        "passing_evidence_count": max(0, int(counts.get("pass") or 0)),
        "failing_evidence_count": max(0, int(counts.get("fail") or 0)),
        "inconclusive_evidence_count": max(0, int(counts.get("inconclusive") or 0)),
        "verified_passed_checks": max(0, int(verification.get("total_passed_checks") or 0)),
        "verified_total_checks": max(0, int(verification.get("total_checks") or 0)),
        "verified_suite_count": max(0, int(verification.get("total_suite_count") or 0)),
        "review_digest": str(review.get("review_digest") or ""),
        "verification_evidence_digest": str(verification.get("verification_evidence_digest") or ""),
    }


def build_repair_candidate_comparison(finding_id: str, candidate_ids: Iterable[str]) -> dict[str, Any]:
    registrations = build_repair_candidate_registrations(finding_id)
    available = {str(row.get("candidate_id") or "") for row in registrations.get("candidates") or ()}
    normalized = _normalize(candidate_ids)
    missing = [candidate_id for candidate_id in normalized if candidate_id not in available]
    if missing:
        raise EvaluationFindingError("One or more repair candidates are not registered to the finding.")
    rows = [_row(finding_id, candidate_id) for candidate_id in normalized]
    baseline = rows[0]
    delta_fields = (
        "review_event_count",
        "verification_evidence_count",
        "passing_evidence_count",
        "failing_evidence_count",
        "inconclusive_evidence_count",
        "verified_passed_checks",
        "verified_total_checks",
        "verified_suite_count",
    )
    deltas = []
    for row in rows[1:]:
        deltas.append(
            {
                "baseline_candidate_id": baseline["candidate_id"],
                "candidate_id": row["candidate_id"],
                "count_deltas": {field: int(row[field]) - int(baseline[field]) for field in delta_fields},
                "same_candidate_kind": row["candidate_kind"] == baseline["candidate_kind"],
                "same_review_state": row["review_state"] == baseline["review_state"],
                "same_source_manifest": row["source_manifest_sha256"] == baseline["source_manifest_sha256"],
                "same_reproducibility_status": (
                    row["reproducibility_status_at_registration"]
                    == baseline["reproducibility_status_at_registration"]
                ),
            }
        )
    stable = {
        "finding_id": str(finding_id or ""),
        "candidate_count": len(rows),
        "minimum_candidates": MIN_REPAIR_CANDIDATES_FOR_COMPARISON,
        "maximum_candidates": MAX_REPAIR_CANDIDATES_FOR_COMPARISON,
        "baseline_candidate_id": baseline["candidate_id"],
        "candidates": rows,
        "deltas": deltas,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_comparison",
        "schema_version": REPAIR_CANDIDATE_COMPARISON_SCHEMA_VERSION,
        **stable,
        "comparison_digest": _digest(stable),
        "descriptive_counts_only": True,
        "candidates_ranked": False,
        "winner_selected": False,
        "priority_assigned": False,
        "autonomous_prioritization": False,
        "statistical_significance_claimed": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "patch_generated": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "provider_invoked": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def repair_candidate_comparison_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_note", "note", "notes", "private_label", "private_reference", "content", "text",
        "transcript", "prompt", "provider_payload", "credentials", "vectors", "hidden_reasoning",
        "chain_of_thought",
    }
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if forbidden & {str(key) for key in current}:
                return True
            stack.extend(current.values())
        elif isinstance(current, (list, tuple)):
            stack.extend(current)
    return False
