from __future__ import annotations

"""Read-only v1090.9 Desktop Alpha repair-candidate review checkpoint.

The checkpoint consolidates v1090.0-v1090.8 into bounded states, counts,
limits, reason codes, booleans, and digests only. It never exposes private
candidate labels, references, review notes, verification notes, lineage notes,
export document bodies, transcripts, prompts, provider payloads, credentials,
vectors, or hidden reasoning. It never invokes a provider, opens or executes a
candidate, runs tests, mutates a finding, creates work, generates or applies a
patch, or grants testing approval, application approval, rollback,
installation, promotion, model, provider, or release authority.
"""

from collections.abc import Iterable, Mapping
from typing import Any
import hashlib
import json

from conversation_evaluation_finding import EvaluationFindingError
from conversation_evaluation_finding_checkpoint import build_evaluation_findings_checkpoint
from repair_candidate_comparison import (
    MAX_REPAIR_CANDIDATES_FOR_COMPARISON,
    MIN_REPAIR_CANDIDATES_FOR_COMPARISON,
    build_repair_candidate_comparison,
)
from repair_candidate_console import build_repair_candidate_console_state
from repair_candidate_lineage import (
    REPAIR_CANDIDATE_LINEAGE_KINDS,
    MAX_REPAIR_CANDIDATE_LINEAGE_EDGES,
    build_repair_candidate_lineage,
)
from repair_candidate_long_session import (
    EARLIER_CANDIDATE_WINDOW,
    INITIAL_CANDIDATE_WINDOW,
    MAX_LONG_SESSION_CANDIDATES,
    build_repair_candidate_window,
)
from repair_candidate_registration import build_repair_candidate_registrations
from repair_candidate_review import build_repair_candidate_review
from repair_candidate_review_export import build_repair_candidate_review_export
from repair_candidate_review_protocol import (
    MAX_CANDIDATE_LABEL_CHARS,
    MAX_CANDIDATE_REFERENCE_CHARS,
    MAX_CANDIDATE_REVIEW_NOTE_CHARS,
    MAX_REPAIR_CANDIDATES_PER_FINDING,
    MAX_REPAIR_CANDIDATE_REVIEW_EVENTS,
    REPAIR_CANDIDATE_KINDS,
    REPAIR_CANDIDATE_REVIEW_AREAS,
    REPAIR_CANDIDATE_REVIEW_STATES,
    build_repair_candidate_review_protocol,
)
from repair_candidate_verification_evidence import (
    MAX_VERIFICATION_EVIDENCE_PER_CANDIDATE,
    MAX_VERIFICATION_NOTE_CHARS,
    VERIFICATION_EVIDENCE_KINDS,
    VERIFICATION_RESULTS,
    build_repair_candidate_verification_evidence,
)
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

REPAIR_CANDIDATE_REVIEW_CHECKPOINT_SCHEMA_VERSION = "1"
CHECKPOINT_AREA_COUNT = 15


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _area(name: str, state: str, reason: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "reason": reason, "metrics": metrics}


