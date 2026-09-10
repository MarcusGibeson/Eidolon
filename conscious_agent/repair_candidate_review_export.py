from __future__ import annotations

"""v1090.7 deterministic privacy-safe repair-candidate review export."""

from typing import Any, Mapping
import hashlib
import json

from repair_candidate_lineage import build_repair_candidate_lineage
from repair_candidate_registration import build_repair_candidate_registrations
from repair_candidate_review import build_repair_candidate_review
from repair_candidate_verification_evidence import build_repair_candidate_verification_evidence
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

REPAIR_CANDIDATE_REVIEW_EXPORT_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_repair_candidate_review_export(finding_id: str, candidate_id: str) -> dict[str, Any]:
    registrations = build_repair_candidate_registrations(finding_id)
    candidate = next(
        (row for row in list(registrations.get("candidates") or ()) if str(row.get("candidate_id") or "") == str(candidate_id or "")),
        None,
    )
    if candidate is None:
        from conversation_evaluation_finding import EvaluationFindingError
        raise EvaluationFindingError("Repair candidate registration not found.")
    review = build_repair_candidate_review(finding_id, candidate_id)
    verification = build_repair_candidate_verification_evidence(finding_id, candidate_id)
    lineage = build_repair_candidate_lineage(finding_id)
    related_edges = [
        edge for edge in list(lineage.get("lineage_edges") or ())
        if str(edge.get("predecessor_candidate_id") or "") == str(candidate_id or "")
        or str(edge.get("successor_candidate_id") or "") == str(candidate_id or "")
    ]
    document_data = {
        "type": "desktop_alpha_repair_candidate_review_export_document",
        "schema_version": REPAIR_CANDIDATE_REVIEW_EXPORT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "finding_id": str(finding_id or ""),
        "finding_revision": max(0, int(registrations.get("finding_revision") or 0)),
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "artifact_sha256": str(candidate.get("artifact_sha256") or ""),
        "source_manifest_sha256": str(candidate.get("source_manifest_sha256") or ""),
        "registration_evidence_digest": str(candidate.get("evidence_digest") or ""),
        "review_state": str(candidate.get("review_state") or "registered"),
        "registered_at": str(candidate.get("registered_at") or ""),
        "updated_at": str(candidate.get("updated_at") or ""),
        "reproducibility_status_at_registration": str(candidate.get("reproducibility_status_at_registration") or "not_reviewed"),
        "private_label_present": bool(candidate.get("private_label_present")),
        "private_label_digest": str(candidate.get("private_label_digest") or ""),
        "private_reference_present": bool(candidate.get("private_reference_present")),
        "private_reference_digest": str(candidate.get("private_reference_digest") or ""),
        "review_event_count": max(0, int(review.get("review_event_count") or 0)),
        "review_events": list(review.get("review_events") or ()),
        "review_digest": str(review.get("review_digest") or ""),
        "verification_evidence_count": max(0, int(verification.get("verification_evidence_count") or 0)),
        "verification_result_counts": dict(verification.get("result_counts") or {}),
        "verification_evidence_kind_counts": dict(verification.get("evidence_kind_counts") or {}),
        "verification_total_passed_checks": max(0, int(verification.get("total_passed_checks") or 0)),
        "verification_total_checks": max(0, int(verification.get("total_checks") or 0)),
        "verification_total_suite_count": max(0, int(verification.get("total_suite_count") or 0)),
        "verification_evidence": list(verification.get("verification_evidence") or ()),
        "verification_evidence_digest": str(verification.get("verification_evidence_digest") or ""),
        "related_lineage_edge_count": len(related_edges),
        "related_lineage_edges": related_edges,
        "related_lineage_digest": _digest(related_edges),
        "operator_review_required": True,
        "testing_decision": "operator_only",
        "application_decision": "operator_only",
        "approval_decision": "operator_only",
        "release_decision": "operator_only",
        "installation_decision": "operator_only",
        "promotion_decision": "operator_only",
        "candidate_ranking_included": False,
        "winner_selected": False,
        "priority_included": False,
        "statistical_significance_claimed": False,
        "automatic_test_execution": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "patch_generated": False,
        "patch_reviewed_automatically": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "private_labels_included": False,
        "private_references_included": False,
        "private_review_notes_included": False,
        "private_verification_notes_included": False,
        "private_lineage_notes_included": False,
        "transcript_included": False,
        "prompt_included": False,
        "memory_content_included": False,
        "provider_payload_included": False,
        "credentials_included": False,
        "vectors_included": False,
        "hidden_reasoning_included": False,
        "provider_invoked": False,
        "generation_invoked": False,
        "content_free": True,
        "redacted": True,
    }
    document_data["candidate_review_export_digest"] = _digest(document_data)
    document = json.dumps(document_data, indent=2, sort_keys=True) + "\n"
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_review_export",
        "schema_version": REPAIR_CANDIDATE_REVIEW_EXPORT_SCHEMA_VERSION,
        "finding_id": str(finding_id or ""),
        "candidate_id": str(candidate_id or ""),
        "filename": f"{candidate_id}_privacy_safe_candidate_review.json",
        "media_type": "application/json",
        "document": document,
        "document_sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
        "review": document_data,
        "client_download_ready": True,
        "server_file_written": False,
        "writes_state": False,
        "provider_invoked": False,
        "generation_invoked": False,
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
        "content_free": True,
        "redacted": True,
    }


def repair_candidate_review_export_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_label", "private_reference", "private_note", "note", "notes", "content", "text",
        "transcript", "prompt", "provider_payload", "credentials", "vectors", "embedding",
        "hidden_reasoning", "chain_of_thought",
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
