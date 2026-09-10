from __future__ import annotations

"""Read-only v1089.9 Desktop Alpha evaluation findings checkpoint.

The checkpoint consolidates the v1089.0-v1089.8 finding and repair-intake arc.
It returns bounded states, counts, limits, reason codes, booleans, and digests
only. It never exposes private finding text, notes, environment labels, repair
reference values, transcripts, prompts, provider payloads, credentials, vectors,
export document bodies, or hidden reasoning. It never invokes a provider,
mutates a finding, creates a task, generates or applies a patch, or grants
approval, rollback, installation, promotion, model, provider, or release
authority.
"""

from collections.abc import Iterable, Mapping
from typing import Any
import hashlib
import json

from conversation_evaluation_campaign_checkpoint import build_operator_evaluation_campaign_checkpoint
from conversation_evaluation_finding import (
    EvaluationFindingError,
    FINDING_STATES,
    MAX_FINDING_DETAILS_CHARS,
    MAX_FINDING_TITLE_CHARS,
    MAX_FINDINGS_RETURNED,
    load_evaluation_finding,
)
from conversation_evaluation_finding_aggregation import (
    MAX_AGGREGATED_FINDINGS,
    build_evaluation_finding_aggregation,
)
from conversation_evaluation_finding_comparison import (
    MAX_COMPARISON_FINDINGS,
    MIN_COMPARISON_FINDINGS,
    build_evaluation_finding_comparison,
)
from conversation_evaluation_finding_console import build_evaluation_finding_console_state
from conversation_evaluation_finding_long_session import (
    EARLIER_FINDING_WINDOW,
    INITIAL_FINDING_WINDOW,
    MAX_LONG_SESSION_FINDINGS,
    build_evaluation_finding_window,
)
from conversation_evaluation_finding_repair_candidates import (
    MAX_REPAIR_REFERENCES,
    REFERENCE_KINDS,
    REFERENCE_STATES,
    build_finding_repair_candidates,
)
from conversation_evaluation_finding_reproducibility import (
    MAX_REPRODUCTION_ATTEMPTS,
    REPRODUCTION_ENVIRONMENTS,
    REPRODUCTION_OUTCOMES,
    build_finding_reproducibility,
)
from conversation_evaluation_finding_review_export import build_evaluation_finding_review_export
from conversation_evaluation_finding_triage import (
    FINDING_TRIAGE_DISPOSITIONS,
    FINDING_TRIAGE_STATES,
    MAX_TRIAGE_NOTE_CHARS,
    build_evaluation_finding_triage,
)
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

EVALUATION_FINDINGS_CHECKPOINT_SCHEMA_VERSION = "1"
CHECKPOINT_AREA_COUNT = 15


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _area(name: str, state: str, reason: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "reason": reason, "metrics": metrics}


