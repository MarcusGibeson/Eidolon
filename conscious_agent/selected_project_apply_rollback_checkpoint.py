from __future__ import annotations

"""v1204.9 selected-project apply and rollback checkpoint.

Seals the exact retained implementation, selected-project snapshot, apply request,
second authorization, rollback manifest, phase journal, apply result, optional
third rollback authorization, rollback journal, and final project state into
immutable content-free checkpoints.  The checkpoint grants no additional write,
repair, release, model-management, or independent authority.
"""

from pathlib import Path
from typing import Any, Mapping

from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _proposal_path,
    _read_json,
    _store_root,
    _validate,
)
from grounded_development_planning import load_grounded_plan
from selected_project_apply import (
    _apply_journal_path,
    _authorization_path,
    _bound,
    _load_final_checkpoint,
    _project_scope_state,
    _request_path,
    _result_path,
    _rollback_authorization_path,
    _rollback_journal_path,
    _rollback_path,
    _rollback_request_path,
    _rollback_result_path,
    _valid_journal,
    _validate_manifest,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1204.9"
APPLY_STAGES = (
    "implementation_checkpoint",
    "selected_project_snapshot",
    "apply_request",
    "apply_authorization",
    "rollback_preparation",
    "apply_journal",
    "apply_result",
    "project_state",
)
ROLLBACK_STAGES = APPLY_STAGES + (
    "rollback_request",
    "rollback_authorization",
    "rollback_journal",
    "rollback_result",
    "final_project_state",
)


def _apply_checkpoint_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_apply_rollback_checkpoints" / proposal_id / f"revision-{int(revision)}-applied.json"


def _rollback_checkpoint_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "selected_project_apply_rollback_checkpoints" / proposal_id / f"revision-{int(revision)}-rolled-back.json"


def _valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("checkpoint_digest") or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != "checkpoint_digest"}))


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


def _stage_valid(row: Mapping[str, Any], expected_sequence: int, stages: tuple[str, ...]) -> bool:
    supplied = str(row.get("stage_receipt_digest") or "")
    payload = {key: value for key, value in row.items() if key != "stage_receipt_digest"}
    return bool(
        supplied
        and supplied == _digest(payload)
        and int(row.get("sequence") or 0) == expected_sequence
        and str(row.get("stage") or "") == stages[expected_sequence - 1]
        and row.get("passed") is True
        and bool(row.get("artifact_digest"))
    )


def _project_root(proposal: Mapping[str, Any]) -> Path | None:
    try:
        root = Path(str(((proposal.get("target") or {}).get("private_path") or ""))).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return root if root.is_dir() and not root.is_symlink() else None


