from __future__ import annotations

"""Operator-facing v1211 build/test results and continuation foundations.

The module projects one sealed v1210 build-and-test loop into a content-free,
durable operator result.  An exact conversational decision may accept, defer,
close, or prepare a later attempt.  Preparing an attempt does not contact a
provider, execute tests, diagnose, repair, apply, or grant execution authority.
Runtime records remain external to source packages.
"""

import re
from pathlib import Path
from typing import Any, Mapping

from conversational_build_test_loop import load_conversational_build_test_loop
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1211.8"

OUTCOME_BY_LOOP_STATUS = {
    "conversational_build_test_completed": "passed",
    "conversational_build_test_tests_failed": "tests_failed",
    "conversational_build_test_test_blocked": "test_blocked",
    "conversational_build_test_build_blocked": "build_blocked",
    "conversational_build_test_internal_error": "internal_error",
}

DECISIONS_BY_OUTCOME = {
    "passed": ("accept", "defer", "close"),
    "tests_failed": ("prepare-next-attempt", "defer", "close"),
    "test_blocked": ("prepare-next-attempt", "defer", "close"),
    "build_blocked": ("prepare-next-attempt", "defer", "close"),
    "internal_error": ("prepare-next-attempt", "defer", "close"),
}

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

_DECISION = re.compile(
    r"^record\s+(?P<decision>accept|defer|close|prepare-next-attempt)\s+for\s+"
    r"build-test\s+result\s+(?P<result_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)[.!?]*$",
    re.I,
)


def _result_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_build_test_results" / proposal_id / f"revision-{int(revision)}.json"


def _decision_path(proposal_id: str, revision: int, runtime_root=None) -> Path:
    return _store_root(runtime_root) / "operator_build_test_continuations" / proposal_id / f"revision-{int(revision)}.json"


def _sealed(record: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    row = dict(record)
    row[digest_field] = _digest({key: value for key, value in row.items() if key != digest_field})
    return row


def _valid(record: Mapping[str, Any], digest_field: str) -> bool:
    supplied = str(record.get(digest_field) or "")
    return bool(supplied and supplied == _digest({key: value for key, value in record.items() if key != digest_field}))


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
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }
    row["public_result_digest"] = _digest(row)
    return row


def _decision_phrase(decision: str, result_digest: str, proposal_id: str, revision: int) -> str:
    return (
        f"Record {decision} for build-test result {result_digest} "
        f"proposal {proposal_id} revision {int(revision)}."
    )


def project_operator_build_test_result(loop_record: Mapping[str, Any]) -> dict[str, Any]:
    """Create a content-free result projection from an already validated loop."""

    result = loop_record.get("result")
    if not isinstance(result, Mapping):
        return _failure("operator_build_test_result_unavailable", reason="sealed_result_missing")
    loop_status = str(result.get("status") or "")
    outcome = OUTCOME_BY_LOOP_STATUS.get(loop_status, "")
    if not outcome:
        return _failure("operator_build_test_result_unsupported", reason="unsupported_loop_status")
    proposal_id = str(result.get("proposal_id") or loop_record.get("proposal_id") or "")
    revision = int(result.get("proposal_revision") or loop_record.get("proposal_revision") or 0)
    loop_digest = str(result.get("loop_digest") or loop_record.get("loop_digest") or "")
    loop_result_digest = str(result.get("loop_result_digest") or "")
    stored_result_digest = str(loop_record.get("result_digest") or "")
    if len(loop_digest) != 64 or len(loop_result_digest) != 64 or len(stored_result_digest) != 64:
        return _failure("operator_build_test_result_invalid", reason="invalid_digest_binding", proposal_id=proposal_id, revision=revision)
    if loop_result_digest != _digest({key: value for key, value in result.items() if key != "loop_result_digest"}):
        return _failure("operator_build_test_result_invalid", reason="tampered_loop_result", proposal_id=proposal_id, revision=revision)
    if stored_result_digest != _digest(result):
        return _failure("operator_build_test_result_invalid", reason="tampered_sealed_result", proposal_id=proposal_id, revision=revision)
    available = list(DECISIONS_BY_OUTCOME[outcome])
    row = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "operator_build_test_result_review_required",
        "proposal_id": proposal_id,
        "proposal_revision": revision,
        "proposal_revision_digest": str(result.get("proposal_revision_digest") or ""),
        "loop_digest": loop_digest,
        "loop_result_digest": loop_result_digest,
        "sealed_result_digest": stored_result_digest,
        "outcome": outcome,
        "completed_stage": str(result.get("completed_stage") or ""),
        "project_kind": str(result.get("project_kind") or ""),
        "selected_adapter_id": str(result.get("selected_adapter_id") or ""),
        "provider_contacted": bool(result.get("provider_contacted")),
        "tests_executed": bool(result.get("tests_executed")),
        "test_passed": result.get("test_passed") if isinstance(result.get("test_passed"), bool) else None,
        "cleanup_confirmed": result.get("cleanup_confirmed") if isinstance(result.get("cleanup_confirmed"), bool) else None,
        "attempt_count": max(0, int(result.get("attempt_count") or 0)),
        "recovery_count": max(0, int(result.get("recovery_count") or 0)),
        "available_decisions": available,
        "decision_phrases": [],
        "operator_review_required": True,
        "continuation_prepared": False,
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
    unsigned = dict(row)
    result_digest = _digest(unsigned)
    row["operator_result_digest"] = result_digest
    row["decision_phrases"] = [
        _decision_phrase(decision, result_digest, proposal_id, revision) for decision in available
    ]
    return _sealed(row, "operator_result_record_digest")


