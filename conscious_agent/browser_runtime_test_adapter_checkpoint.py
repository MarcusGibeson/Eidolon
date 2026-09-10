from __future__ import annotations

"""v1206.9 Browser Runtime Test Adapter checkpoint.

Seals the exact ordinary-chat proposal revision, exactly-once approval,
grounded plan, validated generation, isolated workspace, opaque preview,
durable browser-operation journal, browser-runtime result, and final
privacy/authority boundary into one immutable content-free checkpoint.

The checkpoint records evidence only. It grants no apply, rollback, repair,
provider, network, source, model-management, release, certification, or
independent authority.
"""

from pathlib import Path
from typing import Any, Mapping

from browser_runtime_test_adapter import (
    _operation_valid,
    _record_valid,
    _runtime_operation_path,
    _runtime_test_path,
)
from grounded_development_planning import load_grounded_plan
from isolated_implementation_workspace import _record_path, _verify_record, _workspace_root
from isolated_workspace_preview import _preview_path
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
CONTRACT_VERSION = "v1206.9"
STAGES = (
    "proposal_revision",
    "exact_approval",
    "grounded_planning",
    "structured_generation",
    "isolated_workspace",
    "browser_preview",
    "browser_operation_journal",
    "browser_runtime_result",
    "privacy_authority_boundary",
)


def _checkpoint_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "browser_runtime_checkpoints" / proposal_id / f"revision-{int(revision)}.json"


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


def _preview_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("preview_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "preview_digest"}))


def _generation_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("generation_digest") or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != "generation_digest"}))


def _validate_existing(record: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any]:
    if not _valid(record):
        return {"ok": False, "status": "browser_runtime_checkpoint_invalid"}
    if any(record.get(key) != value for key, value in bindings.items()):
        return {"ok": False, "status": "stale_browser_runtime_checkpoint"}
    rows = list(record.get("stage_receipts") or [])
    if len(rows) != len(STAGES) or any(not _stage_valid(row, index) for index, row in enumerate(rows, 1)):
        return {"ok": False, "status": "browser_runtime_checkpoint_lineage_invalid"}
    if record.get("stage_lineage_digest") != _digest(rows):
        return {"ok": False, "status": "browser_runtime_checkpoint_lineage_invalid"}
    if record.get("network_allowed") is not False:
        return {"ok": False, "status": "browser_runtime_checkpoint_authority_invalid"}
    if any(record.get(key) is not False for key in (
        "selected_project_modified", "source_modified", "apply_authorized", "repair_authorized",
        "release_authorized", "model_management_authorized", "independent_authority_granted",
    )):
        return {"ok": False, "status": "browser_runtime_checkpoint_authority_invalid"}
    return {**record, "operation_status": "resumed"}


