from __future__ import annotations

"""Supervised v1212 conversational build-and-test continuation execution.

One exact v1211 ``prepare-next-attempt`` decision may prepare one continuation
attempt.  A separate digest-bound conversational authorization is required
before the retained v1210 build/test loop is invoked in a fresh external
attempt namespace.  The module adds no diagnosis, repair, apply, installation,
promotion, release, model-management, or independent authority.
"""

import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from conversational_build_test_loop import (
    authorize_and_run_conversational_build_test_loop,
    load_conversational_build_test_loop,
    prepare_conversational_build_test_loop,
)
from operator_build_test_results import (
    load_operator_build_test_continuation,
    load_operator_build_test_result,
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

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1212.8"
ATTEMPT_LEASE_SECONDS = 120.0

AUTHORITY_FLAGS = {
    "continuation_execution_authorized": False,
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "diagnosis_authorized": False,
    "repair_authorized": False,
    "apply_authorized": False,
    "rollback_authorized": False,
    "install_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}

_AUTHORIZATION = re.compile(
    r"^(?:i\s+)?authorize\s+continuation\s+build\s+and\s+tests\s+for\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)\s+"
    r"attempt\s+(?P<attempt>[2-9][0-9]*)\s+(?P<attempt_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)

_STATUS_MAP = {
    "conversational_build_test_completed": (True, "conversational_build_test_continuation_completed", "complete"),
    "conversational_build_test_tests_failed": (False, "conversational_build_test_continuation_tests_failed", "test"),
    "conversational_build_test_test_blocked": (False, "conversational_build_test_continuation_test_blocked", "test"),
    "conversational_build_test_build_blocked": (False, "conversational_build_test_continuation_build_blocked", "build"),
    "conversational_build_test_internal_error": (False, "conversational_build_test_continuation_internal_error", "internal"),
}


def _attempt_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "conversational_build_test_continuations"
        / proposal_id
        / f"revision-{int(revision)}.json"
    )


def _attempt_runtime_root(proposal_id: str, revision: int, attempt_number: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "continuation_attempt_runtime"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"attempt-{int(attempt_number)}"
    )


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({key: value for key, value in record.items() if key != "continuation_attempt_record_digest"})


def _valid_record(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("continuation_attempt_record_digest") or "")
    return bool(supplied and supplied == _record_digest(record))


def _seal(record: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(record)
    row["continuation_attempt_record_digest"] = _record_digest(row)
    return row


def _failure(status: str, *, reason: str = "", proposal_id: str = "", revision: int = 0) -> dict[str, Any]:
    row = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "reason": reason,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "operator_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "runtime_records_external": True,
        "automatic_continuation": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }
    row["continuation_result_digest"] = _digest(row)
    return row


def _authorization_phrase(proposal_id: str, revision: int, attempt_number: int, attempt_digest: str) -> str:
    return (
        f"Authorize continuation build and tests for proposal {proposal_id} revision {int(revision)} "
        f"attempt {int(attempt_number)} {attempt_digest}."
    )


def _validated_bindings(
    proposal_id: str,
    revision: int,
    expected_operator_result_digest: str,
    expected_continuation_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    decision = load_operator_build_test_continuation(proposal_id, revision, runtime_root=runtime_root)
    if not decision or decision.get("decision") != "prepare-next-attempt" or decision.get("continuation_state") != "next_attempt_prepared":
        return None, None, None, _failure(
            "build_test_continuation_preparation_required", proposal_id=proposal_id, revision=revision
        )
    if str(decision.get("operator_result_digest") or "") != str(expected_operator_result_digest or ""):
        return None, None, None, _failure(
            "build_test_continuation_stale_operator_result", proposal_id=proposal_id, revision=revision
        )
    if str(decision.get("continuation_digest") or "") != str(expected_continuation_digest or ""):
        return None, None, None, _failure(
            "build_test_continuation_stale_decision", proposal_id=proposal_id, revision=revision
        )
    result = load_operator_build_test_result(proposal_id, revision, runtime_root=runtime_root)
    if not result or str(result.get("operator_result_digest") or "") != str(expected_operator_result_digest or ""):
        return None, None, None, _failure(
            "build_test_continuation_operator_result_invalid", proposal_id=proposal_id, revision=revision
        )
    parent = load_conversational_build_test_loop(proposal_id, revision, runtime_root=runtime_root)
    if not parent or parent.get("phase") != "sealed" or not isinstance(parent.get("result"), Mapping):
        return None, None, None, _failure(
            "build_test_continuation_parent_loop_invalid", proposal_id=proposal_id, revision=revision
        )
    if str(parent.get("loop_digest") or "") != str(decision.get("loop_digest") or ""):
        return None, None, None, _failure(
            "build_test_continuation_parent_loop_changed", proposal_id=proposal_id, revision=revision
        )
    if str(parent.get("result", {}).get("loop_result_digest") or "") != str(decision.get("loop_result_digest") or ""):
        return None, None, None, _failure(
            "build_test_continuation_parent_result_changed", proposal_id=proposal_id, revision=revision
        )
    return decision, result, parent, None


def prepare_conversational_build_test_continuation(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_operator_result_digest: str,
    expected_continuation_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one non-executing continuation attempt from an exact v1211 decision."""

    proposal_id = str(proposal_id or "").strip().lower()
    decision, result, parent, failure = _validated_bindings(
        proposal_id,
        expected_revision,
        expected_operator_result_digest,
        expected_continuation_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert decision is not None and result is not None and parent is not None
    prior_attempt = max(1, int(parent.get("result", {}).get("attempt_count") or 1))
    attempt_number = prior_attempt + 1
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": str(result.get("proposal_revision_digest") or ""),
        "parent_loop_digest": str(decision.get("loop_digest") or ""),
        "parent_loop_result_digest": str(decision.get("loop_result_digest") or ""),
        "operator_result_digest": str(expected_operator_result_digest),
        "continuation_digest": str(expected_continuation_digest),
        "continuation_record_digest": str(decision.get("continuation_record_digest") or ""),
        "project_kind": str(result.get("project_kind") or ""),
        "selected_adapter_id": str(result.get("selected_adapter_id") or ""),
        "attempt_number": attempt_number,
    }
    attempt_digest = _digest(binding)
    path = _attempt_path(proposal_id, expected_revision, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid_record(existing):
                return _failure("build_test_continuation_record_invalid", proposal_id=proposal_id, revision=expected_revision)
            if str(existing.get("attempt_digest") or "") != attempt_digest:
                return _failure("build_test_continuation_binding_changed", proposal_id=proposal_id, revision=expected_revision)
            return {**existing, "operation_status": "resumed"}
        row = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "status": "build_test_continuation_authorization_required",
            **binding,
            "attempt_digest": attempt_digest,
            "authorization_phrase": _authorization_phrase(proposal_id, expected_revision, attempt_number, attempt_digest),
            "phase": "prepared",
            "attempt_count": attempt_number,
            "recovery_count": 0,
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "provider_contacted": False,
            "tests_executed": False,
            "operator_review_required": True,
            "automatic_continuation": False,
            "selected_project_modified": False,
            "source_modified": False,
            "runtime_records_external": True,
            "private_request_exposed": False,
            "private_path_exposed": False,
            "private_content_exposed": False,
            "raw_provider_output_exposed": False,
            "raw_test_output_exposed": False,
            **AUTHORITY_FLAGS,
        }
        row = _seal(row)
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def _seed_attempt_runtime(
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
    child = _attempt_runtime_root(proposal_id, revision, attempt_number, runtime_root)
    child_proposal_path = _proposal_path(proposal_id, child)
    child_receipt_path = _approval_path(proposal_id, revision, child)
    existing_proposal = _read_json(child_proposal_path)
    existing_receipt = _read_json(child_receipt_path)
    if existing_proposal and existing_proposal != proposal:
        raise ValueError("attempt_proposal_binding_changed")
    if existing_receipt and existing_receipt != receipt:
        raise ValueError("attempt_approval_binding_changed")
    if not existing_proposal:
        _atomic_json(child_proposal_path, proposal)
    if not existing_receipt:
        _atomic_json(child_receipt_path, receipt)
    return child


def authorize_and_run_conversational_build_test_continuation(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_operator_result_digest: str,
    expected_continuation_digest: str,
    expected_attempt_digest: str,
    authorization_phrase: str,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    node_executable: str | None = None,
    python_executable: str | None = None,
    chromium_executable: str | None = None,
) -> dict[str, Any]:
    """Consume exact continuation authorization and invoke the retained v1210 loop."""

    proposal_id = str(proposal_id or "").strip().lower()
    prepared = prepare_conversational_build_test_continuation(
        proposal_id,
        expected_revision=expected_revision,
        expected_operator_result_digest=expected_operator_result_digest,
        expected_continuation_digest=expected_continuation_digest,
        runtime_root=runtime_root,
    )
    if prepared.get("ok") is not True:
        return prepared
    if str(prepared.get("attempt_digest") or "") != str(expected_attempt_digest or ""):
        return _failure("build_test_continuation_stale_authorization", proposal_id=proposal_id, revision=expected_revision)
    expected_phrase = _authorization_phrase(
        proposal_id, expected_revision, int(prepared.get("attempt_number") or 0), str(expected_attempt_digest)
    )
    if str(authorization_phrase or "").strip().casefold() != expected_phrase.casefold():
        return _failure("build_test_continuation_exact_authorization_required", proposal_id=proposal_id, revision=expected_revision)

    path = _attempt_path(proposal_id, expected_revision, runtime_root)
    lease_token = uuid.uuid4().hex
    recovery_count = 0
    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid_record(current):
            return _failure("build_test_continuation_record_invalid", proposal_id=proposal_id, revision=expected_revision)
        if current.get("phase") == "sealed":
            result = current.get("result")
            if not isinstance(result, Mapping) or str(current.get("result_digest") or "") != _digest(result):
                return _failure("build_test_continuation_result_invalid", proposal_id=proposal_id, revision=expected_revision)
            return {**dict(result), "operation_status": "resumed"}
        if current.get("phase") == "running" and float(current.get("lease_expires_unix") or 0.0) > time.time():
            return _failure("build_test_continuation_in_progress", proposal_id=proposal_id, revision=expected_revision)
        if current.get("phase") not in {"prepared", "running"}:
            return _failure("build_test_continuation_record_invalid", proposal_id=proposal_id, revision=expected_revision)
        recovery_count = int(current.get("recovery_count") or 0) + int(current.get("phase") == "running")
        running = dict(current)
        running.update({
            "status": "build_test_continuation_running",
            "phase": "running",
            "recovery_count": recovery_count,
            "lease_token": lease_token,
            "lease_expires_unix": time.time() + ATTEMPT_LEASE_SECONDS,
            "continuation_execution_authorized": True,
            "provider_contact_authorized": True,
            "test_execution_authorized": True,
        })
        _atomic_json(path, _seal(running))

    try:
        child = _seed_attempt_runtime(
            proposal_id,
            expected_revision,
            int(prepared.get("attempt_number") or 0),
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
                provider_generate=provider_generate,
                node_executable=node_executable,
                python_executable=python_executable,
                chromium_executable=chromium_executable,
            )
        ok, status, completed_stage = _STATUS_MAP.get(
            str(child_result.get("status") or ""),
            (False, "conversational_build_test_continuation_internal_error", "internal"),
        )
        parent_line = {
            "attempt_number": int(prepared.get("attempt_number") or 2) - 1,
            "attempt_kind": "initial",
            "loop_digest": str(prepared.get("parent_loop_digest") or ""),
            "result_digest": str(prepared.get("parent_loop_result_digest") or ""),
        }
        continuation_line = {
            "attempt_number": int(prepared.get("attempt_number") or 2),
            "attempt_kind": "operator_authorized_continuation",
            "loop_digest": str(child_loop.get("loop_digest") or "") if isinstance(child_loop, Mapping) else "",
            "result_digest": str(child_result.get("loop_result_digest") or ""),
        }
        lineage = [parent_line, continuation_line]
        result = {
            "ok": ok,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": status,
            "completed_stage": completed_stage,
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": str(prepared.get("proposal_revision_digest") or ""),
            "operator_result_digest": str(expected_operator_result_digest),
            "continuation_digest": str(expected_continuation_digest),
            "attempt_number": int(prepared.get("attempt_number") or 0),
            "attempt_digest": str(expected_attempt_digest),
            "parent_loop_digest": str(prepared.get("parent_loop_digest") or ""),
            "parent_loop_result_digest": str(prepared.get("parent_loop_result_digest") or ""),
            "continuation_loop_digest": continuation_line["loop_digest"],
            "continuation_loop_result_digest": continuation_line["result_digest"],
            "lineage": lineage,
            "lineage_digest": _digest(lineage),
            "project_kind": str(prepared.get("project_kind") or ""),
            "selected_adapter_id": str(prepared.get("selected_adapter_id") or ""),
            "provider_contacted": bool(child_result.get("provider_contacted")),
            "tests_executed": bool(child_result.get("tests_executed")),
            "test_passed": child_result.get("test_passed") if isinstance(child_result.get("test_passed"), bool) else None,
            "cleanup_confirmed": child_result.get("cleanup_confirmed") if isinstance(child_result.get("cleanup_confirmed"), bool) else None,
            "recovery_count": recovery_count,
            "operator_review_required": True,
            "automatic_continuation": False,
            "selected_project_modified": False,
            "source_modified": False,
            "runtime_records_external": True,
            "private_request_exposed": False,
            "private_path_exposed": False,
            "private_content_exposed": False,
            "raw_provider_output_exposed": False,
            "raw_test_output_exposed": False,
            **AUTHORITY_FLAGS,
            "continuation_execution_authorized": True,
            "provider_contact_authorized": True,
            "test_execution_authorized": True,
        }
    except Exception as error:
        result = _failure(
            "conversational_build_test_continuation_internal_error",
            reason=_digest({"type": type(error).__name__}),
            proposal_id=proposal_id,
            revision=expected_revision,
        )
        result.update({
            "attempt_number": int(prepared.get("attempt_number") or 0),
            "attempt_digest": str(expected_attempt_digest),
            "parent_loop_digest": str(prepared.get("parent_loop_digest") or ""),
            "parent_loop_result_digest": str(prepared.get("parent_loop_result_digest") or ""),
            "retry_disposition": "same_authorized_attempt_may_resume",
        })
    result["continuation_result_digest"] = _digest(
        {key: value for key, value in result.items() if key != "continuation_result_digest"}
    )

    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _valid_record(current) or str(current.get("lease_token") or "") != lease_token:
            return _failure("build_test_continuation_lease_lost", proposal_id=proposal_id, revision=expected_revision)
        sealed = dict(current)
        sealed.update({
            "status": str(result.get("status") or "conversational_build_test_continuation_internal_error"),
            "phase": "sealed",
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "provider_contacted": bool(result.get("provider_contacted")),
            "tests_executed": bool(result.get("tests_executed")),
            "result": result,
            "result_digest": _digest(result),
        })
        _atomic_json(path, _seal(sealed))
    return {**result, "operation_status": "recovered" if recovery_count else "created"}


def conversational_build_test_continuation_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "build_test_continuation_authorization_required":
        return (
            "The reviewed build-and-test result has one continuation attempt prepared. "
            f"To authorize that exact attempt, say: {record.get('authorization_phrase', '')}"
        )
    if status == "conversational_build_test_continuation_completed":
        return "The separately authorized continuation build and tests completed successfully. The isolated result is ready for operator review; nothing was applied."
    if status == "conversational_build_test_continuation_tests_failed":
        return "The continuation build completed, but its tests failed. No diagnosis, repair, or apply action was authorized."
    if status == "conversational_build_test_continuation_build_blocked":
        return "The continuation build was blocked before tests completed. No diagnosis, repair, or project change was authorized."
    if status == "conversational_build_test_continuation_test_blocked":
        return "The continuation build completed, but its test adapter was blocked. No diagnosis, repair, or apply action was authorized."
    if status == "build_test_continuation_in_progress":
        return "That exact continuation attempt is already running; no duplicate was started."
    return "The continuation control was rejected because its exact review, decision, or attempt binding was not valid."


def public_conversational_build_test_continuation(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "proposal_revision_digest", "parent_loop_digest",
        "parent_loop_result_digest", "operator_result_digest", "continuation_digest",
        "continuation_record_digest", "project_kind", "selected_adapter_id", "attempt_number",
        "attempt_count", "attempt_digest", "authorization_phrase", "phase", "recovery_count",
        "completed_stage", "continuation_loop_digest", "continuation_loop_result_digest",
        "lineage", "lineage_digest", "provider_contacted", "tests_executed", "test_passed",
        "cleanup_confirmed", "continuation_result_digest", "operation_status",
        "operator_review_required", "automatic_continuation", "runtime_records_external",
        "selected_project_modified", "source_modified", "continuation_execution_authorized",
        "provider_contact_authorized", "test_execution_authorized", "diagnosis_authorized",
        "repair_authorized", "apply_authorized", "rollback_authorized", "install_authorized",
        "promotion_authorized", "release_authorized", "model_management_authorized",
        "authority_granted", "retry_disposition",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    })
    return public


def process_conversational_build_test_continuation_control(
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
    prepared = _read_json(_attempt_path(proposal_id, revision, runtime_root))
    if not prepared or not _valid_record(prepared) or int(prepared.get("attempt_number") or 0) != attempt_number:
        result = _failure("build_test_continuation_record_invalid", proposal_id=proposal_id, revision=revision)
    else:
        result = authorize_and_run_conversational_build_test_continuation(
            proposal_id,
            expected_revision=revision,
            expected_operator_result_digest=str(prepared.get("operator_result_digest") or ""),
            expected_continuation_digest=str(prepared.get("continuation_digest") or ""),
            expected_attempt_digest=match.group("attempt_digest").lower(),
            authorization_phrase=str(user_text or "").strip(),
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
            python_executable=python_executable,
            chromium_executable=chromium_executable,
        )
    public = public_conversational_build_test_continuation(result)
    return {
        "active": True,
        "event": str(result.get("status") or "build_test_continuation_control_blocked"),
        "build_test_continuation": public,
        "conversation_response": conversational_build_test_continuation_response(result),
        "public_digest": _digest(public),
    }


def load_conversational_build_test_continuation(proposal_id: str, revision: int, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_attempt_path(proposal_id, revision, runtime_root)) or {}
    return record if record and _valid_record(record) else {}
