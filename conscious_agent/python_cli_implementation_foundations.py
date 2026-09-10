from __future__ import annotations

"""v1202.0-v1203.2 supervised Python CLI implementation foundations.

Advances one exactly approved Python-CLI proposal through grounded planning,
structured provider generation, isolated workspace materialization, bounded Node
validation, and a digest-only operator-review record. It never applies changes to
the selected project or Eidolon source and grants no repair or release authority.
"""
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping

from ordinary_chat_development_campaign import (
    _approval_path, _atomic_json, _digest, _proposal_lock, _proposal_path,
    _read_json, _store_root, _valid_approval_receipt, _validate,
)
from grounded_development_planning import _planning_path, _valid_plan, create_or_resume_grounded_plan
from structured_development_generation import _path as _generation_path, generate_or_resume_structured_output
from isolated_implementation_workspace import (
    _record_path as _workspace_record_path, _verify_record as _verify_workspace_record,
    _workspace_root, materialize_or_resume_workspace,
)
from bounded_workspace_validation import (
    _record_valid as _validation_record_valid, _validation_path, validate_or_resume_workspace,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1203.2"
PROJECT_KIND = "new_python_cli_project"
SELECTED_PROJECT_KIND = "python_project"
ACCEPTED_PROJECT_KINDS = {PROJECT_KIND, SELECTED_PROJECT_KIND}
STAGES = ("proposal", "approval", "planning", "generation", "workspace", "validation")


def _checkpoint_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_cli_checkpoints" / proposal_id / f"revision-{int(revision)}.json"


def _valid_sealed(record: Mapping[str, Any], field: str) -> bool:
    supplied = str(record.get(field) or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != field}))


def _stage(name: str, status: str, artifact_digest: str) -> dict[str, Any]:
    row = {"sequence": STAGES.index(name) + 1, "stage": name, "status": status, "passed": True, "artifact_digest": str(artifact_digest or "")}
    row["stage_receipt_digest"] = _digest(row)
    return row


def _load_lineage(proposal_id: str, revision: int, revision_digest: str, runtime_root=None):
    proposal = _read_json(_proposal_path(proposal_id, runtime_root))
    if not proposal or not _validate(proposal):
        return None, {"ok": False, "status": "proposal_missing_or_tampered"}
    if int(proposal.get("revision") or 0) != int(revision) or proposal.get("revision_digest") != revision_digest:
        return None, {"ok": False, "status": "stale_proposal_revision"}
    if not proposal.get("approval_consumed") or int(proposal.get("approval_consumption_count") or 0) != 1:
        return None, {"ok": False, "status": "exact_consumed_approval_required"}
    approval = _read_json(_approval_path(proposal_id, revision, runtime_root))
    if not approval or not _valid_approval_receipt(approval, proposal):
        return None, {"ok": False, "status": "approval_receipt_invalid"}
    plan = _read_json(_planning_path(proposal_id, revision, runtime_root))
    if not plan or not _valid_plan(plan) or plan.get("project_kind") not in ACCEPTED_PROJECT_KINDS:
        return None, {"ok": False, "status": "python_cli_scope_required"}
    generation = _read_json(_generation_path(proposal_id, revision, runtime_root))
    if not generation or not _valid_sealed(generation, "generation_digest"):
        return None, {"ok": False, "status": "generation_missing_or_invalid"}
    workspace = _read_json(_workspace_record_path(proposal_id, revision, runtime_root))
    if not workspace:
        return None, {"ok": False, "status": "workspace_missing"}
    root = _workspace_root(proposal_id, revision, str(generation.get("generation_digest") or ""), runtime_root)
    if not _verify_workspace_record(workspace, root):
        return None, {"ok": False, "status": "workspace_record_invalid"}
    validation = _read_json(_validation_path(proposal_id, revision, runtime_root))
    if not validation or not _validation_record_valid(validation):
        return None, {"ok": False, "status": "validation_missing_or_invalid"}
    expected = {
        "proposal_revision_digest": revision_digest,
        "planning_digest": plan.get("planning_digest"),
        "generation_digest": generation.get("generation_digest"),
        "workspace_digest": workspace.get("workspace_digest"),
        "approval_receipt_digest": approval.get("receipt_digest"),
    }
    for record in (generation, workspace, validation):
        for key, value in expected.items():
            if key in record and record.get(key) != value:
                return None, {"ok": False, "status": f"{key}_binding_rejected"}
    if validation.get("passed") is not True:
        return None, {"ok": False, "status": "validation_not_passed", "validation_digest": validation.get("validation_digest", ""), "repair_authorized": False}
    return {"proposal": proposal, "approval": approval, "plan": plan, "generation": generation, "workspace": workspace, "validation": validation}, {}


