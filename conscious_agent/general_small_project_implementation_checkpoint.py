from __future__ import annotations

"""v1205.9 general small-project implementation checkpoint.

Seals the exact proposal revision, exactly-once approval, grounded plan,
capability-registry owner, durable general coordinator journal, delegated
implementation result, and authority boundary into one immutable content-free
checkpoint. It grants no apply, repair, release, model-management, or
independent authority.

The checkpoint also records the v1205.9 ordinary-chat command-distinction audit
outcome. That audit is intentionally incomplete: direct development imperatives
and non-action conversational forms are handled, but a mixed conversational and
action turn is not split into a conversational response plus one proposal.
"""

from pathlib import Path
from typing import Any, Mapping

from general_small_project_implementation import _coordination_path, _valid_coordination
from grounded_development_planning import load_grounded_plan
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
from small_project_capability_registry import (
    capability_for_project_kind,
    list_small_project_capabilities,
    registry_digest,
    validate_registry,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1205.9"
STAGES = (
    "proposal_revision",
    "exact_approval",
    "grounded_planning",
    "capability_registry",
    "general_coordinator",
    "delegated_implementation",
    "authority_boundary",
)
AUDIT_STATUS = "incomplete_deferred"
AUDIT_DEFICIENCY_CODE = "mixed_turn_whole_message_classification_drops_embedded_action_clause"
AUDIT_NEXT_BUNDLE = "v1206.0-v1206.2 Natural Conversation and Command Distinction"


def _checkpoint_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "general-small-project-checkpoints" / proposal_id / f"revision-{int(revision)}.json"


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


def _validate_existing(record: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any]:
    if not _valid(record):
        return {"ok": False, "status": "general_small_project_checkpoint_invalid"}
    if any(record.get(key) != value for key, value in bindings.items()):
        return {"ok": False, "status": "stale_general_small_project_checkpoint"}
    rows = list(record.get("stage_receipts") or [])
    if len(rows) != len(STAGES) or any(not _stage_valid(row, index) for index, row in enumerate(rows, 1)):
        return {"ok": False, "status": "general_small_project_checkpoint_lineage_invalid"}
    if record.get("stage_lineage_digest") != _digest(rows):
        return {"ok": False, "status": "general_small_project_checkpoint_lineage_invalid"}
    if record.get("conversation_command_distinction_audit_status") != AUDIT_STATUS:
        return {"ok": False, "status": "general_small_project_checkpoint_audit_invalid"}
    if record.get("conversation_command_distinction_deficiency_code") != AUDIT_DEFICIENCY_CODE:
        return {"ok": False, "status": "general_small_project_checkpoint_audit_invalid"}
    return {**record, "operation_status": "resumed"}


def seal_or_resume_general_small_project_implementation_checkpoint(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_unified_result_digest: str,
    expected_coordination_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    path = _checkpoint_path(proposal_id, expected_revision, runtime_root)
    bindings = {
        "proposal_id": str(proposal_id),
        "revision": int(expected_revision),
        "proposal_revision_digest": str(expected_revision_digest),
        "unified_result_digest": str(expected_unified_result_digest),
        "coordination_digest": str(expected_coordination_digest),
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

        registry = list_small_project_capabilities()
        registry_value = str(registry.get("registry_digest") or "")
        if not validate_registry(registry.get("capabilities") or []) or registry_value != registry_digest():
            return {"ok": False, "status": "small_project_capability_registry_invalid"}
        project_kind = str(plan.get("project_kind") or "")
        capability = capability_for_project_kind(project_kind)
        if capability is None:
            return {"ok": False, "status": "unsupported_small_project_kind"}

        coordination = _read_json(_coordination_path(proposal_id, expected_revision, runtime_root))
        if not coordination or not _valid_coordination(coordination):
            return {"ok": False, "status": "general_coordinator_record_invalid"}
        if coordination.get("phase") != "sealed":
            return {"ok": False, "status": "general_coordinator_not_sealed"}
        if coordination.get("proposal_id") != proposal_id or coordination.get("revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_general_coordinator_binding"}
        if coordination.get("planning_digest") != planning_digest:
            return {"ok": False, "status": "stale_general_coordinator_binding"}
        if coordination.get("capability_registry_digest") != registry_value:
            return {"ok": False, "status": "stale_general_coordinator_binding"}
        if coordination.get("capability_id") != capability.capability_id or coordination.get("project_kind") != project_kind:
            return {"ok": False, "status": "stale_general_coordinator_binding"}
        if coordination.get("coordination_digest") != expected_coordination_digest:
            return {"ok": False, "status": "stale_general_small_project_checkpoint"}

        result = coordination.get("result")
        if not isinstance(result, dict) or coordination.get("result_digest") != _digest(result):
            return {"ok": False, "status": "general_coordinator_result_invalid"}
        if result.get("unified_result_digest") != expected_unified_result_digest:
            return {"ok": False, "status": "stale_general_small_project_checkpoint"}
        if result.get("capability_id") != capability.capability_id or result.get("project_kind") != project_kind:
            return {"ok": False, "status": "general_coordinator_result_invalid"}
        if result.get("ok") is not True:
            return {"ok": False, "status": "successful_general_small_project_result_required"}

        authority = {
            "operator_review_required": True,
            "apply_authorized": False,
            "repair_authorized": False,
            "release_authorized": False,
            "model_management_authorized": False,
            "source_modification_authorized": False,
            "independent_authority_granted": False,
        }
        authority_digest = _digest(authority)
        rows = [
            _stage(1, STAGES[0], "exact_revision_verified", expected_revision_digest),
            _stage(2, STAGES[1], "approval_consumed_once", approval_digest),
            _stage(3, STAGES[2], "grounded_plan_verified", planning_digest),
            _stage(4, STAGES[3], "capability_owner_verified", registry_value),
            _stage(5, STAGES[4], "coordinator_sealed", expected_coordination_digest),
            _stage(6, STAGES[5], "implementation_result_verified", expected_unified_result_digest),
            _stage(7, STAGES[6], "operator_review_boundary_preserved", authority_digest),
        ]
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            **bindings,
            "request_digest": str(proposal.get("request_digest") or ""),
            "target_digest": str((proposal.get("target") or {}).get("target_digest") or ""),
            "approval_receipt_digest": approval_digest,
            "planning_digest": planning_digest,
            "project_snapshot_digest": str(plan.get("project_snapshot_digest") or ""),
            "project_kind": project_kind,
            "capability_id": capability.capability_id,
            "capability_registry_digest": registry_value,
            "delegate_result_digest": str(coordination.get("result_digest") or ""),
            "implementation_status": str(result.get("status") or ""),
            "stage_count": len(rows),
            "stage_receipts": rows,
            "stage_lineage_digest": _digest(rows),
            "conversation_command_distinction_audit_status": AUDIT_STATUS,
            "conversation_command_distinction_deficiency_code": AUDIT_DEFICIENCY_CODE,
            "conversation_command_distinction_next_bundle": AUDIT_NEXT_BUNDLE,
            "ordinary_chat_path_tested": True,
            "mixed_turn_separate_proposal_supported": False,
            "provider_contacted": bool(result.get("provider_contacted")),
            "selected_project_modified": False,
            "source_modified": False,
            "implementation_applied": False,
            **authority,
            "private_request_included": False,
            "private_path_included": False,
            "private_content_included": False,
            "raw_provider_output_included": False,
            "content_free": True,
            "status": "general_small_project_implementation_checkpoint_ready_with_conversation_distinction_deferral",
            "ok": True,
        }
        record["checkpoint_digest"] = _digest(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def load_general_small_project_implementation_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_checkpoint_path(proposal_id, revision, runtime_root))
    return record if record and _valid(record) else {}


def public_general_small_project_implementation_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = (
        "ok", "status", "contract_version", "proposal_id", "revision", "proposal_revision_digest",
        "approval_receipt_digest", "planning_digest", "project_snapshot_digest", "project_kind",
        "capability_id", "capability_registry_digest", "coordination_digest", "unified_result_digest",
        "delegate_result_digest", "implementation_status", "stage_count", "stage_receipts",
        "stage_lineage_digest", "checkpoint_digest", "conversation_command_distinction_audit_status",
        "conversation_command_distinction_deficiency_code", "conversation_command_distinction_next_bundle",
        "ordinary_chat_path_tested", "mixed_turn_separate_proposal_supported", "provider_contacted",
        "selected_project_modified", "source_modified", "implementation_applied", "operator_review_required",
        "apply_authorized", "repair_authorized", "release_authorized", "model_management_authorized",
        "source_modification_authorized", "independent_authority_granted", "content_free",
    )
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
    })
    return public
