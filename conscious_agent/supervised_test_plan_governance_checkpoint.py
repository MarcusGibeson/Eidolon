from __future__ import annotations

"""Strictly read-only v1138.9 Supervised Test Planning Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from supervised_test_plan_deliberation_checkpoint import build_supervised_test_plan_deliberation_checkpoint
from supervised_test_plan_intake_checkpoint import build_supervised_test_plan_intake_checkpoint
from supervised_test_plan_integration_checkpoint import build_supervised_test_plan_integration_checkpoint
from test_plan_arbitration import OUTCOMES
from test_plan_candidates import STATES as CANDIDATE_STATES
from test_plan_eligibility import STATES as ELIGIBILITY_STATES
from test_plan_eligibility import TEST_PLAN_CATEGORIES
from test_plan_outcome_lineage import STATES as LINEAGE_STATES
from test_plan_reliability_review import FINDINGS

CONTRACT_VERSION = "v1138.9"


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
    for row in report.get("checks") or []:
        if not isinstance(row, dict):
            continue
        identifier = row.get("id") or row.get("check") or row.get("check_id")
        if identifier != check_id:
            continue
        return row.get("status") == "pass" or row.get("ok") is True
    return False


def _authority_inert(*components: dict[str, Any]) -> bool:
    return all(
        not any(bool(value) for value in (component.get("authority_boundary") or {}).values())
        for component in components
    )


def build_supervised_test_plan_governance_checkpoint(
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

    intake = build_supervised_test_plan_intake_checkpoint(runtime, source_root=source)
    deliberation = build_supervised_test_plan_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_supervised_test_plan_integration_checkpoint(
        runtime, source_root=source
    )
    reports = (intake, deliberation, integration)

    eligibility = intake.get("eligibility") or {}
    candidates = intake.get("candidates") or {}
    sessions = deliberation.get("session_summary") or {}
    arbitration = deliberation.get("arbitration_summary") or {}
    lineage = integration.get("lineage") or {}
    reliability = integration.get("reliability") or {}
    components = (eligibility, candidates, sessions, arbitration, lineage, reliability)

    recent_eligibility = eligibility.get("recent_records") or []
    recent_candidates = candidates.get("recent_candidates") or []
    recent_sessions = sessions.get("recent_sessions") or []
    recent_outcomes = arbitration.get("recent_outcomes") or []
    recent_lineage = lineage.get("recent_lineage") or []
    recent_reviews = reliability.get("recent_reviews") or []
    all_records = (
        recent_eligibility
        + recent_candidates
        + recent_sessions
        + recent_outcomes
        + recent_lineage
        + recent_reviews
    )

    expected_categories = {
        "unit_test_plan",
        "integration_test_plan",
        "continuity_test_plan",
        "recovery_test_plan",
        "privacy_test_plan",
        "governance_test_plan",
        "usability_test_plan",
        "regression_test_plan",
        "deliberate_no_test_plan_review",
    }
    expected_outcomes = {
        "test_plan_supported",
        "test_plan_probable",
        "defer_for_more_evidence",
        "defer_for_operator_review",
        "await_prerequisite",
        "defer_for_recovery",
        "defer_for_resource_budget",
        "await_scope_review",
        "await_coverage_review",
        "await_reproducibility_review",
        "await_determinism_review",
        "suppress_weak_support",
        "suppress_low_reproducibility",
        "suppress_low_determinism",
        "contradicted",
        "retracted",
        "deliberate_no_test_plan",
    }
    expected_findings = {
        "stable",
        "repeated_false_positive",
        "possible_missed_test_plan",
        "stale_outcome",
        "continuity_gap",
        "scope_drift",
        "coverage_drift",
        "dependency_drift",
        "reproducibility_drift",
        "determinism_drift",
        "flaky_plan_pattern",
        "operator_review_required",
        "deliberate_no_change",
    }

    privacy_fields = (
        "raw_content_exposed",
        "raw_source_exposed",
        "source_content_exposed",
        "failure_log_exposed",
        "conversation_exposed",
        "prompt_exposed",
        "provider_payload_exposed",
        "evidence_text_exposed",
        "proposal_text_exposed",
        "specification_text_exposed",
        "test_plan_text_exposed",
        "test_code_exposed",
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
        "specification_created",
        "test_plan_created",
        "test_code_created",
        "fixture_created",
        "sandbox_created",
        "tests_executed",
        "approval_created",
        "authorization_created",
        "external_action_executed",
        "source_modified_by_checkpoint",
        "installation_modified",
        "promotion_performed",
        "certification_performed",
        "filesystem_modified",
    )
    downstream_fields = (
        "test_plan_id",
        "test_code_id",
        "test_code_digest",
        "fixture_id",
        "fixture_digest",
        "sandbox_change_id",
        "approval_id",
        "authorization_id",
        "execution_id",
        "promotion_id",
        "certification_id",
    )

    checks = [
        (
            "supervised_test_planning_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1138.2"
            and deliberation.get("contract_version") == "v1138.5"
            and integration.get("contract_version") == "v1138.8",
        ),
        (
            "test_plan_category_state_outcome_and_finding_coverage",
            set(TEST_PLAN_CATEGORIES) == expected_categories
            and set(ELIGIBILITY_STATES)
            == {
                "eligible",
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
            }
            and set(OUTCOMES) == expected_outcomes
            and expected_findings <= set(FINDINGS)
            and {"active", "continued", "superseded", "stale", "retracted", "retired"}
            <= set(LINEAGE_STATES),
        ),
        (
            "exact_specification_eligibility_candidate_lineage",
            _passed(intake, "exact_specification_lineage")
            and all(
                row.get("arbitration_id")
                and row.get("specification_candidate_id")
                and row.get("component_ids")
                and row.get("coverage_target_ids") is not None
                and row.get("project_digests") is not None
                and row.get("scope_digests") is not None
                and row.get("evidence_ids") is not None
                and row.get("structural_digest")
                for row in recent_eligibility
            )
            and all(row.get("eligibility_ids") for row in recent_candidates),
        ),
        (
            "supported_probable_vs_permission_separation",
            _passed(intake, "supported_vs_eligible")
            and all(
                row.get("supported_specification") is not None
                and row.get("eligible_specification") is not None
                for row in recent_eligibility
            )
            and all(
                row.get("outcome") not in {"test_plan_supported", "test_plan_probable"}
                or not any(row.get(field) for field in downstream_fields)
                for row in recent_outcomes
            ),
        ),
        (
            "coverage_environment_dependency_cost_reproducibility_and_determinism",
            _passed(intake, "coverage_without_test_text")
            and _passed(intake, "cost_reproducibility_determinism")
            and _passed(intake, "environment_dependencies")
            and _passed(intake, "prerequisite_operator_review")
            and all(
                row.get("coverage_target_ids") is not None
                and row.get("environment_ids") is not None
                and row.get("dependency_ids") is not None
                and row.get("estimated_cost") is not None
                and row.get("reproducibility") is not None
                and row.get("determinism") is not None
                and row.get("prerequisite_ids") is not None
                and row.get("operator_review_required") is not None
                for row in recent_eligibility
            ),
        ),
        (
            "bounded_deliberation_and_exact_candidate_lineage",
            _passed(deliberation, "bounded_budget")
            and _passed(deliberation, "exact_candidate_lineage")
            and all(
                1 <= int(row.get("deliberation_budget", 1)) <= 6
                and row.get("candidate_id")
                and row.get("eligibility_ids") is not None
                for row in recent_sessions
            ),
        ),
        (
            "evidence_scope_coverage_reproducibility_and_determinism_arbitration",
            _passed(
                deliberation,
                "evidence_scope_coverage_reproducibility_determinism",
            )
            and all(
                all(
                    key in row
                    for key in (
                        "evidence_support",
                        "scope_support",
                        "coverage_support",
                        "reproducibility_support",
                        "determinism_support",
                    )
                )
                for row in recent_outcomes
            ),
        ),
        (
            "deterministic_support_deferral_suppression_and_no_test_plan",
            expected_outcomes == set(OUTCOMES)
            and _passed(deliberation, "deliberate_no_test_plan")
            and _passed(deliberation, "outcome_coverage"),
        ),
        (
            "test_plan_code_fixture_sandbox_and_authority_separation",
            _passed(deliberation, "plan_vs_execution_boundary")
            and _passed(integration, "no_test_plan_or_test_code")
            and _passed(integration, "no_sandbox_or_execution")
            and all(
                not any(row.get(field) for field in downstream_fields)
                for row in all_records
            ),
        ),
        (
            "durable_outcome_lineage_and_continuity",
            _passed(integration, "exact_outcome_lineage")
            and _passed(integration, "restart_and_project_continuity")
            and _passed(integration, "continuity_states")
            and all(
                row.get("arbitration_id") and row.get("structural_digest")
                for row in recent_lineage
            ),
        ),
        (
            "false_positive_missed_stale_continuity_and_drift_review",
            all(
                _passed(integration, check_id)
                for check_id in (
                    "false_positive_review",
                    "missed_test_plan_review",
                    "continuity_gap_review",
                    "scope_coverage_dependency_drift",
                    "reproducibility_determinism_drift",
                    "flaky_plan_review",
                    "staleness_review",
                    "operator_review_visibility",
                    "deliberate_no_change",
                )
            ),
        ),
        (
            "duplicate_overlap_correction_supersession_and_retirement",
            _passed(intake, "duplicate_overlap")
            and _passed(intake, "correction_lineage")
            and {"merged", "superseded", "stale", "obsolete", "retracted", "retired"}
            <= set(CANDIDATE_STATES)
            and {"superseded", "stale", "retracted", "retired"}
            <= set(LINEAGE_STATES),
        ),
        (
            "recovery_resource_prerequisite_and_operator_review_interaction",
            {
                "defer_for_recovery",
                "defer_for_resource_budget",
                "await_prerequisite",
                "defer_for_operator_review",
            }
            <= set(OUTCOMES)
            and all(
                row.get("prerequisite_ids") is not None
                and row.get("operator_review_required") is not None
                for row in recent_eligibility
            ),
        ),
        (
            "privacy_and_hidden_reasoning_boundary",
            all(
                report.get(field) is not True
                for report in reports + components
                for field in privacy_fields
            )
            and _passed(intake, "privacy_boundary")
            and _passed(deliberation, "privacy_boundary")
            and _passed(integration, "privacy_boundary"),
        ),
        (
            "authority_separation_across_all_stages",
            _authority_inert(*components)
            and all(
                report.get(field) is not True
                for report in reports + components
                for field in authority_fields
            )
            and _passed(intake, "authority_separation")
            and _passed(integration, "authority_separation"),
        ),
        (
            "no_test_plan_text_code_fixture_or_downstream_artifact_creation",
            _passed(intake, "no_test_plan_or_code")
            and _passed(deliberation, "no_test_plan_text")
            and _passed(integration, "no_test_plan_or_test_code")
            and all(
                not any(row.get(field) for field in downstream_fields)
                for row in all_records
            ),
        ),
        (
            "read_only_source_runtime_provider_and_action_boundary",
            _passed(intake, "read_only")
            and _passed(deliberation, "read_only")
            and _passed(integration, "read_only")
            and all(report.get("runtime_mutated") is not True for report in reports)
            and all(report.get("source_modified") is not True for report in reports)
            and all(
                component.get("provider_contacted") is not True
                for component in components
            )
            and all(
                component.get("external_action_executed") is not True
                for component in components
            ),
        ),
        (
            "desktop_pending_without_consciousness_claim",
            all(report.get("desktop_verification") == "pending" for report in reports),
        ),
    ]

    rows = [
        {"id": check_id, "status": "pass" if bool(ok) else "fail"}
        for check_id, ok in checks
    ]
    passed = sum(row["status"] == "pass" for row in rows)
    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    runtime_mutated = runtime_before != runtime_after
    source_modified = source_before != source_after
    outcome_counts = arbitration.get("outcome_counts") or {}

    return {
        "ok": passed == len(checks),
        "contract_version": CONTRACT_VERSION,
        "status": (
            "ready_for_desktop_verification" if passed == len(checks) else "degraded"
        ),
        "headline": (
            f"v1138.9 Supervised Test Planning Governance: "
            f"{passed}/{len(checks)} checks passed"
        ),
        "checks": rows,
        "passed": passed,
        "total": len(checks),
        "summary": {
            "eligibility_record_count": eligibility.get("record_count", 0),
            "candidate_count": candidates.get("candidate_count", 0),
            "deliberation_session_count": sessions.get("session_count", 0),
            "arbitration_outcome_count": arbitration.get("outcome_count", 0),
            "outcome_lineage_count": lineage.get("lineage_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "supported_or_probable_count": sum(
                outcome_counts.get(key, 0)
                for key in ("test_plan_supported", "test_plan_probable")
            ),
            "deliberate_no_test_plan_count": outcome_counts.get(
                "deliberate_no_test_plan", 0
            ),
        },
        "intake": intake,
        "deliberation": deliberation,
        "integration": integration,
        "runtime_mutated": runtime_mutated,
        "source_modified": source_modified,
        "raw_content_exposed": False,
        "raw_source_exposed": False,
        "source_content_exposed": False,
        "failure_log_exposed": False,
        "conversation_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "evidence_text_exposed": False,
        "proposal_text_exposed": False,
        "specification_text_exposed": False,
        "test_plan_text_exposed": False,
        "test_code_exposed": False,
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
        "specification_created": False,
        "test_plan_created": False,
        "test_code_created": False,
        "fixture_created": False,
        "sandbox_created": False,
        "tests_executed": False,
        "approval_created": False,
        "authorization_created": False,
        "external_action_executed": False,
        "source_modified_by_checkpoint": False,
        "installation_modified": False,
        "promotion_performed": False,
        "certification_performed": False,
        "filesystem_modified": False,
        "consciousness_proven": False,
        "test_plan_eligibility_created_by_checkpoint": False,
        "test_plan_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "outcome_lineage_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "test_plan_created_by_checkpoint": False,
        "test_code_created_by_checkpoint": False,
        "fixture_created_by_checkpoint": False,
        "sandbox_change_created_by_checkpoint": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