def _generation_record(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    return _read_json(_store_root(runtime_root) / "generation" / proposal_id / f"revision-{int(revision)}.json")


def _validate_existing(record: Mapping[str, Any], *, phase: str, bindings: Mapping[str, str]) -> dict[str, Any]:
    if not _valid(record):
        return {"ok": False, "status": "selected_project_checkpoint_invalid"}
    if record.get("checkpoint_phase") != phase:
        return {"ok": False, "status": "selected_project_checkpoint_phase_invalid"}
    if any(record.get(key) != value for key, value in bindings.items()):
        return {"ok": False, "status": "stale_selected_project_checkpoint"}
    stages = ROLLBACK_STAGES if phase == "rolled_back" else APPLY_STAGES
    rows = list(record.get("stage_receipts") or [])
    if len(rows) != len(stages) or any(not _stage_valid(row, index, stages) for index, row in enumerate(rows, 1)):
        return {"ok": False, "status": "selected_project_checkpoint_lineage_invalid"}
    if record.get("stage_lineage_digest") != _digest(rows):
        return {"ok": False, "status": "selected_project_checkpoint_lineage_invalid"}
    return {**record, "operation_status": "resumed"}


def _seal_apply_locked(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_implementation_checkpoint_digest: str,
    expected_apply_request_digest: str,
    expected_apply_result_digest: str,
    runtime_root=None,
    historical_rollback_result_digest: str = "",
) -> dict[str, Any]:
    path = _apply_checkpoint_path(proposal_id, expected_revision, runtime_root)
    existing = _read_json(path)
    bindings = {
        "proposal_revision_digest": expected_revision_digest,
        "implementation_checkpoint_digest": expected_implementation_checkpoint_digest,
        "apply_request_digest": expected_apply_request_digest,
        "apply_result_digest": expected_apply_result_digest,
    }
    if existing:
        return _validate_existing(existing, phase=str(existing.get("checkpoint_phase") or ""), bindings=bindings)

    proposal = _read_json(_proposal_path(proposal_id, runtime_root))
    if not proposal or not _validate(proposal):
        return {"ok": False, "status": "proposal_missing_or_tampered"}
    if int(proposal.get("revision") or 0) != int(expected_revision) or proposal.get("revision_digest") != expected_revision_digest:
        return {"ok": False, "status": "stale_proposal_revision"}

    implementation = _load_final_checkpoint(proposal_id, expected_revision, runtime_root)
    if not implementation or implementation.get("implementation_checkpoint_digest") != expected_implementation_checkpoint_digest:
        return {"ok": False, "status": "implementation_checkpoint_missing_or_stale"}
    if implementation.get("disposition_action") != "retain" or implementation.get("workspace_retained") is not True:
        return {"ok": False, "status": "retained_result_required"}

    plan = load_grounded_plan(proposal_id, expected_revision, runtime_root=runtime_root)
    if not plan or plan.get("proposal_revision_digest") != expected_revision_digest:
        return {"ok": False, "status": "grounded_plan_missing_or_stale"}

    request = _read_json(_request_path(proposal_id, expected_revision, runtime_root))
    if not request or not _bound(request, "apply_request_digest") or request.get("apply_request_digest") != expected_apply_request_digest:
        return {"ok": False, "status": "apply_request_missing_or_stale"}
    if request.get("implementation_checkpoint_digest") != expected_implementation_checkpoint_digest:
        return {"ok": False, "status": "stale_implementation_checkpoint"}
    if request.get("project_snapshot_digest") != plan.get("project_snapshot_digest"):
        return {"ok": False, "status": "stale_project_snapshot"}

    authorization = _read_json(_authorization_path(proposal_id, expected_revision, runtime_root))
    if not authorization or not _bound(authorization, "authorization_receipt_digest"):
        return {"ok": False, "status": "apply_authorization_receipt_invalid"}
    if authorization.get("apply_request_digest") != expected_apply_request_digest or int(authorization.get("consumption_count") or 0) != 1:
        return {"ok": False, "status": "apply_authorization_binding_rejected"}

    manifest = _read_json(_rollback_path(proposal_id, expected_revision, runtime_root))
    if not _validate_manifest(manifest, expected_apply_request_digest=expected_apply_request_digest):
        return {"ok": False, "status": "rollback_manifest_missing_or_invalid"}
    if authorization.get("rollback_manifest_digest") != manifest.get("rollback_manifest_digest"):
        return {"ok": False, "status": "rollback_manifest_binding_rejected"}

    result = _read_json(_result_path(proposal_id, expected_revision, runtime_root))
    if not result or not _bound(result, "apply_result_digest") or result.get("apply_result_digest") != expected_apply_result_digest:
        return {"ok": False, "status": "apply_result_missing_or_stale"}
    if result.get("apply_request_digest") != expected_apply_request_digest:
        return {"ok": False, "status": "apply_result_binding_rejected"}
    if result.get("authorization_receipt_digest") != authorization.get("authorization_receipt_digest"):
        return {"ok": False, "status": "apply_authorization_binding_rejected"}
    if result.get("rollback_manifest_digest") != manifest.get("rollback_manifest_digest"):
        return {"ok": False, "status": "rollback_manifest_binding_rejected"}
    if int(result.get("authorization_consumption_count") or 0) != 1:
        return {"ok": False, "status": "apply_authorization_consumption_invalid"}

    journal = _read_json(_apply_journal_path(proposal_id, expected_revision, runtime_root))
    if not journal or not _valid_journal(journal):
        return {"ok": False, "status": "apply_journal_invalid"}
    if journal.get("authorization_receipt_digest") != authorization.get("authorization_receipt_digest"):
        return {"ok": False, "status": "apply_journal_binding_rejected"}
    if journal.get("result_digest") != expected_apply_result_digest:
        return {"ok": False, "status": "apply_journal_binding_rejected"}

    status = str(result.get("status") or "")
    if status in {"selected_project_apply_completed", "selected_project_apply_completed_recovered"}:
        phase = "applied"
        expected_scope = "generated"
        allowed_journal_phases = {"sealed_completed", "sealed_recovered"}
    elif status in {"transactional_apply_failed_rolled_back", "interrupted_apply_recovered_by_rollback"}:
        phase = "apply_failed_rolled_back"
        expected_scope = "original"
        allowed_journal_phases = {"sealed_failed_rolled_back", "sealed_recovered_by_rollback"}
    else:
        return {"ok": False, "status": "apply_result_not_checkpointable"}
    if journal.get("phase") not in allowed_journal_phases:
        return {"ok": False, "status": "apply_journal_phase_invalid"}

    generation = _generation_record(proposal_id, expected_revision, runtime_root)
    if not generation or generation.get("generation_digest") != request.get("generation_digest"):
        return {"ok": False, "status": "generation_record_missing_or_stale"}
    root = _project_root(proposal)
    if root is None:
        return {"ok": False, "status": "selected_project_unavailable"}
    observed_scope = _project_scope_state(root, generation, manifest)
    state_evidence_mode = "live_project_state"
    stage_project_status = f"project_state_{observed_scope}"
    if observed_scope != expected_scope:
        if phase == "applied" and observed_scope == "original" and historical_rollback_result_digest:
            historical = _read_json(_rollback_result_path(proposal_id, expected_revision, runtime_root))
            historical_request = _read_json(_rollback_request_path(proposal_id, expected_revision, runtime_root))
            historical_authorization = _read_json(_rollback_authorization_path(proposal_id, expected_revision, runtime_root))
            historical_journal = _read_json(_rollback_journal_path(proposal_id, expected_revision, runtime_root))
            if not historical or not _bound(historical, "rollback_result_digest") or historical.get("rollback_result_digest") != historical_rollback_result_digest:
                return {"ok": False, "status": "historical_rollback_result_missing_or_invalid"}
            if historical.get("apply_result_digest") != expected_apply_result_digest or historical.get("rollback_executed") is not True:
                return {"ok": False, "status": "historical_rollback_result_binding_rejected"}
            if not historical_request or not _bound(historical_request, "rollback_request_digest") or historical_request.get("rollback_request_digest") != historical.get("rollback_request_digest"):
                return {"ok": False, "status": "historical_rollback_request_missing_or_invalid"}
            if not historical_authorization or not _bound(historical_authorization, "authorization_receipt_digest") or historical_authorization.get("authorization_receipt_digest") != historical.get("authorization_receipt_digest"):
                return {"ok": False, "status": "historical_rollback_authorization_invalid"}
            if int(historical_authorization.get("consumption_count") or 0) != 1 or int(historical.get("authorization_consumption_count") or 0) != 1:
                return {"ok": False, "status": "historical_rollback_authorization_invalid"}
            if not historical_journal or not _valid_journal(historical_journal) or historical_journal.get("result_digest") != historical_rollback_result_digest:
                return {"ok": False, "status": "historical_rollback_journal_invalid"}
            observed_scope = "generated"
            state_evidence_mode = "historical_apply_and_rollback_receipts"
            stage_project_status = "project_state_generated_before_authorized_rollback"
        else:
            return {"ok": False, "status": "selected_project_checkpoint_state_conflict", "observed_scope": observed_scope}

    project_state_digest = _digest({
        "project_snapshot_digest": plan.get("project_snapshot_digest"),
        "generation_digest": generation.get("generation_digest"),
        "rollback_manifest_digest": manifest.get("rollback_manifest_digest"),
        "observed_scope": observed_scope,
        "state_evidence_mode": state_evidence_mode,
        "historical_rollback_result_digest": historical_rollback_result_digest,
    })
    stages = [
        _stage(1, "implementation_checkpoint", "retained_implementation_bound", expected_implementation_checkpoint_digest),
        _stage(2, "selected_project_snapshot", "selected_project_snapshot_bound", str(plan.get("project_snapshot_digest") or "")),
        _stage(3, "apply_request", "exact_apply_request_bound", expected_apply_request_digest),
        _stage(4, "apply_authorization", "second_authorization_consumed_exactly_once", str(authorization.get("authorization_receipt_digest") or "")),
        _stage(5, "rollback_preparation", "rollback_manifest_prepared_before_writes", str(manifest.get("rollback_manifest_digest") or "")),
        _stage(6, "apply_journal", str(journal.get("phase") or "apply_journal_bound"), str(journal.get("journal_digest") or "")),
        _stage(7, "apply_result", status, expected_apply_result_digest),
        _stage(8, "project_state", stage_project_status, project_state_digest),
    ]
    record = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "status": "selected_project_apply_checkpoint_ready" if phase == "applied" else "selected_project_apply_failed_rolled_back_checkpoint_ready",
        "checkpoint_phase": phase,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": expected_revision_digest,
        "implementation_checkpoint_digest": expected_implementation_checkpoint_digest,
        "project_snapshot_digest": plan.get("project_snapshot_digest"),
        "generation_digest": generation.get("generation_digest"),
        "workspace_digest": request.get("workspace_digest"),
        "apply_request_digest": expected_apply_request_digest,
        "apply_authorization_receipt_digest": authorization.get("authorization_receipt_digest"),
        "apply_authorization_consumption_count": 1,
        "rollback_manifest_digest": manifest.get("rollback_manifest_digest"),
        "apply_journal_digest": journal.get("journal_digest"),
        "apply_result_digest": expected_apply_result_digest,
        "project_state_digest": project_state_digest,
        "observed_project_scope": observed_scope,
        "state_evidence_mode": state_evidence_mode,
        "stage_receipts": stages,
        "stage_count": len(stages),
        "stage_lineage_digest": _digest(stages),
        "selected_project_modified": phase == "applied",
        "implementation_applied": phase == "applied",
        "rollback_prepared": True,
        "rollback_authorized": False,
        "rollback_executed": phase != "applied",
        "rollback_available": phase == "applied",
        "operator_review_required": True,
        "repair_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
    }
    record["checkpoint_digest"] = _digest(record)
    _atomic_json(path, record)
    return {**record, "operation_status": "created"}


