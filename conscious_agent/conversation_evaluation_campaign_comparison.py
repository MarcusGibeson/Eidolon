from __future__ import annotations

"""Bounded v1088.5 comparison of privacy-safe campaign evidence.

Comparison is descriptive only. It reads redacted campaign progress and issue
aggregation for two to eight campaigns and returns counts plus deltas against
the first campaign. It does not inspect transcripts or private plans, rank
campaigns, choose a winner, prioritize work, certify a release, or write state.
"""

from typing import Any, Iterable, Mapping
import hashlib
import json

from conversation_daily_evaluation_protocol import ISSUE_DOMAINS, ISSUE_SEVERITIES
from conversation_evaluation_campaign import EvaluationCampaignError, load_evaluation_campaign
from conversation_evaluation_campaign_enrollment import build_evaluation_campaign_progress
from conversation_evaluation_campaign_issues import build_evaluation_campaign_issue_aggregation

EVALUATION_CAMPAIGN_COMPARISON_SCHEMA_VERSION = "1"
MIN_COMPARISON_CAMPAIGNS = 2
MAX_COMPARISON_CAMPAIGNS = 8
_DELTA_FIELDS = (
    "enrollment_count",
    "completed_evaluation_count",
    "affected_evaluation_count",
    "reproducible_evaluation_count",
    "reproducible_observation_count",
    "missing_required_signal_count",
    "model_quality_issue_count",
    "provider_transport_issue_count",
    "interface_issue_count",
    "session_continuity_issue_count",
    "major_issue_count",
    "blocking_issue_count",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _normalize_campaign_ids(campaign_ids: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for raw in campaign_ids:
        token = str(raw or "").strip()
        if token and token not in normalized:
            normalized.append(token)
    if len(normalized) < MIN_COMPARISON_CAMPAIGNS:
        raise EvaluationCampaignError("At least two distinct evaluation campaigns are required for comparison.")
    if len(normalized) > MAX_COMPARISON_CAMPAIGNS:
        raise EvaluationCampaignError(f"At most {MAX_COMPARISON_CAMPAIGNS} campaigns may be compared.")
    return normalized


def _campaign_row(campaign_id: str) -> dict[str, Any]:
    campaign = load_evaluation_campaign(campaign_id)
    progress = build_evaluation_campaign_progress(campaign_id)
    issues = build_evaluation_campaign_issue_aggregation(campaign_id)
    domain_counts = issues.get("issue_domain_counts") if isinstance(issues.get("issue_domain_counts"), Mapping) else {}
    severity_counts = issues.get("severity_counts") if isinstance(issues.get("severity_counts"), Mapping) else {}
    completed_count = max(0, int((progress.get("state_counts") or {}).get("completed") or 0))
    return {
        "campaign_id": campaign_id,
        "campaign_state": str(campaign.get("state") or "planned"),
        "campaign_revision": max(0, int(campaign.get("revision") or 0)),
        "focus_areas": list(campaign.get("focus_areas") or ()),
        "enrollment_count": max(0, int(progress.get("enrollment_count") or 0)),
        "completed_evaluation_count": completed_count,
        "completion_ready": bool(progress.get("completion_ready")),
        "target_reached": bool(progress.get("target_reached")),
        "required_signal_coverage_complete": bool(progress.get("required_signal_coverage_complete")),
        "missing_required_signal_count": len(list(progress.get("missing_required_signals") or ())),
        "affected_evaluation_count": max(0, int(issues.get("affected_evaluation_count") or 0)),
        "reproducible_evaluation_count": max(0, int(issues.get("reproducible_evaluation_count") or 0)),
        "reproducible_observation_count": max(0, int(issues.get("reproducible_observation_count") or 0)),
        "model_quality_issue_count": max(0, int(domain_counts.get("model_quality") or 0)),
        "provider_transport_issue_count": max(0, int(domain_counts.get("provider_transport") or 0)),
        "interface_issue_count": max(0, int(domain_counts.get("interface") or 0)),
        "session_continuity_issue_count": max(0, int(domain_counts.get("session_continuity") or 0)),
        "major_issue_count": max(0, int(severity_counts.get("major") or 0)),
        "blocking_issue_count": max(0, int(severity_counts.get("blocking") or 0)),
        "outcome_counts": dict(issues.get("outcome_counts") or {}),
        "issue_aggregation_digest": str(issues.get("issue_aggregation_digest") or ""),
        "progress_digest": str(progress.get("progress_digest") or ""),
    }


def build_evaluation_campaign_comparison(campaign_ids: Iterable[str]) -> dict[str, Any]:
    normalized = _normalize_campaign_ids(campaign_ids)
    rows = [_campaign_row(campaign_id) for campaign_id in normalized]
    baseline = rows[0]
    deltas: list[dict[str, Any]] = []
    for row in rows[1:]:
        values = {field: int(row[field]) - int(baseline[field]) for field in _DELTA_FIELDS}
        deltas.append({
            "baseline_campaign_id": str(baseline.get("campaign_id") or ""),
            "campaign_id": str(row.get("campaign_id") or ""),
            "count_deltas": values,
        })
    stable = {
        "campaign_count": len(rows),
        "minimum_campaigns": MIN_COMPARISON_CAMPAIGNS,
        "maximum_campaigns": MAX_COMPARISON_CAMPAIGNS,
        "baseline_campaign_id": str(baseline.get("campaign_id") or ""),
        "campaigns": rows,
        "deltas": deltas,
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_comparison",
        "schema_version": EVALUATION_CAMPAIGN_COMPARISON_SCHEMA_VERSION,
        **stable,
        "comparison_digest": _digest(stable),
        "descriptive_counts_only": True,
        "campaigns_ranked": False,
        "winner_selected": False,
        "priority_assigned": False,
        "autonomous_prioritization": False,
        "statistical_significance_claimed": False,
        "release_recommendation_produced": False,
        "automatic_task_created": False,
        "transcript_inspected": False,
        "prompt_inspected": False,
        "private_notes_inspected": False,
        "private_campaign_plan_inspected": False,
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def campaign_comparison_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "campaign_label", "objective", "private_reference_value", "content", "text", "message",
        "messages", "user_message", "assistant_response", "transcript", "prompt", "note", "notes",
        "temporary_instruction", "pinned_context", "queued_operator_intent", "provider_payload",
        "credentials", "vectors", "embedding", "receipt", "receipts", "hidden_reasoning",
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
