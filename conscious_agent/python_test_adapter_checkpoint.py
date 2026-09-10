from __future__ import annotations

"""v1208.9 Python Test Adapter checkpoint.

Seals the exact approved proposal, grounded Python plan, validated generation,
isolated workspace, durable Python operation journal, bounded test result, and final
privacy/authority boundary into one immutable content-free checkpoint.  Passing
and failing test outcomes remain operator-review evidence only.
"""

from pathlib import Path
from typing import Any, Mapping

from grounded_development_planning import load_grounded_plan
from isolated_implementation_workspace import _record_path, _verify_record, _workspace_root
from python_test_adapter import (
    SUPPORTED_PROJECT_KINDS,
    _operation_path,
    _operation_valid,
    _record_valid,
    _result_path,
)
from ordinary_chat_development_campaign import (
    _approval_path,
    _atomic_json,
    _digest,
    _proposal_lock,
    _proposal_path,
    _read_json,
    _store_root,
    _validate,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1208.9"
STAGES = (
    "proposal_revision",
    "exact_approval",
    "grounded_planning",
    "structured_generation",
    "isolated_workspace",
    "python_operation_journal",
    "python_test_result",
    "privacy_authority_boundary",
)


def _checkpoint_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_test_checkpoints" / proposal_id / f"revision-{int(revision)}.json"


def _valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("checkpoint_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "checkpoint_digest"}))


def _stage(sequence: int, name: str, status: str, artifact_digest: str) -> dict[str, Any]:
    row = {
        "sequence": int(sequence),
        "stage": str(name),
        "status": str(status),
        "passed": True,
        "artifact_digest": str(artifact_digest or ""),
    }
    row["stage_receipt_digest"] = _digest(row)
    return row


def _stage_valid(row: Mapping[str, Any], sequence: int) -> bool:
    payload = {k: v for k, v in row.items() if k != "stage_receipt_digest"}
    return bool(
        str(row.get("stage_receipt_digest") or "") == _digest(payload)
        and int(row.get("sequence") or 0) == sequence
        and str(row.get("stage") or "") == STAGES[sequence - 1]
        and row.get("passed") is True
        and bool(row.get("artifact_digest"))
    )


def _generation_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("generation_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "generation_digest"}))


def _validate_existing(record: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any]:
    if not _valid(record):
        return {"ok": False, "status": "python_checkpoint_invalid"}
    if any(record.get(key) != value for key, value in bindings.items()):
        return {"ok": False, "status": "stale_python_checkpoint"}
    rows = list(record.get("stage_receipts") or [])
    if len(rows) != len(STAGES) or any(not _stage_valid(row, index) for index, row in enumerate(rows, 1)):
        return {"ok": False, "status": "python_checkpoint_lineage_invalid"}
    if record.get("stage_lineage_digest") != _digest(rows):
        return {"ok": False, "status": "python_checkpoint_lineage_invalid"}
    if any(record.get(key) is not False for key in (
        "network_allowed", "process_spawning_allowed", "native_extensions_allowed", "dependencies_installed", "shell_executed", "selected_project_modified",
        "source_modified", "implementation_applied", "apply_authorized", "rollback_authorized",
        "repair_authorized", "release_authorized", "model_management_authorized",
        "independent_authority_granted",
    )):
        return {"ok": False, "status": "python_checkpoint_authority_invalid"}
    return {**record, "operation_status": "resumed"}


def seal_or_resume_python_test_adapter_checkpoint(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_workspace_digest: str,
    expected_python_test_adapter_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    path = _checkpoint_path(proposal_id, expected_revision, runtime_root)
    bindings = {
        "proposal_id": str(proposal_id),
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": str(expected_revision_digest),
        "workspace_digest": str(expected_workspace_digest),
        "python_test_adapter_digest": str(expected_python_test_adapter_digest),
    }
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            return _validate_existing(existing, bindings)

        proposal = _read_json(_proposal_path(proposal_id, runtime_root))
        if not proposal or not _validate(proposal):
            return {"ok": False, "status": "proposal_missing_or_tampered"}
        if int(proposal.get("revision") or 0) != int(expected_revision) or proposal.get("revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}

        approval = _read_json(_approval_path(proposal_id, expected_revision, runtime_root))
        approval_digest = str((approval or {}).get("receipt_digest") or "")
        if not approval or approval_digest != _digest({k: v for k, v in approval.items() if k != "receipt_digest"}):
            return {"ok": False, "status": "approval_receipt_missing_or_invalid"}
        if approval.get("revision_digest") != expected_revision_digest or approval.get("approval_consumed_once") is not True:
            return {"ok": False, "status": "approval_receipt_binding_rejected"}

        plan = load_grounded_plan(proposal_id, expected_revision, runtime_root=runtime_root)
        planning_digest = str(plan.get("planning_digest") or "")
        if not plan or plan.get("proposal_revision_digest") != expected_revision_digest or not planning_digest:
            return {"ok": False, "status": "grounded_plan_missing_or_stale"}
        if str(plan.get("project_kind") or "") not in SUPPORTED_PROJECT_KINDS:
            return {"ok": False, "status": "python_checkpoint_requires_supported_project"}

        generation = _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(expected_revision)}.json")
        if not generation or not _generation_valid(generation):
            return {"ok": False, "status": "generation_record_missing_or_invalid"}
        if generation.get("proposal_revision_digest") != expected_revision_digest or generation.get("planning_digest") != planning_digest:
            return {"ok": False, "status": "stale_generation_binding"}
        generation_digest = str(generation.get("generation_digest") or "")

        workspace = _read_json(_record_path(proposal_id, expected_revision, runtime_root))
        if not workspace or workspace.get("workspace_digest") != expected_workspace_digest:
            return {"ok": False, "status": "workspace_record_missing_or_stale"}
        if workspace.get("proposal_revision_digest") != expected_revision_digest or workspace.get("planning_digest") != planning_digest:
            return {"ok": False, "status": "stale_workspace_binding"}
        if workspace.get("generation_digest") != generation_digest:
            return {"ok": False, "status": "stale_workspace_binding"}
        root = _workspace_root(proposal_id, expected_revision, generation_digest, runtime_root)
        if not _verify_record(workspace, root):
            return {"ok": False, "status": "workspace_record_invalid"}

        operation = _read_json(_operation_path(proposal_id, expected_revision, runtime_root))
        if not operation or not _operation_valid(operation):
            return {"ok": False, "status": "python_operation_missing_or_invalid"}
        if operation.get("phase") != "sealed":
            return {"ok": False, "status": "python_operation_not_sealed"}
        if (
            operation.get("proposal_revision_digest") != expected_revision_digest
            or operation.get("planning_digest") != planning_digest
            or operation.get("generation_digest") != generation_digest
            or operation.get("workspace_digest") != expected_workspace_digest
        ):
            return {"ok": False, "status": "stale_python_operation"}
        if operation.get("result_digest") != expected_python_test_adapter_digest:
            return {"ok": False, "status": "python_operation_result_mismatch"}
        operation_digest = str(operation.get("operation_digest") or "")

        result = _read_json(_result_path(proposal_id, expected_revision, runtime_root))
        if not result or not _record_valid(result) or result.get("python_test_adapter_digest") != expected_python_test_adapter_digest:
            return {"ok": False, "status": "python_result_missing_or_invalid"}
        if (
            result.get("proposal_revision_digest") != expected_revision_digest
            or result.get("planning_digest") != planning_digest
            or result.get("generation_digest") != generation_digest
            or result.get("workspace_digest") != expected_workspace_digest
        ):
            return {"ok": False, "status": "stale_python_result"}
        if result.get("ok") is not True or result.get("status") not in {
            "python_test_adapter_passed",
            "python_test_adapter_failed",
            "python_tests_not_found",
            "python_runtime_unavailable",
            "python_pytest_unavailable",
            "python_test_capability_contract_rejected",
            "python_test_budget_exceeded",
            "python_test_source_unreadable",
            "python_test_file_rejected",
            "python_test_path_rejected",
        }:
            return {"ok": False, "status": "python_result_not_checkpointable"}
        if result.get("network_allowed") is not False or result.get("dependencies_installed") is not False or result.get("shell_executed") is not False:
            return {"ok": False, "status": "python_authority_boundary_rejected"}
        if any(result.get(key) is not False for key in (
            "selected_project_modified", "source_modified", "implementation_applied", "apply_authorized",
            "rollback_authorized", "repair_authorized", "release_authorized", "authority_granted",
        )):
            return {"ok": False, "status": "python_authority_boundary_rejected"}

        authority = {
            "operator_review_required": True,
            "network_allowed": False,
            "process_spawning_allowed": False,
            "native_extensions_allowed": False,
            "dependencies_installed": False,
            "shell_executed": False,
            "selected_project_modified": False,
            "source_modified": False,
            "implementation_applied": False,
            "apply_authorized": False,
            "rollback_authorized": False,
            "repair_authorized": False,
            "release_authorized": False,
            "model_management_authorized": False,
            "independent_authority_granted": False,
        }
        authority_digest = _digest(authority)
        outcome = "python_tests_passed" if result.get("passed") is True else "python_tests_failed_review_required"
        rows = [
            _stage(1, STAGES[0], "exact_revision_verified", expected_revision_digest),
            _stage(2, STAGES[1], "approval_consumed_once", approval_digest),
            _stage(3, STAGES[2], "grounded_python_plan_verified", planning_digest),
            _stage(4, STAGES[3], "validated_generation_verified", generation_digest),
            _stage(5, STAGES[4], "isolated_workspace_verified", expected_workspace_digest),
            _stage(6, STAGES[5], "python_operation_sealed", operation_digest),
            _stage(7, STAGES[6], outcome, expected_python_test_adapter_digest),
            _stage(8, STAGES[7], "operator_review_boundary_preserved", authority_digest),
        ]
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            **bindings,
            "approval_receipt_digest": approval_digest,
            "planning_digest": planning_digest,
            "generation_digest": generation_digest,
            "python_operation_digest": operation_digest,
            "stage_count": len(rows),
            "stage_receipts": rows,
            "stage_lineage_digest": _digest(rows),
            "tests_passed": bool(result.get("passed")),
            "test_outcome_class": str(result.get("outcome_class") or ""),
            "runner": str(result.get("runner") or "none"),
            "pytest_available": bool(result.get("pytest_available")),
            "python_executed": bool(result.get("python_executed")),
            "platform_family": str(result.get("platform_family") or "unknown"),
            "python_source_class": str(result.get("python_source_class") or "none"),
            "launch_attempt_count": int(result.get("launch_attempt_count") or 0),
            "operation_recovery_count": int(result.get("operation_recovery_count") or 0),
            "syntax_file_count": int(result.get("syntax_file_count") or 0),
            "test_file_count": int(result.get("test_file_count") or 0),
            "command_count": int(result.get("command_count") or 0),
            "passed_command_count": int(result.get("passed_command_count") or 0),
            "failed_command_count": int(result.get("failed_command_count") or 0),
            "cleanup_confirmed": bool(result.get("cleanup_confirmed")),
            "private_request_included": False,
            "private_path_included": False,
            "private_content_included": False,
            "raw_output_included": False,
            "python_executable_path_included": False,
            "content_free": True,
            **authority,
            "status": "python_test_adapter_checkpoint_passed" if result.get("passed") is True else "python_test_adapter_checkpoint_failed_review_required",
            "ok": True,
        }
        record["checkpoint_digest"] = _digest(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_python_test_adapter_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_checkpoint_path(proposal_id, revision, runtime_root))
    return record if record and _valid(record) else {}


def public_python_test_adapter_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "ok", "status", "contract_version", "proposal_id", "proposal_revision",
        "proposal_revision_digest", "approval_receipt_digest", "planning_digest", "generation_digest",
        "workspace_digest", "python_operation_digest", "python_test_adapter_digest", "stage_count",
        "stage_receipts", "stage_lineage_digest", "checkpoint_digest", "tests_passed",
        "test_outcome_class", "runner", "pytest_available", "python_executed", "platform_family", "python_source_class",
        "launch_attempt_count", "operation_recovery_count", "syntax_file_count", "test_file_count",
        "command_count", "passed_command_count", "failed_command_count", "cleanup_confirmed",
        "operator_review_required", "network_allowed", "process_spawning_allowed", "native_extensions_allowed", "dependencies_installed", "shell_executed",
        "selected_project_modified", "source_modified", "implementation_applied", "apply_authorized",
        "rollback_authorized", "repair_authorized", "release_authorized", "model_management_authorized",
        "independent_authority_granted", "content_free",
    )
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_output_exposed": False,
        "python_executable_path_exposed": False,
        "runner_configuration_exposed": False,
    })
    return public
