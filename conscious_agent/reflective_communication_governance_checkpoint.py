from __future__ import annotations

"""Strictly read-only v1129.9 Real Reflective Communication Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from reflective_communication_arbitration import OUTCOMES
from reflective_communication_deliberation_checkpoint import build_reflective_communication_deliberation_checkpoint
from reflective_communication_eligibility_signals import PURPOSES
from reflective_communication_intake_checkpoint import build_reflective_communication_intake_checkpoint
from reflective_communication_integration_checkpoint import build_reflective_communication_integration_checkpoint

CONTRACT_VERSION = "v1129.9"


def _runtime_root() -> Path:
    data_root = Path(
        os.environ.get("EIDOLON_DATA_DIR")
        or Path(__file__).resolve().parents[1] / "data"
    ).expanduser().resolve()
    return data_root / "cognition"


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        try:
            relative = path.relative_to(root).as_posix()
            payload = path.read_bytes()
        except (OSError, ValueError):
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\n")
    return digest.hexdigest()


def _passed(report: dict[str, Any], check_id: str) -> bool:
    return any(
        isinstance(row, dict)
        and (row.get("id") == check_id or row.get("check") == check_id)
        and row.get("status") == "pass"
        for row in report.get("checks") or []
    )


def build_reflective_communication_governance_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    runtime = (
        Path(runtime_root).expanduser().resolve()
        if runtime_root is not None
        else _runtime_root()
    )
    source = (
        Path(source_root).expanduser().resolve()
        if source_root is not None
        else Path(__file__).resolve().parents[1]
    )

    runtime_before = _tree_signature(runtime)
    source_before = _tree_signature(source)

    intake = build_reflective_communication_intake_checkpoint(
        runtime, source_root=source
    )
    deliberation = build_reflective_communication_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_reflective_communication_integration_checkpoint(
        runtime, source_root=source
    )

    reports = (intake, deliberation, integration)
    signals = intake.get("signals") or {}
    candidates = intake.get("candidates") or {}
    sessions = deliberation.get("sessions") or {}
    arbitration = deliberation.get("arbitration") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}
    visible_status = integration.get("visible_status") or {}

    recent_signals = signals.get("recent_signals") or []
    recent_candidates = candidates.get("recent_candidates") or []
    recent_sessions = sessions.get("recent_sessions") or []
    recent_arbitrations = arbitration.get("recent_outcomes") or []
    recent_outcomes = lineage.get("recent_outcomes") or []
    reviews = reliability.get("reviews") or []

    privacy_fields = (
        "raw_messages_exposed",
        "raw_content_exposed",
        "message_text_exposed",
        "proposed_message_text_exposed",
        "reflection_text_exposed",
        "conclusion_text_exposed",
        "evidence_text_exposed",
        "prompt_exposed",
        "prompts_exposed",
        "provider_payload_exposed",
        "provider_payloads_exposed",
        "memory_text_exposed",
        "motivation_text_exposed",
        "goal_text_exposed",
        "identity_text_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    authority_fields = (
        "provider_contacted",
        "model_contacted",
        "message_generated",
        "message_sent",
        "notification_created",
        "initiative_created",
        "conversation_proposal_created",
        "approval_created",
        "approval_granted",
        "authorization_created",
        "authorization_granted",
        "external_action_executed",
        "installation_modified",
        "promotion_performed",
        "release_promoted",
        "certification_performed",
        "release_certified",
        "policy_applied",
        "proposal_applied",
        "schedule_mutated",
        "browsing_performed",
    )
    privacy_ok = all(
        report.get(field) is not True
        for report in reports
        for field in privacy_fields
    ) and not any(visible_status.get(field) is True for field in privacy_fields)
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in authority_fields
    )
    structural_boundaries_inert = all(
        not any((component.get("authority_boundary") or {}).values())
        for component in (
            signals,
            candidates,
            sessions,
            arbitration,
            lineage,
            reliability,
        )
    )

    expected_purposes = {
        "proactive_update",
        "delayed_follow_up",
        "curiosity_question",
        "clarification_request",
        "concern_or_caution",
        "acknowledgment",
        "deliberate_silence_review",
    }
    expected_outcomes = {
        "communicate_when_eligible",
        "delayed_follow_up",
        "curiosity_question_eligible",
        "clarification_eligible",
        "deliberate_silence",
        "defer_for_interruption",
        "defer_for_timing",
        "defer_for_recovery",
        "defer_for_focus",
        "defer_for_operator_review",
        "await_prerequisite",
        "unresolved",
    }
    recognized_reliability_states = {
        "insufficient_evidence",
        "considerate_interruption_failure",
        "possible_over_communication",
        "possible_under_communication",
        "curiosity_usefulness_unproven",
        "communication_recommendation_instability",
        "stable_or_indeterminate",
    }

    checks = [
        (
            "reflective_communication_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1129.2"
            and deliberation.get("contract_version") == "v1129.5"
            and integration.get("contract_version") == "v1129.8",
        ),
        (
            "eligibility_signal_lineage_and_purposes",
            set(PURPOSES) == expected_purposes
            and all(row.get("signal_id") for row in recent_signals)
            and all(row.get("origin_ids") for row in recent_signals)
            and all(row.get("source_categories") for row in recent_signals)
            and all(row.get("purpose") in expected_purposes for row in recent_signals)
            and _passed(intake, "exact_origin_lineage")
            and _passed(intake, "source_categories"),
        ),
        (
            "usefulness_urgency_sensitivity_and_interruption_cost",
            all(
                row.get("relevance") is not None
                and row.get("importance") is not None
                and row.get("urgency") is not None
                and row.get("sensitivity") is not None
                and row.get("interruption_cost") is not None
                for row in recent_signals
            )
            and _passed(intake, "usefulness_distinct_from_urgency")
            and _passed(intake, "sensitivity_and_continuity"),
        ),
        (
            "timing_recovery_and_delayed_follow_up_boundary",
            all(
                row.get("timing_eligible") is not None
                and row.get("delay_compatible") is not None
                and row.get("recovery_compatible") is not None
                and not row.get("notification_id")
                for row in recent_signals
            )
            and all(row.get("timing_window") for row in recent_candidates)
            and _passed(intake, "delay_not_notification")
            and _passed(intake, "recovery_interaction")
            and _passed(intake, "timing_windows"),
        ),
        (
            "candidate_lifecycle_overlap_and_correction_visibility",
            all(row.get("signal_ids") for row in recent_candidates)
            and all("semantic_overlap_key" in row for row in recent_candidates)
            and _passed(intake, "overlap_lineage")
            and _passed(intake, "lifecycle_coverage"),
        ),
        (
            "bounded_content_free_deliberation_sessions",
            sessions.get("contract_version") == "v1129.3"
            and all(int(row.get("deliberation_budget") or 0) >= 1 for row in recent_sessions)
            and all(row.get("candidate_id") for row in recent_sessions)
            and _passed(deliberation, "bounded_sessions"),
        ),
        (
            "deterministic_silence_communication_arbitration",
            arbitration.get("contract_version") == "v1129.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or []) == expected_outcomes
            and all(row.get("session_id") for row in recent_arbitrations)
            and _passed(deliberation, "deterministic_arbitration")
            and _passed(deliberation, "recognized_outcomes"),
        ),
        (
            "deliberate_silence_and_bounded_communication_paths",
            {
                "deliberate_silence",
                "communicate_when_eligible",
                "delayed_follow_up",
                "curiosity_question_eligible",
                "clarification_eligible",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "deliberate_silence")
            and _passed(deliberation, "communication_eligibility")
            and _passed(deliberation, "delayed_follow_up")
            and _passed(deliberation, "curiosity_eligibility")
            and _passed(deliberation, "clarification_eligibility"),
        ),
        (
            "considerate_non_interruption_and_bounded_deferral",
            {
                "defer_for_interruption",
                "defer_for_timing",
                "defer_for_recovery",
                "defer_for_focus",
                "defer_for_operator_review",
                "await_prerequisite",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "interruption_deferral")
            and _passed(deliberation, "timing_deferral")
            and _passed(deliberation, "recovery_deferral")
            and _passed(deliberation, "focus_deferral")
            and _passed(deliberation, "operator_review_deferral")
            and _passed(deliberation, "prerequisite_deferral"),
        ),
        (
            "curiosity_is_not_interruption_permission",
            all(
                row.get("purpose") != "curiosity_question"
                or row.get("interruption_cost") is not None
                for row in recent_signals
            )
            and all(
                "interruption_respected" in row
                for row in recent_outcomes
                if "curiosity_question" in row.get("purpose_categories", [])
            )
            and _passed(intake, "curiosity_not_permission"),
        ),
        (
            "durable_communication_outcome_lineage",
            lineage.get("ok")
            and lineage.get("contract_version") == "v1129.6"
            and all(row.get("communication_outcome_id") for row in recent_outcomes)
            and all(row.get("arbitration_id") for row in recent_outcomes)
            and all(row.get("session_id") for row in recent_outcomes)
            and all(row.get("candidate_id") for row in recent_outcomes),
        ),
        (
            "delayed_follow_up_and_interruption_continuity",
            all("predecessor_outcome_id" in row for row in recent_outcomes)
            and all("continuity_state" in row for row in recent_outcomes)
            and all("timing_state" in row for row in recent_outcomes)
            and all("interruption_respected" in row for row in recent_outcomes)
            and _passed(integration, "delayed_follow_up_continuity")
            and _passed(integration, "interruption_reliability"),
        ),
        (
            "communication_reliability_and_false_pattern_restraint",
            reliability.get("ok")
            and reliability.get("contract_version") == "v1129.7"
            and all(review.get("status") in recognized_reliability_states for review in reviews)
            and all(isinstance(review.get("false_pattern_suppressed"), bool) for review in reviews)
            and _passed(integration, "pattern_review")
            and _passed(integration, "false_pattern_suppression")
            and _passed(integration, "curiosity_usefulness"),
        ),
        (
            "operator_reviewed_policy_proposal_restraint",
            all(
                proposal is None
                or (
                    proposal.get("state") == "proposed"
                    and proposal.get("approved") is False
                    and proposal.get("authorized") is False
                    and proposal.get("applied") is False
                )
                for proposal in (
                    review.get("operator_review_proposal") for review in reviews
                )
            ),
        ),
        (
            "content_free_visible_status_and_privacy",
            privacy_ok
            and visible_status.get("raw_content_exposed") is not True
            and visible_status.get("hidden_reasoning_exposed") is not True
            and _passed(integration, "visible_status")
            and _passed(integration, "privacy"),
        ),
        (
            "strict_downstream_authority_separation",
            authority_inert
            and structural_boundaries_inert
            and _passed(intake, "authority_separation")
            and _passed(deliberation, "no_provider_or_message")
            and _passed(deliberation, "no_notification_or_initiative")
            and _passed(integration, "authority_separation"),
        ),
        (
            "strictly_read_only_source_runtime_separation",
            not any(report.get("runtime_mutated") for report in reports)
            and not any(report.get("source_modified") for report in reports)
            and _passed(intake, "read_only")
            and _passed(deliberation, "source_runtime_read_only"),
        ),
        (
            "desktop_verification_pending_and_no_consciousness_claim",
            all(report.get("desktop_verification") == "pending" for report in reports)
            and not any(report.get("consciousness_proven") is True for report in reports),
        ),
    ]

    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    runtime_mutated = runtime_before != runtime_after
    source_modified = source_before != source_after
    rows = [
        {"id": check_id, "status": "pass" if ok else "fail"}
        for check_id, ok in checks
    ]
    passed = sum(bool(ok) for _, ok in checks)

    return {
        "ok": passed == len(checks),
        "contract_version": CONTRACT_VERSION,
        "status": (
            "ready_for_desktop_verification"
            if passed == len(checks)
            else "degraded"
        ),
        "headline": (
            "v1129.9 Real Reflective Communication Governance: "
            f"{passed}/{len(checks)} checks passed"
        ),
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "eligibility_signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "deliberation_session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "communication_outcome_count": lineage.get("outcome_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "delayed_follow_up_count": visible_status.get(
                "delayed_follow_up_count", 0
            ),
            "deliberate_silence_count": visible_status.get(
                "deliberate_silence_count", 0
            ),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "message_text_exposed": False,
        "proposed_message_text_exposed": False,
        "reflection_text_exposed": False,
        "conclusion_text_exposed": False,
        "evidence_text_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "memory_text_exposed": False,
        "motivation_text_exposed": False,
        "goal_text_exposed": False,
        "identity_text_exposed": False,
        "hidden_reasoning_exposed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "message_generated": False,
        "message_sent": False,
        "notification_created": False,
        "initiative_created": False,
        "conversation_proposal_created": False,
        "approval_created": False,
        "approval_granted": False,
        "authorization_created": False,
        "authorization_granted": False,
        "external_action_executed": False,
        "installation_modified": False,
        "promotion_performed": False,
        "release_promoted": False,
        "certification_performed": False,
        "release_certified": False,
        "policy_applied": False,
        "proposal_applied": False,
        "schedule_mutated": False,
        "browsing_performed": False,
        "consciousness_proven": False,
        "eligibility_signal_created_by_checkpoint": False,
        "communication_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "communication_outcome_created_by_checkpoint": False,
        "desktop_verification_pending": True,
    }
