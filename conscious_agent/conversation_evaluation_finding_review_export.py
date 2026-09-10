from __future__ import annotations

"""v1089.7 deterministic privacy-safe finding repair-intake review export."""

from typing import Any, Mapping
import hashlib
import json

from conversation_evaluation_finding import load_evaluation_finding
from conversation_evaluation_finding_aggregation import build_evaluation_finding_aggregation
from conversation_evaluation_finding_repair_candidates import build_finding_repair_candidates
from conversation_evaluation_finding_reproducibility import build_finding_reproducibility
from conversation_evaluation_finding_triage import build_evaluation_finding_triage
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

EVALUATION_FINDING_REVIEW_EXPORT_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_evaluation_finding_review_export(finding_id: str) -> dict[str, Any]:
    finding = load_evaluation_finding(finding_id)
    reproducibility = build_finding_reproducibility(finding_id)
    repair_candidates = build_finding_repair_candidates(finding_id)
    triage = build_evaluation_finding_triage(finding_id)
    aggregation = build_evaluation_finding_aggregation(
        campaign_id=str(finding.get("campaign_id") or ""),
        evaluation_id=str(finding.get("evaluation_id") or ""),
    )
    document_data = {
        "type": "desktop_alpha_evaluation_finding_repair_intake_review",
        "schema_version": EVALUATION_FINDING_REVIEW_EXPORT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "finding_id": str(finding.get("finding_id") or ""),
        "finding_state": str(finding.get("state") or "open"),
        "finding_revision": max(0, int(finding.get("revision") or 0)),
        "campaign_id": str(finding.get("campaign_id") or ""),
        "evaluation_id": str(finding.get("evaluation_id") or ""),
        "issue_domain": str(finding.get("issue_domain") or "none"),
        "severity": str(finding.get("severity") or "none"),
        "finding_title_present": bool(finding.get("finding_title_present")),
        "finding_title_digest": str(finding.get("finding_title_digest") or ""),
        "finding_details_present": bool(finding.get("finding_details_present")),
        "finding_details_digest": str(finding.get("finding_details_digest") or ""),
        "finding_record_digest": str(finding.get("record_digest") or ""),
        "reproducibility_status": str(reproducibility.get("reproducibility_status") or "not_reviewed"),
        "reproduction_attempt_count": max(0, int(reproducibility.get("attempt_count") or 0)),
        "reproduction_outcome_counts": dict(reproducibility.get("outcome_counts") or {}),
        "reproduction_attempts": list(reproducibility.get("attempts") or ()),
        "reproduction_attempts_digest": str(reproducibility.get("attempts_digest") or ""),
        "repair_candidate_reference_count": max(0, int(repair_candidates.get("reference_count") or 0)),
        "repair_candidate_state_counts": dict(repair_candidates.get("state_counts") or {}),
        "repair_candidate_kind_counts": dict(repair_candidates.get("reference_kind_counts") or {}),
        "repair_candidate_references": list(repair_candidates.get("references") or ()),
        "repair_candidate_references_digest": str(repair_candidates.get("references_digest") or ""),
        "triage_state": str(triage.get("triage_state") or "not_started"),
        "triage_disposition": str(triage.get("triage_disposition") or ""),
        "triage_note_present": bool(triage.get("triage_note_present")),
        "triage_note_digest": str(triage.get("triage_note_digest") or ""),
        "triage_completion_ready": bool(triage.get("completion_ready")),
        "triage_digest": str(triage.get("triage_digest") or ""),
        "related_finding_count": max(0, int(aggregation.get("finding_count") or 0)),
        "related_state_counts": dict(aggregation.get("state_counts") or {}),
        "related_issue_domain_counts": dict(aggregation.get("issue_domain_counts") or {}),
        "related_severity_counts": dict(aggregation.get("severity_counts") or {}),
        "related_aggregation_digest": str(aggregation.get("aggregation_digest") or ""),
        "operator_review_required": True,
        "repair_decision": "operator_only",
        "approval_decision": "operator_only",
        "release_decision": "operator_only",
        "installation_decision": "operator_only",
        "promotion_decision": "operator_only",
        "finding_ranking_included": False,
        "priority_included": False,
        "statistical_significance_claimed": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "patch_generated": False,
        "patch_reviewed": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "transcript_included": False,
        "prompt_included": False,
        "private_finding_content_included": False,
        "private_reproduction_notes_included": False,
        "private_environment_labels_included": False,
        "private_repair_reference_values_included": False,
        "private_triage_notes_included": False,
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
    document_data["finding_review_export_digest"] = _digest(document_data)
    document = json.dumps(document_data, indent=2, sort_keys=True)
    return {
        "ok": True,
        "type": "desktop_alpha_evaluation_finding_review_export",
        "schema_version": EVALUATION_FINDING_REVIEW_EXPORT_SCHEMA_VERSION,
        "finding_id": document_data["finding_id"],
        "filename": f"{document_data['finding_id']}_privacy_safe_repair_intake_review.json",
        "media_type": "application/json",
        "document": document,
        "document_sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
        "review": document_data,
        "client_download_ready": True,
        "server_file_written": False,
        "writes_state": False,
        "provider_invoked": False,
        "generation_invoked": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "patch_generated": False,
        "patch_reviewed": False,
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


def finding_review_export_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_title",
        "private_details",
        "finding_title",
        "finding_details",
        "private_note",
        "note",
        "notes",
        "environment_label",
        "private_environment_label",
        "reference_value",
        "private_reference_value",
        "content",
        "text",
        "message",
        "messages",
        "transcript",
        "prompt",
        "provider_payload",
        "credentials",
        "vectors",
        "embedding",
        "hidden_reasoning",
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
