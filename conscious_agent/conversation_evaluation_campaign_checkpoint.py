from __future__ import annotations

"""Read-only v1088.9 Desktop Alpha operator campaign checkpoint.

This checkpoint consolidates the v1088.0-v1088.8 operator evaluation campaign
arc. It returns only bounded states, counts, limits, reason codes, booleans,
and cryptographic digests. It does not expose private campaign plans, review
notes, external follow-up values, evaluation notes, transcripts, prompts,
provider payloads, credentials, vectors, export document bodies, or hidden
reasoning. It never invokes a provider, mutates campaign state, writes an export
file, creates a task, ranks campaigns, or grants approval, rollback,
installation, promotion, provider, model, generation-setting, or release
authority.
"""

from collections.abc import Iterable, Mapping
from typing import Any
import hashlib
import json

from conversation_daily_evaluation_checkpoint import build_daily_evaluation_checkpoint
from conversation_evaluation_campaign import EvaluationCampaignError, load_evaluation_campaign
from conversation_evaluation_campaign_comparison import (
    MAX_COMPARISON_CAMPAIGNS,
    MIN_COMPARISON_CAMPAIGNS,
    build_evaluation_campaign_comparison,
)
from conversation_evaluation_campaign_console import (
    MAX_CONSOLE_CAMPAIGN_ROWS,
    build_evaluation_campaign_console_state,
)
from conversation_evaluation_campaign_enrollment import build_evaluation_campaign_progress
from conversation_evaluation_campaign_followups import (
    FOLLOW_UP_REFERENCE_KINDS,
    FOLLOW_UP_STATES,
    MAX_CAMPAIGN_FOLLOW_UPS,
    build_evaluation_campaign_follow_ups,
)
from conversation_evaluation_campaign_issues import build_evaluation_campaign_issue_aggregation
from conversation_evaluation_campaign_protocol import (
    CAMPAIGN_FOCUS_AREAS,
    CAMPAIGN_STATES,
    MAX_CAMPAIGN_DURATION_DAYS,
    MAX_CAMPAIGN_EVALUATIONS,
    MAX_CAMPAIGN_REQUIRED_SIGNALS,
    build_evaluation_campaign_protocol,
)
from conversation_evaluation_campaign_review import (
    CAMPAIGN_REVIEW_DISPOSITIONS,
    CAMPAIGN_REVIEW_FINDING_KINDS,
    CAMPAIGN_REVIEW_STATES,
    MAX_CAMPAIGN_REVIEW_DISPOSITIONS,
    build_evaluation_campaign_review,
)
from conversation_evaluation_campaign_review_export import build_evaluation_campaign_review_export
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

OPERATOR_EVALUATION_CAMPAIGN_CHECKPOINT_SCHEMA_VERSION = "1"
CHECKPOINT_AREA_COUNT = 15


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _area(name: str, state: str, reason: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "reason": reason, "metrics": metrics}


