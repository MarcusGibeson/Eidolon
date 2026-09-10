from __future__ import annotations

"""Strictly read-only v1135.9 Supervised Deficiency Identification Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from deficiency_arbitration import OUTCOMES
from deficiency_candidates import STATES as CANDIDATE_STATES
from deficiency_outcome_lineage import STATES as LINEAGE_STATES
from deficiency_reliability_review import FINDINGS
from deficiency_signals import DEFICIENCY_CATEGORIES, SOURCE_CATEGORIES, STATES as SIGNAL_STATES
from supervised_deficiency_deliberation_checkpoint import build_supervised_deficiency_deliberation_checkpoint
from supervised_deficiency_intake_checkpoint import build_supervised_deficiency_intake_checkpoint
from supervised_deficiency_integration_checkpoint import build_supervised_deficiency_integration_checkpoint

CONTRACT_VERSION = "v1135.9"


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


def _all_authority_inert(*components: dict[str, Any]) -> bool:
    return all(
        not any((component.get("authority_boundary") or {}).values())
        for component in components
    )


def build_supervised_deficiency_governance_checkpoint(
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

    intake = build_supervised_deficiency_intake_checkpoint(runtime, source_root=source)
    deliberation = build_supervised_deficiency_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_supervised_deficiency_integration_checkpoint(
        runtime, source_root=source
    )
    reports = (intake, deliberation, integration)

    signals = intake.get("signals") or {}
    candidates = intake.get("candidates") or {}
    sessions = deliberation.get("sessions") or {}
    arbitration = deliberation.get("arbitration") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}

    recent_signals = signals.get("recent_signals") or []
    recent_candidates = candidates.get("recent_candidates") or []
    recent_sessions = sessions.get("recent_sessions") or []
    recent_arbitrations = arbitration.get("recent_outcomes") or []
    recent_lineage = lineage.get("recent_lineage") or []
    recent_reviews = reliability.get("recent_reviews") or []
    outcome_counts = arbitration.get("outcome_counts") or {}

    expected_categories = {
        "capability_deficiency",
        "reliability_deficiency",
        "usability_deficiency",
        "architectural_deficiency",
        "test_coverage_deficiency",
        "documentation_or_operator_control_deficiency",
        "privacy_or_governance_deficiency",
        "deliberate_no_deficiency_review",
    }
    expected_sources = {
        "project_perception",
        "system_perception",
        "failed_checkpoint",
        "degraded_checkpoint",
        "reliability_review",
        "repeated_cognition_failure",
        "repeated_conversation_failure",
        "repeated_inquiry_failure",
        "repeated_goal_failure",
        "repeated_planning_failure",
        "operator_confirmed_problem",
        "stale_work",
        "blocked_work",
        "abandoned_work",
        "deferred_work",
        "resource_budget_failure",
        "continuity_failure",
        "usability_friction",
        "architectural_structure",
        "sandbox_evidence",
        "development_evidence",
    }
    expected_outcomes = {
        "verified_deficiency",
        "probable_deficiency",
        "defer_for_more_evidence",
        "defer_for_operator_review",
        "await_prerequisite",
        "defer_for_recovery",
        "defer_for_resource_budget",
        "await_impact_review",
        "await_feasibility_review",
        "suppress_single_sample",
        "suppress_false_severity",
        "suppress_low_confidence",
        "architectural_suspicion_only",
        "contradicted",
        "retracted",
        "deliberate_no_deficiency",
    }
    expected_findings = {
        "stable",
        "repeated_false_positive",
        "possible_missed_deficiency",
        "stale_outcome",
        "continuity_gap",
        "operator_review_required",
        "deliberate_no_change",
    }

    privacy_fields = (
        "raw_content_exposed",
        "source_content_exposed",
        "failure_log_exposed",
        "conversation_exposed",
        "prompt_exposed",
        "provider_payload_exposed",
        "evidence_text_exposed",
        "proposal_text_exposed",
        "private_project_record_exposed",
        "hidden_reasoning_exposed",
    )
    authority_fields = (
        "browser_contacted",
        "browsing_performed",
        "provider_contacted",
        "model_contacted",
        "message_generated",
        "message_sent",
        "notification_created",
        "goal_mutated",
        "plan_mutated",
        "initiative_mutated",
        "proposal_created",
        "development_proposal_created",
        "policy_proposal_approved",
        "sandbox_created",
        "tests_executed",
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
        "filesystem_modified",
    )
    privacy_ok = all(
        report.get(field) is not True
        for report in reports
        for field in privacy_fields
    )
    authority_inert = all(
        report.get(field) is not True
        for report in reports
        for field in authority_fields
    )

    downstream_fields = (
        "proposal_id",
        "development_proposal_id",
        "policy_proposal_id",
        "specification_id",
        "test_plan_id",
        "sandbox_change_id",
        "approval_id",
        "authorization_id",
        "execution_id",
        "promotion_id",
        "certification_id",
    )
    all_records = (
        recent_signals
        + recent_candidates
        + recent_sessions
        + recent_arbitrations
        + recent_lineage
        + recent_reviews
    )

    checks = [
        (
            "supervised_deficiency_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1135.2"
            and deliberation.get("contract_version") == "v1135.5"
            and integration.get("contract_version") == "v1135.8",
        ),
        (
            "deficiency_source_category_and_lifecycle_coverage",
            set(DEFICIENCY_CATEGORIES) == expected_categories
            and set(SOURCE_CATEGORIES) == expected_sources
            and set(SIGNAL_STATES)
            == {
                "active",
                "suppressed",
                "deferred",
                "awaiting_prerequisite",
                "requires_operator_review",
                "superseded",
                "retracted",
                "stale",
                "retired",
            }
            and set(CANDIDATE_STATES)
            == {
                "active",
                "suppressed",
                "deferred",
                "awaiting_prerequisite",
                "requires_operator_review",
                "merged",
                "superseded",
                "stale",
                "obsolete",
                "retracted",
                "retired",
            },
        ),
        (
            "exact_origin_project_scope_evidence_and_structural_lineage",
            all(row.get("origin_ids") for row in recent_signals)
            and all(row.get("component_ids") for row in recent_signals)
            and all(row.get("project_digest") is not None for row in recent_signals)
            and all(row.get("scope_digest") is not None for row in recent_signals)
            and all(row.get("evidence_ids") for row in recent_signals)
            and all(row.get("structural_digest") for row in recent_signals)
            and _passed(intake, "exact_lineage"),
        ),
        (
            "severity_urgency_impact_and_authority_separation",
            all(
                row.get("severity") is not None
                and row.get("urgency") is not None
                and row.get("user_impact") is not None
                and row.get("operator_impact") is not None
                and row.get("cognitive_impact") is not None
                and row.get("operational_impact") is not None
                and row.get("observed_impact_only") is True
                for row in recent_signals
            )
            and _passed(intake, "severity_vs_urgency")
            and _passed(intake, "impact_vs_authority"),
        ),
        (
            "recurrence_reproducibility_suspicion_and_false_pressure_restraint",
            all(
                row.get("recurrence_count") is not None
                and row.get("reproducibility") is not None
                and row.get("architectural_suspicion") is not None
                and row.get("verified_defect") is not None
                and row.get("single_sample_suppressed") is not None
                and row.get("unsupported_severity_suppressed") is not None
                and row.get("novelty_only_suppressed") is not None
                for row in recent_signals
            )
            and _passed(intake, "recurrence_reproducibility")
            and _passed(intake, "suspicion_vs_verified")
            and _passed(intake, "false_severity_suppression"),
        ),
        (
            "candidate_overlap_correction_and_lifecycle_governance",
            all(row.get("signal_ids") for row in recent_candidates)
            and all(
                row.get("semantic_overlap_key") is not None
                and row.get("contradiction_ids") is not None
                and row.get("retraction_ids") is not None
                for row in recent_candidates
            )
            and _passed(intake, "duplicate_overlap")
            and _passed(intake, "correction_lineage"),
        ),
        (
            "bounded_content_free_deficiency_deliberation",
            sessions.get("contract_version") == "v1135.3"
            and all(
                1 <= int(row.get("deliberation_budget") or 0) <= 6
                for row in recent_sessions
            )
            and all(row.get("candidate_id") for row in recent_sessions)
            and all(row.get("signal_ids") for row in recent_sessions)
            and _passed(deliberation, "bounded_deliberation")
            and _passed(deliberation, "exact_candidate_lineage"),
        ),
        (
            "deterministic_recognized_deficiency_arbitration",
            arbitration.get("contract_version") == "v1135.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or [])
            == expected_outcomes
            and all(row.get("session_id") for row in recent_arbitrations),
        ),
        (
            "verified_probable_evidence_impact_and_feasibility_paths",
            {
                "verified_deficiency",
                "probable_deficiency",
                "defer_for_more_evidence",
                "await_impact_review",
                "await_feasibility_review",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "evidence_sufficiency")
            and _passed(deliberation, "verified_vs_probable")
            and _passed(deliberation, "impact_and_feasibility_review"),
        ),
        (
            "operator_prerequisite_recovery_and_resource_deferral",
            {
                "defer_for_operator_review",
                "await_prerequisite",
                "defer_for_recovery",
                "defer_for_resource_budget",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "operator_and_prerequisite_deferral")
            and _passed(deliberation, "recovery_and_resource_deferral"),
        ),
        (
            "noise_suspicion_contradiction_retraction_and_no_deficiency_paths",
            {
                "suppress_single_sample",
                "suppress_false_severity",
                "suppress_low_confidence",
                "architectural_suspicion_only",
                "contradicted",
                "retracted",
                "deliberate_no_deficiency",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "single_sample_suppression")
            and _passed(deliberation, "false_severity_suppression")
            and _passed(deliberation, "low_confidence_suppression")
            and _passed(deliberation, "architectural_suspicion_separation")
            and _passed(deliberation, "contradiction_and_retraction")
            and _passed(deliberation, "deliberate_no_deficiency"),
        ),
        (
            "durable_outcome_lineage_restart_project_and_scope_continuity",
            lineage.get("contract_version") == "v1135.6"
            and set(LINEAGE_STATES)
            == {"active", "continued", "superseded", "stale", "retracted", "retired"}
            and all(row.get("arbitration_id") for row in recent_lineage)
            and all(row.get("project_digests") is not None for row in recent_lineage)
            and all(row.get("scope_digests") is not None for row in recent_lineage)
            and all(row.get("structural_digest") for row in recent_lineage)
            and _passed(integration, "exact_outcome_lineage")
            and _passed(integration, "restart_and_project_continuity"),
        ),
        (
            "reliability_false_positive_missed_stale_gap_operator_and_no_change_review",
            reliability.get("contract_version") == "v1135.7"
            and set(FINDINGS) == expected_findings
            and set(reliability.get("recognized_findings") or []) == expected_findings
            and _passed(integration, "false_positive_review")
            and _passed(integration, "missed_deficiency_review")
            and _passed(integration, "continuity_gap_review")
            and _passed(integration, "staleness_review")
            and _passed(integration, "operator_review_visibility")
            and _passed(integration, "deliberate_no_change"),
        ),
        (
            "strict_downstream_artifact_and_authority_separation",
            all(
                not any(row.get(field) for field in downstream_fields)
                for row in all_records
            )
            and _passed(deliberation, "no_proposal_or_patch")
            and _passed(integration, "no_development_proposal")
            and _passed(integration, "no_policy_self_approval"),
        ),
        (
            "operator_reviewed_policy_and_development_paths_remain_inert",
            all(
                not row.get("policy_proposal_id")
                and not row.get("development_proposal_id")
                and not row.get("approval_id")
                and not row.get("authorization_id")
                for row in recent_reviews
            ),
        ),
        (
            "strict_content_privacy_and_hidden_reasoning_boundary",
            privacy_ok
            and _passed(intake, "privacy_boundary")
            and _passed(deliberation, "privacy_boundary")
            and _passed(integration, "privacy_boundary"),
        ),
        (
            "strict_project_evidence_proposal_sandbox_execution_release_separation",
            authority_inert
            and _all_authority_inert(
                signals, candidates, sessions, arbitration, lineage, reliability
            )
            and _passed(intake, "authority_separation")
            and _passed(deliberation, "authority_separation")
            and _passed(integration, "authority_separation"),
        ),
        (
            "strictly_read_only_desktop_pending_no_consciousness_claim",
            not any(report.get("runtime_mutated") for report in reports)
            and not any(report.get("source_modified") for report in reports)
            and all(report.get("desktop_verification") == "pending" for report in reports)
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
    verified_or_probable_count = sum(
        outcome_counts.get(key, 0)
        for key in ("verified_deficiency", "probable_deficiency")
    )

    return {
        "ok": passed == len(checks),
        "contract_version": CONTRACT_VERSION,
        "status": (
            "ready_for_desktop_verification"
            if passed == len(checks)
            else "degraded"
        ),
        "headline": (
            f"v1135.9 Supervised Deficiency Identification Governance: "
            f"{passed}/{len(checks)} checks passed"
        ),
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "deficiency_signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "deliberation_session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "outcome_lineage_count": lineage.get("lineage_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "verified_or_probable_count": verified_or_probable_count,
            "deliberate_no_deficiency_count": outcome_counts.get(
                "deliberate_no_deficiency", 0
            ),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "source_content_exposed": False,
        "failure_log_exposed": False,
        "conversation_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "evidence_text_exposed": False,
        "proposal_text_exposed": False,
        "private_project_record_exposed": False,
        "hidden_reasoning_exposed": False,
        "browser_contacted": False,
        "browsing_performed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "message_generated": False,
        "message_sent": False,
        "notification_created": False,
        "goal_mutated": False,
        "plan_mutated": False,
        "initiative_mutated": False,
        "proposal_created": False,
        "development_proposal_created": False,
        "policy_proposal_approved": False,
        "sandbox_created": False,
        "tests_executed": False,
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
        "filesystem_modified": False,
        "consciousness_proven": False,
        "deficiency_signal_created_by_checkpoint": False,
        "deficiency_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "outcome_lineage_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "development_proposal_created_by_checkpoint": False,
        "specification_created_by_checkpoint": False,
        "test_plan_created_by_checkpoint": False,
        "sandbox_change_created_by_checkpoint": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