def _seal_rollback_locked(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_implementation_checkpoint_digest: str,
    expected_apply_request_digest: str,
    expected_apply_result_digest: str,
    expected_rollback_request_digest: str,
    expected_rollback_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    path = _rollback_checkpoint_path(proposal_id, expected_revision, runtime_root)
    existing = _read_json(path)
    bindings = {
        "proposal_revision_digest": expected_revision_digest,
        "implementation_checkpoint_digest": expected_implementation_checkpoint_digest,
        "apply_request_digest": expected_apply_request_digest,
        "apply_result_digest": expected_apply_result_digest,
        "rollback_request_digest": expected_rollback_request_digest,
        "rollback_result_digest": expected_rollback_result_digest,
    }
    if existing:
        return _validate_existing(existing, phase="rolled_back", bindings=bindings)

    request = _read_json(_rollback_request_path(proposal_id, expected_revision, runtime_root))
    if not request or not _bound(request, "rollback_request_digest") or request.get("rollback_request_digest") != expected_rollback_request_digest:
        return {"ok": False, "status": "rollback_request_missing_or_stale"}
    if request.get("apply_result_digest") != expected_apply_result_digest:
        return {"ok": False, "status": "rollback_request_binding_rejected"}

    authorization = _read_json(_rollback_authorization_path(proposal_id, expected_revision, runtime_root))
    if not authorization or not _bound(authorization, "authorization_receipt_digest"):
        return {"ok": False, "status": "rollback_authorization_receipt_invalid"}
    if authorization.get("rollback_request_digest") != expected_rollback_request_digest or int(authorization.get("consumption_count") or 0) != 1:
        return {"ok": False, "status": "rollback_authorization_binding_rejected"}

    result = _read_json(_rollback_result_path(proposal_id, expected_revision, runtime_root))
    if not result or not _bound(result, "rollback_result_digest") or result.get("rollback_result_digest") != expected_rollback_result_digest:
        return {"ok": False, "status": "rollback_result_missing_or_stale"}
    if result.get("rollback_request_digest") != expected_rollback_request_digest or result.get("apply_result_digest") != expected_apply_result_digest:
        return {"ok": False, "status": "rollback_result_binding_rejected"}
    if result.get("authorization_receipt_digest") != authorization.get("authorization_receipt_digest"):
        return {"ok": False, "status": "rollback_authorization_binding_rejected"}
    if int(result.get("authorization_consumption_count") or 0) != 1 or result.get("rollback_executed") is not True:
        return {"ok": False, "status": "rollback_authorization_consumption_invalid"}

    journal = _read_json(_rollback_journal_path(proposal_id, expected_revision, runtime_root))
    if not journal or not _valid_journal(journal):
        return {"ok": False, "status": "rollback_journal_invalid"}
    if journal.get("authorization_receipt_digest") != authorization.get("authorization_receipt_digest"):
        return {"ok": False, "status": "rollback_journal_binding_rejected"}
    if journal.get("result_digest") != expected_rollback_result_digest or journal.get("phase") not in {"sealed_completed", "sealed_recovered"}:
        return {"ok": False, "status": "rollback_journal_binding_rejected"}

    proposal = _read_json(_proposal_path(proposal_id, runtime_root))
    manifest = _read_json(_rollback_path(proposal_id, expected_revision, runtime_root))
    generation = _generation_record(proposal_id, expected_revision, runtime_root)
    if not proposal or not _validate(proposal) or not generation or not _validate_manifest(manifest, expected_apply_request_digest=expected_apply_request_digest):
        return {"ok": False, "status": "rollback_lineage_missing_or_invalid"}
    root = _project_root(proposal)
    if root is None:
        return {"ok": False, "status": "selected_project_unavailable"}
    observed_scope = _project_scope_state(root, generation, manifest)
    if observed_scope != "original":
        return {"ok": False, "status": "selected_project_checkpoint_state_conflict", "observed_scope": observed_scope}

    applied = _seal_apply_locked(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        expected_implementation_checkpoint_digest=expected_implementation_checkpoint_digest,
        expected_apply_request_digest=expected_apply_request_digest,
        expected_apply_result_digest=expected_apply_result_digest,
        runtime_root=runtime_root,
        historical_rollback_result_digest=expected_rollback_result_digest,
    )
    if not applied.get("checkpoint_digest"):
        return applied
    if applied.get("checkpoint_phase") != "applied":
        return {"ok": False, "status": "successful_apply_checkpoint_required"}

    final_state_digest = _digest({
        "apply_checkpoint_digest": applied.get("checkpoint_digest"),
        "rollback_result_digest": expected_rollback_result_digest,
        "rollback_manifest_digest": manifest.get("rollback_manifest_digest"),
        "observed_scope": observed_scope,
    })
    stages = list(applied.get("stage_receipts") or []) + [
        _stage(9, "rollback_request", "exact_rollback_request_bound", expected_rollback_request_digest),
        _stage(10, "rollback_authorization", "third_authorization_consumed_exactly_once", str(authorization.get("authorization_receipt_digest") or "")),
        _stage(11, "rollback_journal", str(journal.get("phase") or "rollback_journal_bound"), str(journal.get("journal_digest") or "")),
        _stage(12, "rollback_result", str(result.get("status") or "selected_project_rollback_completed"), expected_rollback_result_digest),
        _stage(13, "final_project_state", "project_state_original", final_state_digest),
    ]
    record = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "status": "selected_project_apply_rollback_checkpoint_ready",
        "checkpoint_phase": "rolled_back",
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": expected_revision_digest,
        "implementation_checkpoint_digest": expected_implementation_checkpoint_digest,
        "apply_checkpoint_digest": applied.get("checkpoint_digest"),
        "project_snapshot_digest": applied.get("project_snapshot_digest"),
        "generation_digest": applied.get("generation_digest"),
        "workspace_digest": applied.get("workspace_digest"),
        "apply_request_digest": expected_apply_request_digest,
        "apply_authorization_receipt_digest": applied.get("apply_authorization_receipt_digest"),
        "apply_authorization_consumption_count": 1,
        "rollback_manifest_digest": applied.get("rollback_manifest_digest"),
        "apply_journal_digest": applied.get("apply_journal_digest"),
        "apply_result_digest": expected_apply_result_digest,
        "rollback_request_digest": expected_rollback_request_digest,
        "rollback_authorization_receipt_digest": authorization.get("authorization_receipt_digest"),
        "rollback_authorization_consumption_count": 1,
        "rollback_journal_digest": journal.get("journal_digest"),
        "rollback_result_digest": expected_rollback_result_digest,
        "project_state_digest": final_state_digest,
        "observed_project_scope": observed_scope,
        "stage_receipts": stages,
        "stage_count": len(stages),
        "stage_lineage_digest": _digest(stages),
        "selected_project_modified": False,
        "implementation_applied": False,
        "rollback_prepared": True,
        "rollback_authorized": True,
        "rollback_executed": True,
        "rollback_available": False,
        "operator_review_required": True,
        "repair_authorized": False,
        "release_authorized": False,
        "authority_granted": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
    }
    record["checkpoint_digest"] = _digest(record)
    _atomic_json(path, record)
    return {**record, "operation_status": "created"}


