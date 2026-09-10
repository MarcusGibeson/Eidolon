from __future__ import annotations

"""Supervised conversational build-and-test loop for v1210.0-v1210.8.

The loop is prepared only for an exactly approved development proposal.  A
second exact, digest-bound conversational authorization is required before the
existing small-project implementation coordinator or unified test adapter is
called.  Runtime records remain external; selected projects and Eidolon source
are never modified by this module.
"""

import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from grounded_development_planning import create_or_resume_grounded_plan
from isolated_implementation_workspace import _record_path as _workspace_record_path
from isolated_workspace_preview import _preview_path
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _proposal_path,
    _read_json,
    _store_root,
    _validate,
)
from unified_test_adapter_contract import (
    prepare_test_adapter_execution,
    run_or_resume_selected_test_adapter,
    select_test_adapter,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1210.8"
LOOP_LEASE_SECONDS = 120.0

AUTHORITY_FLAGS = {
    "build_authorized": False,
    "test_execution_authorized": False,
    "install_authorized": False,
    "diagnosis_authorized": False,
    "repair_authorized": False,
    "apply_authorized": False,
    "rollback_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}

SUPPORTED_LOOP_PROJECT_KINDS = frozenset({
    "new_small_web_project",
    "new_javascript_tool_project",
    "new_python_cli_project",
})

_AUTHORIZATION = re.compile(
    r"^(?:i\s+)?authorize\s+build\s+and\s+tests\s+for\s+(?:development\s+)?proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)\s+"
    r"loop\s+(?P<loop_digest>[a-f0-9]{64})[.!?]*$",
    re.I,
)


def _loop_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "conversational_build_test_loops" / proposal_id / f"revision-{int(revision)}.json"


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({key: value for key, value in record.items() if key != "loop_record_digest"})


def _record_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("loop_record_digest") or "")
    return bool(supplied and supplied == _record_digest(record))


def _seal(record: Mapping[str, Any]) -> dict[str, Any]:
    sealed = dict(record)
    sealed["loop_record_digest"] = _record_digest(sealed)
    return sealed


def _failure(status: str, *, reason: str = "", proposal_id: str = "", revision: int = 0) -> dict[str, Any]:
    result = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "reason": reason,
        "proposal_id": proposal_id,
        "proposal_revision": int(revision or 0),
        "operator_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
        "selected_project_modified": False,
        "source_modified": False,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        **AUTHORITY_FLAGS,
    }
    result["loop_result_digest"] = _digest(result)
    return result


def _authorization_phrase(proposal_id: str, revision: int, loop_digest: str) -> str:
    return f"Authorize build and tests for development proposal {proposal_id} revision {int(revision)} loop {loop_digest}."


