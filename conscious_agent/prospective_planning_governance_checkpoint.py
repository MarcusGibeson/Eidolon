from __future__ import annotations

"""Strictly read-only v1134.9 Prospective Planning Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from prospective_planning_arbitration import OUTCOMES
from prospective_planning_candidates import STATES as CANDIDATE_STATES
from prospective_planning_deliberation_checkpoint import build_prospective_planning_deliberation_checkpoint
from prospective_planning_intake_checkpoint import build_prospective_planning_intake_checkpoint
from prospective_planning_integration_checkpoint import build_prospective_planning_integration_checkpoint
from prospective_planning_signals import PURPOSE_CATEGORIES, SOURCE_CATEGORIES, STATES as SIGNAL_STATES

CONTRACT_VERSION = "v1134.9"


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


def build_prospective_planning_governance_checkpoint(
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

    intake = build_prospective_planning_intake_checkpoint(runtime, source_root=source)
    deliberation = build_prospective_planning_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_prospective_planning_integration_checkpoint(
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
    outcome_counts = lineage.get("outcome_counts") or {}

    expected_sources = {
        "accepted_goal_outcome",
        "goal_revision_outcome",
        "world_model_outcome",
        "inquiry_outcome",
        "perception_outcome",
        "obligation",
        "constraint",
        "operator_requirement",
    }
    expected_purposes = {
        "capability_path",
        "reliability_path",
        "knowledge_path",
        "project_path",
        "relationship_path",
        "maintenance_path",
        "risk_mitigation",
        "deliberate_no_action_review",
    }
    expected_outcomes = {
        "plan_recommended",
        "alternative_comparison_recommended",
        "counterfactual_review_recommended",
        "plan_revision_recommended",
        "deliberate_no_action",
        "defer_for_recovery",
        "defer_for_focus",
        "defer_for_cognitive_budget",
        "defer_for_operator_review",
        "await_prerequisite",
        "await_timing_window",
        "await_risk_review",
        "await_stop_condition_review",
        "suppress_false_urgency",
        "suppress_low_value_plan",
        "suppress_high_risk_plan",
        "suppress_irreversible_plan",
        "unresolved",
    }
    lifecycle_states = {
        "recommended",
        "deferred",
        "blocked",
        "completed",
        "revised",
        "superseded",
        "abandoned",
        "obsolete",
        "retired",
        "deliberate_no_action",
    }
    reliability_states = {
        "insufficient_evidence",
        "planning_continuity_failure",
        "possible_over_planning",
        "repeated_plan_abandonment",
        "persistent_planning_blockage",
        "planning_priority_instability",
        "repeated_plan_deferral",
        "stable_or_indeterminate",
    }

    privacy_fields = (
        "raw_content_exposed",
        "evidence_text_exposed",
        "goal_text_exposed",
        "plan_text_exposed",
        "counterfactual_text_exposed",
        "prompt_exposed",
        "provider_payload_exposed",
        "hidden_reasoning_exposed",
        "private_content_exposed",
    )
    authority_fields = (
        "browser_contacted",
        "browsing_performed",
        "provider_contacted",
        "model_contacted",
        "message_generated",
        "message_sent",
        "notification_created",
        "initiative_created",
        "initiative_mutated",
        "plan_created",
        "plan_activated",
        "goal_activated",
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

    checks = [
        (
            "prospective_planning_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1134.2"
            and deliberation.get("contract_version") == "v1134.5"
            and integration.get("contract_version") == "v1134.8",
        ),
        (
            "source_purpose_and_candidate_state_coverage",
            set(SOURCE_CATEGORIES) == expected_sources
            and set(PURPOSE_CATEGORIES) == expected_purposes
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
                "awaiting_timing_window",
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
            "exact_goal_origin_evidence_scope_and_predecessor_lineage",
            all(row.get("origin_ids") for row in recent_signals)
            and all(row.get("goal_ids") for row in recent_signals)
            and all(row.get("evidence_ids") for row in recent_signals)
            and all(row.get("scope_digest") is not None for row in recent_signals)
            and all(
                row.get("predecessor_plan_ids") is not None
                for row in recent_signals
            )
            and _passed(intake, "goal_lineage")
            and _passed(intake, "evidence_lineage"),
        ),
        (
            "value_cost_duration_risk_reversibility_uncertainty_and_timing_separation",
            all(
                row.get("importance") is not None
                and row.get("urgency") is not None
                and row.get("uncertainty") is not None
                and row.get("expected_value") is not None
                and row.get("estimated_cost") is not None
                and row.get("estimated_duration") is not None
                and row.get("risk") is not None
                and row.get("reversibility") is not None
                and row.get("time_horizon") is not None
                for row in recent_signals
            )
            and _passed(intake, "value_not_urgency")
            and _passed(intake, "risks_visible"),
        ),
        (
            "alternatives_counterfactuals_constraints_stops_overlap_and_false_pressure",
            all(row.get("alternative_ids") is not None for row in recent_candidates)
            and all(
                row.get("counterfactual_ids") is not None
                for row in recent_candidates
            )
            and all(row.get("constraint_ids") is not None for row in recent_candidates)
            and all(
                row.get("stop_condition_ids") is not None
                for row in recent_candidates
            )
            and all(
                row.get("semantic_overlap_key") is not None
                and row.get("false_pressure_suppressed") is not None
                for row in recent_candidates
            )
            and _passed(intake, "alternatives_visible")
            and _passed(intake, "counterfactuals_visible")
            and _passed(intake, "stop_conditions_visible")
            and _passed(intake, "false_pressure"),
        ),
        (
            "bounded_content_free_planning_deliberation",
            sessions.get("contract_version") == "v1134.3"
            and all(
                1 <= int(row.get("deliberation_budget") or 0) <= 6
                for row in recent_sessions
            )
            and all(row.get("candidate_id") for row in recent_sessions)
            and all(row.get("goal_ids") for row in recent_sessions)
            and all(
                row.get("alternative_ids") is not None
                and row.get("counterfactual_ids") is not None
                for row in recent_sessions
            )
            and _passed(deliberation, "bounded_sessions")
            and _passed(deliberation, "exact_candidate_lineage")
            and _passed(deliberation, "alternatives_and_counterfactuals"),
        ),
        (
            "deterministic_recognized_planning_arbitration",
            arbitration.get("contract_version") == "v1134.4"
            and set(OUTCOMES) == expected_outcomes
            and set(arbitration.get("recognized_outcomes") or [])
            == expected_outcomes
            and all(row.get("session_id") for row in recent_arbitrations),
        ),
        (
            "plan_alternative_counterfactual_and_revision_paths",
            {
                "plan_recommended",
                "alternative_comparison_recommended",
                "counterfactual_review_recommended",
                "plan_revision_recommended",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "plan_recommendation")
            and _passed(deliberation, "alternative_comparison")
            and _passed(deliberation, "counterfactual_review")
            and _passed(deliberation, "plan_revision"),
        ),
        (
            "deliberate_no_action_and_bounded_deferral",
            "deliberate_no_action" in OUTCOMES
            and {
                "defer_for_recovery",
                "defer_for_focus",
                "defer_for_cognitive_budget",
                "defer_for_operator_review",
                "await_prerequisite",
                "await_timing_window",
                "await_risk_review",
                "await_stop_condition_review",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "deliberate_no_action")
            and _passed(deliberation, "recovery_focus_budget_deferral")
            and _passed(deliberation, "operator_prerequisite_timing_deferral")
            and _passed(deliberation, "risk_and_stop_condition_deferral"),
        ),
        (
            "false_urgency_low_value_high_risk_and_irreversibility_suppression",
            {
                "suppress_false_urgency",
                "suppress_low_value_plan",
                "suppress_high_risk_plan",
                "suppress_irreversible_plan",
            }.issubset(OUTCOMES)
            and _passed(deliberation, "false_urgency_suppression")
            and _passed(deliberation, "low_value_and_risk_suppression"),
        ),
        (
            "goal_plan_and_initiative_separation",
            all(
                not row.get("plan_id") and not row.get("initiative_id")
                for row in recent_arbitrations
            )
            and _passed(deliberation, "no_plan_activation"),
        ),
        (
            "durable_outcome_lineage_and_scope_preservation",
            lineage.get("contract_version") == "v1134.6"
            and all(row.get("arbitration_id") for row in recent_outcomes)
            and all(row.get("candidate_id") for row in recent_outcomes)
            and all(row.get("signal_ids") is not None for row in recent_outcomes)
            and all(row.get("scope_digest") is not None for row in recent_outcomes)
            and _passed(integration, "outcome_lineage")
            and _passed(integration, "exact_arbitration_lineage")
            and _passed(integration, "scope_digest_preserved"),
        ),
        (
            "planning_lifecycle_continuity_blocker_and_completion_states",
            all(
                row.get("lifecycle_state") in lifecycle_states
                for row in recent_outcomes
            )
            and all(row.get("continuity_state") is not None for row in recent_outcomes)
            and all(row.get("blocker_state") is not None for row in recent_outcomes)
            and all(row.get("completion_state") is not None for row in recent_outcomes)
            and _passed(integration, "lifecycle_state")
            and _passed(integration, "continuity_state")
            and _passed(integration, "blocker_state")
            and _passed(integration, "completion_state"),
        ),
        (
            "reliability_overplanning_abandonment_blockage_deferral_and_false_patterns",
            reliability.get("contract_version") == "v1134.7"
            and all(row.get("status") in reliability_states for row in reviews)
            and all(
                row.get("false_pattern_suppressed") is not None
                for row in reviews
            )
            and all(
                row.get("accepted_count") is not None
                and row.get("deferred_count") is not None
                and row.get("abandoned_count") is not None
                and row.get("blocked_count") is not None
                and row.get("continuity_failure_count") is not None
                and row.get("reversal_count") is not None
                for row in reviews
            )
            and _passed(integration, "reliability_review")
            and _passed(integration, "false_pattern_suppression")
            and _passed(integration, "over_under_planning_review"),
        ),
        (
            "operator_reviewed_policy_proposals_remain_inert",
            all(
                not proposal
                or (
                    proposal.get("state") == "proposed"
                    and proposal.get("approved") is False
                    and proposal.get("authorized") is False
                    and proposal.get("applied") is False
                )
                for proposal in (
                    row.get("operator_review_proposal") for row in reviews
                )
            ),
        ),
        (
            "strict_content_privacy_and_hidden_reasoning_boundary",
            privacy_ok
            and _passed(intake, "privacy_boundary")
            and _passed(deliberation, "privacy_boundary")
            and _passed(integration, "privacy"),
        ),
        (
            "strict_downstream_authority_and_activation_separation",
            authority_inert
            and structural_boundaries_inert
            and _passed(intake, "authority_separation")
            and _passed(deliberation, "authority_separation")
            and _passed(integration, "no_autonomous_activation")
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
    recommended_or_review_count = sum(
        outcome_counts.get(key, 0)
        for key in (
            "plan_recommended",
            "alternative_comparison_recommended",
            "counterfactual_review_recommended",
            "plan_revision_recommended",
        )
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
            f"v1134.9 Prospective Planning Governance: "
            f"{passed}/{len(checks)} checks passed"
        ),
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "planning_signal_count": signals.get("signal_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "deliberation_session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "planning_outcome_count": lineage.get("outcome_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "recommended_or_review_count": recommended_or_review_count,
            "deliberate_no_action_count": outcome_counts.get(
                "deliberate_no_action", 0
            ),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "evidence_text_exposed": False,
        "goal_text_exposed": False,
        "plan_text_exposed": False,
        "counterfactual_text_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "hidden_reasoning_exposed": False,
        "browser_contacted": False,
        "browsing_performed": False,
        "provider_contacted": False,
        "model_contacted": False,
        "message_generated": False,
        "message_sent": False,
        "notification_created": False,
        "initiative_created": False,
        "initiative_mutated": False,
        "plan_created": False,
        "plan_activated": False,
        "goal_activated": False,
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
        "planning_signal_created_by_checkpoint": False,
        "planning_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "planning_outcome_created_by_checkpoint": False,
        "goal_activated_by_checkpoint": False,
        "plan_created_by_checkpoint": False,
        "plan_activated_by_checkpoint": False,
        "initiative_created_by_checkpoint": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