def seal_or_resume_selected_project_apply_rollback_checkpoint(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_implementation_checkpoint_digest: str,
    expected_apply_request_digest: str,
    expected_apply_result_digest: str,
    expected_rollback_request_digest: str = "",
    expected_rollback_result_digest: str = "",
    runtime_root=None,
) -> dict[str, Any]:
    """Seal or resume the current immutable selected-project checkpoint phase."""
    with _proposal_lock(proposal_id, runtime_root):
        if bool(expected_rollback_request_digest) != bool(expected_rollback_result_digest):
            return {"ok": False, "status": "complete_rollback_binding_required"}
        if expected_rollback_result_digest:
            return _seal_rollback_locked(
                proposal_id,
                expected_revision=expected_revision,
                expected_revision_digest=expected_revision_digest,
                expected_implementation_checkpoint_digest=expected_implementation_checkpoint_digest,
                expected_apply_request_digest=expected_apply_request_digest,
                expected_apply_result_digest=expected_apply_result_digest,
                expected_rollback_request_digest=expected_rollback_request_digest,
                expected_rollback_result_digest=expected_rollback_result_digest,
                runtime_root=runtime_root,
            )
        return _seal_apply_locked(
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=expected_revision_digest,
            expected_implementation_checkpoint_digest=expected_implementation_checkpoint_digest,
            expected_apply_request_digest=expected_apply_request_digest,
            expected_apply_result_digest=expected_apply_result_digest,
            runtime_root=runtime_root,
        )


