from __future__ import annotations

"""v1203.9 Python CLI Implementation checkpoint.

Consolidates the exact approved proposal, grounded plan, structured generation,
isolated workspace, bounded validation, project-owned tests, operator review,
and exactly-once disposition into one content-free final checkpoint.  The
checkpoint never applies files to the selected project and grants no repair,
release, model-management, or independent authority.
"""

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
from python_cli_test_execution_checkpoint import (
    load_python_cli_test_checkpoint,
    run_or_resume_python_cli_with_tests,
)
from python_cli_result_disposition import (
    _disposition_path,
    _packet_path,
    _valid as _valid_bound_record,
    create_or_resume_python_cli_review_packet,
    dispose_python_cli_result,
)
from isolated_implementation_workspace import (
    _record_path as _workspace_record_path,
    _verify_record as _verify_workspace_record,
    _workspace_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1203.9"
STAGES = (
    "proposal",
    "approval",
    "planning",
    "generation",
    "workspace",
    "validation",
    "project_tests",
    "review",
    "disposition",
)


def _path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_cli_implementation_checkpoints" / proposal_id / f"revision-{int(revision)}.json"


def _valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("implementation_checkpoint_digest") or "")
    return bool(
        supplied
        and supplied
        == _digest({key: value for key, value in record.items() if key != "implementation_checkpoint_digest"})
    )


def _stage_valid(record: Mapping[str, Any], expected_sequence: int) -> bool:
    supplied = str(record.get("stage_receipt_digest") or "")
    payload = {key: value for key, value in record.items() if key != "stage_receipt_digest"}
    return bool(
        supplied
        and supplied == _digest(payload)
        and int(record.get("sequence") or 0) == int(expected_sequence)
        and str(record.get("stage") or "") == STAGES[expected_sequence - 1]
        and record.get("passed") is True
        and bool(record.get("artifact_digest"))
    )


def _stage(sequence: int, name: str, status: str, artifact_digest: str) -> dict[str, Any]:
    row = {
        "sequence": int(sequence),
        "stage": name,
        "status": status,
        "passed": True,
        "artifact_digest": str(artifact_digest or ""),
    }
    row["stage_receipt_digest"] = _digest(row)
    return row


def _status_for(action: str) -> str:
    return {
        "retain": "python_cli_implementation_checkpoint_retained",
        "revise": "python_cli_implementation_checkpoint_revision_requested",
        "reject": "python_cli_implementation_checkpoint_rejected",
        "discard": "python_cli_implementation_checkpoint_discarded",
    }[action]


