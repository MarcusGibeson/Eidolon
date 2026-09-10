from __future__ import annotations

"""v1201.9 supervised small-website implementation checkpoint.

This module consolidates the already-governed ordinary-chat proposal, exact
approval, grounded plan, structured provider generation, isolated workspace,
browser preview, and bounded validation stages into one resumable operation.
It never applies files to the selected project or Eidolon source and grants no
model, release, repair, or independent authority.
"""

from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping

from ordinary_chat_development_campaign import (
    _approval_path,
    _atomic_json,
    _digest,
    _proposal_lock,
    _proposal_path,
    _read_json,
    _store_root,
    _valid_approval_receipt,
    _validate,
)
from grounded_development_planning import (
    _planning_path,
    _valid_plan,
    create_or_resume_grounded_plan,
)
from structured_development_generation import (
    _path as _generation_path,
    generate_or_resume_structured_output,
)
from isolated_implementation_workspace import (
    _record_path as _workspace_record_path,
    _verify_record as _verify_workspace_record,
    _workspace_root,
    materialize_or_resume_workspace,
)
from isolated_workspace_preview import (
    _preview_path,
    create_or_resume_workspace_preview,
)
from bounded_workspace_validation import (
    _record_valid as _validation_record_valid,
    _validation_path,
    validate_or_resume_workspace,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1201.9"
SUPPORTED_PROJECT_KINDS = frozenset({
    "new_small_web_project",
    "static_web_project",
    "javascript_or_web_project",
    "empty_project",
})
STAGE_ORDER = (
    "proposal",
    "approval",
    "planning",
    "generation",
    "workspace",
    "preview",
    "validation",
)


def _checkpoint_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "implementation_checkpoints" / proposal_id / f"revision-{int(revision)}.json"


def _valid_sealed(record: Mapping[str, Any], digest_field: str) -> bool:
    supplied = str(record.get(digest_field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != digest_field}))


def _stage(stage: str, status: str, artifact_digest: str, *, passed: bool = True) -> dict[str, Any]:
    row = {
        "sequence": STAGE_ORDER.index(stage) + 1,
        "stage": stage,
        "status": status,
        "passed": bool(passed),
        "artifact_digest": str(artifact_digest or ""),
    }
    row["stage_receipt_digest"] = _digest(row)
    return row