def _selected_finding_probe(finding_id: str) -> dict[str, Any]:
    token = str(finding_id or "").strip()
    empty = {
        "finding_id": "",
        "finding_state": "",
        "finding_revision": 0,
        "campaign_id_present": False,
        "evaluation_id_present": False,
        "issue_domain": "none",
        "severity": "none",
        "reproducibility_status": "not_reviewed",
        "reproduction_attempt_count": 0,
        "repair_reference_count": 0,
        "triage_state": "not_started",
        "triage_disposition": "",
        "finding_record_digest": "",
        "reproducibility_digest": "",
        "repair_references_digest": "",
        "triage_digest": "",
        "review_document_sha256": "",
        "server_file_written": False,
        "private_content_returned": False,
    }
    if not token:
        return {"selection_status": "none_selected", **empty}
    try:
        finding = load_evaluation_finding(token)
        reproducibility = build_finding_reproducibility(token)
        references = build_finding_repair_candidates(token)
        triage = build_evaluation_finding_triage(token)
        review_export = build_evaluation_finding_review_export(token)
    except EvaluationFindingError:
        return {"selection_status": "not_found", **empty}
    review = review_export.get("review") if isinstance(review_export.get("review"), Mapping) else {}
    return {
        "selection_status": "available",
        "finding_id": str(finding.get("finding_id") or ""),
        "finding_state": str(finding.get("state") or "open"),
        "finding_revision": max(0, int(finding.get("revision") or 0)),
        "campaign_id_present": bool(finding.get("campaign_id")),
        "evaluation_id_present": bool(finding.get("evaluation_id")),
        "issue_domain": str(finding.get("issue_domain") or "none"),
        "severity": str(finding.get("severity") or "none"),
        "reproducibility_status": str(reproducibility.get("reproducibility_status") or "not_reviewed"),
        "reproduction_attempt_count": max(0, int(reproducibility.get("attempt_count") or 0)),
        "repair_reference_count": max(0, int(references.get("reference_count") or 0)),
        "triage_state": str(triage.get("triage_state") or "not_started"),
        "triage_disposition": str(triage.get("triage_disposition") or ""),
        "finding_record_digest": str(finding.get("record_digest") or ""),
        "reproducibility_digest": str(reproducibility.get("attempts_digest") or ""),
        "repair_references_digest": str(references.get("references_digest") or ""),
        "triage_digest": str(triage.get("triage_digest") or ""),
        "review_document_sha256": str(review_export.get("document_sha256") or ""),
        "server_file_written": bool(review_export.get("server_file_written")),
        "private_content_returned": bool(
            finding.get("private_title_returned")
            or finding.get("private_details_returned")
            or reproducibility.get("private_environment_labels_returned")
            or reproducibility.get("private_notes_returned")
            or references.get("private_reference_values_returned")
            or references.get("private_labels_returned")
            or triage.get("private_note_returned")
            or review.get("private_finding_content_included")
            or review.get("private_reproduction_notes_included")
            or review.get("private_environment_labels_included")
            or review.get("private_repair_reference_values_included")
            or review.get("private_triage_notes_included")
            or review.get("transcript_included")
            or review.get("prompt_included")
            or review.get("memory_content_included")
            or review.get("provider_payload_included")
            or review.get("credentials_included")
            or review.get("vectors_included")
            or review.get("hidden_reasoning_included")
        ),
    }


def _comparison_probe(finding_ids: Iterable[str]) -> dict[str, Any]:
    normalized = list(dict.fromkeys(str(item or "").strip() for item in finding_ids if str(item or "").strip()))
    if len(normalized) < MIN_COMPARISON_FINDINGS:
        return {
            "comparison_status": "not_requested",
            "finding_count": len(normalized),
            "comparison_digest": "",
            "findings_ranked": False,
            "winner_selected": False,
            "priority_assigned": False,
            "statistical_significance_claimed": False,
            "release_recommendation_produced": False,
        }
    try:
        report = build_evaluation_finding_comparison(normalized[:MAX_COMPARISON_FINDINGS])
    except EvaluationFindingError:
        return {
            "comparison_status": "invalid_request",
            "finding_count": len(normalized),
            "comparison_digest": "",
            "findings_ranked": False,
            "winner_selected": False,
            "priority_assigned": False,
            "statistical_significance_claimed": False,
            "release_recommendation_produced": False,
        }
    return {
        "comparison_status": "available",
        "finding_count": max(0, int(report.get("finding_count") or 0)),
        "comparison_digest": str(report.get("comparison_digest") or ""),
        "findings_ranked": bool(report.get("findings_ranked")),
        "winner_selected": bool(report.get("winner_selected")),
        "priority_assigned": bool(report.get("priority_assigned")),
        "statistical_significance_claimed": bool(report.get("statistical_significance_claimed")),
        "release_recommendation_produced": bool(report.get("release_recommendation_produced")),
    }