def seal_or_resume_python_cli_implementation_checkpoint(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_test_checkpoint_digest: str,
    expected_review_packet_digest: str,
    expected_disposition_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Seal one exact disposed Python CLI result into a final checkpoint."""

    with _proposal_lock(proposal_id, runtime_root):
        path = _path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing):
                return {"ok": False, "status": "python_cli_implementation_checkpoint_invalid"}
            bindings = {
                "proposal_revision_digest": expected_revision_digest,
                "test_checkpoint_digest": expected_test_checkpoint_digest,
                "review_packet_digest": expected_review_packet_digest,
                "disposition_digest": expected_disposition_digest,
            }
            if any(existing.get(key) != value for key, value in bindings.items()):
                return {"ok": False, "status": "stale_python_cli_implementation_checkpoint"}
            return {**existing, "operation_status": "resumed"}

        proposal = _read_json(_proposal_path(proposal_id, runtime_root))
        if not proposal or not _validate(proposal):
            return {"ok": False, "status": "proposal_missing_or_tampered"}
        if int(proposal.get("revision") or 0) != int(expected_revision) or proposal.get("revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if proposal.get("approval_consumed") is not True or int(proposal.get("approval_consumption_count") or 0) != 1:
            return {"ok": False, "status": "exact_consumed_approval_required"}

        approval = _read_json(_approval_path(proposal_id, expected_revision, runtime_root))
        if not approval or not _valid_approval_receipt(approval, proposal):
            return {"ok": False, "status": "approval_receipt_invalid"}

        tested = load_python_cli_test_checkpoint(proposal_id, expected_revision, runtime_root)
        if not tested:
            return {"ok": False, "status": "python_cli_test_checkpoint_missing_or_invalid"}
        if tested.get("checkpoint_digest") != expected_test_checkpoint_digest:
            return {"ok": False, "status": "stale_test_checkpoint_revision"}
        if tested.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if tested.get("approval_receipt_digest") != approval.get("receipt_digest"):
            return {"ok": False, "status": "approval_binding_rejected"}
        if tested.get("status") != "python_cli_tests_ready_for_operator_review" or tested.get("ok") is not True:
            return {"ok": False, "status": "python_cli_test_checkpoint_not_reviewable"}

        inherited_stages = list(tested.get("stage_receipts") or [])
        if len(inherited_stages) != 7 or any(not _stage_valid(row, index) for index, row in enumerate(inherited_stages, 1)):
            return {"ok": False, "status": "python_cli_stage_lineage_invalid"}
        if tested.get("stage_lineage_digest") != _digest(inherited_stages):
            return {"ok": False, "status": "python_cli_stage_lineage_invalid"}

        packet = _read_json(_packet_path(proposal_id, expected_revision, runtime_root))
        if not packet or not _valid_bound_record(packet, "review_packet_digest"):
            return {"ok": False, "status": "python_cli_review_packet_missing_or_invalid"}
        if packet.get("review_packet_digest") != expected_review_packet_digest:
            return {"ok": False, "status": "stale_review_packet"}
        if packet.get("checkpoint_digest") != expected_test_checkpoint_digest:
            return {"ok": False, "status": "stale_test_checkpoint_revision"}
        if packet.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}

        disposition = _read_json(_disposition_path(proposal_id, expected_revision, runtime_root))
        if not disposition or not _valid_bound_record(disposition, "disposition_digest"):
            return {"ok": False, "status": "python_cli_disposition_missing_or_invalid"}
        if disposition.get("disposition_digest") != expected_disposition_digest:
            return {"ok": False, "status": "stale_disposition"}
        if disposition.get("review_packet_digest") != expected_review_packet_digest:
            return {"ok": False, "status": "stale_review_packet"}
        if disposition.get("checkpoint_digest") != expected_test_checkpoint_digest:
            return {"ok": False, "status": "stale_test_checkpoint_revision"}
        if disposition.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if int(disposition.get("consumption_count") or 0) != 1:
            return {"ok": False, "status": "python_cli_disposition_consumption_invalid"}

        action = str(disposition.get("action") or "")
        if action not in {"retain", "revise", "reject", "discard"}:
            return {"ok": False, "status": "python_cli_disposition_invalid"}

        workspace_root = _workspace_root(
            proposal_id,
            expected_revision,
            str(tested.get("generation_digest") or ""),
            runtime_root,
        )
        workspace_record = _read_json(_workspace_record_path(proposal_id, expected_revision, runtime_root))
        if action == "discard":
            if workspace_root.exists() or disposition.get("workspace_discarded") is not True:
                return {"ok": False, "status": "discarded_workspace_still_present"}
        else:
            if not workspace_record or not _verify_workspace_record(workspace_record, workspace_root):
                return {"ok": False, "status": "retained_workspace_missing_or_invalid"}
            if workspace_record.get("workspace_digest") != tested.get("workspace_digest"):
                return {"ok": False, "status": "stale_workspace_revision"}
            if disposition.get("workspace_retained") is not True:
                return {"ok": False, "status": "workspace_retention_binding_rejected"}

        stages = inherited_stages + [
            _stage(8, "review", "operator_review_packet_bound", expected_review_packet_digest),
            _stage(9, "disposition", f"operator_{action}_consumed_exactly_once", expected_disposition_digest),
        ]
        record = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": _status_for(action),
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "request_digest": proposal.get("request_digest"),
            "target_digest": (proposal.get("target") or {}).get("target_digest"),
            "approval_receipt_digest": approval.get("receipt_digest"),
            "planning_digest": tested.get("planning_digest"),
            "project_snapshot_digest": tested.get("project_snapshot_digest"),
            "generation_digest": tested.get("generation_digest"),
            "workspace_digest": tested.get("workspace_digest"),
            "validation_digest": tested.get("validation_digest"),
            "project_test_execution_digest": tested.get("project_test_execution_digest"),
            "test_checkpoint_digest": expected_test_checkpoint_digest,
            "review_packet_digest": expected_review_packet_digest,
            "disposition_digest": expected_disposition_digest,
            "disposition_action": action,
            "disposition_consumption_count": 1,
            "stage_receipts": stages,
            "stage_count": len(stages),
            "stage_lineage_digest": _digest(stages),
            "change_summary": dict(tested.get("change_summary") or {}),
            "test_summary": dict(tested.get("test_summary") or {}),
            "project_test_summary": dict(tested.get("project_test_summary") or {}),
            "operator_review_complete": True,
            "operator_disposition_required": False,
            "terminal": bool(disposition.get("terminal")),
            "revision_required": bool(disposition.get("revision_required")),
            "workspace_retained": bool(disposition.get("workspace_retained")),
            "workspace_discarded": bool(disposition.get("workspace_discarded")),
            "evidence_retained": bool(disposition.get("evidence_retained")),
            "working_result_available": action != "discard",
            "selected_project_modified": False,
            "source_modified": False,
            "implementation_applied": False,
            "dependencies_installed": False,
            "network_allowed": False,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
            "private_request_included": False,
            "private_path_included": False,
            "private_content_included": False,
            "raw_provider_output_included": False,
        }
        record["implementation_checkpoint_digest"] = _digest(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def run_or_resume_python_cli_implementation_checkpoint(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    action: str = "",
    expected_review_packet_digest: str = "",
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    python_executable: str | None = None,
) -> dict[str, Any]:
    """Advance one exact Python CLI campaign to review or final disposition."""

    existing_final = load_python_cli_implementation_checkpoint(proposal_id, expected_revision, runtime_root)
    if existing_final:
        if existing_final.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if expected_review_packet_digest and expected_review_packet_digest != existing_final.get("review_packet_digest"):
            return {"ok": False, "status": "stale_review_packet", "failed_stage": "review"}
        normalized_existing_action = str(action or "").strip().lower()
        if normalized_existing_action and normalized_existing_action != existing_final.get("disposition_action"):
            return {
                "ok": False,
                "status": "python_cli_disposition_already_consumed",
                "consumed_action": existing_final.get("disposition_action"),
                "failed_stage": "disposition",
            }
        return {**existing_final, "operation_status": "resumed"}

    tested = run_or_resume_python_cli_with_tests(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
        provider_generate=provider_generate,
        python_executable=python_executable,
    )
    if not tested.get("checkpoint_digest"):
        return {**tested, "failed_stage": tested.get("failed_stage", "project_tests")}

    packet = create_or_resume_python_cli_review_packet(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_checkpoint_digest=str(tested.get("checkpoint_digest") or ""),
        runtime_root=runtime_root,
    )
    if not packet.get("review_packet_digest"):
        return {**packet, "failed_stage": "review"}

    normalized_action = str(action or "").strip().lower()
    if not normalized_action:
        return {
            "ok": True,
            "status": "python_cli_implementation_checkpoint_awaiting_disposition",
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "test_checkpoint_digest": tested.get("checkpoint_digest"),
            "review_packet_digest": packet.get("review_packet_digest"),
            "stage_count": 8,
            "operator_disposition_required": True,
            "selected_project_modified": False,
            "implementation_applied": False,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
        }
    if expected_review_packet_digest and packet.get("review_packet_digest") != expected_review_packet_digest:
        return {"ok": False, "status": "stale_review_packet", "failed_stage": "disposition"}

    disposition = dispose_python_cli_result(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_checkpoint_digest=str(tested.get("checkpoint_digest") or ""),
        expected_review_packet_digest=str(packet.get("review_packet_digest") or ""),
        action=normalized_action,
        runtime_root=runtime_root,
    )
    if not disposition.get("disposition_digest"):
        return {**disposition, "failed_stage": "disposition"}

    return seal_or_resume_python_cli_implementation_checkpoint(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_test_checkpoint_digest=str(tested.get("checkpoint_digest") or ""),
        expected_review_packet_digest=str(packet.get("review_packet_digest") or ""),
        expected_disposition_digest=str(disposition.get("disposition_digest") or ""),
        runtime_root=runtime_root,
    )


def load_python_cli_implementation_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_path(proposal_id, revision, runtime_root))
    return record if record and _valid(record) else {}


def public_python_cli_implementation_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "proposal_revision": int(record.get("proposal_revision") or 0),
        "implementation_checkpoint_digest": str(record.get("implementation_checkpoint_digest") or ""),
        "test_checkpoint_digest": str(record.get("test_checkpoint_digest") or ""),
        "review_packet_digest": str(record.get("review_packet_digest") or ""),
        "disposition_digest": str(record.get("disposition_digest") or ""),
        "disposition_action": str(record.get("disposition_action") or ""),
        "disposition_consumption_count": int(record.get("disposition_consumption_count") or 0),
        "stage_count": int(record.get("stage_count") or 0),
        "stage_lineage_digest": str(record.get("stage_lineage_digest") or ""),
        "stage_receipts": list(record.get("stage_receipts") or []),
        "change_summary": dict(record.get("change_summary") or {}),
        "test_summary": dict(record.get("test_summary") or {}),
        "project_test_summary": dict(record.get("project_test_summary") or {}),
        "operator_review_complete": bool(record.get("operator_review_complete")),
        "operator_disposition_required": False,
        "terminal": bool(record.get("terminal")),
        "revision_required": bool(record.get("revision_required")),
        "workspace_retained": bool(record.get("workspace_retained")),
        "workspace_discarded": bool(record.get("workspace_discarded")),
        "evidence_retained": bool(record.get("evidence_retained")),
        "working_result_available": bool(record.get("working_result_available")),
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "implementation_applied": False,
        "dependencies_installed": False,
        "network_allowed": False,
        "repair_authorized": False,
        "apply_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
