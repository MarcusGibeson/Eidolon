from __future__ import annotations

"""Exact, isolated, supervised repair execution for v1215.

One sealed v1214 bounded repair proposal may prepare one repair execution
record.  Only the exact digest-bound authorization phrase already emitted by
v1214 may start that record.  The authorized attempt receives the failed
continuation artifact privately, generates one bounded replacement candidate
in a fresh external namespace, and delegates verification to the retained
v1210 build coordinator and v1209 unified test adapter.  The repaired candidate
remains isolated and operator-review-only; this module cannot apply, install,
promote, release, manage models, or acquire independent authority.
"""

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from conversational_build_test_continuation import (
    _attempt_runtime_root,
    load_conversational_build_test_continuation,
)
from conversational_build_test_loop import (
    authorize_and_run_conversational_build_test_loop,
    prepare_conversational_build_test_loop,
)
from isolated_implementation_workspace import (
    _record_path as _workspace_record_path,
    _verify_record as _verify_workspace_record,
    _workspace_root,
)
from operator_diagnosis_review import (
    _repair_authorization_phrase,
    load_bounded_repair_proposal,
    load_operator_diagnosis_decision,
    load_operator_diagnosis_review,
)
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
from structured_development_generation import _path as _generation_path

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1215.8"
REPAIR_LEASE_SECONDS = 180.0
MAX_REPAIR_CONTEXT_BYTES = 512 * 1024

DIAGNOSABLE_FAILURES = frozenset({
    "conversational_build_test_continuation_tests_failed",
    "conversational_build_test_continuation_test_blocked",
    "conversational_build_test_continuation_build_blocked",
    "conversational_build_test_continuation_internal_error",
})

_RESULT_MAP = {
    "conversational_build_test_completed": (True, "supervised_repair_completed", "complete"),
    "conversational_build_test_tests_failed": (False, "supervised_repair_tests_failed", "test"),
    "conversational_build_test_test_blocked": (False, "supervised_repair_test_blocked", "test"),
    "conversational_build_test_build_blocked": (False, "supervised_repair_build_blocked", "build"),
    "conversational_build_test_internal_error": (False, "supervised_repair_internal_error", "internal"),
}

_AUTHORIZATION = re.compile(
    r"^(?:i\s+)?authorize\s+repair\s+proposal\s+"
    r"(?P<repair_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+"
    r"(?P<revision>[1-9][0-9]*)\s+attempt\s+"
    r"(?P<attempt>[2-9][0-9]*)[.!?]*$",
    re.I,
)


def _execution_path(proposal_id: str, revision: int, attempt_number: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "conversational_supervised_repair_executions"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"attempt-{int(attempt_number)}.json"
    )


def _repair_runtime_root(proposal_id: str, revision: int, attempt_number: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "conversational_supervised_repair_runtime"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(attempt_number)}"
        / "repair-1"
    )