def create_or_resume_operator_build_test_result(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_loop_digest: str,
    expected_loop_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    proposal_id = str(proposal_id or "").strip().lower()
    loop = load_conversational_build_test_loop(proposal_id, expected_revision, runtime_root=runtime_root)
    if not loop:
        return _failure("operator_build_test_loop_missing_or_invalid", proposal_id=proposal_id, revision=expected_revision)
    if loop.get("phase") != "sealed" or not isinstance(loop.get("result"), Mapping):
        return _failure("operator_build_test_result_not_sealed", proposal_id=proposal_id, revision=expected_revision)
    if str(loop.get("loop_digest") or "") != str(expected_loop_digest or ""):
        return _failure("operator_build_test_result_stale_loop", proposal_id=proposal_id, revision=expected_revision)
    if str(loop.get("result", {}).get("loop_result_digest") or "") != str(expected_loop_result_digest or ""):
        return _failure("operator_build_test_result_stale_result", proposal_id=proposal_id, revision=expected_revision)
    projected = project_operator_build_test_result(loop)
    if projected.get("ok") is not True:
        return projected
    path = _result_path(proposal_id, expected_revision, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_result_record_digest"):
                return _failure("operator_build_test_result_record_invalid", proposal_id=proposal_id, revision=expected_revision)
            if str(existing.get("operator_result_digest") or "") != str(projected.get("operator_result_digest") or ""):
                return _failure("operator_build_test_result_binding_changed", proposal_id=proposal_id, revision=expected_revision)
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, projected)
    return {**projected, "operation_status": "created"}


def record_operator_build_test_decision(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_operator_result_digest: str,
    decision: str,
    decision_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    proposal_id = str(proposal_id or "").strip().lower()
    decision = str(decision or "").strip().lower()
    result_path = _result_path(proposal_id, expected_revision, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        result = _read_json(result_path)
        if not result or not _valid(result, "operator_result_record_digest"):
            return _failure("operator_build_test_result_record_invalid", proposal_id=proposal_id, revision=expected_revision)
        if str(result.get("operator_result_digest") or "") != str(expected_operator_result_digest or ""):
            return _failure("operator_build_test_decision_stale_result", proposal_id=proposal_id, revision=expected_revision)
        allowed = tuple(result.get("available_decisions") or ())
        if decision not in allowed:
            return _failure("operator_build_test_decision_not_allowed", reason="outcome_decision_mismatch", proposal_id=proposal_id, revision=expected_revision)
        expected_phrase = _decision_phrase(decision, expected_operator_result_digest, proposal_id, expected_revision)
        if str(decision_phrase or "").strip().casefold() != expected_phrase.casefold():
            return _failure("operator_build_test_exact_decision_required", proposal_id=proposal_id, revision=expected_revision)
        path = _decision_path(proposal_id, expected_revision, runtime_root)
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "continuation_record_digest"):
                return _failure("operator_build_test_continuation_record_invalid", proposal_id=proposal_id, revision=expected_revision)
            if str(existing.get("operator_result_digest") or "") != str(expected_operator_result_digest):
                return _failure("operator_build_test_continuation_binding_changed", proposal_id=proposal_id, revision=expected_revision)
            if str(existing.get("decision") or "") != decision:
                return _failure("operator_build_test_conflicting_decision", proposal_id=proposal_id, revision=expected_revision)
            return {**existing, "operation_status": "resumed"}
        state = {
            "accept": "accepted",
            "defer": "deferred",
            "close": "closed",
            "prepare-next-attempt": "next_attempt_prepared",
        }[decision]
        row = {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "status": "operator_build_test_decision_recorded",
            "proposal_id": proposal_id,
            "proposal_revision": int(expected_revision),
            "loop_digest": str(result.get("loop_digest") or ""),
            "loop_result_digest": str(result.get("loop_result_digest") or ""),
            "operator_result_digest": str(expected_operator_result_digest),
            "outcome": str(result.get("outcome") or ""),
            "decision": decision,
            "continuation_state": state,
            "continuation_prepared": decision == "prepare-next-attempt",
            "automatic_continuation": False,
            "operator_review_required": decision == "prepare-next-attempt",
            "provider_contacted": False,
            "tests_executed": False,
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
        row["continuation_digest"] = _digest(row)
        row = _sealed(row, "continuation_record_digest")
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def operator_build_test_result_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "operator_build_test_result_review_required":
        outcome = str(record.get("outcome") or "result").replace("_", " ")
        phrases = list(record.get("decision_phrases") or [])
        choices = " ".join(f"Say: {phrase}" for phrase in phrases)
        return f"The isolated build-and-test result is {outcome} and ready for your review. {choices}".strip()
    if status == "operator_build_test_decision_recorded":
        if record.get("decision") == "prepare-next-attempt":
            return "A next build-and-test attempt is prepared for later, separate authorization. Nothing was executed, diagnosed, repaired, or applied."
        return f"The {record.get('decision', 'operator')} decision was recorded. No additional work was started."
    return "The build-and-test result control was rejected because its exact result or decision binding was not valid."


def public_operator_build_test_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "proposal_revision_digest", "loop_digest", "loop_result_digest",
        "sealed_result_digest", "operator_result_digest", "operator_result_record_digest",
        "outcome", "completed_stage", "project_kind", "selected_adapter_id", "provider_contacted",
        "tests_executed", "test_passed", "cleanup_confirmed", "attempt_count", "recovery_count",
        "available_decisions", "decision_phrases", "decision", "continuation_state",
        "continuation_prepared", "continuation_digest", "continuation_record_digest",
        "automatic_continuation", "operation_status", "operator_review_required",
        "runtime_records_external", "selected_project_modified", "source_modified",
        "continuation_execution_authorized", "provider_contact_authorized",
        "test_execution_authorized", "diagnosis_authorized", "repair_authorized",
        "apply_authorized", "rollback_authorized", "install_authorized",
        "promotion_authorized", "release_authorized", "model_management_authorized",
        "authority_granted",
    }
    projection = {key: record.get(key) for key in allowed if key in record}
    projection.update({
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    })
    return projection


def process_operator_build_test_result_control(user_text: str, *, runtime_root=None) -> dict[str, Any]:
    match = _DECISION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision = int(match.group("revision"))
    decision = match.group("decision").lower()
    record = record_operator_build_test_decision(
        proposal_id,
        expected_revision=revision,
        expected_operator_result_digest=match.group("result_digest").lower(),
        decision=decision,
        decision_phrase=str(user_text or "").strip(),
        runtime_root=runtime_root,
    )
    public = public_operator_build_test_record(record)
    response = {
        "active": True,
        "event": str(record.get("status") or "operator_build_test_result_control_blocked"),
        "operator_build_test_result": public,
        "conversation_response": operator_build_test_result_response(record),
        "public_digest": _digest(public),
    }
    if record.get("ok") is True and record.get("decision") == "prepare-next-attempt":
        try:
            from conversational_build_test_continuation import (
                conversational_build_test_continuation_response,
                prepare_conversational_build_test_continuation,
                public_conversational_build_test_continuation,
            )
            prepared = prepare_conversational_build_test_continuation(
                proposal_id,
                expected_revision=revision,
                expected_operator_result_digest=str(record.get("operator_result_digest") or ""),
                expected_continuation_digest=str(record.get("continuation_digest") or ""),
                runtime_root=runtime_root,
            )
            response["build_test_continuation"] = public_conversational_build_test_continuation(prepared)
            if prepared.get("ok") is True:
                response["conversation_response"] = conversational_build_test_continuation_response(prepared)
        except Exception as error:
            response["build_test_continuation"] = {
                "ok": False,
                "status": "build_test_continuation_preparation_blocked",
                "reason_digest": _digest({"type": type(error).__name__}),
                "content_free": True,
                "authority_granted": False,
            }
    response["public_digest"] = _digest({key: value for key, value in response.items() if key != "conversation_response"})
    return response


def load_operator_build_test_result(proposal_id: str, revision: int, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_result_path(proposal_id, revision, runtime_root)) or {}
    return record if record and _valid(record, "operator_result_record_digest") else {}


def load_operator_build_test_continuation(proposal_id: str, revision: int, *, runtime_root=None) -> dict[str, Any]:
    record = _read_json(_decision_path(proposal_id, revision, runtime_root)) or {}
    return record if record and _valid(record, "continuation_record_digest") else {}
