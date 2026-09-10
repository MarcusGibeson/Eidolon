from __future__ import annotations

"""Strictly read-only v1141.9 Supervised Sandbox Repair Implementation Governance checkpoint."""

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

from supervised_repair_implementation_intake_checkpoint import build_supervised_repair_implementation_intake_checkpoint
from supervised_repair_execution_checkpoint import build_supervised_repair_execution_checkpoint
from supervised_repair_execution_integration_checkpoint import build_supervised_repair_execution_integration_checkpoint

CONTRACT_VERSION = "v1141.9"


def _runtime_root() -> Path:
    return (
        Path(
            os.environ.get("EIDOLON_DATA_DIR")
            or Path(__file__).resolve().parents[1] / "data"
        )
        .expanduser()
        .resolve()
        / "cognition"
    )


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing-tree")
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
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


def _passed(report: dict[str, Any], identifier: str) -> bool:
    for row in report.get("checks") or []:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id") or row.get("name") or row.get("check") or row.get("check_id")
        if row_id != identifier:
            continue
        return bool(row.get("passed") or row.get("ok") or row.get("status") == "pass")
    return False


def _false_across(components: Iterable[dict[str, Any]], fields: Iterable[str]) -> bool:
    return all(not bool(component.get(field)) for component in components for field in fields)


def _authority_inert(component: dict[str, Any]) -> bool:
    boundary = component.get("authority_boundary") or {}
    return not any(bool(value) for value in boundary.values())