def load_selected_project_apply_rollback_checkpoint(proposal_id: str, revision: int, runtime_root=None) -> dict[str, Any]:
    for path in (
        _rollback_checkpoint_path(proposal_id, revision, runtime_root),
        _apply_checkpoint_path(proposal_id, revision, runtime_root),
    ):
        record = _read_json(path)
        if record and _valid(record):
            return record
    return {}


def public_selected_project_apply_rollback_checkpoint(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "status", "checkpoint_phase", "proposal_id", "proposal_revision",
        "proposal_revision_digest", "implementation_checkpoint_digest", "apply_checkpoint_digest",
        "project_snapshot_digest", "generation_digest", "workspace_digest", "apply_request_digest",
        "apply_authorization_receipt_digest", "apply_authorization_consumption_count",
        "rollback_manifest_digest", "apply_journal_digest", "apply_result_digest",
        "rollback_request_digest", "rollback_authorization_receipt_digest",
        "rollback_authorization_consumption_count", "rollback_journal_digest", "rollback_result_digest",
        "project_state_digest", "observed_project_scope", "state_evidence_mode", "stage_receipts", "stage_count",
        "stage_lineage_digest", "selected_project_modified", "implementation_applied",
        "rollback_prepared", "rollback_authorized", "rollback_executed", "rollback_available",
        "operator_review_required", "repair_authorized", "release_authorized", "authority_granted",
        "checkpoint_digest", "operation_status",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "private_path_exposed": False,
        "private_content_exposed": False,
        "rollback_content_exposed": False,
        "authorization_phrase_exposed": False,
    })
    return public
