from __future__ import annotations
"""Strictly read-only v1141.2 supervised repair implementation intake checkpoint."""

import hashlib
import os
from pathlib import Path

from repair_implementation_eligibility import STATES as ELIGIBILITY_STATES, build_repair_implementation_eligibility_inspection
from sandbox_repair_work_orders import STATES as WORK_ORDER_STATES, build_sandbox_repair_work_order_inspection

CONTRACT_VERSION = "v1141.2"


def _root() -> Path:
    return (
        Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")
        .expanduser()
        .resolve()
        / "cognition"
    )


def _signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file() and "__pycache__" not in item.parts and path_suffix_ok(item)):
        stat = path.stat()
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(str(stat.st_size).encode())
        digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def path_suffix_ok(path: Path) -> bool:
    return path.suffix not in {".pyc", ".pyo"}


def build_supervised_repair_implementation_intake_checkpoint(
    runtime_root: str | Path | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict:
    runtime = Path(runtime_root).resolve() if runtime_root else _root()
    source = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]
    runtime_before = _signature(runtime)
    source_before = _signature(source)
    eligibility = build_repair_implementation_eligibility_inspection(runtime)
    work_orders = build_sandbox_repair_work_order_inspection(runtime)
    eligibility_rows = eligibility.get("recent_records", [])
    work_order_rows = work_orders.get("recent_work_orders", [])

    checks = [
        ("eligibility_contract", eligibility.get("contract_version") == "v1141.0"),
        ("work_order_contract", work_orders.get("contract_version") == "v1141.1"),
        ("v1140_execution_outcome_lineage", all(row.get("v1140_arbitration_id") and row.get("v1140_deliberation_session_id") and row.get("v1140_candidate_id") and row.get("v1140_eligibility_ids") for row in eligibility_rows)),
        ("sandbox_change_through_deficiency_lineage", all(row.get("sandbox_change_candidate_ids") and row.get("test_plan_candidate_ids") and row.get("specification_candidate_ids") and row.get("proposal_candidate_ids") and row.get("deficiency_candidate_ids") for row in eligibility_rows)),
        ("reviewed_artifact_set_binding", all(row.get("reviewed_artifact_set_digest") and row.get("approval_artifact_set_digest") is not None and row.get("authorization_artifact_set_digest") is not None for row in eligibility_rows)),
        ("approval_authorization_separation", all(row.get("approval_id") != row.get("authorization_id") and row.get("approval_binding_valid") is not None and row.get("authorization_binding_valid") is not None for row in eligibility_rows)),
        ("eligibility_execution_separation", all(not row.get("sandbox_id") and not row.get("workspace_id") and not row.get("candidate_change_id") and not row.get("command_receipt_ids") and not row.get("test_receipt_ids") for row in eligibility_rows)),
        ("workspace_isolation_integrity", all(row.get("workspace_manifest_digests") and row.get("isolation_profile_ids") for row in eligibility_rows)),
        ("operation_execution_categories", all(row.get("allowed_operation_categories") and row.get("allowed_execution_modes") for row in eligibility_rows)),
        ("command_test_resource_time_budgets", all(row.get("command_profile_ids") and row.get("resource_budget_ids") and row.get("test_profile_id") and int(row.get("time_budget_seconds") or 0) > 0 for row in work_order_rows)),
        ("path_component_boundaries", all(row.get("component_ids") and (row.get("path_digests") or row.get("component_ids")) for row in eligibility_rows)),
        ("containment_reversibility_recovery_rollback", all(row.get("containment_requirements") and row.get("reversibility_requirements") and row.get("recovery_requirements") and row.get("rollback_requirements") for row in eligibility_rows)),
        ("duplicate_stale_retry_cross_tab", all(row.get("semantic_key") and row.get("stale_worker_suppressed") is not None and row.get("tab_session_digest") is not None for row in eligibility_rows)),
        ("correction_lifecycle", all(row.get("contradiction_ids") is not None and row.get("retraction_ids") is not None and row.get("supersession_ids") is not None for row in eligibility_rows) and all(row.get("retirement_ids") is not None for row in work_order_rows)),
        ("work_order_state_coverage", {"active", "suppressed", "deferred", "awaiting_prerequisite", "awaiting_approval", "awaiting_authorization", "ready_for_operator_confirmed_materialization", "claimed", "expired", "superseded", "retracted", "retired"} <= WORK_ORDER_STATES),
        ("eligibility_state_coverage", {"eligible", "awaiting_prerequisite", "awaiting_approval", "awaiting_authorization", "requires_operator_review", "suppressed", "expired", "superseded", "retracted", "retired"} <= ELIGIBILITY_STATES),
        ("execution_token_inert", all(row.get("execution_token_id") and not row.get("execution_token_activated") and not row.get("execution_token_grants_authority") for row in work_order_rows)),
        ("immutable_authorized_bounds", all(row.get("immutable_authorized_bounds") and row.get("authorized_bounds_match") is not None for row in work_order_rows)),
        ("privacy_hidden_reasoning_boundary", not eligibility.get("raw_source_exposed") and not eligibility.get("patch_text_exposed") and not eligibility.get("commands_exposed") and not eligibility.get("test_instructions_exposed") and not eligibility.get("hidden_reasoning_exposed") and not work_orders.get("raw_source_exposed") and not work_orders.get("patch_text_generated") and not work_orders.get("commands_exposed") and not work_orders.get("test_instructions_exposed") and not work_orders.get("hidden_reasoning_exposed")),
        ("authority_separation", not any(eligibility.get("authority_boundary", {}).values()) and not any(work_orders.get("authority_boundary", {}).values())),
        ("no_sandbox_command_test_or_source_action", not eligibility.get("sandbox_created") and not eligibility.get("workspace_materialized") and not eligibility.get("commands_executed") and not eligibility.get("tests_executed") and not eligibility.get("source_modified") and not work_orders.get("sandbox_created") and not work_orders.get("workspace_materialized") and not work_orders.get("commands_executed") and not work_orders.get("tests_executed") and not work_orders.get("source_modified")),
        ("no_approval_authorization_install_promotion_certification", not eligibility.get("approval_created") and not eligibility.get("authorization_created") and not work_orders.get("approval_created") and not work_orders.get("authorization_created") and not eligibility.get("installation_modified") and not work_orders.get("installation_modified")),
        ("read_only", runtime_before == _signature(runtime) and source_before == _signature(source)),
        ("desktop_verification_pending", True),
    ]
    passed = sum(bool(value) for _, value in checks)
    runtime_after = _signature(runtime)
    source_after = _signature(source)
    return {
        "ok": passed == len(checks),
        "status": "ready_for_desktop_verification" if passed == len(checks) else "review_required",
        "contract_version": CONTRACT_VERSION,
        "passed": passed,
        "total": len(checks),
        "checks": [{"id": identifier, "status": "pass" if value else "fail"} for identifier, value in checks],
        "eligibility": eligibility,
        "work_orders": work_orders,
        "summary": {
            "eligibility_record_count": eligibility.get("record_count", 0),
            "work_order_count": work_orders.get("work_order_count", 0),
            "ready_for_operator_confirmed_materialization_count": work_orders.get("state_counts", {}).get("ready_for_operator_confirmed_materialization", 0),
            "awaiting_approval_count": work_orders.get("state_counts", {}).get("awaiting_approval", 0),
            "awaiting_authorization_count": work_orders.get("state_counts", {}).get("awaiting_authorization", 0),
            "suppressed_count": work_orders.get("state_counts", {}).get("suppressed", 0),
        },
        "runtime_mutated": runtime_before != runtime_after,
        "source_modified": source_before != source_after,
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
        "work_order_created_by_checkpoint": False,
        "eligibility_created_by_checkpoint": False,
        "claim_created_by_checkpoint": False,
        "sandbox_created": False,
        "workspace_materialized": False,
        "candidate_change_created": False,
        "commands_executed": False,
        "tests_executed": False,
        "structural_receipt_created": False,
        "verified_completion_created": False,
        "source_modified_by_checkpoint": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "external_action_executed": False,
        "consciousness_proven": False,
        "desktop_verification": "pending",
        "desktop_verification_pending": True,
    }
