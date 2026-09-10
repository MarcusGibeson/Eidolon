from __future__ import annotations
"""v1203.6-v1203.8 operator review and disposition for Python CLI results."""
import shutil
from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import _atomic_json, _digest, _proposal_lock, _read_json, _store_root
from python_cli_test_execution_checkpoint import load_python_cli_test_checkpoint
from isolated_implementation_workspace import _workspace_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1203.8"
ACTIONS = {"retain", "revise", "reject", "discard"}


def _packet_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_cli_review_packets" / proposal_id / f"revision-{int(revision)}.json"


def _disposition_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "python_cli_dispositions" / proposal_id / f"revision-{int(revision)}.json"


def _valid(record: Mapping[str, Any], digest_key: str) -> bool:
    supplied = str(record.get(digest_key) or "")
    return bool(supplied and supplied == _digest({k: v for k, v in record.items() if k != digest_key}))


def create_or_resume_python_cli_review_packet(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_checkpoint_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    with _proposal_lock(proposal_id, runtime_root):
        checkpoint = load_python_cli_test_checkpoint(proposal_id, expected_revision, runtime_root)
        if not checkpoint:
            return {"ok": False, "status": "python_cli_checkpoint_missing"}
        if checkpoint.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if checkpoint.get("checkpoint_digest") != expected_checkpoint_digest:
            return {"ok": False, "status": "stale_checkpoint_revision"}
        if checkpoint.get("ok") is not True or checkpoint.get("status") != "python_cli_tests_ready_for_operator_review":
            return {"ok": False, "status": "python_cli_result_not_reviewable"}

        path = _packet_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "review_packet_digest"):
                return {"ok": False, "status": "python_cli_review_packet_invalid"}
            if existing.get("checkpoint_digest") != expected_checkpoint_digest:
                return {"ok": False, "status": "stale_review_packet"}
            return {**existing, "operation_status": "resumed"}

        packet = {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "python_cli_result_awaiting_disposition",
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": expected_revision_digest,
            "checkpoint_digest": expected_checkpoint_digest,
            "stage_lineage_digest": checkpoint.get("stage_lineage_digest"),
            "workspace_digest": checkpoint.get("workspace_digest"),
            "generation_digest": checkpoint.get("generation_digest"),
            "validation_digest": checkpoint.get("validation_digest"),
            "project_test_execution_digest": checkpoint.get("project_test_execution_digest"),
            "change_summary": dict(checkpoint.get("change_summary") or {}),
            "test_summary": dict(checkpoint.get("test_summary") or {}),
            "project_test_summary": dict(checkpoint.get("project_test_summary") or {}),
            "allowed_dispositions": sorted(ACTIONS),
            "operator_disposition_required": True,
            "selected_project_modified": False,
            "source_modified": False,
            "repair_authorized": False,
            "apply_authorized": False,
            "release_authorized": False,
            "authority_granted": False,
        }
        packet["review_packet_digest"] = _digest(packet)
        _atomic_json(path, packet)
        return {**packet, "operation_status": "created"}