def _selected_campaign_probe(campaign_id: str) -> dict[str, Any]:
    token = str(campaign_id or "").strip()
    empty = {
        "campaign_id": "",
        "campaign_state": "",
        "campaign_revision": 0,
        "enrollment_count": 0,
        "completion_ready": False,
        "issue_evaluation_count": 0,
        "affected_evaluation_count": 0,
        "reproducible_evaluation_count": 0,
        "follow_up_count": 0,
        "review_state": "not_started",
        "review_completion_ready": False,
        "progress_digest": "",
        "issue_digest": "",
        "follow_up_digest": "",
        "review_digest": "",
        "review_document_sha256": "",
        "server_file_written": False,
        "private_content_returned": False,
    }
    if not token:
        return {"selection_status": "none_selected", **empty}
    try:
        campaign = load_evaluation_campaign(token)
        progress = build_evaluation_campaign_progress(token)
        issues = build_evaluation_campaign_issue_aggregation(token)
        follow_ups = build_evaluation_campaign_follow_ups(token)
        review = build_evaluation_campaign_review(token)
        review_export = build_evaluation_campaign_review_export(token)
    except EvaluationCampaignError:
        return {"selection_status": "not_found", **empty}
    exported_review = review_export.get("review") if isinstance(review_export.get("review"), Mapping) else {}
    return {
        "selection_status": "available",
        "campaign_id": str(campaign.get("campaign_id") or ""),
        "campaign_state": str(campaign.get("state") or "planned"),
        "campaign_revision": max(0, int(campaign.get("revision") or 0)),
        "enrollment_count": max(0, int(progress.get("enrollment_count") or 0)),
        "completion_ready": bool(progress.get("completion_ready")),
        "issue_evaluation_count": max(0, int(issues.get("evaluation_count") or 0)),
        "affected_evaluation_count": max(0, int(issues.get("affected_evaluation_count") or 0)),
        "reproducible_evaluation_count": max(0, int(issues.get("reproducible_evaluation_count") or 0)),
        "follow_up_count": max(0, int(follow_ups.get("follow_up_count") or 0)),
        "review_state": str(review.get("review_state") or "not_started"),
        "review_completion_ready": bool(review.get("review_completion_ready")),
        "progress_digest": str(progress.get("progress_digest") or ""),
        "issue_digest": str(issues.get("issue_aggregation_digest") or ""),
        "follow_up_digest": str(follow_ups.get("follow_up_digest") or ""),
        "review_digest": str(review.get("review_digest") or ""),
        "review_document_sha256": str(review_export.get("document_sha256") or ""),
        "server_file_written": bool(review_export.get("server_file_written")),
        "private_content_returned": bool(
            campaign.get("private_campaign_label_returned")
            or campaign.get("private_objective_returned")
            or follow_ups.get("private_reference_values_returned")
            or review.get("private_review_notes_returned")
            or exported_review.get("private_campaign_plan_included")
            or exported_review.get("private_follow_up_values_included")
            or exported_review.get("private_review_notes_included")
            or exported_review.get("private_evaluation_notes_included")
            or exported_review.get("transcript_included")
            or exported_review.get("prompt_included")
            or exported_review.get("memory_content_included")
            or exported_review.get("provider_payload_included")
            or exported_review.get("credentials_included")
            or exported_review.get("vectors_included")
            or exported_review.get("hidden_reasoning_included")
        ),
    }


def _comparison_probe(campaign_ids: Iterable[str]) -> dict[str, Any]:
    normalized = list(dict.fromkeys(str(item or "").strip() for item in campaign_ids if str(item or "").strip()))
    if len(normalized) < MIN_COMPARISON_CAMPAIGNS:
        return {
            "comparison_status": "not_requested",
            "campaign_count": len(normalized),
            "comparison_digest": "",
            "campaign_ranking_included": False,
            "winner_declared": False,
            "statistical_significance_claimed": False,
            "release_recommendation_produced": False,
        }
    try:
        report = build_evaluation_campaign_comparison(normalized[:MAX_COMPARISON_CAMPAIGNS])
    except EvaluationCampaignError:
        return {
            "comparison_status": "invalid_request",
            "campaign_count": len(normalized),
            "comparison_digest": "",
            "campaign_ranking_included": False,
            "winner_declared": False,
            "statistical_significance_claimed": False,
            "release_recommendation_produced": False,
        }
    return {
        "comparison_status": "available",
        "campaign_count": max(0, int(report.get("campaign_count") or 0)),
        "comparison_digest": str(report.get("comparison_digest") or ""),
        "campaign_ranking_included": bool(report.get("campaign_ranking_included")),
        "winner_declared": bool(report.get("winner_declared")),
        "statistical_significance_claimed": bool(report.get("statistical_significance_claimed")),
        "release_recommendation_produced": bool(report.get("release_recommendation_produced")),
    }