def _load_and_validate_lineage(
    proposal_id: str,
    revision: int,
    revision_digest: str,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
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
    if not plan or not _valid_plan(plan):
        return None, {"ok": False, "status": "grounded_plan_missing_or_invalid"}
    if plan.get("proposal_revision_digest") != revision_digest:
        return None, {"ok": False, "status": "planning_binding_rejected"}
    if plan.get("planning_status") != "grounded_plan_ready" or plan.get("project_kind") not in SUPPORTED_PROJECT_KINDS:
        return None, {"ok": False, "status": "small_website_scope_required"}
    if plan.get("approval_receipt_digest") != approval.get("receipt_digest"):
        return None, {"ok": False, "status": "planning_approval_binding_rejected"}

    generation = _read_json(_generation_path(proposal_id, revision, runtime_root))
    if not generation or not _valid_sealed(generation, "generation_digest"):
        return None, {"ok": False, "status": "generation_missing_or_invalid"}
    expected_generation = {
        "proposal_revision_digest": revision_digest,
        "planning_digest": plan.get("planning_digest"),
        "project_snapshot_digest": plan.get("project_snapshot_digest"),
        "approval_receipt_digest": approval.get("receipt_digest"),
    }
    if any(generation.get(key) != value for key, value in expected_generation.items()):
        return None, {"ok": False, "status": "generation_binding_rejected"}

    workspace = _read_json(_workspace_record_path(proposal_id, revision, runtime_root))
    if not workspace:
        return None, {"ok": False, "status": "workspace_missing"}
    workspace_root = _workspace_root(proposal_id, revision, str(generation.get("generation_digest") or ""), runtime_root)
    if not _verify_workspace_record(workspace, workspace_root):
        return None, {"ok": False, "status": "workspace_record_invalid"}
    expected_workspace = {
        "proposal_revision_digest": revision_digest,
        "planning_digest": plan.get("planning_digest"),
        "generation_digest": generation.get("generation_digest"),
        "project_snapshot_digest": plan.get("project_snapshot_digest"),
        "approval_receipt_digest": approval.get("receipt_digest"),
    }
    if any(workspace.get(key) != value for key, value in expected_workspace.items()):
        return None, {"ok": False, "status": "workspace_binding_rejected"}

    preview = _read_json(_preview_path(proposal_id, revision, runtime_root))
    if not preview or not _valid_sealed(preview, "preview_digest"):
        return None, {"ok": False, "status": "preview_missing_or_invalid"}
    if preview.get("proposal_revision_digest") != revision_digest or preview.get("workspace_digest") != workspace.get("workspace_digest"):
        return None, {"ok": False, "status": "preview_binding_rejected"}

    validation = _read_json(_validation_path(proposal_id, revision, runtime_root))
    if not validation or not _validation_record_valid(validation):
        return None, {"ok": False, "status": "validation_missing_or_invalid"}
    expected_validation = {
        "proposal_revision_digest": revision_digest,
        "planning_digest": plan.get("planning_digest"),
        "generation_digest": generation.get("generation_digest"),
        "workspace_digest": workspace.get("workspace_digest"),
        "preview_digest": preview.get("preview_digest"),
        "approval_receipt_digest": approval.get("receipt_digest"),
    }
    if any(validation.get(key) != value for key, value in expected_validation.items()):
        return None, {"ok": False, "status": "validation_binding_rejected"}
    if validation.get("passed") is not True or validation.get("status") != "workspace_validation_passed":
        return None, {
            "ok": False,
            "status": "validation_not_passed",
            "validation_digest": validation.get("validation_digest", ""),
            "repair_authorized": False,
        }

    return {
        "proposal": proposal,
        "approval": approval,
        "plan": plan,
        "generation": generation,
        "workspace": workspace,
        "preview": preview,
        "validation": validation,
    }, {}


def create_or_resume_small_website_checkpoint(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        lineage, error = _load_and_validate_lineage(
            proposal_id,
            expected_revision,
            expected_revision_digest,
            runtime_root,
        )
        if lineage is None:
            return error

        path = _checkpoint_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            expected_bindings = {
                "proposal_revision_digest": expected_revision_digest,
                "approval_receipt_digest": lineage["approval"].get("receipt_digest"),
                "planning_digest": lineage["plan"].get("planning_digest"),
                "generation_digest": lineage["generation"].get("generation_digest"),
                "workspace_digest": lineage["workspace"].get("workspace_digest"),
                "preview_digest": lineage["preview"].get("preview_digest"),
                "validation_digest": lineage["validation"].get("validation_digest"),
            }
            valid = _valid_sealed(existing, "checkpoint_digest") and all(existing.get(key) == value for key, value in expected_bindings.items())
            return ({**existing, "operation_status": "resumed"} if valid else {"ok": False, "status": "implementation_checkpoint_invalid"})

        generation = lineage["generation"]
        operations = Counter(str(row.get("operation") or "") for row in generation.get("files") or [])
        stages = [
            _stage("proposal", "approved_revision_bound", lineage["proposal"].get("proposal_digest", "")),
            _stage("approval", "consumed_exactly_once", lineage["approval"].get("receipt_digest", "")),
            _stage("planning", "grounded_plan_ready", lineage["plan"].get("planning_digest", "")),
            _stage("generation", "validated_generation_ready", generation.get("generation_digest", "")),
            _stage("workspace", "isolated_workspace_ready", lineage["workspace"].get("workspace_digest", "")),
            _stage("preview", "browser_preview_ready", lineage["preview"].get("preview_digest", "")),
            _stage("validation", "workspace_validation_passed", lineage["validation"].get("validation_digest", "")),
        ]
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "small_website_implementation_ready_for_operator_review",
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "request_digest": lineage["proposal"].get("request_digest"),
            "target_digest": (lineage["proposal"].get("target") or {}).get("target_digest"),
            "approval_receipt_digest": lineage["approval"].get("receipt_digest"),
            "planning_digest": lineage["plan"].get("planning_digest"),
            "project_snapshot_digest": lineage["plan"].get("project_snapshot_digest"),
            "generation_digest": generation.get("generation_digest"),
            "workspace_digest": lineage["workspace"].get("workspace_digest"),
            "preview_digest": lineage["preview"].get("preview_digest"),
            "preview_url": lineage["preview"].get("preview_url", ""),
            "validation_digest": lineage["validation"].get("validation_digest"),
            "stage_receipts": stages,
            "stage_count": len(stages),
            "stage_lineage_digest": _digest(stages),
            "change_summary": {
                "file_count": int(generation.get("file_count") or 0),
                "total_bytes": int(generation.get("total_bytes") or 0),
                "create_count": int(operations.get("create", 0)),
                "modify_count": int(operations.get("modify", 0)),
                "delete_count": int(operations.get("delete", 0)),
                "path_digests": [str(row.get("relative_path_digest") or "") for row in generation.get("files") or []],
                "content_digests": [str(row.get("content_digest") or "") for row in generation.get("files") or []],
                "syntax_kinds": [str(row.get("syntax") or "") for row in generation.get("files") or []],
            },
            "test_summary": {
                "passed": True,
                "adapter_count": int(lineage["validation"].get("adapter_count") or 0),
                "command_count": int(lineage["validation"].get("command_count") or 0),
                "adapter_statuses": [
                    {
                        "adapter": str(adapter.get("adapter") or ""),
                        "status": str(adapter.get("status") or ""),
                        "passed": bool(adapter.get("passed")),
                    }
                    for adapter in lineage["validation"].get("adapters") or []
                ],
            },
            "operator_review_required": True,
            "working_result_available": True,
            "selected_project_modified": False,
            "source_modified": False,
            "implementation_applied": False,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
            "private_request_included": False,
            "private_path_included": False,
            "private_content_included": False,
            "raw_provider_output_included": False,
        }
        record["checkpoint_digest"] = _digest(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def run_or_resume_small_website_implementation(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    node_executable: str | None = None,
) -> dict[str, Any]:
    """Advance one exact approved revision through all bounded stages.

    Every individual stage owns its lock and durable record. Re-running after a
    crash resumes the valid prefix and cannot consume approval or provider output
    twice. Failure returns content-free stage status and never auto-repairs.
    """
    plan = create_or_resume_grounded_plan(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
    )
    if not plan.get("planning_digest"):
        return {"ok": False, "status": plan.get("status", "planning_failed"), "failed_stage": "planning"}

    generation = generate_or_resume_structured_output(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_planning_digest=str(plan.get("planning_digest") or ""),
        runtime_root=runtime_root,
        provider_generate=provider_generate,
    )
    if not generation.get("generation_digest"):
        return {
            "ok": False,
            "status": generation.get("status", "generation_failed"),
            "failed_stage": "generation",
            "provider_contacted": bool(generation.get("provider_contacted")),
            "reason": generation.get("reason", ""),
        }

    workspace = materialize_or_resume_workspace(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_planning_digest=str(plan.get("planning_digest") or ""),
        expected_generation_digest=str(generation.get("generation_digest") or ""),
        runtime_root=runtime_root,
    )
    if not workspace.get("workspace_digest"):
        return {"ok": False, "status": workspace.get("status", "materialization_failed"), "failed_stage": "workspace"}

    preview = create_or_resume_workspace_preview(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
    )
    if not preview.get("preview_digest"):
        return {"ok": False, "status": preview.get("status", "preview_failed"), "failed_stage": "preview"}

    validation = validate_or_resume_workspace(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_workspace_digest=str(workspace.get("workspace_digest") or ""),
        expected_preview_digest=str(preview.get("preview_digest") or ""),
        runtime_root=runtime_root,
        node_executable=node_executable,
    )
    if not validation.get("validation_digest"):
        return {"ok": False, "status": validation.get("status", "validation_failed"), "failed_stage": "validation"}
    if validation.get("passed") is not True:
        return {
            "ok": False,
            "status": "validation_not_passed",
            "failed_stage": "validation",
            "validation_digest": validation.get("validation_digest", ""),
            "repair_authorized": False,
        }

    checkpoint = create_or_resume_small_website_checkpoint(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
    )
    return checkpoint


def load_small_website_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_checkpoint_path(proposal_id, revision, runtime_root))
    if not record:
        return {}
    return record if _valid_sealed(record, "checkpoint_digest") else {"ok": False, "status": "implementation_checkpoint_invalid"}


def public_small_website_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "proposal_revision": int(record.get("proposal_revision") or 0),
        "proposal_revision_digest": str(record.get("proposal_revision_digest") or ""),
        "checkpoint_digest": str(record.get("checkpoint_digest") or ""),
        "stage_count": int(record.get("stage_count") or 0),
        "stage_lineage_digest": str(record.get("stage_lineage_digest") or ""),
        "stage_receipts": list(record.get("stage_receipts") or []),
        "change_summary": dict(record.get("change_summary") or {}),
        "test_summary": dict(record.get("test_summary") or {}),
        "preview_url": str(record.get("preview_url") or ""),
        "working_result_available": bool(record.get("working_result_available")),
        "operator_review_required": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "implementation_applied": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