def dispose_python_cli_result(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_checkpoint_digest: str,
    expected_review_packet_digest: str,
    action: str,
    runtime_root=None,
) -> dict[str, Any]:
    normalized = str(action or "").strip().lower()
    if normalized not in ACTIONS:
        return {"ok": False, "status": "unsupported_python_cli_disposition"}

    operation_status = "created"
    with _proposal_lock(proposal_id, runtime_root):
        packet = _read_json(_packet_path(proposal_id, expected_revision, runtime_root))
        if not packet or not _valid(packet, "review_packet_digest"):
            return {"ok": False, "status": "python_cli_review_packet_missing_or_invalid"}
        if packet.get("proposal_revision_digest") != expected_revision_digest:
            return {"ok": False, "status": "stale_proposal_revision"}
        if packet.get("checkpoint_digest") != expected_checkpoint_digest:
            return {"ok": False, "status": "stale_checkpoint_revision"}
        if packet.get("review_packet_digest") != expected_review_packet_digest:
            return {"ok": False, "status": "stale_review_packet"}

        path = _disposition_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "disposition_digest"):
                return {"ok": False, "status": "python_cli_disposition_invalid"}
            if existing.get("action") != normalized:
                return {"ok": False, "status": "python_cli_disposition_already_consumed", "consumed_action": existing.get("action")}
            record = existing
            operation_status = "resumed"
        else:
            checkpoint = load_python_cli_test_checkpoint(proposal_id, expected_revision, runtime_root)
            if not checkpoint or checkpoint.get("checkpoint_digest") != expected_checkpoint_digest:
                return {"ok": False, "status": "python_cli_checkpoint_missing_or_stale"}

            workspace_discarded = False
            if normalized == "discard":
                root = _workspace_root(
                    proposal_id,
                    expected_revision,
                    str(checkpoint.get("generation_digest") or ""),
                    runtime_root,
                )
                if root.exists():
                    shutil.rmtree(root)
                workspace_discarded = not root.exists()
                if not workspace_discarded:
                    return {"ok": False, "status": "python_cli_workspace_discard_failed"}

            status_by_action = {
                "retain": "python_cli_result_retained_for_review",
                "revise": "python_cli_result_revision_requested",
                "reject": "python_cli_result_rejected",
                "discard": "python_cli_result_discarded",
            }
            record = {
                "schema_version": SCHEMA_VERSION,
                "contract_version": CONTRACT_VERSION,
                "ok": True,
                "status": status_by_action[normalized],
                "proposal_id": proposal_id,
                "proposal_revision": int(expected_revision),
                "proposal_revision_digest": expected_revision_digest,
                "checkpoint_digest": expected_checkpoint_digest,
                "review_packet_digest": expected_review_packet_digest,
                "action": normalized,
                "consumption_count": 1,
                "terminal": normalized in {"reject", "discard"},
                "revision_required": normalized == "revise",
                "workspace_retained": normalized in {"retain", "revise", "reject"},
                "workspace_discarded": workspace_discarded,
                "evidence_retained": True,
                "selected_project_modified": False,
                "source_modified": False,
                "implementation_applied": False,
                "repair_authorized": False,
                "apply_authorized": False,
                "release_authorized": False,
                "authority_granted": False,
            }
            record["disposition_digest"] = _digest(record)
            _atomic_json(path, record)

    # Seal outside the proposal lock. If a process stops after the disposition
    # write but before this checkpoint write, an identical retry resumes the
    # consumed disposition and completes the checkpoint without consuming the
    # decision again.
    try:
        from python_cli_implementation_checkpoint import seal_or_resume_python_cli_implementation_checkpoint
        sealed = seal_or_resume_python_cli_implementation_checkpoint(
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=expected_revision_digest,
            expected_test_checkpoint_digest=expected_checkpoint_digest,
            expected_review_packet_digest=expected_review_packet_digest,
            expected_disposition_digest=str(record.get("disposition_digest") or ""),
            runtime_root=runtime_root,
        )
    except Exception as error:  # content-free failure receipt; disposition remains consumed once
        sealed = {"ok": False, "status": "python_cli_implementation_checkpoint_seal_failed", "error_type": type(error).__name__}

    return {
        **record,
        "operation_status": operation_status,
        "implementation_checkpoint_sealed": bool(sealed.get("implementation_checkpoint_digest")),
        "implementation_checkpoint_digest": str(sealed.get("implementation_checkpoint_digest") or ""),
        "implementation_checkpoint_status": str(sealed.get("status") or ""),
        "implementation_checkpoint_operation_status": str(sealed.get("operation_status") or ""),
    }

def load_python_cli_disposition(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_disposition_path(proposal_id, revision, runtime_root))
    return record if record and _valid(record, "disposition_digest") else {}


def public_python_cli_review_packet(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "proposal_revision": int(record.get("proposal_revision") or 0),
        "checkpoint_digest": str(record.get("checkpoint_digest") or ""),
        "review_packet_digest": str(record.get("review_packet_digest") or ""),
        "stage_lineage_digest": str(record.get("stage_lineage_digest") or ""),
        "change_summary": dict(record.get("change_summary") or {}),
        "test_summary": dict(record.get("test_summary") or {}),
        "project_test_summary": dict(record.get("project_test_summary") or {}),
        "allowed_dispositions": list(record.get("allowed_dispositions") or []),
        "operator_disposition_required": True,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "apply_authorized": False,
        "repair_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }


def public_python_cli_disposition(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "ok": bool(record.get("ok")),
        "status": str(record.get("status") or ""),
        "proposal_id": str(record.get("proposal_id") or ""),
        "proposal_revision": int(record.get("proposal_revision") or 0),
        "action": str(record.get("action") or ""),
        "disposition_digest": str(record.get("disposition_digest") or ""),
        "consumption_count": int(record.get("consumption_count") or 0),
        "terminal": bool(record.get("terminal")),
        "revision_required": bool(record.get("revision_required")),
        "workspace_retained": bool(record.get("workspace_retained")),
        "workspace_discarded": bool(record.get("workspace_discarded")),
        "evidence_retained": bool(record.get("evidence_retained")),
        "implementation_checkpoint_sealed": bool(record.get("implementation_checkpoint_sealed")),
        "implementation_checkpoint_digest": str(record.get("implementation_checkpoint_digest") or ""),
        "implementation_checkpoint_status": str(record.get("implementation_checkpoint_status") or ""),
        "operator_disposition_required": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_output_exposed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "implementation_applied": False,
        "apply_authorized": False,
        "repair_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
    }