def _selected_candidate_probe(finding_id: str, candidate_id: str) -> dict[str, Any]:
    finding_token = str(finding_id or "").strip()
    candidate_token = str(candidate_id or "").strip()
    empty = {
        "finding_id": "",
        "finding_revision": 0,
        "candidate_id": "",
        "candidate_kind": "",
        "artifact_sha256": "",
        "source_manifest_sha256": "",
        "registration_evidence_digest": "",
        "review_state": "",
        "review_event_count": 0,
        "verification_evidence_count": 0,
        "passing_evidence_count": 0,
        "failing_evidence_count": 0,
        "inconclusive_evidence_count": 0,
        "lineage_edge_count": 0,
        "registrations_digest": "",
        "review_digest": "",
        "verification_evidence_digest": "",
        "lineage_digest": "",
        "review_document_sha256": "",
        "server_file_written": False,
        "private_content_returned": False,
    }
    if not finding_token and not candidate_token:
        return {"selection_status": "none_selected", **empty}
    if not finding_token or not candidate_token:
        return {"selection_status": "incomplete_selection", **empty}
    try:
        registrations = build_repair_candidate_registrations(finding_token)
        candidate = next(
            (
                row
                for row in list(registrations.get("candidates") or ())
                if str(row.get("candidate_id") or "") == candidate_token
            ),
            None,
        )
        if candidate is None:
            raise EvaluationFindingError("Repair candidate registration not found.")
        review = build_repair_candidate_review(finding_token, candidate_token)
        verification = build_repair_candidate_verification_evidence(finding_token, candidate_token)
        lineage = build_repair_candidate_lineage(finding_token)
        export = build_repair_candidate_review_export(finding_token, candidate_token)
    except EvaluationFindingError:
        return {"selection_status": "not_found", **empty}
    document = export.get("review") if isinstance(export.get("review"), Mapping) else {}
    result_counts = verification.get("result_counts") if isinstance(verification.get("result_counts"), Mapping) else {}
    related_edges = [
        edge for edge in list(lineage.get("lineage_edges") or ())
        if str(edge.get("predecessor_candidate_id") or "") == candidate_token
        or str(edge.get("successor_candidate_id") or "") == candidate_token
    ]
    return {
        "selection_status": "available",
        "finding_id": finding_token,
        "finding_revision": max(0, int(registrations.get("finding_revision") or 0)),
        "candidate_id": candidate_token,
        "candidate_kind": str(candidate.get("candidate_kind") or ""),
        "artifact_sha256": str(candidate.get("artifact_sha256") or ""),
        "source_manifest_sha256": str(candidate.get("source_manifest_sha256") or ""),
        "registration_evidence_digest": str(candidate.get("evidence_digest") or ""),
        "review_state": str(candidate.get("review_state") or "registered"),
        "review_event_count": max(0, int(review.get("review_event_count") or 0)),
        "verification_evidence_count": max(0, int(verification.get("verification_evidence_count") or 0)),
        "passing_evidence_count": max(0, int(result_counts.get("pass") or 0)),
        "failing_evidence_count": max(0, int(result_counts.get("fail") or 0)),
        "inconclusive_evidence_count": max(0, int(result_counts.get("inconclusive") or 0)),
        "lineage_edge_count": len(related_edges),
        "registrations_digest": str(registrations.get("registrations_digest") or ""),
        "review_digest": str(review.get("review_digest") or ""),
        "verification_evidence_digest": str(verification.get("verification_evidence_digest") or ""),
        "lineage_digest": _digest(related_edges),
        "review_document_sha256": str(export.get("document_sha256") or ""),
        "server_file_written": bool(export.get("server_file_written")),
        "private_content_returned": bool(
            candidate.get("private_label_returned")
            or candidate.get("private_reference_returned")
            or review.get("private_notes_returned")
            or verification.get("private_notes_returned")
            or lineage.get("private_notes_returned")
            or document.get("private_labels_included")
            or document.get("private_references_included")
            or document.get("private_review_notes_included")
            or document.get("private_verification_notes_included")
            or document.get("private_lineage_notes_included")
            or document.get("transcript_included")
            or document.get("prompt_included")
            or document.get("memory_content_included")
            or document.get("provider_payload_included")
            or document.get("credentials_included")
            or document.get("vectors_included")
            or document.get("hidden_reasoning_included")
        ),
    }


