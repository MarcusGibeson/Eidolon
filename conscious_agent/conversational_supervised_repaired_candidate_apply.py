from __future__ import annotations

"""Exact, transactional repaired-candidate apply execution for v1217.

One sealed v1216 apply proposal may prepare one execution record. Only the
exact digest-bound authorization phrase already emitted by v1216 may consume
that record. The apply target is the exact failed continuation project
workspace named by ``source_workspace_digest``; the passing repaired workspace
is the only allowed replacement state. A private rollback manifest is sealed
before the first write. Results always return to operator review and never
install, promote, release, manage models, or grant independent authority.
"""

import base64
import hashlib
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from conversational_build_test_continuation import _attempt_runtime_root
from conversational_supervised_repair_execution import (
    _repair_runtime_root,
    load_conversational_supervised_repair_execution,
)
from isolated_implementation_workspace import (
    _record_path as _workspace_record_path,
    _verify_record as _verify_workspace_record,
    _workspace_root,
)
from operator_repair_result_review import (
    _apply_authorization_phrase,
    load_bounded_repaired_candidate_apply_proposal,
    load_operator_repair_result_decision,
    load_operator_repair_result_review,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)
from structured_development_generation import _safe_relative

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1217.8"
APPLY_LEASE_SECONDS = 180.0
MAX_APPLY_FILES = 64
MAX_APPLY_BYTES = 2 * 1024 * 1024
APPLY_RESULT_STATUSES = frozenset({
    "supervised_repaired_candidate_apply_completed",
    "supervised_repaired_candidate_apply_completed_recovered",
    "supervised_repaired_candidate_apply_failed_rolled_back",
    "interrupted_repaired_candidate_apply_recovered_by_rollback",
})

_AUTHORIZATION = re.compile(
    r"^(?:i\s+)?authorize\s+repaired\s+candidate\s+apply\s+proposal\s+"
    r"(?P<apply_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+"
    r"(?P<revision>[1-9][0-9]*)\s+failed\s+attempt\s+"
    r"(?P<failed_attempt>[2-9][0-9]*)\s+repair\s+attempt\s+"
    r"(?P<repair_attempt>[1-9][0-9]*)[.!?]*$",
    re.I,
)


def _execution_path(
    proposal_id: str, revision: int, failed_attempt: int, runtime_root=None
) -> Path:
    return (
        _store_root(runtime_root)
        / "conversational_supervised_repaired_candidate_applies"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1.json"
    )


def _authorization_path(
    proposal_id: str, revision: int, failed_attempt: int, runtime_root=None
) -> Path:
    return (
        _store_root(runtime_root)
        / "conversational_supervised_repaired_candidate_apply_authorizations"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1.json"
    )


def _rollback_manifest_path(
    proposal_id: str, revision: int, failed_attempt: int, runtime_root=None
) -> Path:
    return (
        _store_root(runtime_root)
        / "conversational_supervised_repaired_candidate_apply_rollbacks"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1.json"
    )


def _journal_path(
    proposal_id: str, revision: int, failed_attempt: int, runtime_root=None
) -> Path:
    return (
        _store_root(runtime_root)
        / "conversational_supervised_repaired_candidate_apply_journals"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1.json"
    )