def _sha256(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(char in "0123456789abcdef" for char in token) else ""


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({
        key: value for key, value in record.items()
        if key not in {"supervised_repair_execution_record_digest", "operation_status"}
    })


def _valid_record(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("supervised_repair_execution_record_digest") or "")
    return bool(supplied and supplied == _record_digest(record))


def _seal(record: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(record)
    row["supervised_repair_execution_record_digest"] = _record_digest(row)
    return row


def _authority(*, authorized: bool = False) -> dict[str, bool]:
    return {
        "repair_execution_authorized": bool(authorized),
        "provider_contact_authorized": bool(authorized),
        "test_execution_authorized": bool(authorized),
        "retest_authorized": bool(authorized),
        "apply_authorized": False,
        "rollback_authorized": False,
        "install_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "model_management_authorized": False,
        "authority_granted": False,
    }


def _base(*, proposal_id: str = "", revision: int = 0, attempt_number: int = 0) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "failed_attempt_number": int(attempt_number or 0),
        "repair_attempt_number": 1,
        "repair_attempt_limit": 1,
        "operator_review_required": True,
        "repair_result_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "patch_generated": False,
        "repair_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "runtime_records_external": True,
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
    attempt_number: int = 0,
) -> dict[str, Any]:
    row = {
        "ok": False,
        "status": str(status or "supervised_repair_blocked"),
        "reason": str(reason or ""),
        **_base(proposal_id=proposal_id, revision=revision, attempt_number=attempt_number),
    }
    row["supervised_repair_result_digest"] = _digest(row)
    return row


def _valid_repair_proposal_digest(record: Mapping[str, Any]) -> bool:
    binding_keys = (
        "contract_version", "proposal_id", "proposal_revision", "proposal_revision_digest",
        "attempt_number", "attempt_digest", "continuation_result_digest", "evidence_digest",
        "diagnosis_digest", "diagnosis_result_digest", "diagnosis_candidate_digest",
        "review_digest", "operator_diagnosis_decision_digest",
    )
    binding = {key: record.get(key) for key in binding_keys}
    return _sha256(record.get("repair_proposal_digest")) == _digest(binding)


def _validated_lineage(
    proposal_id: str,
    revision: int,
    attempt_number: int,
    expected_repair_proposal_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    repair = load_bounded_repair_proposal(
        proposal_id, revision, attempt_number, runtime_root=runtime_root
    )
    review = load_operator_diagnosis_review(
        proposal_id, revision, attempt_number, runtime_root=runtime_root
    )
    decision = load_operator_diagnosis_decision(
        proposal_id, revision, attempt_number, runtime_root=runtime_root
    )
    if not repair or not review or not decision:
        return None, None, _failure(
            "supervised_repair_proposal_invalid",
            reason="sealed_review_decision_and_proposal_required",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    if repair.get("status") != "bounded_repair_proposal_authorization_required":
        return None, None, _failure(
            "supervised_repair_proposal_invalid",
            reason="authorization_required_proposal_expected",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    if (
        repair.get("repair_scope") != "one_bounded_isolated_attempt"
        or repair.get("repair_target") != "exact_failed_continuation_artifact"
        or int(repair.get("maximum_repair_attempts") or 0) != 1
        or repair.get("requires_exact_authorization") is not True
        or repair.get("repair_execution_authorized") is not False
        or not _valid_repair_proposal_digest(repair)
    ):
        return None, None, _failure(
            "supervised_repair_proposal_invalid",
            reason="bounded_repair_contract_invalid",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    expected_digest = _sha256(expected_repair_proposal_digest)
    if str(repair.get("repair_proposal_digest") or "") != expected_digest:
        return None, None, _failure(
            "supervised_repair_stale_authorization",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    if (
        str(repair.get("review_digest") or "") != str(review.get("review_digest") or "")
        or str(repair.get("operator_diagnosis_decision_digest") or "")
        != str(decision.get("operator_diagnosis_decision_digest") or "")
        or decision.get("decision") != "propose-repair"
        or decision.get("repair_proposal_requested") is not True
    ):
        return None, None, _failure(
            "supervised_repair_lineage_changed",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    continuation = load_conversational_build_test_continuation(
        proposal_id, revision, runtime_root=runtime_root
    )
    result = continuation.get("result") if isinstance(continuation, Mapping) else None
    if (
        not continuation
        or continuation.get("phase") != "sealed"
        or not isinstance(result, Mapping)
        or str(continuation.get("result_digest") or "") != _digest(result)
        or int(result.get("attempt_number") or 0) != int(attempt_number)
        or str(result.get("attempt_digest") or "") != str(repair.get("attempt_digest") or "")
        or str(result.get("continuation_result_digest") or "")
        != str(repair.get("continuation_result_digest") or "")
        or str(result.get("status") or "") not in DIAGNOSABLE_FAILURES
    ):
        return None, None, _failure(
            "supervised_repair_failed_artifact_invalid",
            proposal_id=proposal_id,
            revision=revision,
            attempt_number=attempt_number,
        )
    return dict(repair), dict(result), None


def _failed_workspace(
    proposal_id: str,
    revision: int,
    attempt_number: int,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    child = _attempt_runtime_root(proposal_id, revision, attempt_number, runtime_root)
    generation = _read_json(_generation_path(proposal_id, revision, child)) or {}
    workspace = _read_json(_workspace_record_path(proposal_id, revision, child)) or {}
    if not generation or not workspace:
        return {}, []
    generation_digest = _sha256(generation.get("generation_digest"))
    root = _workspace_root(proposal_id, revision, generation_digest, child)
    if not generation_digest or not _verify_workspace_record(workspace, root):
        raise ValueError("failed_workspace_invalid")
    files: list[dict[str, str]] = []
    total = 0
    for row in workspace.get("files") or []:
        relative = str(row.get("relative_path") or "")
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError("failed_workspace_file_invalid")
        content = path.read_text(encoding="utf-8")
        total += len(content.encode("utf-8"))
        if total > MAX_REPAIR_CONTEXT_BYTES:
            raise ValueError("repair_context_budget_exceeded")
        files.append({"path": relative, "content": content})
    return dict(workspace), files


def prepare_conversational_supervised_repair_execution(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_attempt_number: int,
    expected_repair_proposal_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one non-executing repair attempt from an exact v1214 proposal."""

    proposal_id = str(proposal_id or "").strip().lower()
    repair, failed, failure = _validated_lineage(
        proposal_id,
        expected_revision,
        expected_attempt_number,
        expected_repair_proposal_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert repair is not None and failed is not None
    try:
        workspace, _ = _failed_workspace(
            proposal_id,
            expected_revision,
            expected_attempt_number,
            runtime_root=runtime_root,
        )
    except Exception as error:
        return _failure(
            "supervised_repair_source_artifact_invalid",
            reason=_digest({"type": type(error).__name__}),
            proposal_id=proposal_id,
            revision=expected_revision,
            attempt_number=expected_attempt_number,
        )
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": str(repair.get("proposal_revision_digest") or ""),
        "failed_attempt_number": int(expected_attempt_number),
        "failed_attempt_digest": str(repair.get("attempt_digest") or ""),
        "failed_continuation_result_digest": str(repair.get("continuation_result_digest") or ""),
        "failed_loop_result_digest": str(failed.get("continuation_loop_result_digest") or ""),
        "diagnosis_digest": str(repair.get("diagnosis_digest") or ""),
        "diagnosis_result_digest": str(repair.get("diagnosis_result_digest") or ""),
        "review_digest": str(repair.get("review_digest") or ""),
        "operator_diagnosis_decision_digest": str(repair.get("operator_diagnosis_decision_digest") or ""),
        "repair_proposal_digest": str(repair.get("repair_proposal_digest") or ""),
        "bounded_repair_proposal_record_digest": str(repair.get("bounded_repair_proposal_record_digest") or ""),
        "source_workspace_digest": str(workspace.get("workspace_digest") or ""),
        "source_generation_digest": str(workspace.get("generation_digest") or ""),
        "project_kind": str(failed.get("project_kind") or ""),
        "selected_adapter_id": str(failed.get("selected_adapter_id") or ""),
        "repair_attempt_number": 1,
    }
    execution_digest = _digest(binding)
    row = {
        "ok": True,
        "status": "supervised_repair_execution_prepared",
        **binding,
        "supervised_repair_execution_digest": execution_digest,
        "authorization_phrase": _repair_authorization_phrase(
            str(repair.get("repair_proposal_digest") or ""),
            proposal_id,
            expected_revision,
            expected_attempt_number,
        ),
        "phase": "prepared",
        "lease_token": "",
        "lease_expires_unix": 0.0,
        "recovery_count": 0,
        **_base(
            proposal_id=proposal_id,
            revision=expected_revision,
            attempt_number=expected_attempt_number,
        ),
    }
    path = _execution_path(
        proposal_id, expected_revision, expected_attempt_number, runtime_root
    )
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid_record(existing):
                return _failure(
                    "supervised_repair_execution_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            if str(existing.get("supervised_repair_execution_digest") or "") != execution_digest:
                return _failure(
                    "supervised_repair_execution_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, _seal(row))
    return {**row, "supervised_repair_execution_record_digest": _record_digest(row), "operation_status": "created"}


def _seed_repair_runtime(
    proposal_id: str,
    revision: int,
    attempt_number: int,
    *,
    runtime_root=None,
) -> Path:
    proposal = _read_json(_proposal_path(proposal_id, runtime_root))
    if not proposal or not _validate(proposal):
        raise ValueError("invalid_parent_proposal")
    if int(proposal.get("revision") or 0) != int(revision) or not proposal.get("approval_consumed"):
        raise ValueError("stale_parent_proposal")
    receipt = _read_json(_approval_path(proposal_id, revision, runtime_root))
    if not receipt or not _valid_approval_receipt(receipt, proposal):
        raise ValueError("invalid_parent_approval")
    child = _repair_runtime_root(proposal_id, revision, attempt_number, runtime_root)
    child_proposal_path = _proposal_path(proposal_id, child)
    child_receipt_path = _approval_path(proposal_id, revision, child)
    existing_proposal = _read_json(child_proposal_path)
    existing_receipt = _read_json(child_receipt_path)
    if existing_proposal and existing_proposal != proposal:
        raise ValueError("repair_proposal_binding_changed")
    if existing_receipt and existing_receipt != receipt:
        raise ValueError("repair_approval_binding_changed")
    if not existing_proposal:
        _atomic_json(child_proposal_path, proposal)
    if not existing_receipt:
        _atomic_json(child_receipt_path, receipt)
    return child


def _repair_provider(
    provider_generate: Callable[[str], str] | None,
    *,
    failed_files: list[dict[str, str]],
    prepared: Mapping[str, Any],
) -> Callable[[str], str]:
    def generate(base_prompt: str) -> str:
        if provider_generate is None:
            from local_model import LocalModelClient
            provider = LocalModelClient().generate
        else:
            provider = provider_generate
        envelope = json.loads(base_prompt)
        envelope["task"] = (
            "Return ONLY one JSON object containing the complete bounded file changes for one "
            "isolated repair candidate. Preserve the authority object exactly. Do not use markdown."
        )
        envelope["repair_context"] = {
            "repair_proposal_digest": str(prepared.get("repair_proposal_digest") or ""),
            "failed_attempt_digest": str(prepared.get("failed_attempt_digest") or ""),
            "failed_continuation_result_digest": str(prepared.get("failed_continuation_result_digest") or ""),
            "diagnosis_digest": str(prepared.get("diagnosis_digest") or ""),
            "diagnosis_result_digest": str(prepared.get("diagnosis_result_digest") or ""),
            "source_workspace_digest": str(prepared.get("source_workspace_digest") or ""),
            "current_files": failed_files,
            "authority_boundary": {
                "one_isolated_attempt": True,
                "selected_project_write": False,
                "source_write": False,
                "apply": False,
                "installation": False,
                "promotion": False,
                "release": False,
            },
        }
        return provider(json.dumps(envelope, sort_keys=True, separators=(",", ":")))

    return generate


def authorize_and_run_conversational_supervised_repair(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_attempt_number: int,
    expected_repair_proposal_digest: str,
    authorization_phrase: str,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    node_executable: str | None = None,
    python_executable: str | None = None,
    chromium_executable: str | None = None,
) -> dict[str, Any]:
    """Consume exact authorization and run one isolated repair plus retest."""

    proposal_id = str(proposal_id or "").strip().lower()
    prepared = prepare_conversational_supervised_repair_execution(
        proposal_id,
        expected_revision=expected_revision,
        expected_attempt_number=expected_attempt_number,
        expected_repair_proposal_digest=expected_repair_proposal_digest,
        runtime_root=runtime_root,
    )
    if prepared.get("ok") is not True:
        return prepared
    expected_phrase = _repair_authorization_phrase(
        str(expected_repair_proposal_digest or ""),
        proposal_id,
        expected_revision,
        expected_attempt_number,
    )
    if str(authorization_phrase or "").strip().casefold() != expected_phrase.casefold():
        return _failure(
            "supervised_repair_exact_authorization_required",
            proposal_id=proposal_id,
            revision=expected_revision,
            attempt_number=expected_attempt_number,
        )

    path = _execution_path(proposal_id, expected_revision, expected_attempt_number, runtime_root)
    lease_token = uuid.uuid4().hex
    recovery_count = 0
    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid_record(current):
            return _failure(
                "supervised_repair_execution_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if current.get("phase") == "sealed":
            result = current.get("result")
            if not isinstance(result, Mapping) or str(current.get("result_digest") or "") != _digest(result):
                return _failure(
                    "supervised_repair_result_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    attempt_number=expected_attempt_number,
                )
            return {**dict(result), "operation_status": "resumed"}
        if current.get("phase") == "running" and float(current.get("lease_expires_unix") or 0.0) > time.time():
            return _failure(
                "supervised_repair_in_progress",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        if current.get("phase") not in {"prepared", "running"}:
            return _failure(
                "supervised_repair_execution_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        recovery_count = int(current.get("recovery_count") or 0) + int(current.get("phase") == "running")
        running = dict(current)
        running.update({
            "status": "supervised_repair_running",
            "phase": "running",
            "lease_token": lease_token,
            "lease_expires_unix": time.time() + REPAIR_LEASE_SECONDS,
            "recovery_count": recovery_count,
            **_authority(authorized=True),
        })
        _atomic_json(path, _seal(running))

    try:
        _, failed_files = _failed_workspace(
            proposal_id,
            expected_revision,
            expected_attempt_number,
            runtime_root=runtime_root,
        )
        child = _seed_repair_runtime(
            proposal_id,
            expected_revision,
            expected_attempt_number,
            runtime_root=runtime_root,
        )
        child_loop = prepare_conversational_build_test_loop(
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=str(prepared.get("proposal_revision_digest") or ""),
            runtime_root=child,
        )
        if child_loop.get("ok") is not True:
            child_result = child_loop
        else:
            child_result = authorize_and_run_conversational_build_test_loop(
                proposal_id,
                expected_revision=expected_revision,
                expected_revision_digest=str(prepared.get("proposal_revision_digest") or ""),
                expected_loop_digest=str(child_loop.get("loop_digest") or ""),
                authorization_phrase=str(child_loop.get("authorization_phrase") or ""),
                runtime_root=child,
                provider_generate=_repair_provider(
                    provider_generate,
                    failed_files=failed_files,
                    prepared=prepared,
                ),
                node_executable=node_executable,
                python_executable=python_executable,
                chromium_executable=chromium_executable,
            )
        ok, status, completed_stage = _RESULT_MAP.get(
            str(child_result.get("status") or ""),
            (False, "supervised_repair_internal_error", "internal"),
        )
        provider_contacted = bool(child_result.get("provider_contacted"))
        tests_executed = bool(child_result.get("tests_executed"))
        implementation = child_result.get("implementation")
        repair_workspace = _read_json(
            _workspace_record_path(proposal_id, expected_revision, child)
        ) or {}
        patch_generated = bool(isinstance(implementation, Mapping) and implementation.get("ok") is True)
        lineage = [
            {
                "stage": "failed_continuation_artifact",
                "artifact_digest": str(prepared.get("failed_continuation_result_digest") or ""),
            },
            {
                "stage": "authorized_repair_proposal",
                "artifact_digest": str(prepared.get("repair_proposal_digest") or ""),
            },
            {
                "stage": "isolated_repair_build_and_test",
                "artifact_digest": str(child_result.get("loop_result_digest") or ""),
            },
        ]
        result = {
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            ),
            "ok": ok,
            "status": status,
            "completed_stage": completed_stage,
            "supervised_repair_execution_digest": str(prepared.get("supervised_repair_execution_digest") or ""),
            "repair_proposal_digest": str(prepared.get("repair_proposal_digest") or ""),
            "bounded_repair_proposal_record_digest": str(prepared.get("bounded_repair_proposal_record_digest") or ""),
            "failed_attempt_digest": str(prepared.get("failed_attempt_digest") or ""),
            "failed_continuation_result_digest": str(prepared.get("failed_continuation_result_digest") or ""),
            "diagnosis_digest": str(prepared.get("diagnosis_digest") or ""),
            "diagnosis_result_digest": str(prepared.get("diagnosis_result_digest") or ""),
            "review_digest": str(prepared.get("review_digest") or ""),
            "source_workspace_digest": str(prepared.get("source_workspace_digest") or ""),
            "repair_workspace_digest": str(repair_workspace.get("workspace_digest") or ""),
            "repair_loop_digest": str(child_loop.get("loop_digest") or "") if isinstance(child_loop, Mapping) else "",
            "repair_loop_result_digest": str(child_result.get("loop_result_digest") or ""),
            "project_kind": str(prepared.get("project_kind") or ""),
            "selected_adapter_id": str(prepared.get("selected_adapter_id") or ""),
            "provider_contacted": provider_contacted,
            "tests_executed": tests_executed,
            "retest_executed": tests_executed,
            "test_passed": child_result.get("test_passed") if isinstance(child_result.get("test_passed"), bool) else None,
            "cleanup_confirmed": child_result.get("cleanup_confirmed") if isinstance(child_result.get("cleanup_confirmed"), bool) else None,
            "patch_generated": patch_generated,
            "repair_executed": provider_contacted or patch_generated,
            "repair_lineage": lineage,
            "repair_lineage_digest": _digest(lineage),
            "recovery_count": recovery_count,
            **_authority(authorized=True),
        }
    except Exception as error:
        result = _failure(
            "supervised_repair_internal_error",
            reason=_digest({"type": type(error).__name__}),
            proposal_id=proposal_id,
            revision=expected_revision,
            attempt_number=expected_attempt_number,
        )
        result.update({
            "supervised_repair_execution_digest": str(prepared.get("supervised_repair_execution_digest") or ""),
            "repair_proposal_digest": str(prepared.get("repair_proposal_digest") or ""),
            "retry_disposition": "same_authorized_repair_may_resume",
            "recovery_count": recovery_count,
            **_authority(authorized=True),
        })
    result["supervised_repair_result_digest"] = _digest({
        key: value for key, value in result.items() if key != "supervised_repair_result_digest"
    })

    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid_record(current) or str(current.get("lease_token") or "") != lease_token:
            return _failure(
                "supervised_repair_lease_lost",
                proposal_id=proposal_id,
                revision=expected_revision,
                attempt_number=expected_attempt_number,
            )
        sealed = dict(current)
        sealed.update({
            "status": str(result.get("status") or "supervised_repair_internal_error"),
            "phase": "sealed",
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "provider_contacted": bool(result.get("provider_contacted")),
            "tests_executed": bool(result.get("tests_executed")),
            "retest_executed": bool(result.get("retest_executed")),
            "patch_generated": bool(result.get("patch_generated")),
            "repair_executed": bool(result.get("repair_executed")),
            "result": result,
            "result_digest": _digest(result),
        })
        _atomic_json(path, _seal(sealed))
    return {**result, "operation_status": "recovered" if recovery_count else "created"}


def public_conversational_supervised_repair(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "proposal_revision_digest", "failed_attempt_number",
        "repair_attempt_number", "repair_attempt_limit", "failed_attempt_digest",
        "failed_continuation_result_digest", "failed_loop_result_digest", "diagnosis_digest",
        "diagnosis_result_digest", "review_digest", "operator_diagnosis_decision_digest",
        "repair_proposal_digest", "bounded_repair_proposal_record_digest",
        "source_workspace_digest", "source_generation_digest", "repair_workspace_digest",
        "project_kind", "selected_adapter_id", "supervised_repair_execution_digest",
        "supervised_repair_execution_record_digest", "supervised_repair_result_digest",
        "authorization_phrase", "phase", "completed_stage", "repair_loop_digest",
        "repair_loop_result_digest", "repair_lineage", "repair_lineage_digest",
        "provider_contacted", "tests_executed", "retest_executed", "test_passed",
        "cleanup_confirmed", "patch_generated", "repair_executed", "recovery_count",
        "operation_status", "retry_disposition", "operator_review_required",
        "repair_result_review_required", "runtime_records_external", "project_modified",
        "selected_project_modified", "source_modified", "repair_execution_authorized",
        "provider_contact_authorized", "test_execution_authorized", "retest_authorized",
        "apply_authorized", "rollback_authorized", "install_authorized",
        "promotion_authorized", "release_authorized", "model_management_authorized",
        "authority_granted",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "content_free": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    })
    public["public_supervised_repair_digest"] = _digest(public)
    return public


def conversational_supervised_repair_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "supervised_repair_execution_prepared":
        return (
            "The exact bounded repair proposal is prepared for one isolated attempt. "
            f"To authorize it, reply: {record.get('authorization_phrase', '')}"
        )
    if status == "supervised_repair_completed":
        return (
            "The exact supervised repair completed in isolation and its retained tests passed. "
            "The repaired candidate is ready for operator review; nothing was applied to the selected project."
        )
    if status == "supervised_repair_tests_failed":
        return "The isolated repair candidate was generated, but its retained tests still failed. Nothing was applied."
    if status == "supervised_repair_test_blocked":
        return "The isolated repair candidate was generated, but verification was blocked. Nothing was applied."
    if status == "supervised_repair_build_blocked":
        return "The authorized repair attempt was blocked before verification completed. Nothing was applied."
    if status == "supervised_repair_in_progress":
        return "That exact repair attempt is already running; no duplicate was started."
    return (
        "The supervised repair control was rejected because its exact proposal or evidence binding was invalid. "
        "No repair, retest, apply, installation, promotion, or release action was authorized."
    )


def process_conversational_supervised_repair_control(
    user_text: str,
    *,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    node_executable: str | None = None,
    python_executable: str | None = None,
    chromium_executable: str | None = None,
) -> dict[str, Any]:
    match = _AUTHORIZATION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision = int(match.group("revision"))
    attempt_number = int(match.group("attempt"))
    result = authorize_and_run_conversational_supervised_repair(
        proposal_id,
        expected_revision=revision,
        expected_attempt_number=attempt_number,
        expected_repair_proposal_digest=match.group("repair_digest").lower(),
        authorization_phrase=str(user_text or "").strip(),
        runtime_root=runtime_root,
        provider_generate=provider_generate,
        node_executable=node_executable,
        python_executable=python_executable,
        chromium_executable=chromium_executable,
    )
    public = public_conversational_supervised_repair(result)
    return {
        "active": True,
        "event": str(result.get("status") or "supervised_repair_control_blocked"),
        "supervised_repair_execution": public,
        "conversation_response": conversational_supervised_repair_response(result),
        "public_digest": _digest(public),
    }


def load_conversational_supervised_repair_execution(
    proposal_id: str, revision: int, attempt_number: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_execution_path(proposal_id, revision, attempt_number, runtime_root)) or {}
    return record if record and _valid_record(record) else {}