def build_supervised_sandbox_repair_implementation_governance_checkpoint(
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

    intake = build_supervised_repair_implementation_intake_checkpoint(
        runtime, source_root=source
    )
    execution = build_supervised_repair_execution_checkpoint(runtime, source)
    integration = build_supervised_repair_execution_integration_checkpoint(
        runtime, source
    )

    eligibility = intake.get("eligibility") or {}
    work_orders = intake.get("work_orders") or {}
    materialization = execution.get("materialization") or {}
    sandbox_execution = execution.get("execution") or {}
    continuity = integration.get("continuity") or {}
    reliability = integration.get("reliability") or {}
    components = (
        eligibility,
        work_orders,
        materialization,
        sandbox_execution,
        continuity,
        reliability,
    )

    eligibility_rows = eligibility.get("recent_records") or []
    work_order_rows = work_orders.get("recent_work_orders") or []
    materialization_rows = materialization.get("recent_materializations") or []
    execution_rows = sandbox_execution.get("recent_executions") or []
    reconciliation_rows = continuity.get("recent_reconciliations") or []
    reliability_rows = reliability.get("recent_reviews") or []

    privacy_fields = (
        "raw_content_exposed",
        "raw_source_exposed",
        "source_content_exposed",
        "patch_text_exposed",
        "commands_exposed",
        "test_instructions_exposed",
        "logs_exposed",
        "conversation_exposed",
        "prompt_exposed",
        "provider_payload_exposed",
        "private_project_record_exposed",
        "private_path_exposed",
        "hidden_reasoning_exposed",
    )
    forbidden_authority_fields = (
        "browser_contacted",
        "provider_contacted",
        "model_contacted",
        "message_sent",
        "notification_created",
        "goal_mutated",
        "plan_mutated",
        "initiative_mutated",
        "proposal_created",
        "approval_created",
        "authorization_created",
        "source_modified",
        "installation_modified",
        "installation_performed",
        "promotion_created",
        "promotion_performed",
        "certification_created",
        "certification_performed",
    )

    checks = [
        (
            "supervised_repair_implementation_arc_lineage",
            intake.get("ok")
            and execution.get("ok")
            and integration.get("ok")
            and intake.get("contract_version") == "v1141.2"
            and execution.get("contract_version") == "v1141.5"
            and integration.get("contract_version") == "v1141.8",
        ),
        (
            "exact_v1140_through_v1135_lineage",
            _passed(intake, "v1140_execution_outcome_lineage")
            and _passed(intake, "sandbox_change_through_deficiency_lineage")
            and all(
                row.get("v1140_arbitration_id")
                and row.get("v1140_candidate_id")
                and row.get("sandbox_change_candidate_ids")
                and row.get("test_plan_candidate_ids")
                and row.get("specification_candidate_ids")
                and row.get("proposal_candidate_ids")
                and row.get("deficiency_candidate_ids")
                for row in eligibility_rows
            ),
        ),
        (
            "reviewed_artifact_approval_authorization_binding",
            _passed(intake, "reviewed_artifact_set_binding")
            and _passed(intake, "approval_authorization_separation")
            and all(
                row.get("reviewed_artifact_set_digest")
                and row.get("approval_id") != row.get("authorization_id")
                and row.get("approval_binding_valid") is not None
                and row.get("authorization_binding_valid") is not None
                for row in eligibility_rows
            ),
        ),
        (
            "eligibility_work_order_materialization_execution_separation",
            _passed(intake, "eligibility_execution_separation")
            and all(not row.get("workspace_id") for row in eligibility_rows)
            and all(not row.get("candidate_change_id") for row in work_order_rows)
            and all(row.get("candidate_change_id") is not None for row in execution_rows),
        ),
        (
            "immutable_authorized_scope_profiles_paths_and_budgets",
            _passed(intake, "workspace_isolation_integrity")
            and _passed(intake, "operation_execution_categories")
            and _passed(intake, "command_test_resource_time_budgets")
            and _passed(intake, "path_component_boundaries")
            and _passed(intake, "immutable_authorized_bounds")
            and all(row.get("immutable_authorized_bounds") for row in work_order_rows),
        ),
        (
            "operator_confirmation_claim_token_and_duplicate_suppression",
            _passed(intake, "duplicate_stale_retry_cross_tab")
            and _passed(intake, "execution_token_inert")
            and continuity.get("stale_worker_suppression") is True
            and continuity.get("duplicate_suppression") is True
            and all(row.get("claim_id") and row.get("execution_token_id") for row in materialization_rows),
        ),
        (
            "isolated_workspace_source_installation_containment",
            _passed(execution, "source_protected")
            and _passed(execution, "installation_protected")
            and all(not row.get("source_modified") and not row.get("installation_modified") for row in materialization_rows)
            and all(not row.get("source_modified") and not row.get("installation_modified") for row in execution_rows),
        ),
        (
            "bounded_candidate_change_command_test_cancellation_timeout_and_rollback",
            _passed(intake, "containment_reversibility_recovery_rollback")
            and sandbox_execution.get("contract_version") == "v1141.4"
            and all(int(row.get("timeout_seconds") or 0) > 0 for row in execution_rows)
            and all(int(row.get("max_output_bytes") or 0) > 0 for row in execution_rows),
        ),
        (
            "structural_receipts_and_exact_result_lineage",
            reliability.get("contract_version") == "v1141.7"
            and all(
                item.get("execution_id")
                and item.get("materialization_id")
                and item.get("structural_digest")
                for row in reliability_rows
                for item in row.get("result_lineage") or []
            ),
        ),
        (
            "restart_interruption_and_stale_worker_reconciliation",
            _passed(integration, "restart_safe")
            and _passed(integration, "stale_worker_suppression")
            and _passed(integration, "duplicate_suppression")
            and continuity.get("restart_safe") is True
            and all(row.get("structural_digest") for row in reconciliation_rows),
        ),
        (
            "contamination_repeated_failure_and_candidate_evidence_review",
            _passed(integration, "candidate_evidence_only")
            and _passed(integration, "not_installation_eligible")
            and reliability.get("operator_candidate_evidence_only") is True
            and not reliability.get("installation_eligible")
            and all(row.get("finding") and row.get("structural_digest") for row in reliability_rows),
        ),
        (
            "contradiction_retraction_supersession_expiry_and_retirement",
            _passed(intake, "correction_lifecycle")
            and _passed(intake, "work_order_state_coverage")
            and _passed(intake, "eligibility_state_coverage"),
        ),
        (
            "privacy_and_hidden_reasoning_boundaries",
            _passed(intake, "privacy_hidden_reasoning_boundary")
            and _passed(execution, "privacy_patch")
            and _passed(execution, "privacy_commands")
            and _passed(execution, "privacy_logs")
            and _passed(integration, "privacy")
            and _false_across(components, privacy_fields),
        ),
        (
            "stage_and_authority_separation",
            _passed(intake, "authority_separation")
            and _passed(execution, "approval_separate")
            and _passed(execution, "authorization_separate")
            and _passed(integration, "approval_separate")
            and _passed(integration, "authorization_separate")
            and _authority_inert(eligibility)
            and _authority_inert(work_orders)
            and _authority_inert(materialization)
            and _authority_inert(continuity),
        ),
        (
            "no_installation_self_approval_self_authorization_promotion_or_certification",
            _passed(execution, "promotion_protected")
            and _passed(execution, "certification_protected")
            and _passed(integration, "promotion_protected")
            and _passed(integration, "certification_protected")
            and _false_across(components, forbidden_authority_fields),
        ),
        (
            "checkpoint_is_strictly_read_only",
            not intake.get("runtime_mutated")
            and not intake.get("source_modified")
            and not execution.get("runtime_mutated")
            and not integration.get("runtime_mutated")
            and runtime_before == _tree_signature(runtime)
            and source_before == _tree_signature(source),
        ),
        (
            "source_runtime_separation",
            all(not component.get("source_modified") for component in components)
            and all(not component.get("installation_modified") for component in components),
        ),
        (
            "desktop_pending_and_consciousness_unproven",
            intake.get("desktop_verification") == "pending"
            and execution.get("desktop_verification") == "pending"
            and integration.get("desktop_verification") == "pending",
        ),
    ]

    runtime_after = _tree_signature(runtime)
    source_after = _tree_signature(source)
    passed = sum(bool(value) for _, value in checks)
    total = len(checks)
    state_counts = work_orders.get("state_counts") or {}
    candidate_ready = sum(
        1 for row in reliability_rows if row.get("operator_candidate_evidence_ready")
    )

    return {
        "ok": passed == total,
        "status": "ready_for_desktop_verification" if passed == total else "review_required",
        "contract_version": CONTRACT_VERSION,
        "passed": passed,
        "total": total,
        "checks": [
            {"id": identifier, "status": "pass" if value else "fail"}
            for identifier, value in checks
        ],
        "summary": {
            "eligibility_record_count": eligibility.get("record_count", 0),
            "work_order_count": work_orders.get("work_order_count", 0),
            "ready_for_materialization_count": state_counts.get(
                "ready_for_operator_confirmed_materialization", 0
            ),
            "materialization_count": materialization.get("materialization_count", 0),
            "execution_count": sandbox_execution.get("execution_count", 0),
            "reconciliation_count": continuity.get("reconciliation_count", 0),
            "reliability_review_count": reliability.get("review_count", 0),
            "operator_candidate_evidence_ready_count": candidate_ready,
        },
        "intake": intake,
        "execution": execution,
        "integration": integration,
        "runtime_mutated": runtime_before != runtime_after,
        "source_modified": source_before != source_after,
        "raw_content_exposed": False,
        "raw_source_exposed": False,
        "source_content_exposed": False,
        "patch_text_exposed": False,
        "commands_exposed": False,
        "test_instructions_exposed": False,
        "logs_exposed": False,
        "conversation_exposed": False,
        "prompt_exposed": False,
        "provider_payload_exposed": False,
        "private_project_record_exposed": False,
        "private_path_exposed": False,
        "hidden_reasoning_exposed": False,
        "browser_contacted": False,
        "provider_contacted": False,
        "model_contacted": False,
        "message_sent": False,
        "notification_created": False,
        "goal_mutated": False,
        "plan_mutated": False,
        "initiative_mutated": False,
        "proposal_created": False,
        "approval_created": False,
        "authorization_created": False,
        "eligibility_created_by_checkpoint": False,
        "work_order_created_by_checkpoint": False,
        "claim_created_by_checkpoint": False,
        "sandbox_created_by_checkpoint": False,
        "workspace_materialized_by_checkpoint": False,
        "candidate_change_created_by_checkpoint": False,
        "command_executed_by_checkpoint": False,
        "test_executed_by_checkpoint": False,
        "rollback_executed_by_checkpoint": False,
        "structural_receipt_created_by_checkpoint": False,
        "continuity_record_created_by_checkpoint": False,
        "reliability_review_created_by_checkpoint": False,
        "source_modified_by_checkpoint": False,
        "installation_modified": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
