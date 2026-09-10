from __future__ import annotations

"""Read-only v1087.9 Desktop Alpha daily-evaluation checkpoint.

This checkpoint consolidates the v1087.0-v1087.8 operator-guided daily-
evaluation arc. It emits only bounded states, counts, limits, reason codes,
booleans, and cryptographic digests. It never invokes a provider, reads private
notes or transcript content, mutates evaluation state, writes export files, or
grants release, installation, promotion, approval, rollback, provider, model,
or generation-setting authority.
"""

from typing import Any, Mapping
import hashlib
import json

from conversation_daily_evaluation import DailyEvaluationError, load_daily_evaluation
from conversation_daily_evaluation_protocol import (
    EVALUATION_SIGNALS,
    ISSUE_DOMAINS,
    ISSUE_SEVERITIES,
    MAX_EVALUATION_OBSERVATIONS,
    MAX_OPERATOR_NOTE_CHARS,
    RATING_DIMENSIONS,
    RATING_MAXIMUM,
    RATING_MINIMUM,
    build_daily_evaluation_protocol,
)
from conversation_evaluation_console import build_evaluation_console_state
from conversation_evaluation_long_session import REQUIRED_LONG_SESSION_SIGNALS, build_long_session_evaluation
from conversation_evaluation_outcomes import OUTCOME_CLASSES, classify_evaluation_outcome
from conversation_evaluation_recovery_scenarios import REQUIRED_RECOVERY_SIGNALS, build_restart_outage_evaluation
from conversation_evaluation_reproduction import build_reproduction_packet
from conversation_evaluation_review_export import build_evaluation_review_export
from conversation_evaluation_trends import MAX_TREND_EVALUATIONS, build_daily_evaluation_trends
from release_metadata import RUNTIME_MILESTONE, RUNTIME_VERSION

DAILY_EVALUATION_CHECKPOINT_SCHEMA_VERSION = "1"
CHECKPOINT_AREA_COUNT = 15


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _area(name: str, state: str, reason: str, **metrics: Any) -> dict[str, Any]:
    return {"name": name, "state": state, "reason": reason, "metrics": metrics}


def _classification_probe() -> dict[str, Any]:
    probes = {
        "successful_session": classify_evaluation_outcome(evaluation_state="completed", observations=[]),
        "minor_friction": classify_evaluation_outcome(
            evaluation_state="completed",
            observations=[{"issue_domain": "interface", "severity": "minor", "reproducible": False}],
        ),
        "reproducible_defect": classify_evaluation_outcome(
            evaluation_state="completed",
            observations=[{"issue_domain": "session_continuity", "severity": "major", "reproducible": True}],
        ),
        "provider_failure": classify_evaluation_outcome(
            evaluation_state="completed",
            observations=[{"issue_domain": "provider_transport", "severity": "major", "reproducible": False}],
        ),
        "operator_aborted": classify_evaluation_outcome(evaluation_state="aborted", observations=[]),
    }
    return {
        "outcome_classes": list(OUTCOME_CLASSES),
        "probe_outcomes": {name: str(report.get("outcome") or "") for name, report in probes.items()},
        "probe_reasons": {name: str(report.get("reason") or "") for name, report in probes.items()},
        "classification_digest": _digest({name: report.get("classification_digest") for name, report in probes.items()}),
        "note_text_inspected": any(bool(report.get("note_text_inspected")) for report in probes.values()),
        "transcript_inspected": any(bool(report.get("transcript_inspected")) for report in probes.values()),
        "provider_invoked": any(bool(report.get("provider_invoked")) for report in probes.values()),
        "writes_state": any(bool(report.get("writes_state")) for report in probes.values()),
    }


