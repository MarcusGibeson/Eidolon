from __future__ import annotations

"""v1088.8 deterministic privacy-safe campaign review export."""

from typing import Any, Mapping
import hashlib
import json

from conversation_evaluation_campaign import load_evaluation_campaign
from conversation_evaluation_campaign_enrollment import build_evaluation_campaign_progress
from conversation_evaluation_campaign_issues import build_evaluation_campaign_issue_aggregation
from conversation_evaluation_campaign_followups import build_evaluation_campaign_follow_ups
from conversation_evaluation_campaign_review import build_evaluation_campaign_review
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

EVALUATION_CAMPAIGN_REVIEW_EXPORT_SCHEMA_VERSION = "1"


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def build_evaluation_campaign_review_export(campaign_id: str) -> dict[str, Any]:
    campaign = load_evaluation_campaign(campaign_id)
    progress = build_evaluation_campaign_progress(campaign_id)
    issues = build_evaluation_campaign_issue_aggregation(campaign_id)
    follow_ups = build_evaluation_campaign_follow_ups(campaign_id)
    review = build_evaluation_campaign_review(campaign_id)
    document_data = {
        "type": "desktop_alpha_operator_evaluation_campaign_review",
        "schema_version": EVALUATION_CAMPAIGN_REVIEW_EXPORT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "campaign_id": str(campaign.get("campaign_id") or ""),
        "campaign_state": str(campaign.get("state") or "planned"),
        "campaign_revision": max(0, int(campaign.get("revision") or 0)),
        "focus_areas": list(campaign.get("focus_areas") or ()),
        "target_evaluation_count": max(0, int(campaign.get("target_evaluation_count") or 0)),
        "minimum_completed_evaluations": max(0, int(campaign.get("minimum_completed_evaluations") or 0)),
        "planned_duration_days": max(0, int(campaign.get("planned_duration_days") or 0)),
        "required_signals": list(campaign.get("required_signals") or ()),
        "campaign_label_digest": str(campaign.get("campaign_label_digest") or ""),
        "campaign_objective_digest": str(campaign.get("campaign_objective_digest") or ""),
        "enrollment_count": max(0, int(progress.get("enrollment_count") or 0)),
        "completion_ready": bool(progress.get("completion_ready")),
        "progress_digest": str(progress.get("progress_digest") or ""),
        "issue_domain_counts": dict(issues.get("issue_domain_counts") or {}),
        "severity_counts": dict(issues.get("severity_counts") or {}),
        "outcome_counts": dict(issues.get("outcome_counts") or {}),
        "affected_evaluation_count": max(0, int(issues.get("affected_evaluation_count") or 0)),
        "reproducible_evaluation_count": max(0, int(issues.get("reproducible_evaluation_count") or 0)),
        "issue_aggregation_digest": str(issues.get("issue_aggregation_digest") or ""),
        "follow_up_count": max(0, int(follow_ups.get("follow_up_count") or 0)),
        "follow_up_state_counts": dict(follow_ups.get("state_counts") or {}),
        "follow_up_reference_kind_counts": dict(follow_ups.get("reference_kind_counts") or {}),
        "follow_up_digest": str(follow_ups.get("follow_up_digest") or ""),
        "review_state": str(review.get("review_state") or "not_started"),
        "review_completion_ready": bool(review.get("review_completion_ready")),
        "review_disposition_counts": dict(review.get("disposition_counts") or {}),
        "review_dispositions": list(review.get("dispositions") or ()),
        "missing_review_findings": list(review.get("missing_findings") or ()),
        "review_digest": str(review.get("review_digest") or ""),
        "operator_review_required": True,
        "release_decision": "operator_only",
        "installation_decision": "operator_only",
        "promotion_decision": "operator_only",
        "release_recommendation_produced": False,
        "campaign_ranking_included": False,
        "statistical_significance_claimed": False,
        "automatic_task_created": False,
        "autonomous_prioritization": False,
        "transcript_included": False,
        "prompt_included": False,
        "private_evaluation_notes_included": False,
        "private_review_notes_included": False,
        "private_campaign_plan_included": False,
        "private_follow_up_values_included": False,
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
    document_data["campaign_review_export_digest"] = _digest(document_data)
    document = json.dumps(document_data, indent=2, sort_keys=True) + "\n"
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_review_export",
        "schema_version": EVALUATION_CAMPAIGN_REVIEW_EXPORT_SCHEMA_VERSION,
        "filename": f"{document_data['campaign_id']}_privacy_safe_campaign_review.json",
        "media_type": "application/json",
        "document_sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
        "document": document,
        "review": document_data,
        "server_file_written": False,
        "client_download_ready": True,
        "operator_review_required": True,
        "release_certified": False,
        "promotion_performed": False,
        "installation_performed": False,
        "provider_invoked": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }


def campaign_review_export_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "private_note", "campaign_label", "objective", "private_reference_value", "content", "text",
        "message", "messages", "user_message", "assistant_response", "transcript", "prompt", "note", "notes",
        "memory", "memories", "provider_payload", "credentials", "vectors", "embedding", "receipt", "receipts",
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