def _sha256(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(char in "0123456789abcdef" for char in token) else ""


def _record_digest(record: Mapping[str, Any], digest_field: str) -> str:
    return _digest({
        key: value for key, value in record.items()
        if key not in {digest_field, "operation_status"}
    })


def _seal(record: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    row = dict(record)
    row[digest_field] = _record_digest(row, digest_field)
    return row


def _valid(record: Mapping[str, Any], digest_field: str) -> bool:
    supplied = str(record.get(digest_field) or "")
    return bool(supplied and supplied == _record_digest(record, digest_field))


def _authority(*, authorized: bool = False) -> dict[str, bool]:
    return {
        "apply_execution_authorized": bool(authorized),
        "apply_authorized": bool(authorized),
        "rollback_authorized": False,
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


def _base(
    *, proposal_id: str = "", revision: int = 0, failed_attempt: int = 0
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "failed_attempt_number": int(failed_attempt or 0),
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "apply_attempt_limit": 1,
        "operator_review_required": True,
        "apply_result_review_required": True,
        "runtime_records_external": True,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "repair_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "rollback_prepared": False,
        "rollback_executed": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **_authority(authorized=False),
    }


def _failure(
    status: str,
    *,
    reason: str = "",
    proposal_id: str = "",
    revision: int = 0,
    failed_attempt: int = 0,
) -> dict[str, Any]:
    row = {
        "ok": False,
        "status": str(status or "supervised_repaired_candidate_apply_blocked"),
        "reason": str(reason or ""),
        **_base(
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        ),
    }
    row["supervised_repaired_candidate_apply_result_digest"] = _digest(row)
    return row


def _valid_apply_proposal_digest(record: Mapping[str, Any]) -> bool:
    binding_keys = (
        "contract_version", "proposal_id", "proposal_revision",
        "failed_attempt_number", "repair_attempt_number",
        "supervised_repair_execution_digest", "supervised_repair_result_digest",
        "repair_proposal_digest", "source_workspace_digest",
        "repair_workspace_digest", "repair_loop_result_digest", "review_digest",
        "operator_repair_result_decision_digest",
    )
    return _sha256(record.get("apply_proposal_digest")) == _digest({
        key: record.get(key) for key in binding_keys
    })


def _validated_lineage(
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    expected_apply_proposal_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    apply_proposal = load_bounded_repaired_candidate_apply_proposal(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root
    )
    review = load_operator_repair_result_review(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root
    )
    decision = load_operator_repair_result_decision(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root
    )
    repair_execution = load_conversational_supervised_repair_execution(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root
    )
    if not apply_proposal or not review or not decision or not repair_execution:
        return None, None, _failure(
            "supervised_repaired_candidate_apply_proposal_invalid",
            reason="sealed_repair_review_decision_and_apply_proposal_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if (
        apply_proposal.get("status")
        != "bounded_repaired_candidate_apply_proposal_authorization_required"
        or apply_proposal.get("apply_scope") != "one_selected_project_apply_attempt"
        or apply_proposal.get("apply_target") != "exact_isolated_repaired_candidate"
        or int(apply_proposal.get("maximum_apply_attempts") or 0) != 1
        or int(apply_proposal.get("repair_attempt_number") or 0) != 1
        or apply_proposal.get("requires_exact_authorization") is not True
        or apply_proposal.get("apply_authorization_required") is not True
        or apply_proposal.get("apply_authorized") is not False
        or apply_proposal.get("authority_granted") is not False
        or not _valid_apply_proposal_digest(apply_proposal)
    ):
        return None, None, _failure(
            "supervised_repaired_candidate_apply_proposal_invalid",
            reason="bounded_apply_contract_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if str(apply_proposal.get("apply_proposal_digest") or "") != _sha256(
        expected_apply_proposal_digest
    ):
        return None, None, _failure(
            "supervised_repaired_candidate_apply_stale_authorization",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if (
        str(apply_proposal.get("review_digest") or "")
        != str(review.get("review_digest") or "")
        or str(apply_proposal.get("operator_repair_result_decision_digest") or "")
        != str(decision.get("operator_repair_result_decision_digest") or "")
        or decision.get("decision") != "propose-apply"
        or decision.get("apply_proposal_requested") is not True
        or review.get("candidate_apply_eligible") is not True
        or review.get("repair_passed") is not True
    ):
        return None, None, _failure(
            "supervised_repaired_candidate_apply_lineage_changed",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    result = repair_execution.get("result")
    if (
        repair_execution.get("phase") != "sealed"
        or not isinstance(result, Mapping)
        or str(repair_execution.get("result_digest") or "") != _digest(result)
        or result.get("status") != "supervised_repair_completed"
        or result.get("ok") is not True
        or result.get("test_passed") is not True
        or result.get("cleanup_confirmed") is not True
        or result.get("selected_project_modified") is not False
        or result.get("apply_authorized") is not False
        or str(result.get("supervised_repair_execution_digest") or "")
        != str(apply_proposal.get("supervised_repair_execution_digest") or "")
        or str(result.get("supervised_repair_result_digest") or "")
        != str(apply_proposal.get("supervised_repair_result_digest") or "")
        or str(result.get("source_workspace_digest") or "")
        != str(apply_proposal.get("source_workspace_digest") or "")
        or str(result.get("repair_workspace_digest") or "")
        != str(apply_proposal.get("repair_workspace_digest") or "")
        or str(result.get("repair_loop_result_digest") or "")
        != str(apply_proposal.get("repair_loop_result_digest") or "")
    ):
        return None, None, _failure(
            "supervised_repaired_candidate_apply_repair_invalid",
            reason="passing_cleanup_confirmed_repair_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    return dict(apply_proposal), dict(result), None


def _workspace_descriptor(
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    *,
    repaired: bool,
    runtime_root=None,
) -> tuple[dict[str, Any], Path]:
    child = (
        _repair_runtime_root(proposal_id, revision, failed_attempt, runtime_root)
        if repaired
        else _attempt_runtime_root(proposal_id, revision, failed_attempt, runtime_root)
    )
    record = _read_json(_workspace_record_path(proposal_id, revision, child)) or {}
    supplied = str(record.get("workspace_digest") or "")
    if not supplied or supplied != _digest({
        key: value for key, value in record.items() if key != "workspace_digest"
    }):
        raise ValueError("workspace_record_invalid")
    root = _workspace_root(
        proposal_id, revision, str(record.get("generation_digest") or ""), child
    )
    return dict(record), root


def _record_inventory(record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = list(record.get("files") or [])
    if len(rows) != int(record.get("file_count") or -1) or len(rows) > MAX_APPLY_FILES:
        raise ValueError("workspace_file_count_invalid")
    inventory: dict[str, dict[str, Any]] = {}
    total = 0
    for row in rows:
        relative = _safe_relative(str(row.get("relative_path") or ""))
        folded = relative.casefold()
        if folded in {value.casefold() for value in inventory}:
            raise ValueError("workspace_duplicate_path")
        size = int(row.get("size_bytes") or 0)
        digest = _sha256(row.get("content_digest"))
        if (
            not digest
            or size < 0
            or _sha256(row.get("relative_path_digest"))
            != hashlib.sha256(relative.encode()).hexdigest()
        ):
            raise ValueError("workspace_entry_invalid")
        total += size
        inventory[relative] = {"content_digest": digest, "size_bytes": size}
    if total != int(record.get("total_bytes") or -1) or total > MAX_APPLY_BYTES:
        raise ValueError("workspace_byte_budget_invalid")
    return inventory


def _actual_inventory(root: Path) -> dict[str, dict[str, Any]]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("workspace_unavailable")
    inventory: dict[str, dict[str, Any]] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        relative_path = path.relative_to(root)
        if (
            any(part in {"__pycache__", ".pytest_cache", ".mypy_cache"} for part in relative_path.parts)
            or path.suffix.lower() in {".pyc", ".pyo"}
        ):
            continue
        if path.is_symlink():
            raise ValueError("workspace_symlink_rejected")
        if not path.is_file():
            continue
        relative = _safe_relative(relative_path.as_posix())
        size = path.stat().st_size
        total += size
        inventory[relative] = {
            "content_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": size,
        }
        if len(inventory) > MAX_APPLY_FILES or total > MAX_APPLY_BYTES:
            raise ValueError("workspace_budget_exceeded")
    return inventory


def _workspace_matches(root: Path, expected: Mapping[str, Mapping[str, Any]]) -> bool:
    try:
        return _actual_inventory(root) == dict(expected)
    except Exception:
        return False


def _apply_plan(
    source: Mapping[str, Mapping[str, Any]], repaired: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    operations: list[dict[str, Any]] = []
    total = 0
    for relative in sorted(set(source) | set(repaired)):
        before = dict(source.get(relative) or {})
        after = dict(repaired.get(relative) or {})
        if before == after:
            continue
        operation = "delete" if not after else ("create" if not before else "replace")
        size = int(after.get("size_bytes") or 0)
        total += size
        operations.append({
            "relative_path": relative,
            "relative_path_digest": hashlib.sha256(relative.encode()).hexdigest(),
            "operation": operation,
            "source_content_digest": str(before.get("content_digest") or ""),
            "candidate_content_digest": str(after.get("content_digest") or ""),
            "candidate_size_bytes": size,
        })
    if not operations or len(operations) > MAX_APPLY_FILES or total > MAX_APPLY_BYTES:
        raise ValueError("apply_budget_or_empty_plan")
    return operations, _digest(operations)


def prepare_supervised_repaired_candidate_apply(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_apply_proposal_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one exact apply execution without modifying either workspace."""

    proposal_id = str(proposal_id or "").strip().lower()
    apply_proposal, repair_result, failure = _validated_lineage(
        proposal_id,
        expected_revision,
        expected_failed_attempt_number,
        expected_apply_proposal_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert apply_proposal is not None and repair_result is not None
    try:
        source_record, source_root = _workspace_descriptor(
            proposal_id,
            expected_revision,
            expected_failed_attempt_number,
            repaired=False,
            runtime_root=runtime_root,
        )
        repaired_record, repaired_root = _workspace_descriptor(
            proposal_id,
            expected_revision,
            expected_failed_attempt_number,
            repaired=True,
            runtime_root=runtime_root,
        )
        source_inventory = _record_inventory(source_record)
        repaired_inventory = _record_inventory(repaired_record)
        operations, apply_plan_digest = _apply_plan(source_inventory, repaired_inventory)
    except Exception as error:
        return _failure(
            "supervised_repaired_candidate_apply_workspace_invalid",
            reason=_digest({"type": type(error).__name__}),
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        )
    if (
        str(source_record.get("workspace_digest") or "")
        != str(apply_proposal.get("source_workspace_digest") or "")
        or str(repaired_record.get("workspace_digest") or "")
        != str(apply_proposal.get("repair_workspace_digest") or "")
        or source_root == repaired_root
    ):
        return _failure(
            "supervised_repaired_candidate_apply_workspace_binding_changed",
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        )
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "failed_attempt_number": int(expected_failed_attempt_number),
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "apply_proposal_digest": str(apply_proposal.get("apply_proposal_digest") or ""),
        "review_digest": str(apply_proposal.get("review_digest") or ""),
        "operator_repair_result_decision_digest": str(
            apply_proposal.get("operator_repair_result_decision_digest") or ""
        ),
        "supervised_repair_execution_digest": str(
            apply_proposal.get("supervised_repair_execution_digest") or ""
        ),
        "supervised_repair_result_digest": str(
            apply_proposal.get("supervised_repair_result_digest") or ""
        ),
        "source_workspace_digest": str(source_record.get("workspace_digest") or ""),
        "repair_workspace_digest": str(repaired_record.get("workspace_digest") or ""),
        "repair_loop_result_digest": str(repair_result.get("repair_loop_result_digest") or ""),
        "apply_plan_digest": apply_plan_digest,
    }
    execution_digest = _digest(binding)
    row = {
        "ok": True,
        "status": "supervised_repaired_candidate_apply_prepared",
        **binding,
        "supervised_repaired_candidate_apply_digest": execution_digest,
        "authorization_phrase": _apply_authorization_phrase(
            str(apply_proposal.get("apply_proposal_digest") or ""),
            proposal_id,
            expected_revision,
            expected_failed_attempt_number,
        ),
        "operation_count": len(operations),
        "operation_path_digests": [row["relative_path_digest"] for row in operations],
        "total_apply_bytes": sum(int(row["candidate_size_bytes"]) for row in operations),
        "operations": operations,
        "phase": "prepared",
        "lease_token": "",
        "lease_expires_unix": 0.0,
        "recovery_count": 0,
        **_base(
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        ),
    }
    path = _execution_path(
        proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
    )
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "supervised_repaired_candidate_apply_record_digest"):
                return _failure(
                    "supervised_repaired_candidate_apply_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("supervised_repaired_candidate_apply_digest") or "") != execution_digest:
                return _failure(
                    "supervised_repaired_candidate_apply_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        if not _workspace_matches(source_root, source_inventory):
            return _failure(
                "supervised_repaired_candidate_apply_source_changed",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if not _verify_workspace_record(repaired_record, repaired_root) or not _workspace_matches(
            repaired_root, repaired_inventory
        ):
            return _failure(
                "supervised_repaired_candidate_apply_candidate_changed",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        sealed = _seal(row, "supervised_repaired_candidate_apply_record_digest")
        _atomic_json(path, sealed)
    return {**sealed, "operation_status": "created"}


def _prepare_rollback_manifest(
    prepared: Mapping[str, Any], source_root: Path, *, runtime_root=None
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    total = 0
    for operation in prepared.get("operations") or []:
        relative = _safe_relative(str(operation.get("relative_path") or ""))
        target = source_root / relative
        existed = target.is_file() and not target.is_symlink()
        content = target.read_bytes() if existed else b""
        total += len(content)
        entries.append({
            "relative_path": relative,
            "relative_path_digest": hashlib.sha256(relative.encode()).hexdigest(),
            "existed": existed,
            "content_digest": hashlib.sha256(content).hexdigest() if existed else "",
            "content_b64": base64.b64encode(content).decode("ascii") if existed else "",
        })
    if len(entries) > MAX_APPLY_FILES or total > MAX_APPLY_BYTES:
        raise ValueError("rollback_budget_exceeded")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "ok": True,
        "status": "supervised_repaired_candidate_apply_rollback_prepared",
        "proposal_id": str(prepared.get("proposal_id") or ""),
        "proposal_revision": int(prepared.get("proposal_revision") or 0),
        "failed_attempt_number": int(prepared.get("failed_attempt_number") or 0),
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "supervised_repaired_candidate_apply_digest": str(
            prepared.get("supervised_repaired_candidate_apply_digest") or ""
        ),
        "apply_proposal_digest": str(prepared.get("apply_proposal_digest") or ""),
        "source_workspace_digest": str(prepared.get("source_workspace_digest") or ""),
        "repair_workspace_digest": str(prepared.get("repair_workspace_digest") or ""),
        "apply_plan_digest": str(prepared.get("apply_plan_digest") or ""),
        "entries": entries,
        "entry_count": len(entries),
        "total_backup_bytes": total,
        "rollback_authorized": False,
        "rollback_executed": False,
        "private_paths_external_only": True,
    }
    return _seal(manifest, "rollback_manifest_digest")


def _valid_manifest(manifest: Mapping[str, Any], prepared: Mapping[str, Any]) -> bool:
    if not _valid(manifest, "rollback_manifest_digest"):
        return False
    if any(
        manifest.get(key) != prepared.get(key)
        for key in (
            "proposal_id", "proposal_revision", "failed_attempt_number",
            "supervised_repaired_candidate_apply_digest", "apply_proposal_digest",
            "source_workspace_digest", "repair_workspace_digest", "apply_plan_digest",
        )
    ):
        return False
    entries = list(manifest.get("entries") or [])
    if len(entries) != int(manifest.get("entry_count") or -1) or len(entries) > MAX_APPLY_FILES:
        return False
    total = 0
    try:
        for entry in entries:
            relative = _safe_relative(str(entry.get("relative_path") or ""))
            if _sha256(entry.get("relative_path_digest")) != hashlib.sha256(relative.encode()).hexdigest():
                return False
            if entry.get("existed"):
                content = base64.b64decode(str(entry.get("content_b64") or ""), validate=True)
                total += len(content)
                if hashlib.sha256(content).hexdigest() != entry.get("content_digest"):
                    return False
            elif entry.get("content_b64") or entry.get("content_digest"):
                return False
    except Exception:
        return False
    return total == int(manifest.get("total_backup_bytes") or -1) and total <= MAX_APPLY_BYTES


def _write_journal(path: Path, **fields: Any) -> dict[str, Any]:
    row = _seal({
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        **fields,
    }, "journal_digest")
    _atomic_json(path, row)
    return row


def _restore_manifest(source_root: Path, manifest: Mapping[str, Any]) -> None:
    for entry in manifest.get("entries") or []:
        target = source_root / _safe_relative(str(entry.get("relative_path") or ""))
        if target.is_symlink():
            raise RuntimeError("rollback_symlink_conflict")
        if entry.get("existed"):
            content = base64.b64decode(str(entry.get("content_b64") or ""), validate=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
            os.close(fd)
            temp = Path(temp_name)
            try:
                temp.write_bytes(content)
                os.replace(temp, target)
            finally:
                temp.unlink(missing_ok=True)
        else:
            target.unlink(missing_ok=True)


def _workspace_state(
    root: Path,
    source_inventory: Mapping[str, Mapping[str, Any]],
    repaired_inventory: Mapping[str, Mapping[str, Any]],
) -> str:
    try:
        actual = _actual_inventory(root)
    except Exception:
        return "conflict"
    if actual == dict(source_inventory):
        return "source"
    if actual == dict(repaired_inventory):
        return "repaired"
    if set(actual) != set(source_inventory) and set(actual) != set(repaired_inventory):
        return "conflict"
    allowed = {
        relative: {tuple(sorted(dict(value).items())) for value in (
            source_inventory.get(relative, {}), repaired_inventory.get(relative, {})
        )}
        for relative in set(source_inventory) | set(repaired_inventory)
    }
    if set(actual) == set(allowed) and all(
        tuple(sorted(dict(value).items())) in allowed[relative]
        for relative, value in actual.items()
    ):
        return "mixed_known"
    return "conflict"


def _result(
    prepared: Mapping[str, Any],
    auth: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    status: str,
    ok: bool,
    applied_count: int,
    rollback_executed: bool,
    recovery_count: int,
) -> dict[str, Any]:
    row = {
        **_base(
            proposal_id=str(prepared.get("proposal_id") or ""),
            revision=int(prepared.get("proposal_revision") or 0),
            failed_attempt=int(prepared.get("failed_attempt_number") or 0),
        ),
        "ok": bool(ok),
        "status": status,
        "supervised_repaired_candidate_apply_digest": str(
            prepared.get("supervised_repaired_candidate_apply_digest") or ""
        ),
        "apply_proposal_digest": str(prepared.get("apply_proposal_digest") or ""),
        "source_workspace_digest": str(prepared.get("source_workspace_digest") or ""),
        "repair_workspace_digest": str(prepared.get("repair_workspace_digest") or ""),
        "apply_plan_digest": str(prepared.get("apply_plan_digest") or ""),
        "authorization_receipt_digest": str(auth.get("authorization_receipt_digest") or ""),
        "authorization_consumption_count": 1,
        "rollback_manifest_digest": str(manifest.get("rollback_manifest_digest") or ""),
        "rollback_prepared": True,
        "rollback_available": not rollback_executed,
        "rollback_executed": bool(rollback_executed),
        "applied_count": int(applied_count),
        "applied_path_digests": list(prepared.get("operation_path_digests") or []) if applied_count else [],
        "project_modified": bool(ok and not rollback_executed),
        "selected_project_modified": bool(ok and not rollback_executed),
        "recovery_count": int(recovery_count),
        **_authority(authorized=True),
    }
    row["supervised_repaired_candidate_apply_result_digest"] = _digest(row)
    return row


def _recover_locked(
    prepared: Mapping[str, Any],
    *,
    source_root: Path,
    source_inventory: Mapping[str, Mapping[str, Any]],
    repaired_inventory: Mapping[str, Mapping[str, Any]],
    runtime_root=None,
) -> dict[str, Any]:
    proposal_id = str(prepared.get("proposal_id") or "")
    revision = int(prepared.get("proposal_revision") or 0)
    failed_attempt = int(prepared.get("failed_attempt_number") or 0)
    auth = _read_json(_authorization_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    manifest = _read_json(_rollback_manifest_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    journal = _read_json(_journal_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    if (
        not _valid(auth, "authorization_receipt_digest")
        or auth.get("supervised_repaired_candidate_apply_digest")
        != prepared.get("supervised_repaired_candidate_apply_digest")
        or not _valid_manifest(manifest, prepared)
        or not _valid(journal, "journal_digest")
        or journal.get("authorization_receipt_digest") != auth.get("authorization_receipt_digest")
    ):
        return _failure(
            "supervised_repaired_candidate_apply_recovery_evidence_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    state = _workspace_state(source_root, source_inventory, repaired_inventory)
    recovery_count = int(prepared.get("recovery_count") or 0) + 1
    if state == "conflict":
        return _failure(
            "supervised_repaired_candidate_apply_recovery_conflict",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if state == "repaired":
        result = _result(
            prepared,
            auth,
            manifest,
            status="supervised_repaired_candidate_apply_completed_recovered",
            ok=True,
            applied_count=int(prepared.get("operation_count") or 0),
            rollback_executed=False,
            recovery_count=recovery_count,
        )
    else:
        try:
            _restore_manifest(source_root, manifest)
        except Exception as error:
            return _failure(
                "supervised_repaired_candidate_apply_recovery_rollback_failed",
                reason=_digest({"type": type(error).__name__}),
                proposal_id=proposal_id,
                revision=revision,
                failed_attempt=failed_attempt,
            )
        if not _workspace_matches(source_root, source_inventory):
            return _failure(
                "supervised_repaired_candidate_apply_recovery_verification_failed",
                proposal_id=proposal_id,
                revision=revision,
                failed_attempt=failed_attempt,
            )
        result = _result(
            prepared,
            auth,
            manifest,
            status="interrupted_repaired_candidate_apply_recovered_by_rollback",
            ok=False,
            applied_count=0,
            rollback_executed=True,
            recovery_count=recovery_count,
        )
    sealed = dict(prepared)
    sealed.update({
        "status": result["status"],
        "phase": "sealed",
        "lease_token": "",
        "lease_expires_unix": 0.0,
        "recovery_count": recovery_count,
        "result": result,
        "result_digest": _digest(result),
    })
    sealed = _seal(sealed, "supervised_repaired_candidate_apply_record_digest")
    _atomic_json(_execution_path(proposal_id, revision, failed_attempt, runtime_root), sealed)
    _write_journal(
        _journal_path(proposal_id, revision, failed_attempt, runtime_root),
        proposal_id=proposal_id,
        proposal_revision=revision,
        failed_attempt_number=failed_attempt,
        authorization_receipt_digest=auth.get("authorization_receipt_digest"),
        phase="sealed_recovered",
        result_digest=result["supervised_repaired_candidate_apply_result_digest"],
    )
    return {**result, "operation_status": "recovered"}


def authorize_and_apply_repaired_candidate(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_apply_proposal_digest: str,
    authorization_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Consume one exact authorization and transactionally apply one repair."""

    proposal_id = str(proposal_id or "").strip().lower()
    prepared = prepare_supervised_repaired_candidate_apply(
        proposal_id,
        expected_revision=expected_revision,
        expected_failed_attempt_number=expected_failed_attempt_number,
        expected_apply_proposal_digest=expected_apply_proposal_digest,
        runtime_root=runtime_root,
    )
    if prepared.get("ok") is not True:
        return prepared
    expected_phrase = _apply_authorization_phrase(
        str(expected_apply_proposal_digest or ""),
        proposal_id,
        expected_revision,
        expected_failed_attempt_number,
    )
    if str(authorization_phrase or "").strip().casefold() != expected_phrase.casefold():
        return _failure(
            "supervised_repaired_candidate_apply_exact_authorization_required",
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        )
    try:
        source_record, source_root = _workspace_descriptor(
            proposal_id,
            expected_revision,
            expected_failed_attempt_number,
            repaired=False,
            runtime_root=runtime_root,
        )
        repaired_record, repaired_root = _workspace_descriptor(
            proposal_id,
            expected_revision,
            expected_failed_attempt_number,
            repaired=True,
            runtime_root=runtime_root,
        )
        source_inventory = _record_inventory(source_record)
        repaired_inventory = _record_inventory(repaired_record)
    except Exception as error:
        return _failure(
            "supervised_repaired_candidate_apply_workspace_invalid",
            reason=_digest({"type": type(error).__name__}),
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        )

    path = _execution_path(
        proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
    )
    lease_token = uuid.uuid4().hex
    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid(current, "supervised_repaired_candidate_apply_record_digest"):
            return _failure(
                "supervised_repaired_candidate_apply_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if current.get("phase") == "sealed":
            result = current.get("result")
            if not isinstance(result, Mapping) or str(current.get("result_digest") or "") != _digest(result):
                return _failure(
                    "supervised_repaired_candidate_apply_result_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**dict(result), "operation_status": "resumed"}
        if current.get("phase") == "running":
            if float(current.get("lease_expires_unix") or 0.0) > time.time():
                return _failure(
                    "supervised_repaired_candidate_apply_in_progress",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return _recover_locked(
                current,
                source_root=source_root,
                source_inventory=source_inventory,
                repaired_inventory=repaired_inventory,
                runtime_root=runtime_root,
            )
        if current.get("phase") != "prepared":
            return _failure(
                "supervised_repaired_candidate_apply_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if not _workspace_matches(source_root, source_inventory):
            return _failure(
                "supervised_repaired_candidate_apply_source_changed",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if not _verify_workspace_record(repaired_record, repaired_root) or not _workspace_matches(
            repaired_root, repaired_inventory
        ):
            return _failure(
                "supervised_repaired_candidate_apply_candidate_changed",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        try:
            manifest = _prepare_rollback_manifest(current, source_root, runtime_root=runtime_root)
        except Exception as error:
            return _failure(
                "supervised_repaired_candidate_apply_backup_failed",
                reason=_digest({"type": type(error).__name__}),
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        _atomic_json(
            _rollback_manifest_path(
                proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
            ),
            manifest,
        )
        auth = _seal({
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "ok": True,
            "status": "supervised_repaired_candidate_apply_authorization_consumed",
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "failed_attempt_number": int(expected_failed_attempt_number),
            "repair_attempt_number": 1,
            "apply_attempt_number": 1,
            "supervised_repaired_candidate_apply_digest": str(
                current.get("supervised_repaired_candidate_apply_digest") or ""
            ),
            "apply_proposal_digest": str(current.get("apply_proposal_digest") or ""),
            "authorization_phrase_digest": hashlib.sha256(expected_phrase.casefold().encode()).hexdigest(),
            "consumption_count": 1,
            "rollback_manifest_digest": str(manifest.get("rollback_manifest_digest") or ""),
        }, "authorization_receipt_digest")
        _atomic_json(
            _authorization_path(
                proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
            ),
            auth,
        )
        _write_journal(
            _journal_path(
                proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
            ),
            proposal_id=proposal_id,
            proposal_revision=int(expected_revision),
            failed_attempt_number=int(expected_failed_attempt_number),
            authorization_receipt_digest=auth["authorization_receipt_digest"],
            phase="applying",
            completed_count=0,
            operation_count=int(current.get("operation_count") or 0),
        )
        running = dict(current)
        running.update({
            "status": "supervised_repaired_candidate_apply_running",
            "phase": "running",
            "lease_token": lease_token,
            "lease_expires_unix": time.time() + APPLY_LEASE_SECONDS,
            "authorization_receipt_digest": auth["authorization_receipt_digest"],
            "rollback_manifest_digest": manifest["rollback_manifest_digest"],
            "rollback_prepared": True,
            **_authority(authorized=True),
        })
        running = _seal(running, "supervised_repaired_candidate_apply_record_digest")
        _atomic_json(path, running)

    applied: list[str] = []
    try:
        for operation in prepared.get("operations") or []:
            relative = _safe_relative(str(operation.get("relative_path") or ""))
            target = source_root / relative
            action = str(operation.get("operation") or "")
            if target.is_symlink():
                raise RuntimeError("apply_target_symlink_rejected")
            if action == "delete":
                target.unlink(missing_ok=True)
            else:
                source = repaired_root / relative
                if (
                    not source.is_file()
                    or source.is_symlink()
                    or hashlib.sha256(source.read_bytes()).hexdigest()
                    != operation.get("candidate_content_digest")
                ):
                    raise RuntimeError("repair_candidate_content_changed")
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
                os.close(fd)
                temp = Path(temp_name)
                try:
                    shutil.copyfile(source, temp)
                    os.replace(temp, target)
                finally:
                    temp.unlink(missing_ok=True)
            applied.append(relative)
            with _proposal_lock(proposal_id, runtime_root):
                _write_journal(
                    _journal_path(
                        proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
                    ),
                    proposal_id=proposal_id,
                    proposal_revision=int(expected_revision),
                    failed_attempt_number=int(expected_failed_attempt_number),
                    authorization_receipt_digest=auth["authorization_receipt_digest"],
                    phase="applying",
                    completed_count=len(applied),
                    operation_count=int(prepared.get("operation_count") or 0),
                )
        if not _workspace_matches(source_root, repaired_inventory):
            raise RuntimeError("applied_workspace_verification_failed")
        result = _result(
            prepared,
            auth,
            manifest,
            status="supervised_repaired_candidate_apply_completed",
            ok=True,
            applied_count=len(applied),
            rollback_executed=False,
            recovery_count=int(prepared.get("recovery_count") or 0),
        )
    except Exception as error:
        try:
            _restore_manifest(source_root, manifest)
            restored = _workspace_matches(source_root, source_inventory)
        except Exception:
            restored = False
        if not restored:
            return _failure(
                "supervised_repaired_candidate_apply_failed_recovery_required",
                reason=_digest({"type": type(error).__name__}),
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        result = _result(
            prepared,
            auth,
            manifest,
            status="supervised_repaired_candidate_apply_failed_rolled_back",
            ok=False,
            applied_count=0,
            rollback_executed=True,
            recovery_count=int(prepared.get("recovery_count") or 0),
        )
        result["reason"] = _digest({"type": type(error).__name__})
        result["supervised_repaired_candidate_apply_result_digest"] = _digest({
            key: value for key, value in result.items()
            if key != "supervised_repaired_candidate_apply_result_digest"
        })

    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if (
            not current
            or not _valid(current, "supervised_repaired_candidate_apply_record_digest")
            or str(current.get("lease_token") or "") != lease_token
        ):
            return _failure(
                "supervised_repaired_candidate_apply_lease_lost",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        sealed = dict(current)
        sealed.update({
            "status": result["status"],
            "phase": "sealed",
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "result": result,
            "result_digest": _digest(result),
        })
        sealed = _seal(sealed, "supervised_repaired_candidate_apply_record_digest")
        _atomic_json(path, sealed)
        _write_journal(
            _journal_path(
                proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
            ),
            proposal_id=proposal_id,
            proposal_revision=int(expected_revision),
            failed_attempt_number=int(expected_failed_attempt_number),
            authorization_receipt_digest=auth["authorization_receipt_digest"],
            phase="sealed_completed" if result.get("ok") else "sealed_failed_rolled_back",
            result_digest=result["supervised_repaired_candidate_apply_result_digest"],
        )
    return {**result, "operation_status": "created"}


def public_supervised_repaired_candidate_apply(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "failed_attempt_number", "repair_attempt_number",
        "apply_attempt_number", "apply_attempt_limit", "apply_proposal_digest",
        "review_digest", "operator_repair_result_decision_digest",
        "supervised_repair_execution_digest", "supervised_repair_result_digest",
        "source_workspace_digest", "repair_workspace_digest", "repair_loop_result_digest",
        "apply_plan_digest", "supervised_repaired_candidate_apply_digest",
        "supervised_repaired_candidate_apply_record_digest", "authorization_phrase",
        "operation_count", "operation_path_digests", "total_apply_bytes", "phase",
        "authorization_receipt_digest", "authorization_consumption_count",
        "rollback_manifest_digest", "rollback_prepared", "rollback_available",
        "rollback_executed", "applied_count", "applied_path_digests",
        "supervised_repaired_candidate_apply_result_digest", "recovery_count",
        "operation_status", "operator_review_required", "apply_result_review_required",
        "runtime_records_external", "provider_contacted", "tests_executed",
        "retest_executed", "repair_executed", "project_modified",
        "selected_project_modified", "source_modified", "apply_execution_authorized",
        "apply_authorized", "rollback_authorized", "repair_execution_authorized",
        "provider_contact_authorized", "test_execution_authorized", "retest_authorized",
        "install_authorized", "promotion_authorized", "release_authorized",
        "model_management_authorized", "authority_granted",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "content_free": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        "rollback_content_exposed": False,
    })
    public["public_supervised_repaired_candidate_apply_digest"] = _digest(public)
    return public


def supervised_repaired_candidate_apply_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "supervised_repaired_candidate_apply_prepared":
        return (
            "The exact passing repaired candidate is prepared for one transactional apply. "
            f"To authorize it, reply: {record.get('authorization_phrase', '')}"
        )
    if status in {
        "supervised_repaired_candidate_apply_completed",
        "supervised_repaired_candidate_apply_completed_recovered",
    }:
        return (
            "The exact repaired candidate was applied transactionally to its bound project "
            "workspace after sealing rollback evidence. The result now requires operator review; "
            "nothing was installed, promoted, or released."
        )
    if status == "supervised_repaired_candidate_apply_in_progress":
        return "That exact apply is already running; no duplicate apply was started."
    if status in {
        "supervised_repaired_candidate_apply_failed_rolled_back",
        "interrupted_repaired_candidate_apply_recovered_by_rollback",
    }:
        return (
            "The repaired-candidate apply did not complete, and the bound project workspace was "
            "restored from its sealed rollback evidence. Operator review is required."
        )
    return (
        "The repaired-candidate apply control was rejected because its exact authorization, "
        "workspace, or evidence binding was invalid. No apply, rollback authorization, "
        "installation, promotion, or release action was granted."
    )


def process_supervised_repaired_candidate_apply_control(
    user_text: str, *, runtime_root=None
) -> dict[str, Any]:
    match = _AUTHORIZATION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision = int(match.group("revision"))
    failed_attempt = int(match.group("failed_attempt"))
    repair_attempt = int(match.group("repair_attempt"))
    if repair_attempt != 1:
        result = _failure(
            "supervised_repaired_candidate_apply_attempt_limit_exceeded",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    else:
        result = authorize_and_apply_repaired_candidate(
            proposal_id,
            expected_revision=revision,
            expected_failed_attempt_number=failed_attempt,
            expected_apply_proposal_digest=match.group("apply_digest").lower(),
            authorization_phrase=str(user_text or "").strip(),
            runtime_root=runtime_root,
        )
    public = public_supervised_repaired_candidate_apply(result)
    return {
        "active": True,
        "event": str(result.get("status") or "supervised_repaired_candidate_apply_control_blocked"),
        "supervised_repaired_candidate_apply": public,
        "conversation_response": supervised_repaired_candidate_apply_response(result),
        "public_digest": _digest(public),
    }


def load_supervised_repaired_candidate_apply(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_execution_path(
        proposal_id, revision, failed_attempt, runtime_root
    )) or {}
    return (
        record
        if record and _valid(record, "supervised_repaired_candidate_apply_record_digest")
        else {}
    )