def _selected_evaluation_probe(evaluation_id: str) -> dict[str, Any]:
    token = str(evaluation_id or "").strip()
    if not token:
        return {
            "selection_status": "none_selected",
            "evaluation_id": "",
            "evaluation_state": "",
            "evaluation_revision": 0,
            "observation_count": 0,
            "outcome": "unclassified",
            "reproduction_packet_digest": "",
            "restart_outage_status": "not_selected",
            "restart_outage_covered_count": 0,
            "restart_outage_required_count": len(REQUIRED_RECOVERY_SIGNALS),
            "long_session_status": "not_selected",
            "long_session_covered_count": 0,
            "long_session_required_count": len(REQUIRED_LONG_SESSION_SIGNALS),
            "review_digest": "",
            "review_document_sha256": "",
            "server_file_written": False,
            "private_content_returned": False,
        }
    try:
        summary = load_daily_evaluation(token)
        reproduction = build_reproduction_packet(token)
        recovery = build_restart_outage_evaluation(token)
        long_session = build_long_session_evaluation(token)
        review_export = build_evaluation_review_export(token)
    except DailyEvaluationError:
        return {
            "selection_status": "not_found",
            "evaluation_id": "",
            "evaluation_state": "",
            "evaluation_revision": 0,
            "observation_count": 0,
            "outcome": "unclassified",
            "reproduction_packet_digest": "",
            "restart_outage_status": "not_found",
            "restart_outage_covered_count": 0,
            "restart_outage_required_count": len(REQUIRED_RECOVERY_SIGNALS),
            "long_session_status": "not_found",
            "long_session_covered_count": 0,
            "long_session_required_count": len(REQUIRED_LONG_SESSION_SIGNALS),
            "review_digest": "",
            "review_document_sha256": "",
            "server_file_written": False,
            "private_content_returned": False,
        }
    outcome = summary.get("outcome") if isinstance(summary.get("outcome"), Mapping) else {}
    review = review_export.get("review") if isinstance(review_export.get("review"), Mapping) else {}
    return {
        "selection_status": "available",
        "evaluation_id": str(summary.get("evaluation_id") or ""),
        "evaluation_state": str(summary.get("state") or "active"),
        "evaluation_revision": max(0, int(summary.get("revision") or 0)),
        "observation_count": max(0, int(summary.get("observation_count") or 0)),
        "outcome": str(outcome.get("outcome") or outcome.get("outcome_code") or "unclassified"),
        "reproduction_packet_digest": str(reproduction.get("packet_digest") or ""),
        "restart_outage_status": str(recovery.get("coverage_status") or "incomplete"),
        "restart_outage_covered_count": max(0, int(recovery.get("covered_count") or 0)),
        "restart_outage_required_count": max(0, int(recovery.get("required_count") or 0)),
        "long_session_status": str(long_session.get("coverage_status") or "incomplete"),
        "long_session_covered_count": max(0, int(long_session.get("covered_count") or 0)),
        "long_session_required_count": max(0, int(long_session.get("required_count") or 0)),
        "review_digest": str(review.get("review_digest") or ""),
        "review_document_sha256": str(review_export.get("document_sha256") or ""),
        "server_file_written": bool(review_export.get("server_file_written")),
        "private_content_returned": bool(
            summary.get("private_note_content_returned")
            or review.get("private_notes_included")
            or review.get("transcript_included")
            or review.get("prompt_included")
            or review.get("memory_content_included")
            or review.get("provider_payload_included")
            or review.get("credentials_included")
            or review.get("vectors_included")
            or review.get("hidden_reasoning_included")
        ),
    }


