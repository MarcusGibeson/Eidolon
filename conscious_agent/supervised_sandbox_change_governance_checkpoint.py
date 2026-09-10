from __future__ import annotations

"""Strictly read-only v1139.9 Supervised Sandbox Change Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any

from sandbox_change_arbitration import OUTCOMES
from sandbox_change_candidates import STATES as CANDIDATE_STATES
from sandbox_change_eligibility import CHANGE_CATEGORIES, OPERATION_CATEGORIES
from sandbox_change_eligibility import STATES as ELIGIBILITY_STATES
from sandbox_change_outcome_lineage import STATES as LINEAGE_STATES
from sandbox_change_reliability_review import FINDINGS
from supervised_sandbox_change_deliberation_checkpoint import build_supervised_sandbox_change_deliberation_checkpoint
from supervised_sandbox_change_intake_checkpoint import build_supervised_sandbox_change_intake_checkpoint
from supervised_sandbox_change_integration_checkpoint import build_supervised_sandbox_change_integration_checkpoint

CONTRACT_VERSION = "v1139.9"


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


def build_supervised_sandbox_change_governance_checkpoint(
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

    intake = build_supervised_sandbox_change_intake_checkpoint(runtime, source_root=source)
    deliberation = build_supervised_sandbox_change_deliberation_checkpoint(
        runtime, source_root=source
    )
    integration = build_supervised_sandbox_change_integration_checkpoint(
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

    expected_change_categories = {
        "source_repair",
        "test_repair",
        "documentation_repair",
        "configuration_repair",
        "architecture_repair",
        "usability_repair",
        "privacy_governance_repair",
        "deliberate_no_sandbox_change_review",
    }
    expected_operation_categories = {
        "create_candidate_file",
        "modify_candidate_file",
        "delete_candidate_file",
        "create_candidate_test",
        "modify_candidate_test",
        "candidate_documentation_change",
        "candidate_configuration_change",
    }
    expected_outcomes = {
        "sandbox_change_supported",
        "sandbox_change_probable",
        "defer_for_more_evidence",
        "defer_for_operator_review",
        "await_prerequisite",
        "defer_for_recovery",
        "defer_for_resource_budget",
        "await_scope_review",
        "await_containment_review",
        "await_reversibility_review",
        "await_isolation_review",
        "suppress_weak_support",
        "suppress_low_containment",
        "suppress_low_reversibility",
        "contradicted",
        "retracted",
        "deliberate_no_sandbox_change",
    }
    expected_findings = {
        "stable",
        "repeated_false_positive",
        "possible_missed_sandbox_change",
        "stale_outcome",
        "continuity_gap",
        "scope_drift",
        "path_drift",
        "containment_drift",
        "reversibility_drift",
        "isolation_drift",
        "resource_budget_drift",
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
        "patch_text_exposed",
        "private_path_exposed",
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
        "sandbox_created",
        "sandbox_change_created",
        "files_modified",
        "commands_executed",
        "tests_executed",
        "approval_created",
        "authorization_created",
        "external_action_executed",
        "source_modified_by_checkpoint",
        "installation_modified",
        "installation_performed",
        "promotion_performed",
        "certification_performed",
        "filesystem_modified",
    )
    downstream_fields = (
        "patch_text_digest",
        "sandbox_id",
        "sandbox_change_id",
        "changed_file_id",
        "changed_file_digest",
        "command_id",
        "test_execution_id",
        "approval_id",
        "authorization_id",
        "execution_id",
        "promotion_id",
        "certification_id",
    )

    checks = [
        (
            "supervised_sandbox_change_arc_lineage",
            intake.get("ok")
            and deliberation.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1139.2"
            and deliberation.get("contract_version") == "v1139.5"
            and integration.get("contract_version") == "v1139.8",
        ),
        (
            "change_operation_state_outcome_and_finding_coverage",
            set(CHANGE_CATEGORIES) == expected_change_categories
            and set(OPERATION_CATEGORIES) == expected_operation_categories
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
            "exact_test_plan_eligibility_candidate_lineage",
            _passed(intake, "exact_test_plan_lineage")
            and all(
                row.get("arbitration_id")
                and row.get("test_plan_candidate_id")
                and row.get("component_ids")
                and row.get("path_digests")
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
                row.get("supported_test_plan") is not None
                and row.get("eligible_test_plan") is not None
                for row in recent_eligibility
            )
            and all(
                row.get("outcome")
                not in {"sandbox_change_supported", "sandbox_change_probable"}
                or not any(row.get(field) for field in downstream_fields)
                for row in recent_outcomes
            ),
        ),
        (
            "component_path_operation_isolation_budget_reversibility_and_containment",
            _passed(intake, "structural_scope_only")
            and _passed(intake, "isolation_budget_reversibility")
            and _passed(intake, "bounded_operations")
            and _passed(intake, "prerequisite_operator_review")
            and all(
                row.get("component_ids")
                and row.get("path_digests")
                and row.get("operation_categories")
                and row.get("isolation_profile_id")
                and row.get("resource_budget_id") is not None
                and row.get("estimated_cost") is not None
                and row.get("reversibility") is not None
                and row.get("containment_confidence") is not None
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
            "evidence_scope_containment_reversibility_and_isolation_arbitration",
            _passed(
                deliberation,
                "evidence_scope_containment_reversibility_isolation",
            )
            and all(
                all(
                    key in row
                    for key in (
                        "evidence_support",
                        "scope_support",
                        "containment_support",
                        "reversibility_support",
                        "isolation_support",
                    )
                )
                for row in recent_outcomes
            ),
        ),
        (
            "deterministic_support_deferral_suppression_and_no_sandbox_change",
            expected_outcomes == set(OUTCOMES)
            and _passed(deliberation, "deliberate_no_sandbox_change")
            and _passed(deliberation, "outcome_coverage"),
        ),
        (
            "patch_sandbox_source_test_and_authority_separation",
            _passed(deliberation, "change_vs_execution_boundary")
            and _passed(integration, "no_patch_or_sandbox")
            and _passed(integration, "no_execution_or_self_approval")
            and all(
                not any(row.get(field) for field in downstream_fields)
                for row in all_records
            ),
        ),
        (
            "durable_outcome_lineage_and_continuity",
            _passed(integration, "exact_outcome_lineage")
            and _passed(integration, "restart_project_scope_continuity")
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
                    "missed_change_review",
                    "continuity_gap_review",
                    "scope_path_drift",
                    "containment_reversibility_isolation_drift",
                    "resource_budget_drift",
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
            "no_patch_sandbox_command_test_or_downstream_artifact_creation",
            _passed(intake, "no_patch_or_sandbox")
            and _passed(deliberation, "no_patch_text")
            and _passed(integration, "no_patch_or_sandbox")
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
            f"v1139.9 Supervised Sandbox Change Governance: "
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
                for key in ("sandbox_change_supported", "sandbox_change_probable")
            ),
            "deliberate_no_sandbox_change_count": outcome_counts.get(
                "deliberate_no_sandbox_change", 0
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
        "patch_text_exposed": False,
        "private_path_exposed": False,
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
        "sandbox_created": False,
        "sandbox_change_created": False,
        "files_modified": False,
        "commands_executed": False,
        "tests_executed": False,
        "approval_created": False,
        "authorization_created": False,
        "external_action_executed": False,
        "source_modified_by_checkpoint": False,
        "installation_modified": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "filesystem_modified": False,
        "consciousness_proven": False,
        "sandbox_change_eligibility_created_by_checkpoint": False,
        "sandbox_change_candidate_created_by_checkpoint": False,
        "deliberation_session_created_by_checkpoint": False,
        "arbitration_outcome_created_by_checkpoint": False,
        "outcome_lineage_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "patch_created_by_checkpoint": False,
        "sandbox_created_by_checkpoint": False,
        "sandbox_change_created_by_checkpoint": False,
        "command_executed_by_checkpoint": False,
        "test_executed_by_checkpoint": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