def prepare_conversational_build_test_loop(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one non-executing loop request for an approved proposal."""

    proposal_id = str(proposal_id or "").strip().lower()
    with _proposal_lock(proposal_id, runtime_root):
        proposal = _read_json(_proposal_path(proposal_id, runtime_root))
        if not proposal:
            return _failure("conversational_build_test_proposal_missing", proposal_id=proposal_id, revision=expected_revision)
        if not _validate(proposal):
            return _failure("conversational_build_test_proposal_invalid", proposal_id=proposal_id, revision=expected_revision)
        if int(proposal.get("revision") or 0) != int(expected_revision) or str(proposal.get("revision_digest") or "") != str(expected_revision_digest or ""):
            return _failure("conversational_build_test_stale_proposal", proposal_id=proposal_id, revision=expected_revision)
        if not proposal.get("approval_consumed") or proposal.get("lifecycle_state") in {"rejected", "cancelled", "unsupported_request", "approval_receipt_invalid"}:
            return _failure("conversational_build_test_proposal_approval_required", proposal_id=proposal_id, revision=expected_revision)

    plan = create_or_resume_grounded_plan(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
    )
    if plan.get("planning_status") != "grounded_plan_ready" or not plan.get("planning_digest"):
        return _failure(str(plan.get("status") or "conversational_build_test_plan_unavailable"), proposal_id=proposal_id, revision=expected_revision)
    project_kind = str(plan.get("project_kind") or "")
    if project_kind not in SUPPORTED_LOOP_PROJECT_KINDS:
        return _failure("conversational_build_test_project_kind_unsupported", reason="new_small_project_required", proposal_id=proposal_id, revision=expected_revision)
    selection = select_test_adapter(project_kind)
    if selection.get("status") != "test_adapter_selected":
        return _failure(str(selection.get("status") or "conversational_build_test_adapter_unavailable"), reason=str(selection.get("reason") or "adapter_not_selected"), proposal_id=proposal_id, revision=expected_revision)

    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": str(expected_revision_digest),
        "approval_receipt_digest": str(plan.get("approval_receipt_digest") or ""),
        "planning_digest": str(plan.get("planning_digest") or ""),
        "project_snapshot_digest": str(plan.get("project_snapshot_digest") or ""),
        "project_kind": project_kind,
        "selected_adapter_id": str(selection.get("selected_adapter_id") or ""),
        "adapter_selection_digest": str(selection.get("selection_digest") or ""),
    }
    loop_digest = _digest(binding)
    path = _loop_path(proposal_id, expected_revision, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _record_valid(existing):
                return _failure("conversational_build_test_loop_record_invalid", proposal_id=proposal_id, revision=expected_revision)
            if str(existing.get("loop_digest") or "") != loop_digest:
                return _failure("conversational_build_test_loop_binding_changed", proposal_id=proposal_id, revision=expected_revision)
            return {**existing, "operation_status": "resumed"}
        record = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "conversational_build_test_authorization_required",
            **binding,
            "loop_digest": loop_digest,
            "authorization_phrase": _authorization_phrase(proposal_id, expected_revision, loop_digest),
            "phase": "prepared",
            "attempt_count": 0,
            "recovery_count": 0,
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "provider_contacted": False,
            "tests_executed": False,
            "selected_project_modified": False,
            "source_modified": False,
            "operator_review_required": True,
            "runtime_records_external": True,
            "private_request_exposed": False,
            "private_path_exposed": False,
            "private_content_exposed": False,
            **AUTHORITY_FLAGS,
        }
        record = _seal(record)
        _atomic_json(path, record)
        return {**record, "operation_status": "created"}


def _result_status(implementation: Mapping[str, Any], test_result: Mapping[str, Any]) -> tuple[bool, str, str]:
    if implementation.get("ok") is not True:
        return False, "conversational_build_test_build_blocked", "build"
    if test_result.get("status") != "test_adapter_execution_completed":
        return False, "conversational_build_test_test_blocked", "test"
    if (test_result.get("outcome") or {}).get("passed") is not True:
        return False, "conversational_build_test_tests_failed", "test"
    return True, "conversational_build_test_completed", "complete"


def authorize_and_run_conversational_build_test_loop(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_revision_digest: str,
    expected_loop_digest: str,
    authorization_phrase: str,
    runtime_root=None,
    provider_generate: Callable[[str], str] | None = None,
    node_executable: str | None = None,
    python_executable: str | None = None,
    chromium_executable: str | None = None,
) -> dict[str, Any]:
    """Consume exact loop authorization and delegate to preserved coordinators."""

    proposal_id = str(proposal_id or "").strip().lower()
    prepared = prepare_conversational_build_test_loop(
        proposal_id,
        expected_revision=expected_revision,
        expected_revision_digest=expected_revision_digest,
        runtime_root=runtime_root,
    )
    if prepared.get("ok") is not True:
        return prepared
    if str(prepared.get("loop_digest") or "") != str(expected_loop_digest or ""):
        return _failure("conversational_build_test_stale_authorization", proposal_id=proposal_id, revision=expected_revision)
    expected_phrase = _authorization_phrase(proposal_id, expected_revision, str(expected_loop_digest))
    if str(authorization_phrase or "").strip().casefold() != expected_phrase.casefold():
        return _failure("conversational_build_test_exact_authorization_required", proposal_id=proposal_id, revision=expected_revision)

    path = _loop_path(proposal_id, expected_revision, runtime_root)
    lease_token = uuid.uuid4().hex
    recovery_count = 0
    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _record_valid(current):
            return _failure("conversational_build_test_loop_record_invalid", proposal_id=proposal_id, revision=expected_revision)
        if current.get("phase") == "sealed":
            result = current.get("result")
            if not isinstance(result, Mapping) or str(current.get("result_digest") or "") != _digest(result):
                return _failure("conversational_build_test_result_invalid", proposal_id=proposal_id, revision=expected_revision)
            return {**dict(result), "operation_status": "resumed"}
        if current.get("phase") == "running" and float(current.get("lease_expires_unix") or 0.0) > time.time():
            return _failure("conversational_build_test_in_progress", proposal_id=proposal_id, revision=expected_revision)
        if current.get("phase") not in {"prepared", "running"}:
            return _failure("conversational_build_test_loop_record_invalid", proposal_id=proposal_id, revision=expected_revision)
        recovery_count = int(current.get("recovery_count") or 0) + int(current.get("phase") == "running")
        running = dict(current)
        running.update({
            "status": "conversational_build_test_running",
            "phase": "running",
            "attempt_count": int(current.get("attempt_count") or 0) + 1,
            "recovery_count": recovery_count,
            "lease_token": lease_token,
            "lease_expires_unix": time.time() + LOOP_LEASE_SECONDS,
            "build_authorized": True,
            "test_execution_authorized": True,
        })
        _atomic_json(path, _seal(running))

    try:
        from general_small_project_implementation import (
            public_general_small_project_result,
            run_or_resume_general_small_project_implementation,
        )

        implementation = run_or_resume_general_small_project_implementation(
            proposal_id,
            expected_revision=expected_revision,
            expected_revision_digest=expected_revision_digest,
            runtime_root=runtime_root,
            provider_generate=provider_generate,
            node_executable=node_executable,
            python_executable=python_executable,
        )
        public_implementation = public_general_small_project_result(implementation)
        from structured_development_generation import _path as _generation_record_path
        generation_record = _read_json(_generation_record_path(proposal_id, expected_revision, runtime_root)) or {}
        test_result: dict[str, Any]
        if implementation.get("ok") is True:
            workspace = _read_json(_workspace_record_path(proposal_id, expected_revision, runtime_root)) or {}
            preview = _read_json(_preview_path(proposal_id, expected_revision, runtime_root)) or {}
            request = prepare_test_adapter_execution(
                str(prepared.get("project_kind") or ""),
                proposal_id=proposal_id,
                expected_revision=expected_revision,
                expected_revision_digest=expected_revision_digest,
                expected_workspace_digest=str(workspace.get("workspace_digest") or ""),
                approval_receipt_digest=str(prepared.get("approval_receipt_digest") or ""),
                expected_preview_digest=str(preview.get("preview_digest") or "") or None,
                requested_adapter_id=str(prepared.get("selected_adapter_id") or ""),
                execution_authorized=True,
            )
            executable = {
                "browser_runtime": chromium_executable,
                "node_javascript": node_executable,
                "python": python_executable,
            }.get(str(prepared.get("selected_adapter_id") or ""))
            test_result = run_or_resume_selected_test_adapter(request, runtime_root=runtime_root, executable=executable)
        else:
            test_result = {
                "status": "test_adapter_not_started",
                "tests_executed": False,
                "outcome": {"state": "not_executed", "passed": None},
                "cleanup": {"state": "not_required", "cleanup_confirmed": None},
                "reliability": {"failure_class": "build_blocked", "retry_disposition": "same_loop_may_resume"},
                "authority": {"execution_authorized": True, **AUTHORITY_FLAGS},
            }
        ok, status, completed_stage = _result_status(implementation, test_result)
        result = {
            "ok": ok,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": status,
            "completed_stage": completed_stage,
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "proposal_revision_digest": str(expected_revision_digest),
            "loop_digest": str(expected_loop_digest),
            "project_kind": str(prepared.get("project_kind") or ""),
            "selected_adapter_id": str(prepared.get("selected_adapter_id") or ""),
            "implementation": public_implementation,
            "test_result": dict(test_result),
            "provider_contacted": bool(generation_record.get("provider_contacted")),
            "tests_executed": bool(test_result.get("tests_executed")),
            "test_passed": (test_result.get("outcome") or {}).get("passed"),
            "cleanup_confirmed": (test_result.get("cleanup") or {}).get("cleanup_confirmed"),
            "attempt_count": int(prepared.get("attempt_count") or 0) + 1,
            "recovery_count": recovery_count,
            "operator_review_required": True,
            "selected_project_modified": False,
            "source_modified": False,
            "runtime_records_external": True,
            "private_request_exposed": False,
            "private_path_exposed": False,
            "private_content_exposed": False,
            "raw_provider_output_exposed": False,
            "raw_test_output_exposed": False,
            **AUTHORITY_FLAGS,
            "build_authorized": True,
            "test_execution_authorized": True,
        }
    except Exception as error:
        result = _failure("conversational_build_test_internal_error", reason=_digest({"type": type(error).__name__}), proposal_id=proposal_id, revision=expected_revision)
        result.update({"loop_digest": str(expected_loop_digest), "retry_disposition": "same_loop_may_resume"})
    result["loop_result_digest"] = _digest({key: value for key, value in result.items() if key != "loop_result_digest"})

    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _record_valid(current) or str(current.get("lease_token") or "") != lease_token:
            return _failure("conversational_build_test_lease_lost", proposal_id=proposal_id, revision=expected_revision)
        sealed = dict(current)
        sealed.update({
            "status": str(result.get("status") or "conversational_build_test_internal_error"),
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


def process_conversational_build_test_control(
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
    proposal = _read_json(_proposal_path(proposal_id, runtime_root)) or {}
    result = authorize_and_run_conversational_build_test_loop(
        proposal_id,
        expected_revision=revision,
        expected_revision_digest=str(proposal.get("revision_digest") or ""),
        expected_loop_digest=match.group("loop_digest").lower(),
        authorization_phrase=str(user_text or "").strip(),
        runtime_root=runtime_root,
        provider_generate=provider_generate,
        node_executable=node_executable,
        python_executable=python_executable,
        chromium_executable=chromium_executable,
    )
    response = {
        "active": True,
        "event": str(result.get("status") or "conversational_build_test_control_blocked"),
        "build_test_loop": public_conversational_build_test_loop(result),
        "conversation_response": conversational_build_test_response(result),
        "public_digest": _digest(public_conversational_build_test_loop(result)),
    }
    # v1211 adds a content-free operator result after a sealed v1210 outcome.
    # Import lazily so the retained loop remains the sole build/test executor.
    if result.get("loop_result_digest") and result.get("status") in {
        "conversational_build_test_completed",
        "conversational_build_test_tests_failed",
        "conversational_build_test_test_blocked",
        "conversational_build_test_build_blocked",
        "conversational_build_test_internal_error",
    }:
        try:
            from operator_build_test_results import (
                create_or_resume_operator_build_test_result,
                operator_build_test_result_response,
                public_operator_build_test_record,
            )
            operator_result = create_or_resume_operator_build_test_result(
                proposal_id,
                expected_revision=revision,
                expected_loop_digest=match.group("loop_digest").lower(),
                expected_loop_result_digest=str(result.get("loop_result_digest") or ""),
                runtime_root=runtime_root,
            )
            response["operator_build_test_result"] = public_operator_build_test_record(operator_result)
            if operator_result.get("ok") is True:
                response["conversation_response"] = operator_build_test_result_response(operator_result)
        except Exception as error:
            response["operator_build_test_result"] = {
                "ok": False,
                "status": "operator_build_test_result_presentation_blocked",
                "reason_digest": _digest({"type": type(error).__name__}),
                "content_free": True,
                "authority_granted": False,
            }
    response["public_digest"] = _digest({key: value for key, value in response.items() if key != "conversation_response"})
    return response


def conversational_build_test_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "conversational_build_test_authorization_required":
        return (
            "The approved proposal is grounded and ready for a supervised build-and-test loop. "
            f"To authorize that exact loop, say: {record.get('authorization_phrase', '')}"
        )
    if status == "conversational_build_test_completed":
        return "The supervised build and tests completed successfully. The isolated result is ready for operator review; nothing was applied to the selected project."
    if status == "conversational_build_test_tests_failed":
        return "The supervised build completed, but its tests failed. The failure is review evidence only; no diagnosis, repair, or apply action was authorized."
    if status == "conversational_build_test_build_blocked":
        return "The supervised build was blocked before unified tests could run. No project files were applied or repaired."
    if status == "conversational_build_test_test_blocked":
        return "The isolated build completed, but the selected test adapter could not complete. No repair or apply action was authorized."
    if status == "conversational_build_test_in_progress":
        return "That exact build-and-test loop is already running; a duplicate execution was not started."
    return "The build-and-test control was rejected because its exact approval or lifecycle binding was not valid."


def public_conversational_build_test_loop(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "proposal_revision_digest", "approval_receipt_digest", "planning_digest",
        "project_snapshot_digest", "project_kind", "selected_adapter_id", "adapter_selection_digest",
        "loop_digest", "authorization_phrase", "phase", "attempt_count", "recovery_count",
        "provider_contacted", "tests_executed", "test_passed", "cleanup_confirmed", "completed_stage",
        "loop_result_digest", "operation_status", "operator_review_required", "runtime_records_external",
        "selected_project_modified", "source_modified", "build_authorized", "test_execution_authorized",
        "install_authorized", "diagnosis_authorized", "repair_authorized", "apply_authorized",
        "rollback_authorized", "promotion_authorized", "release_authorized",
        "model_management_authorized", "authority_granted",
    }
    projection = {key: record.get(key) for key in allowed if key in record}
    if isinstance(record.get("implementation"), Mapping):
        projection["implementation"] = dict(record["implementation"])
    if isinstance(record.get("test_result"), Mapping):
        projection["test_result"] = dict(record["test_result"])
    projection.update({
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    })
    return projection


def load_conversational_build_test_loop(proposal_id: str, revision: int, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_loop_path(proposal_id, revision, runtime_root)) or {}
    return record if record and _record_valid(record) else {}
