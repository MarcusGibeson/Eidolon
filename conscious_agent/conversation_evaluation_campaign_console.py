from __future__ import annotations

"""v1088.7 provider-free state assembly for the operator campaign console."""

from typing import Any, Iterable
import hashlib
import json

from conversation_evaluation_campaign import (
    EvaluationCampaignError,
    campaign_public_summary,
    iter_evaluation_campaign_private,
    load_evaluation_campaign,
)
from conversation_evaluation_campaign_protocol import build_evaluation_campaign_protocol
from conversation_evaluation_campaign_enrollment import build_evaluation_campaign_progress
from conversation_evaluation_campaign_issues import build_evaluation_campaign_issue_aggregation
from conversation_evaluation_campaign_followups import build_evaluation_campaign_follow_ups
from conversation_evaluation_campaign_review import build_evaluation_campaign_review
from conversation_evaluation_campaign_comparison import build_evaluation_campaign_comparison

EVALUATION_CAMPAIGN_CONSOLE_SCHEMA_VERSION = "1"
MAX_CONSOLE_CAMPAIGN_ROWS = 64


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _campaign_rows() -> list[dict[str, Any]]:
    rows = [campaign_public_summary(record) for record in iter_evaluation_campaign_private()]
    rows.sort(key=lambda row: (str(row.get("updated_at") or ""), str(row.get("campaign_id") or "")), reverse=True)
    return rows[:MAX_CONSOLE_CAMPAIGN_ROWS]


def build_evaluation_campaign_console_state(
    *, campaign_id: str = "", comparison_campaign_ids: Iterable[str] = ()
) -> dict[str, Any]:
    protocol = build_evaluation_campaign_protocol()
    rows = _campaign_rows()
    token = str(campaign_id or "").strip()
    selected = progress = issues = follow_ups = review = comparison = None
    selection_status = "none_selected"
    if token:
        try:
            selected = load_evaluation_campaign(token)
            progress = build_evaluation_campaign_progress(token)
            issues = build_evaluation_campaign_issue_aggregation(token)
            follow_ups = build_evaluation_campaign_follow_ups(token)
            review = build_evaluation_campaign_review(token)
            selection_status = "available"
        except EvaluationCampaignError:
            selection_status = "not_found"
    comparison_ids = [str(item or "").strip() for item in comparison_campaign_ids if str(item or "").strip()]
    if len(dict.fromkeys(comparison_ids)) >= 2:
        try:
            comparison = build_evaluation_campaign_comparison(comparison_ids)
        except EvaluationCampaignError:
            comparison = None
    stable = {
        "protocol_digest": str(protocol.get("campaign_contract_digest") or ""),
        "campaign_rows_digest": _digest(rows),
        "selection_status": selection_status,
        "selected_campaign_id": token if selection_status == "available" else "",
        "selected_campaign_revision": int((selected or {}).get("revision") or 0),
        "progress_digest": str((progress or {}).get("progress_digest") or ""),
        "issue_digest": str((issues or {}).get("issue_aggregation_digest") or ""),
        "follow_up_digest": str((follow_ups or {}).get("follow_up_digest") or ""),
        "review_digest": str((review or {}).get("review_digest") or ""),
        "comparison_digest": str((comparison or {}).get("comparison_digest") or ""),
    }
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_console_state",
        "schema_version": EVALUATION_CAMPAIGN_CONSOLE_SCHEMA_VERSION,
        "selection_status": selection_status,
        "selected_campaign_id": stable["selected_campaign_id"],
        "campaign_count": len(rows),
        "maximum_campaign_rows": MAX_CONSOLE_CAMPAIGN_ROWS,
        "campaigns": rows,
        "protocol": protocol,
        "selected_campaign": selected,
        "progress": progress,
        "issues": issues,
        "follow_ups": follow_ups,
        "review": review,
        "comparison": comparison,
        "console_digest": _digest(stable),
        "operator_confirmation_required_for_mutation": True,
        "optimistic_revision_required": True,
        "mutation_route": "/api/conversation/evaluation-campaign",
        "read_routes_only_for_evidence": True,
        "private_campaign_plan_returned": False,
        "private_follow_up_values_returned": False,
        "private_review_notes_returned": False,
        "automatic_task_created": False,
        "autonomous_prioritization": False,
        "release_recommendation_produced": False,
        "provider_invoked": False,
        "generation_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_certified": False,
        "writes_state": False,
        "content_free": True,
        "redacted": True,
    }