def seal_or_resume_browser_runtime_test_adapter_checkpoint(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_workspace_digest: str,
    expected_preview_digest: str,
    expected_browser_runtime_test_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    path = _checkpoint_path(proposal_id, expected_revision, runtime_root)
    bindings = {
        "proposal_id": str(proposal_id),
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": str(expected_revision_digest),
        "workspace_digest": str(expected_workspace_digest),
        "preview_digest": str(expected_preview_digest),
        "browser_runtime_test_digest": str(expected_browser_runtime_test_digest),
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
        approval_digest = str(approval.get("receipt_digest") or "")
        if not approval or approval_digest != _digest({k: v for k, v in approval.items() if k != "receipt_digest"}):
            return {"ok": False, "status": "approval_receipt_missing_or_invalid"}
        if approval.get("revision_digest") != expected_revision_digest or approval.get("approval_consumed_once") is not True:
            return {"ok": False, "status": "approval_receipt_binding_rejected"}

        plan = load_grounded_plan(proposal_id, expected_revision, runtime_root=runtime_root)
        planning_digest = str(plan.get("planning_digest") or "")
        if not plan or plan.get("proposal_revision_digest") != expected_revision_digest or not planning_digest:
            return {"ok": False, "status": "grounded_plan_missing_or_stale"}
        if str(plan.get("project_kind") or "") not in {"new_small_web_project", "static_web_project", "javascript_or_web_project", "empty_project"}:
            return {"ok": False, "status": "browser_runtime_checkpoint_requires_website"}

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
        workspace_root = _workspace_root(proposal_id, expected_revision, generation_digest, runtime_root)
        if not _verify_record(workspace, workspace_root):
            return {"ok": False, "status": "workspace_record_invalid"}

        preview = _read_json(_preview_path(proposal_id, expected_revision, runtime_root))
        if not preview or not _preview_valid(preview) or preview.get("preview_digest") != expected_preview_digest:
            return {"ok": False, "status": "preview_record_missing_or_invalid"}
        if preview.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_preview_binding"}
        if preview.get("workspace_digest") != expected_workspace_digest or preview.get("generation_digest") != generation_digest:
            return {"ok": False, "status": "stale_preview_binding"}
        if preview.get("planning_digest") != planning_digest:
            return {"ok": False, "status": "stale_preview_binding"}

        operation = _read_json(_runtime_operation_path(proposal_id, expected_revision, runtime_root))
        if not operation or not _operation_valid(operation):
            return {"ok": False, "status": "browser_runtime_operation_missing_or_invalid"}
        if operation.get("phase") != "sealed":
            return {"ok": False, "status": "browser_runtime_operation_not_sealed"}
        if operation.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_browser_runtime_operation"}
        if operation.get("workspace_digest") != expected_workspace_digest or operation.get("preview_digest") != expected_preview_digest:
            return {"ok": False, "status": "stale_browser_runtime_operation"}
        if operation.get("result_digest") != expected_browser_runtime_test_digest:
            return {"ok": False, "status": "browser_runtime_operation_result_mismatch"}
        operation_digest = str(operation.get("operation_digest") or "")

        result = _read_json(_runtime_test_path(proposal_id, expected_revision, runtime_root))
        if not result or not _record_valid(result) or result.get("browser_runtime_test_digest") != expected_browser_runtime_test_digest:
            return {"ok": False, "status": "browser_runtime_result_missing_or_invalid"}
        if result.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_browser_runtime_result"}
        if result.get("workspace_digest") != expected_workspace_digest or result.get("preview_digest") != expected_preview_digest:
            return {"ok": False, "status": "stale_browser_runtime_result"}
        if result.get("ok") is not True or result.get("status") not in {"browser_runtime_test_passed", "browser_runtime_test_failed"}:
            return {"ok": False, "status": "browser_runtime_result_not_checkpointable"}
        if result.get("passed") is True and result.get("cleanup_confirmed") is not True:
            return {"ok": False, "status": "browser_runtime_cleanup_not_confirmed"}
        if result.get("network_allowed") is not False:
            return {"ok": False, "status": "browser_runtime_authority_boundary_rejected"}
        if any(result.get(key) is not False for key in (
            "selected_project_modified", "source_modified", "apply_authorized", "repair_authorized",
            "release_authorized", "authority_granted",
        )):
            return {"ok": False, "status": "browser_runtime_authority_boundary_rejected"}

        authority = {
            "operator_review_required": True,
            "network_allowed": False,
            "selected_project_modified": False,
            "source_modified": False,
            "apply_authorized": False,
            "rollback_authorized": False,
            "repair_authorized": False,
            "release_authorized": False,
            "model_management_authorized": False,
            "independent_authority_granted": False,
        }
        authority_digest = _digest(authority)
        outcome_status = "browser_runtime_passed" if result.get("passed") is True else "browser_runtime_failed_review_required"
        rows = [
            _stage(1, STAGES[0], "exact_revision_verified", expected_revision_digest),
            _stage(2, STAGES[1], "approval_consumed_once", approval_digest),
            _stage(3, STAGES[2], "grounded_website_plan_verified", planning_digest),
            _stage(4, STAGES[3], "validated_generation_verified", generation_digest),
            _stage(5, STAGES[4], "isolated_workspace_verified", expected_workspace_digest),
            _stage(6, STAGES[5], "opaque_preview_verified", expected_preview_digest),
            _stage(7, STAGES[6], "browser_operation_sealed", operation_digest),
            _stage(8, STAGES[7], outcome_status, expected_browser_runtime_test_digest),
            _stage(9, STAGES[8], "operator_review_boundary_preserved", authority_digest),
        ]
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            **bindings,
            "approval_receipt_digest": approval_digest,
            "planning_digest": planning_digest,
            "generation_digest": generation_digest,
            "browser_operation_digest": operation_digest,
            "stage_count": len(rows),
            "stage_receipts": rows,
            "stage_lineage_digest": _digest(rows),
            "browser_runtime_passed": bool(result.get("passed")),
            "browser_executed": bool(result.get("browser_executed")),
            "platform_family": str(result.get("platform_family") or "unknown"),
            "browser_source_class": str(result.get("browser_source_class") or "none"),
            "launch_attempt_count": int(result.get("launch_attempt_count") or 0),
            "operation_recovery_count": int(result.get("operation_recovery_count") or 0),
            "cleanup_confirmed": bool(result.get("cleanup_confirmed")),
            "dom_ready": bool(result.get("dom_ready")),
            "runtime_marker_present": bool(result.get("runtime_marker_present")),
            "page_error_count": int(result.get("page_error_count") or 0),
            "blocked_external_request_count": int(result.get("blocked_external_request_count") or 0),
            "runtime_outcome_status": str(result.get("status") or ""),
            "private_request_included": False,
            "private_path_included": False,
            "private_content_included": False,
            "raw_browser_output_included": False,
            "content_free": True,
            **authority,
            "status": "browser_runtime_adapter_checkpoint_passed" if result.get("passed") is True else "browser_runtime_adapter_checkpoint_failed_review_required",
            "ok": True,
        }
        record["checkpoint_digest"] = _digest(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_browser_runtime_test_adapter_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_checkpoint_path(proposal_id, revision, runtime_root))
    return record if record and _valid(record) else {}


def public_browser_runtime_test_adapter_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "ok", "status", "contract_version", "proposal_id", "proposal_revision", "proposal_revision_digest",
        "approval_receipt_digest", "planning_digest", "generation_digest", "workspace_digest", "preview_digest",
        "browser_operation_digest", "browser_runtime_test_digest", "stage_count", "stage_receipts",
        "stage_lineage_digest", "checkpoint_digest", "browser_runtime_passed", "browser_executed",
        "platform_family", "browser_source_class", "launch_attempt_count", "operation_recovery_count",
        "cleanup_confirmed", "dom_ready", "runtime_marker_present", "page_error_count",
        "blocked_external_request_count", "runtime_outcome_status", "operator_review_required", "network_allowed",
        "selected_project_modified", "source_modified", "apply_authorized", "rollback_authorized",
        "repair_authorized", "release_authorized", "model_management_authorized",
        "independent_authority_granted", "content_free",
    )
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_browser_output_exposed": False,
    })
    return public