def _comparison_probe(finding_id: str, candidate_ids: Iterable[str]) -> dict[str, Any]:
    normalized = list(dict.fromkeys(str(item or "").strip() for item in candidate_ids if str(item or "").strip()))
    if len(normalized) < MIN_REPAIR_CANDIDATES_FOR_COMPARISON:
        return {
            "comparison_status": "not_requested",
            "candidate_count": len(normalized),
            "comparison_digest": "",
            "candidates_ranked": False,
            "winner_selected": False,
            "priority_assigned": False,
            "statistical_significance_claimed": False,
            "release_recommendation_produced": False,
        }
    if not str(finding_id or "").strip():
        return {
            "comparison_status": "invalid_request",
            "candidate_count": len(normalized),
            "comparison_digest": "",
            "candidates_ranked": False,
            "winner_selected": False,
            "priority_assigned": False,
            "statistical_significance_claimed": False,
            "release_recommendation_produced": False,
        }
    try:
        report = build_repair_candidate_comparison(
            str(finding_id or "").strip(),
            normalized[:MAX_REPAIR_CANDIDATES_FOR_COMPARISON],
        )
    except EvaluationFindingError:
        return {
            "comparison_status": "invalid_request",
            "candidate_count": len(normalized),
            "comparison_digest": "",
            "candidates_ranked": False,
            "winner_selected": False,
            "priority_assigned": False,
            "statistical_significance_claimed": False,
            "release_recommendation_produced": False,
        }
    return {
        "comparison_status": "available",
        "candidate_count": max(0, int(report.get("candidate_count") or 0)),
        "comparison_digest": str(report.get("comparison_digest") or ""),
        "candidates_ranked": bool(report.get("candidates_ranked")),
        "winner_selected": bool(report.get("winner_selected")),
        "priority_assigned": bool(report.get("priority_assigned")),
        "statistical_significance_claimed": bool(report.get("statistical_significance_claimed")),
        "release_recommendation_produced": bool(report.get("release_recommendation_produced")),
    }


