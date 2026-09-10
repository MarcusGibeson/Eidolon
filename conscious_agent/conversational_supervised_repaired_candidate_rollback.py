from __future__ import annotations

"""Exact, one-attempt supervised rollback of the v1217 repaired-candidate apply.

The only accepted control is the digest-bound phrase emitted by v1218.  The
operation consumes that authorization once, restores the exact pre-apply
workspace from the already-sealed private v1217 manifest, verifies the restored
inventory, and seals a content-free result for later operator review.  It does
not contact a provider, run tests, install, promote, release, manage models, or
grant independent authority.
"""

import hashlib
import re
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from conversational_supervised_repaired_candidate_apply import (
    _actual_inventory,
    _authorization_path as _apply_authorization_path,
    _record_inventory,
    _restore_manifest,
    _rollback_manifest_path,
    _sha256,
    _valid as _valid_apply_record,
    _valid_manifest,
    _workspace_descriptor,
    _workspace_matches,
    _workspace_state,
    load_supervised_repaired_candidate_apply,
)
from operator_repaired_candidate_apply_result_review import (
    _rollback_authorization_phrase,
    load_bounded_repaired_candidate_rollback_proposal,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1219.8"
ROLLBACK_LEASE_SECONDS = 180.0
ROLLBACK_RESULT_STATUSES = frozenset({
    "supervised_repaired_candidate_rollback_completed",
    "supervised_repaired_candidate_rollback_completed_recovered",
    "supervised_repaired_candidate_rollback_failed_applied_state_restored",
    "interrupted_repaired_candidate_rollback_recovered_to_applied_state",
})

_AUTHORIZATION = re.compile(
    r"^(?:i\s+)?authorize\s+repaired\s+candidate\s+rollback\s+proposal\s+"
    r"(?P<rollback_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+"
    r"(?P<revision>[1-9][0-9]*)\s+failed\s+attempt\s+"
    r"(?P<failed_attempt>[2-9][0-9]*)\s+repair\s+attempt\s+"
    r"(?P<repair_attempt>[1-9][0-9]*)\s+apply\s+attempt\s+"
    r"(?P<apply_attempt>[1-9][0-9]*)[.!?]*$",
    re.I,
)


def _execution_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (_store_root(runtime_root) / "conversational_supervised_repaired_candidate_rollbacks"
            / proposal_id / f"revision-{int(revision)}" / f"failed-attempt-{int(failed_attempt)}"
            / "repair-1-apply-1.json")


def _authorization_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (_store_root(runtime_root) / "conversational_supervised_repaired_candidate_rollback_authorizations"
            / proposal_id / f"revision-{int(revision)}" / f"failed-attempt-{int(failed_attempt)}"
            / "repair-1-apply-1.json")


def _journal_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (_store_root(runtime_root) / "conversational_supervised_repaired_candidate_rollback_journals"
            / proposal_id / f"revision-{int(revision)}" / f"failed-attempt-{int(failed_attempt)}"
            / "repair-1-apply-1.json")


def _record_digest(record: Mapping[str, Any], digest_field: str) -> str:
    return _digest({key: value for key, value in record.items()
                    if key not in {digest_field, "operation_status"}})


def _seal(record: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    row = dict(record)
    row[digest_field] = _record_digest(row, digest_field)
    return row


def _valid(record: Mapping[str, Any], digest_field: str) -> bool:
    supplied = str(record.get(digest_field) or "")
    return bool(supplied and supplied == _record_digest(record, digest_field))


def _authority(*, authorized: bool = False) -> dict[str, bool]:
    return {
        "rollback_execution_authorized": bool(authorized),
        "rollback_authorized": bool(authorized),
        "apply_execution_authorized": False,
        "apply_authorized": False,
        "repair_execution_authorized": False,
        "provider_contact_authorized": False,
        "test_execution_authorized": False,
        "retest_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }


def _base(*, proposal_id: str = "", revision: int = 0, failed_attempt: int = 0) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "failed_attempt_number": int(failed_attempt or 0),
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "rollback_attempt_number": 1,
        "rollback_attempt_limit": 1,
        "operator_review_required": True,
        "rollback_result_review_required": True,
        "runtime_records_external": True,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "rollback_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **_authority(),
    }


def _failure(status: str, *, reason: str = "", proposal_id: str = "", revision: int = 0,
             failed_attempt: int = 0) -> dict[str, Any]:
    row = {"ok": False, "status": status, "reason": reason,
           **_base(proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt)}
    row["supervised_repaired_candidate_rollback_result_digest"] = _digest(row)
    return row


def _write_journal(path: Path, **fields: Any) -> dict[str, Any]:
    row = _seal({"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION, **fields},
                "journal_digest")
    _atomic_json(path, row)
    return row


def _validated_lineage(proposal_id: str, revision: int, failed_attempt: int,
                       expected_rollback_proposal_digest: str, *, runtime_root=None):
    rollback = load_bounded_repaired_candidate_rollback_proposal(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root)
    apply_execution = load_supervised_repaired_candidate_apply(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root)
    if not rollback:
        return None, None, None, _failure("supervised_repaired_candidate_rollback_proposal_invalid",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt)
    if _sha256(rollback.get("rollback_proposal_digest")) != _sha256(expected_rollback_proposal_digest):
        return None, None, None, _failure("supervised_repaired_candidate_rollback_stale_proposal",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt)
    if (rollback.get("status") != "bounded_repaired_candidate_rollback_proposal_authorization_required"
            or rollback.get("rollback_proposal_created") is not True
            or rollback.get("rollback_authorization_required") is not True
            or rollback.get("maximum_rollback_attempts") != 1
            or rollback.get("rollback_authorized") is not False
            or rollback.get("rollback_executed") is not False):
        return None, None, None, _failure("supervised_repaired_candidate_rollback_proposal_ineligible",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt)
    result = apply_execution.get("result") if isinstance(apply_execution, Mapping) else None
    if (not apply_execution or apply_execution.get("phase") != "sealed"
            or not isinstance(result, Mapping)
            or apply_execution.get("result_digest") != _digest(result)
            or result.get("status") not in {"supervised_repaired_candidate_apply_completed",
                                            "supervised_repaired_candidate_apply_completed_recovered"}
            or result.get("rollback_available") is not True
            or result.get("rollback_executed") is not False
            or result.get("selected_project_modified") is not True):
        return None, None, None, _failure("supervised_repaired_candidate_rollback_apply_result_invalid",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt)
    for key in ("supervised_repaired_candidate_apply_digest",
                "supervised_repaired_candidate_apply_result_digest", "apply_proposal_digest",
                "source_workspace_digest", "repair_workspace_digest", "apply_plan_digest",
                "authorization_receipt_digest", "rollback_manifest_digest"):
        if _sha256(rollback.get(key)) != _sha256(result.get(key)):
            return None, None, None, _failure("supervised_repaired_candidate_rollback_binding_changed",
                reason=key, proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt)
    manifest = _read_json(_rollback_manifest_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    apply_auth = _read_json(_apply_authorization_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    if (not _valid_manifest(manifest, apply_execution)
            or manifest.get("rollback_manifest_digest") != rollback.get("rollback_manifest_digest")
            or not _valid_apply_record(apply_auth, "authorization_receipt_digest")
            or apply_auth.get("authorization_receipt_digest") != rollback.get("authorization_receipt_digest")
            or int(apply_auth.get("consumption_count") or 0) != 1):
        return None, None, None, _failure("supervised_repaired_candidate_rollback_private_evidence_invalid",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt)
    return dict(rollback), dict(apply_execution), dict(manifest), None


def prepare_supervised_repaired_candidate_rollback(proposal_id: str, *, expected_revision: int,
        expected_failed_attempt_number: int, expected_rollback_proposal_digest: str,
        runtime_root=None) -> dict[str, Any]:
    """Prepare one exact rollback record without changing project bytes."""
    proposal_id = str(proposal_id or "").strip().lower()
    rollback, apply_execution, manifest, failure = _validated_lineage(
        proposal_id, expected_revision, expected_failed_attempt_number,
        expected_rollback_proposal_digest, runtime_root=runtime_root)
    if failure:
        return failure
    assert rollback is not None and apply_execution is not None and manifest is not None
    path = _execution_path(proposal_id, expected_revision, expected_failed_attempt_number, runtime_root)
    existing = _read_json(path)
    if existing:
        if not _valid(existing, "supervised_repaired_candidate_rollback_record_digest"):
            return _failure("supervised_repaired_candidate_rollback_record_invalid",
                proposal_id=proposal_id, revision=expected_revision,
                failed_attempt=expected_failed_attempt_number)
        if existing.get("rollback_proposal_digest") != rollback.get("rollback_proposal_digest"):
            return _failure("supervised_repaired_candidate_rollback_binding_changed",
                proposal_id=proposal_id, revision=expected_revision,
                failed_attempt=expected_failed_attempt_number)
        return {**existing, "operation_status": "resumed"}
    try:
        source_record, source_root = _workspace_descriptor(proposal_id, expected_revision,
            expected_failed_attempt_number, repaired=False, runtime_root=runtime_root)
        repaired_record, repaired_root = _workspace_descriptor(proposal_id, expected_revision,
            expected_failed_attempt_number, repaired=True, runtime_root=runtime_root)
        source_inventory = _record_inventory(source_record)
        repaired_inventory = _record_inventory(repaired_record)
    except Exception as error:
        return _failure("supervised_repaired_candidate_rollback_workspace_invalid",
            reason=_digest({"type": type(error).__name__}), proposal_id=proposal_id,
            revision=expected_revision, failed_attempt=expected_failed_attempt_number)
    if source_root == repaired_root or not _workspace_matches(source_root, repaired_inventory):
        return _failure("supervised_repaired_candidate_rollback_applied_state_changed",
            proposal_id=proposal_id, revision=expected_revision,
            failed_attempt=expected_failed_attempt_number)
    binding = {
        "contract_version": CONTRACT_VERSION, "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "failed_attempt_number": int(expected_failed_attempt_number),
        "repair_attempt_number": 1, "apply_attempt_number": 1, "rollback_attempt_number": 1,
        "rollback_proposal_digest": str(rollback.get("rollback_proposal_digest") or ""),
        "supervised_repaired_candidate_apply_digest": str(rollback.get("supervised_repaired_candidate_apply_digest") or ""),
        "supervised_repaired_candidate_apply_result_digest": str(rollback.get("supervised_repaired_candidate_apply_result_digest") or ""),
        "apply_proposal_digest": str(rollback.get("apply_proposal_digest") or ""),
        "source_workspace_digest": str(rollback.get("source_workspace_digest") or ""),
        "repair_workspace_digest": str(rollback.get("repair_workspace_digest") or ""),
        "apply_plan_digest": str(rollback.get("apply_plan_digest") or ""),
        "apply_authorization_receipt_digest": str(rollback.get("authorization_receipt_digest") or ""),
        "rollback_manifest_digest": str(rollback.get("rollback_manifest_digest") or ""),
        "operator_apply_result_review_digest": str(rollback.get("review_digest") or ""),
        "operator_apply_result_decision_digest": str(rollback.get("operator_repaired_candidate_apply_result_decision_digest") or ""),
    }
    execution_digest = _digest(binding)
    row = {"ok": True, "status": "supervised_repaired_candidate_rollback_prepared", **binding,
        "supervised_repaired_candidate_rollback_digest": execution_digest,
        "authorization_phrase": _rollback_authorization_phrase(rollback["rollback_proposal_digest"],
            proposal_id, expected_revision, expected_failed_attempt_number),
        "operation_count": int(manifest.get("entry_count") or 0),
        "operation_path_digests": [str(e.get("relative_path_digest") or "") for e in manifest.get("entries") or []],
        "phase": "prepared", "lease_token": "", "lease_expires_unix": 0.0,
        "recovery_count": 0,
        **_base(proposal_id=proposal_id, revision=expected_revision,
                failed_attempt=expected_failed_attempt_number)}
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "supervised_repaired_candidate_rollback_record_digest"):
                return _failure("supervised_repaired_candidate_rollback_record_invalid",
                    proposal_id=proposal_id, revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number)
            if existing.get("supervised_repaired_candidate_rollback_digest") != execution_digest:
                return _failure("supervised_repaired_candidate_rollback_binding_changed",
                    proposal_id=proposal_id, revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number)
            return {**existing, "operation_status": "resumed"}
        sealed = _seal(row, "supervised_repaired_candidate_rollback_record_digest")
        _atomic_json(path, sealed)
    return {**sealed, "operation_status": "created"}


def _restore_repaired_state(root: Path, apply_execution: Mapping[str, Any], repaired_root: Path) -> None:
    import os
    import shutil
    import tempfile
    from structured_development_generation import _safe_relative
    for operation in apply_execution.get("operations") or []:
        relative = _safe_relative(str(operation.get("relative_path") or ""))
        target = root / relative
        action = str(operation.get("operation") or "")
        if target.is_symlink():
            raise RuntimeError("rollback_recovery_symlink_conflict")
        if action == "delete":
            target.unlink(missing_ok=True)
            continue
        source = repaired_root / relative
        if (not source.is_file() or source.is_symlink()
                or hashlib.sha256(source.read_bytes()).hexdigest() != operation.get("candidate_content_digest")):
            raise RuntimeError("repaired_candidate_changed")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
        os.close(fd)
        temp = Path(name)
        try:
            shutil.copyfile(source, temp)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)


def _result(prepared: Mapping[str, Any], auth: Mapping[str, Any], *, status: str, ok: bool,
            restored_count: int, recovery_count: int) -> dict[str, Any]:
    row = {**_base(proposal_id=str(prepared.get("proposal_id") or ""),
                   revision=int(prepared.get("proposal_revision") or 0),
                   failed_attempt=int(prepared.get("failed_attempt_number") or 0)),
        "ok": bool(ok), "status": status,
        "supervised_repaired_candidate_rollback_digest": str(prepared.get("supervised_repaired_candidate_rollback_digest") or ""),
        "rollback_proposal_digest": str(prepared.get("rollback_proposal_digest") or ""),
        "supervised_repaired_candidate_apply_digest": str(prepared.get("supervised_repaired_candidate_apply_digest") or ""),
        "supervised_repaired_candidate_apply_result_digest": str(prepared.get("supervised_repaired_candidate_apply_result_digest") or ""),
        "source_workspace_digest": str(prepared.get("source_workspace_digest") or ""),
        "repair_workspace_digest": str(prepared.get("repair_workspace_digest") or ""),
        "rollback_manifest_digest": str(prepared.get("rollback_manifest_digest") or ""),
        "authorization_receipt_digest": str(auth.get("authorization_receipt_digest") or ""),
        "authorization_consumption_count": 1, "restored_count": int(restored_count),
        "restored_path_digests": list(prepared.get("operation_path_digests") or []) if ok else [],
        "rollback_executed": bool(ok), "project_modified": False if ok else True,
        "selected_project_modified": False if ok else True,
        "recovery_count": int(recovery_count), **_authority(authorized=True)}
    row["supervised_repaired_candidate_rollback_result_digest"] = _digest(row)
    return row


def _recover_locked(prepared: Mapping[str, Any], *, source_root: Path,
                    source_inventory: Mapping[str, Mapping[str, Any]],
                    repaired_inventory: Mapping[str, Mapping[str, Any]], repaired_root: Path,
                    manifest: Mapping[str, Any], runtime_root=None) -> dict[str, Any]:
    proposal_id = str(prepared.get("proposal_id") or "")
    revision = int(prepared.get("proposal_revision") or 0)
    failed = int(prepared.get("failed_attempt_number") or 0)
    auth = _read_json(_authorization_path(proposal_id, revision, failed, runtime_root)) or {}
    journal = _read_json(_journal_path(proposal_id, revision, failed, runtime_root)) or {}
    if (not _valid(auth, "authorization_receipt_digest") or not _valid(journal, "journal_digest")
            or journal.get("authorization_receipt_digest") != auth.get("authorization_receipt_digest")):
        return _failure("supervised_repaired_candidate_rollback_recovery_evidence_invalid",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed)
    state = _workspace_state(source_root, source_inventory, repaired_inventory)
    recovery = int(prepared.get("recovery_count") or 0) + 1
    if state == "conflict":
        return _failure("supervised_repaired_candidate_rollback_recovery_conflict",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed)
    try:
        if state != "source":
            _restore_manifest(source_root, manifest)
        if not _workspace_matches(source_root, source_inventory):
            raise RuntimeError("rollback_recovery_verification_failed")
        result = _result(prepared, auth,
            status="supervised_repaired_candidate_rollback_completed_recovered", ok=True,
            restored_count=int(prepared.get("operation_count") or 0), recovery_count=recovery)
    except Exception as error:
        try:
            _restore_repaired_state(source_root, prepared, repaired_root)
            repaired = _workspace_matches(source_root, repaired_inventory)
        except Exception:
            repaired = False
        if not repaired:
            return _failure("supervised_repaired_candidate_rollback_recovery_failed",
                reason=_digest({"type": type(error).__name__}), proposal_id=proposal_id,
                revision=revision, failed_attempt=failed)
        result = _result(prepared, auth,
            status="interrupted_repaired_candidate_rollback_recovered_to_applied_state", ok=False,
            restored_count=0, recovery_count=recovery)
    return _seal_result(prepared, result, auth, runtime_root=runtime_root, operation_status="recovered")


def _seal_result(prepared: Mapping[str, Any], result: Mapping[str, Any], auth: Mapping[str, Any],
                 *, runtime_root=None, operation_status: str = "created") -> dict[str, Any]:
    proposal_id = str(prepared.get("proposal_id") or "")
    revision = int(prepared.get("proposal_revision") or 0)
    failed = int(prepared.get("failed_attempt_number") or 0)
    sealed = dict(prepared)
    sealed.update({"status": result["status"], "phase": "sealed", "lease_token": "",
                   "lease_expires_unix": 0.0, "recovery_count": int(result.get("recovery_count") or 0),
                   "result": dict(result), "result_digest": _digest(result)})
    sealed = _seal(sealed, "supervised_repaired_candidate_rollback_record_digest")
    _atomic_json(_execution_path(proposal_id, revision, failed, runtime_root), sealed)
    _write_journal(_journal_path(proposal_id, revision, failed, runtime_root),
        proposal_id=proposal_id, proposal_revision=revision, failed_attempt_number=failed,
        authorization_receipt_digest=auth.get("authorization_receipt_digest"),
        phase="sealed_completed" if result.get("ok") else "sealed_applied_state_restored",
        result_digest=result.get("supervised_repaired_candidate_rollback_result_digest"))
    return {**dict(result), "operation_status": operation_status}


def authorize_and_rollback_repaired_candidate(proposal_id: str, *, expected_revision: int,
        expected_failed_attempt_number: int, expected_rollback_proposal_digest: str,
        authorization_phrase: str, runtime_root=None) -> dict[str, Any]:
    """Consume the v1218 phrase once and transactionally restore pre-apply state."""
    proposal_id = str(proposal_id or "").strip().lower()
    prepared = prepare_supervised_repaired_candidate_rollback(proposal_id,
        expected_revision=expected_revision,
        expected_failed_attempt_number=expected_failed_attempt_number,
        expected_rollback_proposal_digest=expected_rollback_proposal_digest,
        runtime_root=runtime_root)
    if prepared.get("ok") is not True:
        return prepared
    expected_phrase = _rollback_authorization_phrase(expected_rollback_proposal_digest,
        proposal_id, expected_revision, expected_failed_attempt_number)
    if str(authorization_phrase or "").strip().casefold() != expected_phrase.casefold():
        return _failure("supervised_repaired_candidate_rollback_exact_authorization_required",
            proposal_id=proposal_id, revision=expected_revision,
            failed_attempt=expected_failed_attempt_number)
    try:
        source_record, source_root = _workspace_descriptor(proposal_id, expected_revision,
            expected_failed_attempt_number, repaired=False, runtime_root=runtime_root)
        repaired_record, repaired_root = _workspace_descriptor(proposal_id, expected_revision,
            expected_failed_attempt_number, repaired=True, runtime_root=runtime_root)
        source_inventory = _record_inventory(source_record)
        repaired_inventory = _record_inventory(repaired_record)
    except Exception as error:
        return _failure("supervised_repaired_candidate_rollback_workspace_invalid",
            reason=_digest({"type": type(error).__name__}), proposal_id=proposal_id,
            revision=expected_revision, failed_attempt=expected_failed_attempt_number)
    manifest = _read_json(_rollback_manifest_path(proposal_id, expected_revision,
        expected_failed_attempt_number, runtime_root)) or {}
    path = _execution_path(proposal_id, expected_revision, expected_failed_attempt_number, runtime_root)
    lease_token = uuid.uuid4().hex
    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid(current, "supervised_repaired_candidate_rollback_record_digest"):
            return _failure("supervised_repaired_candidate_rollback_record_invalid",
                proposal_id=proposal_id, revision=expected_revision,
                failed_attempt=expected_failed_attempt_number)
        if current.get("phase") == "sealed":
            result = current.get("result")
            if not isinstance(result, Mapping) or current.get("result_digest") != _digest(result):
                return _failure("supervised_repaired_candidate_rollback_result_invalid",
                    proposal_id=proposal_id, revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number)
            return {**dict(result), "operation_status": "resumed"}
        if current.get("phase") == "running":
            if float(current.get("lease_expires_unix") or 0.0) > time.time():
                return _failure("supervised_repaired_candidate_rollback_in_progress",
                    proposal_id=proposal_id, revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number)
            return _recover_locked(current, source_root=source_root, source_inventory=source_inventory,
                repaired_inventory=repaired_inventory, repaired_root=repaired_root,
                manifest=manifest, runtime_root=runtime_root)
        if current.get("phase") != "prepared" or not _workspace_matches(source_root, repaired_inventory):
            return _failure("supervised_repaired_candidate_rollback_applied_state_changed",
                proposal_id=proposal_id, revision=expected_revision,
                failed_attempt=expected_failed_attempt_number)
        auth = _seal({"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
            "ok": True, "status": "supervised_repaired_candidate_rollback_authorization_consumed",
            "proposal_id": proposal_id, "proposal_revision": int(expected_revision),
            "failed_attempt_number": int(expected_failed_attempt_number), "repair_attempt_number": 1,
            "apply_attempt_number": 1, "rollback_attempt_number": 1,
            "supervised_repaired_candidate_rollback_digest": current["supervised_repaired_candidate_rollback_digest"],
            "rollback_proposal_digest": expected_rollback_proposal_digest,
            "rollback_manifest_digest": current["rollback_manifest_digest"],
            "authorization_phrase_digest": hashlib.sha256(expected_phrase.casefold().encode()).hexdigest(),
            "consumption_count": 1}, "authorization_receipt_digest")
        _atomic_json(_authorization_path(proposal_id, expected_revision,
            expected_failed_attempt_number, runtime_root), auth)
        _write_journal(_journal_path(proposal_id, expected_revision,
            expected_failed_attempt_number, runtime_root), proposal_id=proposal_id,
            proposal_revision=int(expected_revision), failed_attempt_number=int(expected_failed_attempt_number),
            authorization_receipt_digest=auth["authorization_receipt_digest"], phase="rolling_back",
            completed_count=0, operation_count=int(current.get("operation_count") or 0))
        running = dict(current)
        running.update({"status": "supervised_repaired_candidate_rollback_running", "phase": "running",
            "lease_token": lease_token, "lease_expires_unix": time.time() + ROLLBACK_LEASE_SECONDS,
            "authorization_receipt_digest": auth["authorization_receipt_digest"],
            **_authority(authorized=True)})
        running = _seal(running, "supervised_repaired_candidate_rollback_record_digest")
        _atomic_json(path, running)
    try:
        _restore_manifest(source_root, manifest)
        if not _workspace_matches(source_root, source_inventory):
            raise RuntimeError("rollback_verification_failed")
        result = _result(prepared, auth, status="supervised_repaired_candidate_rollback_completed",
            ok=True, restored_count=int(prepared.get("operation_count") or 0),
            recovery_count=int(prepared.get("recovery_count") or 0))
    except Exception as error:
        try:
            _restore_repaired_state(source_root, prepared, repaired_root)
            restored = _workspace_matches(source_root, repaired_inventory)
        except Exception:
            restored = False
        if not restored:
            return _failure("supervised_repaired_candidate_rollback_failed_recovery_required",
                reason=_digest({"type": type(error).__name__}), proposal_id=proposal_id,
                revision=expected_revision, failed_attempt=expected_failed_attempt_number)
        result = _result(prepared, auth,
            status="supervised_repaired_candidate_rollback_failed_applied_state_restored",
            ok=False, restored_count=0, recovery_count=int(prepared.get("recovery_count") or 0))
        result["reason"] = _digest({"type": type(error).__name__})
        result["supervised_repaired_candidate_rollback_result_digest"] = _digest({
            key: value for key, value in result.items()
            if key != "supervised_repaired_candidate_rollback_result_digest"})
    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if (not current or not _valid(current, "supervised_repaired_candidate_rollback_record_digest")
                or current.get("lease_token") != lease_token):
            return _failure("supervised_repaired_candidate_rollback_lease_lost",
                proposal_id=proposal_id, revision=expected_revision,
                failed_attempt=expected_failed_attempt_number)
        return _seal_result(current, result, auth, runtime_root=runtime_root)


def public_supervised_repaired_candidate_rollback(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "failed_attempt_number", "repair_attempt_number", "apply_attempt_number",
        "rollback_attempt_number", "rollback_attempt_limit", "rollback_proposal_digest",
        "supervised_repaired_candidate_apply_digest", "supervised_repaired_candidate_apply_result_digest",
        "source_workspace_digest", "repair_workspace_digest", "apply_plan_digest",
        "apply_authorization_receipt_digest", "rollback_manifest_digest",
        "supervised_repaired_candidate_rollback_digest", "authorization_phrase", "operation_count",
        "operation_path_digests", "phase", "authorization_receipt_digest",
        "authorization_consumption_count", "restored_count", "restored_path_digests",
        "supervised_repaired_candidate_rollback_result_digest", "recovery_count", "operation_status",
        "operator_review_required", "rollback_result_review_required", "runtime_records_external",
        "provider_contacted", "tests_executed", "retest_executed", "repair_executed", "apply_executed",
        "rollback_executed", "project_modified", "selected_project_modified", "source_modified",
        "rollback_execution_authorized", "rollback_authorized", "apply_execution_authorized",
        "apply_authorized", "repair_execution_authorized", "provider_contact_authorized",
        "test_execution_authorized", "retest_authorized", "install_authorized", "promotion_authorized",
        "release_authorized", "model_management_authorized", "authority_granted"}
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({"content_free": True, "private_request_exposed": False,
        "private_path_exposed": False, "private_content_exposed": False,
        "rollback_content_exposed": False, "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False})
    public["public_supervised_repaired_candidate_rollback_digest"] = _digest(public)
    return public


def supervised_repaired_candidate_rollback_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "supervised_repaired_candidate_rollback_prepared":
        return f"The exact repaired-candidate rollback is prepared. To authorize it, reply: {record.get('authorization_phrase', '')}"
    if status in {"supervised_repaired_candidate_rollback_completed",
                  "supervised_repaired_candidate_rollback_completed_recovered"}:
        return ("The exact pre-apply project state was restored and verified. The rollback result now "
                "requires operator review; nothing was installed, promoted, or released.")
    if status == "supervised_repaired_candidate_rollback_in_progress":
        return "That exact rollback is already running; no duplicate rollback was started."
    if status in {"supervised_repaired_candidate_rollback_failed_applied_state_restored",
                  "interrupted_repaired_candidate_rollback_recovered_to_applied_state"}:
        return ("The rollback did not complete, and the exact applied repaired-candidate state was restored. "
                "Operator review is required.")
    return ("The repaired-candidate rollback control was rejected because its exact authorization, "
            "workspace, or evidence binding was invalid. No installation, promotion, or release was authorized.")


def process_supervised_repaired_candidate_rollback_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    match = _AUTHORIZATION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision, failed = int(match.group("revision")), int(match.group("failed_attempt"))
    if int(match.group("repair_attempt")) != 1 or int(match.group("apply_attempt")) != 1:
        result = _failure("supervised_repaired_candidate_rollback_attempt_limit_exceeded",
            proposal_id=proposal_id, revision=revision, failed_attempt=failed)
    else:
        result = authorize_and_rollback_repaired_candidate(proposal_id,
            expected_revision=revision, expected_failed_attempt_number=failed,
            expected_rollback_proposal_digest=match.group("rollback_digest").lower(),
            authorization_phrase=str(user_text or "").strip(), runtime_root=runtime_root)
    public = public_supervised_repaired_candidate_rollback(result)
    return {"active": True, "event": str(result.get("status") or "supervised_repaired_candidate_rollback_control_blocked"),
        "supervised_repaired_candidate_rollback": public,
        "conversation_response": supervised_repaired_candidate_rollback_response(result),
        "public_digest": _digest(public)}


def load_supervised_repaired_candidate_rollback(proposal_id: str, revision: int,
        failed_attempt: int, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_execution_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return record if record and _valid(record, "supervised_repaired_candidate_rollback_record_digest") else {}