def build_evaluation_findings_checkpoint(
    *,
    finding_id: str = "",
    campaign_id: str = "",
    evaluation_id: str = "",
    state: str = "",
    comparison_finding_ids: Iterable[str] = (),
) -> dict[str, Any]:
    campaign_checkpoint = build_operator_evaluation_campaign_checkpoint(campaign_id=campaign_id)
    selected = _selected_finding_probe(finding_id)
    comparison_ids = list(comparison_finding_ids)
    comparison = _comparison_probe(comparison_ids)
    aggregation = build_evaluation_finding_aggregation(campaign_id=campaign_id, evaluation_id=evaluation_id)
    window = build_evaluation_finding_window(campaign_id=campaign_id, evaluation_id=evaluation_id, state=state)
    console = build_evaluation_finding_console_state(
        finding_id=finding_id,
        campaign_id=campaign_id,
        evaluation_id=evaluation_id,
        state=state,
        comparison_finding_ids=comparison_ids,
    )

    stable_contract = {
        "runtime_version": RUNTIME_VERSION,
        "finding_states": list(FINDING_STATES),
        "maximum_finding_title_chars": MAX_FINDING_TITLE_CHARS,
        "maximum_finding_details_chars": MAX_FINDING_DETAILS_CHARS,
        "maximum_findings_returned": MAX_FINDINGS_RETURNED,
        "reproduction_outcomes": list(REPRODUCTION_OUTCOMES),
        "reproduction_environments": list(REPRODUCTION_ENVIRONMENTS),
        "maximum_reproduction_attempts": MAX_REPRODUCTION_ATTEMPTS,
        "repair_reference_kinds": list(REFERENCE_KINDS),
        "repair_reference_states": list(REFERENCE_STATES),
        "maximum_repair_references": MAX_REPAIR_REFERENCES,
        "triage_states": list(FINDING_TRIAGE_STATES),
        "triage_dispositions": list(FINDING_TRIAGE_DISPOSITIONS),
        "maximum_triage_note_chars": MAX_TRIAGE_NOTE_CHARS,
        "comparison_finding_minimum": MIN_COMPARISON_FINDINGS,
        "comparison_finding_maximum": MAX_COMPARISON_FINDINGS,
        "initial_finding_window": INITIAL_FINDING_WINDOW,
        "earlier_finding_window": EARLIER_FINDING_WINDOW,
        "maximum_long_session_findings": MAX_LONG_SESSION_FINDINGS,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "provider_invoked": False,
        "automatic_task_creation": False,
        "patch_generation": False,
        "release_decision": "operator_only",
    }
    contract_digest = _digest(stable_contract)
    dynamic_evidence = {
        "campaign_checkpoint_contract_digest": str(campaign_checkpoint.get("contract_digest") or ""),
        "campaign_checkpoint_areas_digest": str(campaign_checkpoint.get("areas_digest") or ""),
        "selection_status": selected["selection_status"],
        "selected_finding_revision": selected["finding_revision"],
        "selected_finding_record_digest": selected["finding_record_digest"],
        "selected_reproducibility_digest": selected["reproducibility_digest"],
        "selected_repair_references_digest": selected["repair_references_digest"],
        "selected_triage_digest": selected["triage_digest"],
        "aggregation_digest": str(aggregation.get("aggregation_digest") or ""),
        "window_digest": str(window.get("window_digest") or ""),
        "console_digest": str(console.get("console_digest") or ""),
        "comparison_status": comparison["comparison_status"],
        "comparison_digest": comparison["comparison_digest"],
    }
    evidence_digest = _digest(dynamic_evidence)

    areas = [
        _area(
            "operator_campaign_evaluation_foundation",
            "ready",
            "v1088 campaign checkpoint remains the explicit evaluation and enrollment foundation",
            checkpoint_status=str(campaign_checkpoint.get("checkpoint_status") or "unknown"),
            area_count=max(0, int(campaign_checkpoint.get("area_count") or 0)),
            contract_digest=str(campaign_checkpoint.get("contract_digest") or ""),
            areas_digest=str(campaign_checkpoint.get("areas_digest") or ""),
        ),
        _area(
            "privacy_safe_finding_intake",
            "ready",
            "findings are explicit private runtime records with bounded public summaries",
            finding_states=list(FINDING_STATES),
            maximum_title_chars=MAX_FINDING_TITLE_CHARS,
            maximum_details_chars=MAX_FINDING_DETAILS_CHARS,
            maximum_findings=MAX_FINDINGS_RETURNED,
            operator_confirmation_required=True,
            optimistic_revision_required=True,
            transcript_inspected=False,
            private_finding_content_returned=False,
        ),
        _area(
            "explicit_reproducibility_review",
            "ready",
            "reproduction attempts are operator-recorded and never automatic provider work",
            outcomes=list(REPRODUCTION_OUTCOMES),
            environment_kinds=list(REPRODUCTION_ENVIRONMENTS),
            maximum_attempts=MAX_REPRODUCTION_ATTEMPTS,
            automatic_rerun=False,
            automatic_replay=False,
            automatic_resend=False,
            private_notes_returned=False,
            private_environment_labels_returned=False,
        ),
        _area(
            "explicit_repair_candidate_references",
            "ready",
            "repair candidates are private references and do not generate or apply patches",
            reference_kinds=list(REFERENCE_KINDS),
            reference_states=list(REFERENCE_STATES),
            maximum_references=MAX_REPAIR_REFERENCES,
            private_reference_values_returned=False,
            automatic_task_created=False,
            automatic_work_item_created=False,
            patch_generated=False,
            patch_applied=False,
        ),
        _area(
            "privacy_safe_finding_aggregation",
            "ready",
            "aggregation is descriptive, bounded, and content-free",
            finding_count=max(0, int(aggregation.get("finding_count") or 0)),
            maximum_findings=MAX_AGGREGATED_FINDINGS,
            aggregation_digest=str(aggregation.get("aggregation_digest") or ""),
            descriptive_counts_only=True,
            findings_ranked=False,
            priority_assigned=False,
            private_content_inspected=False,
        ),
        _area(
            "explicit_triage_and_dispositions",
            "ready",
            "triage remains explicit, revision-guarded, and operator-controlled",
            triage_states=list(FINDING_TRIAGE_STATES),
            triage_dispositions=list(FINDING_TRIAGE_DISPOSITIONS),
            maximum_note_chars=MAX_TRIAGE_NOTE_CHARS,
            automatic_triage=False,
            autonomous_prioritization=False,
            private_triage_notes_returned=False,
        ),
        _area(
            "bounded_repair_intake_comparison",
            "ready",
            "finding comparison is descriptive arithmetic without ranking or release advice",
            minimum_findings=MIN_COMPARISON_FINDINGS,
            maximum_findings=MAX_COMPARISON_FINDINGS,
            comparison_status=comparison["comparison_status"],
            compared_finding_count=comparison["finding_count"],
            comparison_digest=comparison["comparison_digest"],
            findings_ranked=comparison["findings_ranked"],
            winner_selected=comparison["winner_selected"],
            priority_assigned=comparison["priority_assigned"],
            statistical_significance_claimed=comparison["statistical_significance_claimed"],
            release_recommendation_produced=comparison["release_recommendation_produced"],
        ),
        _area(
            "operator_findings_console",
            "ready",
            "console composes redacted read evidence and routes writes through confirmed revision-guarded actions",
            selection_status=str(console.get("selection_status") or "none_selected"),
            console_digest=str(console.get("console_digest") or ""),
            operator_confirmation_required_for_mutation=True,
            optimistic_revision_required=True,
            read_routes_only_for_evidence=True,
        ),
        _area(
            "privacy_safe_repair_intake_export",
            "ready",
            "review export is deterministic, client-side, and content-free",
            selected_export_status="available" if selected["selection_status"] == "available" else "not_selected",
            selected_document_sha256=selected["review_document_sha256"],
            server_file_written=selected["server_file_written"],
            transcript_included=False,
            prompt_included=False,
            private_finding_content_included=False,
            private_reproduction_notes_included=False,
            private_reference_values_included=False,
            private_triage_notes_included=False,
        ),
        _area(
            "long_session_findings_windows",
            "ready",
            "findings use bounded stable windows for long operator sessions",
            total_matching_findings=max(0, int(window.get("total_matching_findings") or 0)),
            returned_count=max(0, int(window.get("returned_count") or 0)),
            initial_window_limit=INITIAL_FINDING_WINDOW,
            earlier_window_limit=EARLIER_FINDING_WINDOW,
            maximum_findings=MAX_LONG_SESSION_FINDINGS,
            stable_ordering=str(window.get("stable_ordering") or ""),
            complete_finding_rows_only=bool(window.get("complete_finding_rows_only")),
            window_digest=str(window.get("window_digest") or ""),
        ),
        _area(
            "selected_finding_evidence",
            "ready",
            "optional selected-finding evidence is bounded and redacted",
            **selected,
        ),
        _area(
            "multi_process_revision_and_source_safety",
            "ready",
            "finding writes retain cross-process exclusion and optimistic revisions while checkpoint reads remain immutable",
            optimistic_revision_required=True,
            cross_process_lock_required=True,
            same_revision_single_winner=True,
            checkpoint_writes_state=False,
            source_tree_written=False,
        ),
        _area(
            "provider_outage_and_no_replay_boundary",
            "ready",
            "finding review remains available as redacted evidence while provider work stays explicit",
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
            finding_text_returned=False,
            reproduction_note_returned=False,
            environment_label_returned=False,
            repair_reference_value_returned=False,
            triage_note_returned=False,
            provider_payload_returned=False,
            credentials_returned=False,
            vectors_returned=False,
            hidden_reasoning_returned=False,
        ),
        _area(
            "operator_authority_and_checkpoint_boundary",
            "ready",
            "checkpoint cannot create work, modify code, or grant protected authority",
            release_decision="operator_only",
            repair_decision="operator_only",
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
            automatic_work_item_created=False,
            patch_generated=False,
            patch_reviewed=False,
            patch_applied=False,
            checkpoint_writes_state=False,
        ),
    ]
    areas_digest = _digest(areas)
    ready = (
        len(areas) == CHECKPOINT_AREA_COUNT
        and campaign_checkpoint.get("checkpoint_status") == "ready_for_operator_campaign_evaluation"
        and not selected["private_content_returned"]
        and not selected["server_file_written"]
        and not comparison["findings_ranked"]
        and not comparison["winner_selected"]
        and not comparison["priority_assigned"]
        and not comparison["statistical_significance_claimed"]
        and not comparison["release_recommendation_produced"]
    )
    return {
        "ok": True,
        "type": "desktop_alpha_evaluation_findings_repair_intake_checkpoint",
        "schema_version": EVALUATION_FINDINGS_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "ready_for_operator_finding_review" if ready else "review_required",
        "area_count": len(areas),
        "areas": areas,
        "contract_digest": contract_digest,
        "evidence_digest": evidence_digest,
        "areas_digest": areas_digest,
        "selected_finding_status": selected["selection_status"],
        "comparison_status": comparison["comparison_status"],
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "automatic_provider_request": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "automatic_finding_creation": False,
        "automatic_reproduction": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_scoring": False,
        "autonomous_prioritization": False,
        "patch_generated": False,
        "patch_reviewed": False,
        "patch_applied": False,
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


def evaluation_findings_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "messages", "user_message", "assistant_response",
        "transcript", "prompt", "private_title", "private_details", "finding_title", "finding_details",
        "private_note", "private_notes", "triage_note", "reproduction_note", "environment_label",
        "private_environment_label", "reference_value", "private_reference_value", "provider_payload",
        "credentials", "vectors", "embedding", "receipt", "receipts", "hidden_reasoning",
        "chain_of_thought", "document",
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