def build_repair_candidate_review_checkpoint(
    *,
    finding_id: str = "",
    candidate_id: str = "",
    comparison_candidate_ids: Iterable[str] = (),
    candidate_kind: str = "",
    review_state: str = "",
) -> dict[str, Any]:
    findings_checkpoint = build_evaluation_findings_checkpoint(finding_id=finding_id)
    protocol = build_repair_candidate_review_protocol()
    selected = _selected_candidate_probe(finding_id, candidate_id)
    comparison_ids = list(comparison_candidate_ids)
    comparison = _comparison_probe(finding_id, comparison_ids)
    window = build_repair_candidate_window(
        finding_id=finding_id,
        candidate_kind=candidate_kind,
        review_state=review_state,
    )
    console = build_repair_candidate_console_state(
        finding_id=finding_id,
        candidate_id=candidate_id,
        comparison_candidate_ids=comparison_ids,
        candidate_kind=candidate_kind,
        review_state=review_state,
    )

    stable_contract = {
        "runtime_version": RUNTIME_VERSION,
        "candidate_kinds": list(REPAIR_CANDIDATE_KINDS),
        "review_states": list(REPAIR_CANDIDATE_REVIEW_STATES),
        "review_areas": list(REPAIR_CANDIDATE_REVIEW_AREAS),
        "maximum_candidates_per_finding": MAX_REPAIR_CANDIDATES_PER_FINDING,
        "maximum_review_events_per_candidate": MAX_REPAIR_CANDIDATE_REVIEW_EVENTS,
        "maximum_private_label_chars": MAX_CANDIDATE_LABEL_CHARS,
        "maximum_private_reference_chars": MAX_CANDIDATE_REFERENCE_CHARS,
        "maximum_private_review_note_chars": MAX_CANDIDATE_REVIEW_NOTE_CHARS,
        "verification_evidence_kinds": list(VERIFICATION_EVIDENCE_KINDS),
        "verification_results": list(VERIFICATION_RESULTS),
        "maximum_verification_evidence_per_candidate": MAX_VERIFICATION_EVIDENCE_PER_CANDIDATE,
        "maximum_private_verification_note_chars": MAX_VERIFICATION_NOTE_CHARS,
        "comparison_candidate_minimum": MIN_REPAIR_CANDIDATES_FOR_COMPARISON,
        "comparison_candidate_maximum": MAX_REPAIR_CANDIDATES_FOR_COMPARISON,
        "lineage_relations": list(REPAIR_CANDIDATE_LINEAGE_KINDS),
        "maximum_lineage_edges_per_finding": MAX_REPAIR_CANDIDATE_LINEAGE_EDGES,
        "initial_candidate_window": INITIAL_CANDIDATE_WINDOW,
        "earlier_candidate_window": EARLIER_CANDIDATE_WINDOW,
        "maximum_long_session_candidates": MAX_LONG_SESSION_CANDIDATES,
        "most_favorable_review_state": "acceptable_for_testing",
        "application_approval_state_exists": False,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "automatic_test_execution": False,
        "candidate_ranking": False,
        "winner_selection": False,
        "release_decision": "operator_only",
    }
    contract_digest = _digest(stable_contract)
    dynamic_evidence = {
        "findings_checkpoint_contract_digest": str(findings_checkpoint.get("contract_digest") or ""),
        "findings_checkpoint_areas_digest": str(findings_checkpoint.get("areas_digest") or ""),
        "protocol_digest": str(protocol.get("protocol_digest") or ""),
        "console_digest": str(console.get("console_digest") or ""),
        "window_digest": str(window.get("window_digest") or ""),
        "selection_status": selected["selection_status"],
        "selected_finding_revision": selected["finding_revision"],
        "selected_registrations_digest": selected["registrations_digest"],
        "selected_review_digest": selected["review_digest"],
        "selected_verification_evidence_digest": selected["verification_evidence_digest"],
        "selected_lineage_digest": selected["lineage_digest"],
        "comparison_status": comparison["comparison_status"],
        "comparison_digest": comparison["comparison_digest"],
    }
    evidence_digest = _digest(dynamic_evidence)

    areas = [
        _area(
            "evaluation_findings_foundation",
            "ready",
            "v1089 evaluation-findings checkpoint remains the candidate-review evidence foundation",
            checkpoint_status=str(findings_checkpoint.get("checkpoint_status") or "unknown"),
            area_count=max(0, int(findings_checkpoint.get("area_count") or 0)),
            contract_digest=str(findings_checkpoint.get("contract_digest") or ""),
            areas_digest=str(findings_checkpoint.get("areas_digest") or ""),
        ),
        _area(
            "repair_candidate_review_protocol",
            "ready",
            "candidate review vocabulary and limits are bounded and operator-controlled",
            protocol_status=str(protocol.get("protocol_status") or "review_required"),
            candidate_kinds=list(REPAIR_CANDIDATE_KINDS),
            review_states=list(REPAIR_CANDIDATE_REVIEW_STATES),
            review_areas=list(REPAIR_CANDIDATE_REVIEW_AREAS),
            maximum_candidates_per_finding=MAX_REPAIR_CANDIDATES_PER_FINDING,
            maximum_review_events_per_candidate=MAX_REPAIR_CANDIDATE_REVIEW_EVENTS,
            most_favorable_review_state="acceptable_for_testing",
            application_approval_state_exists=False,
            protocol_digest=str(protocol.get("protocol_digest") or ""),
        ),
        _area(
            "immutable_candidate_registration",
            "ready",
            "operator-supplied candidates are bound to immutable artifact identity and private references",
            artifact_sha256_required=True,
            source_manifest_sha256_supported=True,
            finding_id_required=True,
            maximum_candidates=MAX_REPAIR_CANDIDATES_PER_FINDING,
            immutable_artifact_identity=True,
            automatic_registration=False,
            candidate_generation=False,
            private_labels_returned=False,
            private_references_returned=False,
        ),
        _area(
            "explicit_candidate_review_findings",
            "ready",
            "candidate review events are append-only, revision-guarded, and stop at acceptable-for-testing",
            review_states=list(REPAIR_CANDIDATE_REVIEW_STATES),
            review_areas=list(REPAIR_CANDIDATE_REVIEW_AREAS),
            maximum_review_events=MAX_REPAIR_CANDIDATE_REVIEW_EVENTS,
            most_favorable_review_state="acceptable_for_testing",
            application_approval_state_exists=False,
            automatic_review=False,
            private_review_notes_returned=False,
        ),
        _area(
            "deterministic_verification_evidence",
            "ready",
            "operators attach artifact-bound verification evidence without automatic execution",
            evidence_kinds=list(VERIFICATION_EVIDENCE_KINDS),
            results=list(VERIFICATION_RESULTS),
            maximum_evidence=MAX_VERIFICATION_EVIDENCE_PER_CANDIDATE,
            automatic_test_execution=False,
            source_tree_immutability_recorded=True,
            private_verification_notes_returned=False,
        ),
        _area(
            "bounded_candidate_comparison",
            "ready",
            "candidate comparison is descriptive arithmetic without ranking, winner selection, or release advice",
            minimum_candidates=MIN_REPAIR_CANDIDATES_FOR_COMPARISON,
            maximum_candidates=MAX_REPAIR_CANDIDATES_FOR_COMPARISON,
            comparison_status=comparison["comparison_status"],
            compared_candidate_count=comparison["candidate_count"],
            comparison_digest=comparison["comparison_digest"],
            candidates_ranked=comparison["candidates_ranked"],
            winner_selected=comparison["winner_selected"],
            priority_assigned=comparison["priority_assigned"],
            statistical_significance_claimed=comparison["statistical_significance_claimed"],
            release_recommendation_produced=comparison["release_recommendation_produced"],
        ),
        _area(
            "immutable_supersession_lineage",
            "ready",
            "lineage preserves history, prevents cycles, and never deletes or applies a candidate",
            lineage_relations=list(REPAIR_CANDIDATE_LINEAGE_KINDS),
            maximum_edges=MAX_REPAIR_CANDIDATE_LINEAGE_EDGES,
            cycle_prevention=True,
            ambiguous_successor_prevention=True,
            predecessor_history_preserved=True,
            successor_auto_selected=False,
            private_lineage_notes_returned=False,
        ),
        _area(
            "operator_candidate_review_console",
            "ready",
            "console composes redacted evidence and routes all writes through confirmed revision-guarded actions",
            selection_status=str(console.get("selection_status") or "none_selected"),
            console_digest=str(console.get("console_digest") or ""),
            operator_confirmation_required_for_mutation=True,
            optimistic_revision_required=True,
            read_routes_only_for_evidence=True,
        ),
        _area(
            "privacy_safe_candidate_review_export",
            "ready",
            "candidate review export is deterministic, client-side, and content-free",
            selected_export_status="available" if selected["selection_status"] == "available" else "not_selected",
            selected_document_sha256=selected["review_document_sha256"],
            server_file_written=selected["server_file_written"],
            private_labels_included=False,
            private_references_included=False,
            private_review_notes_included=False,
            private_verification_notes_included=False,
            private_lineage_notes_included=False,
            transcript_included=False,
            prompt_included=False,
        ),
        _area(
            "long_session_candidate_windows",
            "ready",
            "candidate review uses bounded stable windows for long operator sessions",
            total_matching_candidates=max(0, int(window.get("total_matching_candidates") or 0)),
            returned_count=max(0, int(window.get("returned_count") or 0)),
            initial_window_limit=INITIAL_CANDIDATE_WINDOW,
            earlier_window_limit=EARLIER_CANDIDATE_WINDOW,
            maximum_candidates=MAX_LONG_SESSION_CANDIDATES,
            stable_ordering=str(window.get("stable_ordering") or ""),
            complete_candidate_rows_only=bool(window.get("complete_candidate_rows_only")),
            window_digest=str(window.get("window_digest") or ""),
        ),
        _area(
            "selected_candidate_evidence",
            "ready",
            "optional selected-candidate evidence is artifact-bound, bounded, and redacted",
            **selected,
        ),
        _area(
            "multi_process_revision_and_source_safety",
            "ready",
            "candidate writes retain cross-process exclusion and optimistic revisions while checkpoint reads remain immutable",
            optimistic_revision_required=True,
            cross_process_lock_required=True,
            same_revision_single_winner=True,
            checkpoint_writes_state=False,
            source_tree_written=False,
        ),
        _area(
            "provider_outage_and_no_execution_boundary",
            "ready",
            "candidate review remains available as redacted evidence while provider and execution work stay explicit",
            provider_invoked=False,
            generation_invoked=False,
            automatic_provider_request=False,
            automatic_test_execution=False,
            automatic_replay=False,
            automatic_resend=False,
            candidate_opened=False,
            artifact_executed=False,
        ),
        _area(
            "content_free_privacy_boundary",
            "ready",
            "public checkpoint evidence excludes private candidate, runtime, and model content",
            private_content_returned=selected["private_content_returned"],
            private_label_returned=False,
            private_reference_returned=False,
            private_review_note_returned=False,
            private_verification_note_returned=False,
            private_lineage_note_returned=False,
            transcript_returned=False,
            prompt_returned=False,
            provider_payload_returned=False,
            credentials_returned=False,
            vectors_returned=False,
            hidden_reasoning_returned=False,
        ),
        _area(
            "operator_authority_and_checkpoint_boundary",
            "ready",
            "checkpoint cannot test, create work, modify code, or grant protected authority",
            testing_decision="operator_only",
            application_decision="operator_only",
            approval_decision="operator_only",
            release_decision="operator_only",
            automatic_test_execution=False,
            automatic_task_created=False,
            automatic_work_item_created=False,
            candidate_ranked=False,
            winner_selected=False,
            patch_generated=False,
            patch_reviewed_automatically=False,
            patch_applied=False,
            approval_granted=False,
            rollback_authorized=False,
            installation_performed=False,
            promotion_performed=False,
            release_recommendation_produced=False,
            release_certified=False,
            model_management=False,
            provider_switching=False,
            generation_settings_changed=False,
            checkpoint_writes_state=False,
        ),
    ]
    areas_digest = _digest(areas)
    ready = (
        len(areas) == CHECKPOINT_AREA_COUNT
        and findings_checkpoint.get("checkpoint_status") == "ready_for_operator_finding_review"
        and protocol.get("protocol_status") == "ready"
        and not selected["private_content_returned"]
        and not selected["server_file_written"]
        and not comparison["candidates_ranked"]
        and not comparison["winner_selected"]
        and not comparison["priority_assigned"]
        and not comparison["statistical_significance_claimed"]
        and not comparison["release_recommendation_produced"]
    )
    return {
        "ok": True,
        "type": "desktop_alpha_repair_candidate_review_checkpoint",
        "schema_version": REPAIR_CANDIDATE_REVIEW_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "ready_for_operator_candidate_review" if ready else "review_required",
        "area_count": len(areas),
        "areas": areas,
        "contract_digest": contract_digest,
        "evidence_digest": evidence_digest,
        "areas_digest": areas_digest,
        "selected_candidate_status": selected["selection_status"],
        "comparison_status": comparison["comparison_status"],
        "provider_invoked": False,
        "generation_invoked": False,
        "automatic_provider_request": False,
        "automatic_test_execution": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "automatic_task_created": False,
        "automatic_work_item_created": False,
        "autonomous_scoring": False,
        "autonomous_prioritization": False,
        "candidate_ranked": False,
        "winner_selected": False,
        "patch_generated": False,
        "patch_reviewed_automatically": False,
        "patch_applied": False,
        "approval_granted": False,
        "rollback_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "release_recommendation_produced": False,
        "release_certified": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
    }


def repair_candidate_review_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "content", "text", "message", "messages", "transcript", "prompt",
        "private_label", "private_reference", "private_note", "note", "notes",
        "provider_payload", "credentials", "vectors", "embedding", "receipt", "receipts",
        "hidden_reasoning", "chain_of_thought", "document",
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