def create_or_resume_python_cli_checkpoint(proposal_id: str, *, expected_revision: int, expected_revision_digest: str, runtime_root=None) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        lineage, error = _load_lineage(proposal_id, expected_revision, expected_revision_digest, runtime_root)
        if lineage is None:
            return error
        path = _checkpoint_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            return ({**existing, "operation_status": "resumed"} if _valid_sealed(existing, "checkpoint_digest") else {"ok": False, "status": "python_cli_checkpoint_invalid"})
        generation = lineage["generation"]
        operations = Counter(str(row.get("operation") or "") for row in generation.get("files") or [])
        stages = [
            _stage("proposal", "approved_revision_bound", lineage["proposal"].get("proposal_digest", "")),
            _stage("approval", "consumed_exactly_once", lineage["approval"].get("receipt_digest", "")),
            _stage("planning", "python_cli_plan_ready", lineage["plan"].get("planning_digest", "")),
            _stage("generation", "validated_generation_ready", generation.get("generation_digest", "")),
            _stage("workspace", "isolated_workspace_ready", lineage["workspace"].get("workspace_digest", "")),
            _stage("validation", "python_validation_passed", lineage["validation"].get("validation_digest", "")),
        ]
        record = {
            "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, "ok": True,
            "status": "python_cli_implementation_ready_for_operator_review",
            "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "request_digest": lineage["proposal"].get("request_digest"),
            "target_digest": (lineage["proposal"].get("target") or {}).get("target_digest"),
            "approval_receipt_digest": lineage["approval"].get("receipt_digest"),
            "planning_digest": lineage["plan"].get("planning_digest"),
            "project_snapshot_digest": lineage["plan"].get("project_snapshot_digest"),
            "generation_digest": generation.get("generation_digest"),
            "workspace_digest": lineage["workspace"].get("workspace_digest"),
            "validation_digest": lineage["validation"].get("validation_digest"),
            "stage_receipts": stages, "stage_count": len(stages), "stage_lineage_digest": _digest(stages),
            "change_summary": {
                "file_count": int(generation.get("file_count") or 0), "total_bytes": int(generation.get("total_bytes") or 0),
                "create_count": int(operations.get("create", 0)), "modify_count": int(operations.get("modify", 0)),
                "delete_count": int(operations.get("delete", 0)),
                "path_digests": [str(row.get("relative_path_digest") or "") for row in generation.get("files") or []],
                "content_digests": [str(row.get("content_digest") or "") for row in generation.get("files") or []],
            },
            "test_summary": {
                "passed": True, "adapter_count": int(lineage["validation"].get("adapter_count") or 0),
                "command_count": int(lineage["validation"].get("command_count") or 0),
                "adapter_statuses": [{"adapter": str(a.get("adapter") or ""), "status": str(a.get("status") or ""), "passed": bool(a.get("passed"))} for a in lineage["validation"].get("adapters") or []],
            },
            "operator_review_required": True, "working_result_available": True,
            "selected_project_modified": False, "source_modified": False, "implementation_applied": False,
            "repair_authorized": False, "apply_authorized": False, "release_authorized": False, "authority_granted": False,
            "private_request_included": False, "private_path_included": False, "private_content_included": False,
            "raw_provider_output_included": False,
        }
        record["checkpoint_digest"] = _digest(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def run_or_resume_python_cli_implementation(proposal_id: str, *, expected_revision: int, expected_revision_digest: str, runtime_root=None, provider_generate: Callable[[str], str] | None = None, python_executable: str | None = None) -> dict[str, Any]:
    plan = create_or_resume_grounded_plan(proposal_id, expected_revision=expected_revision, expected_revision_digest=expected_revision_digest, runtime_root=runtime_root)
    if plan.get("project_kind") not in ACCEPTED_PROJECT_KINDS:
        return {"ok": False, "status": "python_cli_scope_required", "failed_stage": "planning"}
    generation = generate_or_resume_structured_output(proposal_id, expected_revision=expected_revision, expected_revision_digest=expected_revision_digest, expected_planning_digest=str(plan.get("planning_digest") or ""), runtime_root=runtime_root, provider_generate=provider_generate)
    if not generation.get("generation_digest"):
        return {"ok": False, "status": generation.get("status", "generation_failed"), "failed_stage": "generation", "repair_authorized": False, "apply_authorized": False}
    workspace = materialize_or_resume_workspace(proposal_id, expected_revision=expected_revision, expected_revision_digest=expected_revision_digest, expected_planning_digest=str(plan.get("planning_digest") or ""), expected_generation_digest=str(generation.get("generation_digest") or ""), runtime_root=runtime_root)
    if not workspace.get("workspace_digest"):
        return {"ok": False, "status": workspace.get("status", "materialization_failed"), "failed_stage": "workspace", "repair_authorized": False, "apply_authorized": False}
    validation = validate_or_resume_workspace(proposal_id, expected_revision=expected_revision, expected_revision_digest=expected_revision_digest, expected_workspace_digest=str(workspace.get("workspace_digest") or ""), expected_preview_digest="", runtime_root=runtime_root, python_executable=python_executable)
    if not validation.get("validation_digest") or validation.get("passed") is not True:
        return {"ok": False, "status": validation.get("status", "validation_failed"), "failed_stage": "validation", "validation_digest": validation.get("validation_digest", ""), "repair_authorized": False}
    return create_or_resume_python_cli_checkpoint(proposal_id, expected_revision=expected_revision, expected_revision_digest=expected_revision_digest, runtime_root=runtime_root)


def load_python_cli_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_checkpoint_path(proposal_id, revision, runtime_root))
    return record if record and _valid_sealed(record, "checkpoint_digest") else {}


def public_python_cli_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "ok": bool(record.get("ok")), "status": str(record.get("status") or ""),
        "proposal_id": str(record.get("proposal_id") or ""), "proposal_revision": int(record.get("proposal_revision") or 0),
        "checkpoint_digest": str(record.get("checkpoint_digest") or ""), "stage_count": int(record.get("stage_count") or 0),
        "stage_lineage_digest": str(record.get("stage_lineage_digest") or ""), "stage_receipts": list(record.get("stage_receipts") or []),
        "change_summary": dict(record.get("change_summary") or {}), "test_summary": dict(record.get("test_summary") or {}),
        "working_result_available": bool(record.get("working_result_available")), "operator_review_required": True,
        "private_request_exposed": False, "private_path_exposed": False, "private_content_exposed": False,
        "raw_provider_output_exposed": False, "selected_project_modified": False, "source_modified": False,
        "implementation_applied": False, "dependencies_installed": False, "network_allowed": False,
        "repair_authorized": False, "apply_authorized": False,
        "release_authorized": False, "authority_granted": False,
    }