def build_operator_evaluation_campaign_checkpoint(
    *,
    campaign_id: str = "",
    comparison_campaign_ids: Iterable[str] = (),
) -> dict[str, Any]:
    daily_checkpoint = build_daily_evaluation_checkpoint()
    protocol = build_evaluation_campaign_protocol()
    selected = _selected_campaign_probe(campaign_id)
    comparison = _comparison_probe(comparison_campaign_ids)
    console = build_evaluation_campaign_console_state(
        campaign_id=str(campaign_id or ""),
        comparison_campaign_ids=list(comparison_campaign_ids),
    )

    stable_contract = {
        "runtime_version": RUNTIME_VERSION,
        "campaign_states": list(CAMPAIGN_STATES),
        "focus_areas": list(CAMPAIGN_FOCUS_AREAS),
        "maximum_campaign_evaluations": MAX_CAMPAIGN_EVALUATIONS,
        "maximum_campaign_duration_days": MAX_CAMPAIGN_DURATION_DAYS,
        "maximum_required_signals": MAX_CAMPAIGN_REQUIRED_SIGNALS,
        "follow_up_states": list(FOLLOW_UP_STATES),
        "follow_up_reference_kinds": list(FOLLOW_UP_REFERENCE_KINDS),
        "maximum_campaign_follow_ups": MAX_CAMPAIGN_FOLLOW_UPS,
        "comparison_campaign_minimum": MIN_COMPARISON_CAMPAIGNS,
        "comparison_campaign_maximum": MAX_COMPARISON_CAMPAIGNS,
        "review_states": list(CAMPAIGN_REVIEW_STATES),
        "review_dispositions": list(CAMPAIGN_REVIEW_DISPOSITIONS),
        "review_finding_kinds": list(CAMPAIGN_REVIEW_FINDING_KINDS),
        "maximum_review_dispositions": MAX_CAMPAIGN_REVIEW_DISPOSITIONS,
        "maximum_console_campaign_rows": MAX_CONSOLE_CAMPAIGN_ROWS,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "automatic_campaign_launch": False,
        "automatic_evaluation_creation": False,
        "automatic_task_creation": False,
        "autonomous_prioritization": False,
        "provider_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "release_decision": "operator_only",
    }
    contract_digest = _digest(stable_contract)
    dynamic_evidence = {
        "daily_checkpoint_contract_digest": str(daily_checkpoint.get("contract_digest") or ""),
        "daily_checkpoint_areas_digest": str(daily_checkpoint.get("areas_digest") or ""),
        "campaign_protocol_digest": str(protocol.get("campaign_contract_digest") or ""),
        "campaign_rows_digest": str(console.get("console_digest") or ""),
        "selection_status": selected["selection_status"],
        "selected_campaign_revision": selected["campaign_revision"],
        "selected_progress_digest": selected["progress_digest"],
        "selected_issue_digest": selected["issue_digest"],
        "selected_follow_up_digest": selected["follow_up_digest"],
        "selected_review_digest": selected["review_digest"],
        "comparison_status": comparison["comparison_status"],
        "comparison_digest": comparison["comparison_digest"],
    }
    evidence_digest = _digest(dynamic_evidence)

    areas = [
        _area(
            "daily_evaluation_foundation",
            "ready",
            "v1087 daily-evaluation checkpoint remains the campaign evidence foundation",
            checkpoint_status=str(daily_checkpoint.get("checkpoint_status") or "unknown"),
            area_count=max(0, int(daily_checkpoint.get("area_count") or 0)),
            contract_digest=str(daily_checkpoint.get("contract_digest") or ""),
            areas_digest=str(daily_checkpoint.get("areas_digest") or ""),
        ),
        _area(
            "campaign_protocol_and_bounds",
            "ready",
            "campaign protocol is bounded and operator-started",
            protocol_status=str(protocol.get("protocol_status") or "review_required"),
            campaign_states=list(CAMPAIGN_STATES),
            focus_area_count=len(CAMPAIGN_FOCUS_AREAS),
            maximum_campaign_evaluations=MAX_CAMPAIGN_EVALUATIONS,
            maximum_campaign_duration_days=MAX_CAMPAIGN_DURATION_DAYS,
            maximum_required_signals=MAX_CAMPAIGN_REQUIRED_SIGNALS,
            protocol_digest=str(protocol.get("campaign_contract_digest") or ""),
        ),
        _area(
            "private_campaign_lifecycle",
            "ready",
            "campaign plans remain private runtime state with explicit revision-guarded transitions",
            operator_confirmation_required=True,
            optimistic_revision_required=True,
            private_plan_runtime_only=True,
            automatic_campaign_launch=False,
            source_tree_written=False,
        ),
        _area(
            "explicit_enrollment_and_completion",
            "ready",
            "existing evaluations are enrolled explicitly and campaign completion remains operator-only",
            maximum_enrollments=MAX_CAMPAIGN_EVALUATIONS,
            automatic_evaluation_creation=False,
            automatic_evaluation_enrollment=False,
            automatic_campaign_completion=False,
            operator_completion_required=True,
        ),
        _area(
            "privacy_safe_issue_aggregation",
            "ready",
            "issue evidence is descriptive and content-free",
            descriptive_counts_only=True,
            autonomous_prioritization=False,
            automatic_task_created=False,
            statistical_significance_claimed=False,
            private_notes_inspected=False,
            transcript_inspected=False,
        ),
        _area(
            "explicit_follow_up_references",
            "ready",
            "follow-up references are explicit, revision-guarded, and do not create work automatically",
            reference_kinds=list(FOLLOW_UP_REFERENCE_KINDS),
            states=list(FOLLOW_UP_STATES),
            maximum_follow_ups=MAX_CAMPAIGN_FOLLOW_UPS,
            private_reference_values_returned=False,
            automatic_task_created=False,
            automatic_work_item_created=False,
        ),
        _area(
            "bounded_campaign_comparison",
            "ready",
            "campaign comparison is descriptive arithmetic without ranking or release advice",
            minimum_campaigns=MIN_COMPARISON_CAMPAIGNS,
            maximum_campaigns=MAX_COMPARISON_CAMPAIGNS,
            comparison_status=comparison["comparison_status"],
            compared_campaign_count=comparison["campaign_count"],
            comparison_digest=comparison["comparison_digest"],
            campaign_ranking_included=comparison["campaign_ranking_included"],
            winner_declared=comparison["winner_declared"],
            statistical_significance_claimed=comparison["statistical_significance_claimed"],
            release_recommendation_produced=comparison["release_recommendation_produced"],
        ),
        _area(
            "explicit_campaign_review_workflow",
            "ready",
            "review findings require explicit dispositions and revision-guarded operator actions",
            review_states=list(CAMPAIGN_REVIEW_STATES),
            review_dispositions=list(CAMPAIGN_REVIEW_DISPOSITIONS),
            finding_kinds=list(CAMPAIGN_REVIEW_FINDING_KINDS),
            maximum_dispositions=MAX_CAMPAIGN_REVIEW_DISPOSITIONS,
            automatic_review_completion=False,
            private_review_notes_returned=False,
        ),
        _area(
            "operator_campaign_console",
            "ready",
            "operator console composes redacted read evidence and routes writes through confirmed actions",
            selection_status=str(console.get("selection_status") or "none_selected"),
            campaign_count=max(0, int(console.get("campaign_count") or 0)),
            maximum_campaign_rows=MAX_CONSOLE_CAMPAIGN_ROWS,
            console_digest=str(console.get("console_digest") or ""),
            operator_confirmation_required_for_mutation=True,
            optimistic_revision_required=True,
            read_routes_only_for_evidence=True,
        ),
        _area(
            "privacy_safe_campaign_review_export",
            "ready",
            "campaign review export is deterministic, client-side, and content-free",
            selected_export_status="available" if selected["selection_status"] == "available" else "not_selected",
            selected_document_sha256=selected["review_document_sha256"],
            server_file_written=selected["server_file_written"],
            transcript_included=False,
            prompt_included=False,
            private_campaign_plan_included=False,
            private_follow_up_values_included=False,
            private_review_notes_included=False,
            private_evaluation_notes_included=False,
        ),
        _area(
            "selected_campaign_evidence",
            "ready",
            "optional selected-campaign evidence is bounded and redacted",
            **selected,
        ),
        _area(
            "multi_process_revision_and_source_safety",
            "ready",
            "campaign writes retain cross-process exclusion and optimistic revisions while checkpoint reads remain immutable",
            optimistic_revision_required=True,
            cross_process_lock_required=True,
            same_revision_single_winner=True,
            checkpoint_writes_state=False,
            source_tree_written=False,
        ),
        _area(
            "provider_outage_and_no_replay_boundary",
            "ready",
            "campaign evaluation remains usable as redacted evidence while provider work stays explicit",
            provider_invoked=False,
            embedding_provider_invoked=False,
            generation_invoked=False,
            automatic_provider_request=False,
            automatic_replay=False,
            automatic_resend=False,
        ),
        _area(
            "content_free_privacy_boundary",
            "ready",
            "public checkpoint evidence excludes private runtime and model content",
            private_content_returned=selected["private_content_returned"],
            transcript_returned=False,
            prompt_returned=False,
            evaluation_note_returned=False,
            review_note_returned=False,
            campaign_plan_returned=False,
            follow_up_value_returned=False,
            provider_payload_returned=False,
            credentials_returned=False,
            vectors_returned=False,
            hidden_reasoning_returned=False,
        ),
        _area(
            "operator_authority_and_checkpoint_boundary",
            "ready",
            "checkpoint cannot create work or grant protected authority",
            release_decision="operator_only",
            approval_granted=False,
            rollback_authorized=False,
            installation_performed=False,
            promotion_performed=False,
            release_certified=False,
            model_management=False,
            provider_switching=False,
            generation_settings_changed=False,
            autonomous_scoring=False,
            autonomous_prioritization=False,
            automatic_task_created=False,
            checkpoint_writes_state=False,
        ),
    ]
    areas_digest = _digest(areas)
    ready = (
        len(areas) == CHECKPOINT_AREA_COUNT
        and protocol.get("protocol_status") == "ready"
        and daily_checkpoint.get("checkpoint_status") == "ready_for_operator_daily_evaluation"
        and not selected["private_content_returned"]
        and not selected["server_file_written"]
        and not comparison["campaign_ranking_included"]
        and not comparison["winner_declared"]
        and not comparison["statistical_significance_claimed"]
        and not comparison["release_recommendation_produced"]
    )
    return {
        "ok": True,
        "type": "desktop_alpha_operator_evaluation_campaign_checkpoint",
        "schema_version": OPERATOR_EVALUATION_CAMPAIGN_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "ready_for_operator_campaign_evaluation" if ready else "review_required",
        "area_count": len(areas),
        "areas": areas,
        "contract_digest": contract_digest,
        "evidence_digest": evidence_digest,
        "areas_digest": areas_digest,
        "selected_campaign_status": selected["selection_status"],
        "comparison_status": comparison["comparison_status"],
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "automatic_provider_request": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "automatic_campaign_launch": False,
        "automatic_evaluation_creation": False,
        "automatic_task_created": False,
        "autonomous_scoring": False,
        "autonomous_prioritization": False,
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


def operator_evaluation_campaign_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "messages", "user_message", "assistant_response",
        "transcript", "prompt", "private_note", "private_notes", "review_note", "review_notes",
        "campaign_label", "objective", "private_campaign_label", "private_objective",
        "private_reference_value", "provider_payload", "credentials", "vectors", "embedding",
        "receipt", "receipts", "hidden_reasoning", "chain_of_thought", "document",
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