def build_daily_evaluation_checkpoint(*, evaluation_id: str = "", session_id: str = "") -> dict[str, Any]:
    protocol = build_daily_evaluation_protocol(session_id=session_id)
    trends = build_daily_evaluation_trends(maximum_evaluations=MAX_TREND_EVALUATIONS)
    classification = _classification_probe()
    selected = _selected_evaluation_probe(evaluation_id)
    console = build_evaluation_console_state(evaluation_id=evaluation_id, session_id=session_id)

    stable_contract = {
        "runtime_version": RUNTIME_VERSION,
        "rating_dimensions": list(RATING_DIMENSIONS),
        "rating_scale": {"minimum": RATING_MINIMUM, "maximum": RATING_MAXIMUM},
        "maximum_observations": MAX_EVALUATION_OBSERVATIONS,
        "maximum_operator_note_chars": MAX_OPERATOR_NOTE_CHARS,
        "issue_domains": list(ISSUE_DOMAINS),
        "issue_severities": list(ISSUE_SEVERITIES),
        "evaluation_signals": list(EVALUATION_SIGNALS),
        "outcome_classes": list(OUTCOME_CLASSES),
        "recovery_signals": list(REQUIRED_RECOVERY_SIGNALS),
        "long_session_signals": list(REQUIRED_LONG_SESSION_SIGNALS),
        "maximum_trend_evaluations": MAX_TREND_EVALUATIONS,
        "operator_confirmation_required": True,
        "optimistic_revision_required": True,
        "provider_invoked": False,
        "automatic_replay": False,
        "automatic_resend": False,
        "server_export_file_written": False,
        "release_decision": "operator_only",
    }
    contract_digest = _digest(stable_contract)
    dynamic_evidence = {
        "protocol_digest": str(protocol.get("readiness_contract_digest") or ""),
        "trends_digest": str(trends.get("evidence_digest") or ""),
        "trend_evaluation_count": max(0, int(trends.get("evaluation_count") or 0)),
        "selection_status": selected["selection_status"],
        "selected_review_digest": selected["review_digest"],
        "console_digest": str(console.get("console_digest") or ""),
    }
    evidence_digest = _digest(dynamic_evidence)

    areas = [
        _area(
            "conversation_readiness_bridge", "ready" if protocol.get("protocol_status") == "ready" else "review_required",
            str(protocol.get("readiness_checkpoint_status") or "unknown"),
            readiness_area_count=max(0, int(protocol.get("readiness_area_count") or 0)),
            readiness_contract_digest=str(protocol.get("readiness_contract_digest") or ""),
            readiness_areas_digest=str(protocol.get("readiness_areas_digest") or ""),
            session_requested=bool(protocol.get("session_requested")),
            session_available=bool(protocol.get("session_available")),
            writes_state=False,
        ),
        _area(
            "operator_observation_capture", "ready", "explicit_private_runtime_capture",
            rating_dimensions=list(RATING_DIMENSIONS),
            rating_minimum=RATING_MINIMUM,
            rating_maximum=RATING_MAXIMUM,
            maximum_observations=MAX_EVALUATION_OBSERVATIONS,
            maximum_private_note_chars=MAX_OPERATOR_NOTE_CHARS,
            explicit_confirmation_required=True,
            optimistic_revision_required=True,
            private_notes_runtime_only=True,
            private_note_content_returned=False,
        ),
        _area(
            "session_outcome_classification", "ready", "explicit_operator_markers_only",
            **classification,
            autonomous_scoring=False,
            release_certified=False,
        ),
        _area(
            "privacy_safe_reproduction_packets", "ready", "content_free_digest_bound_packet",
            selection_status=selected["selection_status"],
            packet_digest=selected["reproduction_packet_digest"],
            environment_family_only=True,
            transcript_included=False,
            prompt_included=False,
            private_notes_included=False,
            provider_payload_included=False,
            credentials_included=False,
            vectors_included=False,
            hidden_reasoning_included=False,
            writes_state=False,
        ),
        _area(
            "bounded_longitudinal_trends", "ready", "bounded_nonstatistical_aggregation",
            evaluation_count=max(0, int(trends.get("evaluation_count") or 0)),
            maximum_evaluations=max(0, int(trends.get("maximum_evaluations") or 0)),
            sample_too_small=bool(trends.get("sample_too_small")),
            statistical_significance_claimed=bool(trends.get("statistical_significance_claimed")),
            outcome_counts=dict(trends.get("outcome_counts") or {}),
            evidence_digest=str(trends.get("evidence_digest") or ""),
            private_notes_returned=bool(trends.get("private_notes_returned")),
            provider_invoked=bool(trends.get("provider_invoked")),
            writes_state=bool(trends.get("writes_state")),
        ),
        _area(
            "restart_and_session_resumption_evaluation", "ready", "explicit_signal_coverage",
            selection_status=selected["selection_status"],
            coverage_status=selected["restart_outage_status"],
            covered_count=selected["restart_outage_covered_count"],
            required_count=selected["restart_outage_required_count"],
            restart_signal_required="restart_resume" in REQUIRED_RECOVERY_SIGNALS,
            provider_invoked=False,
            writes_state=False,
        ),
        _area(
            "provider_outage_return_and_no_replay", "ready", "operator_observation_without_execution",
            outage_signal_required="provider_outage" in REQUIRED_RECOVERY_SIGNALS,
            return_signal_required="provider_return" in REQUIRED_RECOVERY_SIGNALS,
            automatic_request_replay=False,
            automatic_resend=False,
            provider_invoked=False,
            generation_invoked=False,
        ),
        _area(
            "interruption_retry_regeneration_resend", "ready", "separate_explicit_evaluation_signals",
            generation_interruption_signal="generation_interruption" in REQUIRED_RECOVERY_SIGNALS,
            failed_retry_signal="failed_retry" in REQUIRED_RECOVERY_SIGNALS,
            completed_regeneration_signal="completed_regeneration" in REQUIRED_RECOVERY_SIGNALS,
            explicit_resend_signal="explicit_resend" in REQUIRED_RECOVERY_SIGNALS,
            identities_remain_separate=True,
            automatic_retry=False,
            automatic_regeneration=False,
            automatic_resend=False,
        ),
        _area(
            "long_session_daily_use_evaluation", "ready", "bounded_explicit_signal_coverage",
            selection_status=selected["selection_status"],
            coverage_status=selected["long_session_status"],
            covered_count=selected["long_session_covered_count"],
            required_count=selected["long_session_required_count"],
            required_signals=list(REQUIRED_LONG_SESSION_SIGNALS),
            transcript_inspected=False,
            private_notes_inspected=False,
            provider_invoked=False,
            writes_state=False,
        ),
        _area(
            "desktop_alpha_evaluation_console", "ready", str(console.get("selection_status") or "none_selected"),
            console_digest=str(console.get("console_digest") or ""),
            operator_confirmation_required_for_mutation=bool(console.get("operator_confirmation_required_for_mutation")),
            read_routes_only=bool(console.get("read_routes_only")),
            provider_invoked=bool(console.get("provider_invoked")),
            generation_invoked=bool(console.get("generation_invoked")),
            writes_state=bool(console.get("writes_state")),
            release_certified=bool(console.get("release_certified")),
        ),
        _area(
            "privacy_safe_review_export", "ready", "client_download_without_server_persistence",
            selection_status=selected["selection_status"],
            review_digest=selected["review_digest"],
            document_sha256=selected["review_document_sha256"],
            server_file_written=selected["server_file_written"],
            private_content_returned=selected["private_content_returned"],
            operator_review_required=True,
            release_decision="operator_only",
            installation_decision="operator_only",
            promotion_decision="operator_only",
        ),
        _area(
            "revision_multi_tab_and_exactly_once_safety", "ready", "optimistic_revision_and_existing_claims",
            optimistic_revision_required=True,
            stale_revision_rejected=True,
            explicit_operator_confirmation_required=True,
            existing_multi_tab_claims_preserved=True,
            automatic_duplicate_mutation=False,
            source_tree_written=False,
        ),
        _area(
            "provider_free_non_autonomous_evaluation", "ready", "operator_guided_evidence_only",
            provider_invoked=False,
            embedding_provider_invoked=False,
            generation_invoked=False,
            autonomous_scoring=False,
            automatic_release_certification=False,
            provider_switching=False,
            model_management=False,
            generation_settings_changed=False,
        ),
        _area(
            "private_runtime_source_only_and_redaction", "ready", "private_state_excluded_from_public_evidence",
            private_notes_runtime_only=True,
            transcript_content_required=False,
            private_content_returned=selected["private_content_returned"],
            source_tree_written=False,
            server_export_file_written=selected["server_file_written"],
            content_free=True,
            redacted=True,
        ),
        _area(
            "operator_authority_and_release_boundary", "ready", "operator_only_decisions",
            approval_granted=False,
            rollback_authorized=False,
            installation_performed=False,
            promotion_performed=False,
            release_certified=False,
            release_decision="operator_only",
            checkpoint_writes_state=False,
        ),
    ]

    all_ready = (
        len(areas) == CHECKPOINT_AREA_COUNT
        and all(area["state"] in {"ready", "review_required"} for area in areas)
        and protocol.get("protocol_status") == "ready"
        and not classification["provider_invoked"]
        and not classification["writes_state"]
        and not trends.get("provider_invoked")
        and not trends.get("writes_state")
        and not trends.get("statistical_significance_claimed")
        and not console.get("provider_invoked")
        and not console.get("generation_invoked")
        and not console.get("writes_state")
        and not selected["server_file_written"]
        and not selected["private_content_returned"]
    )
    return {
        "type": "desktop_alpha_daily_evaluation_checkpoint",
        "schema_version": DAILY_EVALUATION_CHECKPOINT_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_milestone": RUNTIME_MILESTONE,
        "checkpoint_status": "ready_for_operator_daily_evaluation" if all_ready else "review_required",
        "area_count": len(areas),
        "ready_area_count": sum(1 for area in areas if area["state"] == "ready"),
        "review_required_area_count": sum(1 for area in areas if area["state"] == "review_required"),
        "areas": areas,
        "selected_evaluation_status": selected["selection_status"],
        "selected_evaluation_id": selected["evaluation_id"],
        "selected_evaluation_state": selected["evaluation_state"],
        "selected_evaluation_revision": selected["evaluation_revision"],
        "selected_observation_count": selected["observation_count"],
        "selected_outcome": selected["outcome"],
        "contract_digest": contract_digest,
        "evidence_digest": evidence_digest,
        "areas_digest": _digest(areas),
        "provider_invoked": False,
        "embedding_provider_invoked": False,
        "generation_invoked": False,
        "writes_state": False,
        "read_only": True,
        "content_free": True,
        "redacted": True,
        "operator_review_required": True,
        "release_certified": False,
        "promotion_performed": False,
        "installation_performed": False,
    }


def daily_evaluation_checkpoint_contains_private_fields(value: Mapping[str, Any] | None) -> bool:
    forbidden = {
        "note", "notes", "content", "text", "message", "messages", "user_message",
        "assistant_response", "transcript", "prompt", "memory", "memories",
        "temporary_instruction", "pinned_context", "queued_operator_intent",
        "provider_payload", "credentials", "vectors", "embedding", "receipt",
        "receipts", "document", "hidden_reasoning", "chain_of_thought",
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
