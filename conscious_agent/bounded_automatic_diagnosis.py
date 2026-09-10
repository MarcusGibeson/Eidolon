from __future__ import annotations

"""Evidence-bound automatic diagnosis for failed v1212 continuations.

One exact sealed continuation result may produce one bounded, content-free
diagnosis record.  Diagnosis is deterministic and provider-free: it classifies
only the observed build/test lifecycle state, preserves explicit unknowns, and
requires operator review.  It never proves root cause or authorizes repair,
retesting, apply, installation, promotion, release, or model management.
"""

import time
import uuid
from pathlib import Path
from typing import Any, Mapping

from conversational_build_test_continuation import load_conversational_build_test_continuation
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1213.8"
DIAGNOSIS_LEASE_SECONDS = 60.0

DIAGNOSABLE_OUTCOMES = {
    "conversational_build_test_continuation_tests_failed": {
        "diagnosis_code": "test_failure_observed",
        "observed_conclusion": "reviewed_tests_executed_and_did_not_pass",
        "unknowns": ["failing_assertion_or_runtime_cause", "required_repair"],
        "suggested_next_step": "operator_review_test_failure_before_repair_proposal",
    },
    "conversational_build_test_continuation_test_blocked": {
        "diagnosis_code": "test_execution_blocked",
        "observed_conclusion": "selected_test_adapter_did_not_complete",
        "unknowns": ["whether_generated_artifact_would_pass", "required_unblock_or_repair"],
        "suggested_next_step": "operator_review_test_block_before_repair_proposal",
    },
    "conversational_build_test_continuation_build_blocked": {
        "diagnosis_code": "build_stage_blocked",
        "observed_conclusion": "isolated_build_did_not_reach_completed_tests",
        "unknowns": ["generation_materialization_or_validation_cause", "required_repair"],
        "suggested_next_step": "operator_review_build_block_before_repair_proposal",
    },
    "conversational_build_test_continuation_internal_error": {
        "diagnosis_code": "continuation_pipeline_error_observed",
        "observed_conclusion": "bounded_continuation_pipeline_did_not_complete",
        "unknowns": ["private_internal_error_cause", "whether_artifact_requires_repair"],
        "suggested_next_step": "operator_review_pipeline_error_before_repair_proposal",
    },
}

NON_DIAGNOSABLE_OUTCOMES = frozenset({"conversational_build_test_continuation_completed"})

AUTHORITY_FLAGS = {
    "operator_authorized_diagnosis": False,
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "retest_authorized": False,
    "repair_authorized": False,
    "apply_authorized": False,
    "rollback_authorized": False,
    "install_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}


def _diagnosis_path(proposal_id: str, revision: int, attempt_number: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "bounded_automatic_diagnoses"
        / str(proposal_id)
        / f"revision-{int(revision)}"
        / f"attempt-{int(attempt_number)}.json"
    )


def _record_digest(record: Mapping[str, Any]) -> str:
    return _digest({key: value for key, value in record.items() if key != "diagnosis_record_digest"})


def _record_valid(record: Mapping[str, Any]) -> bool:
    supplied = str(record.get("diagnosis_record_digest") or "")
    return bool(supplied and supplied == _record_digest(record))


def _seal(record: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(record)
    row["diagnosis_record_digest"] = _record_digest(row)
    return row


def _sha256(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(character in "0123456789abcdef" for character in token) else ""


def _base(*, proposal_id: str = "", revision: int = 0) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "diagnosis_performed": False,
        "automatic_diagnosis": False,
        "diagnosis_authorized": False,
        "root_cause_proven": False,
        "operator_review_required": True,
        "provider_contacted": False,
        "tests_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "patch_created": False,
        "repair_created": False,
        "runtime_records_external": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
    }


def _failure(status: str, *, reason: str = "", proposal_id: str = "", revision: int = 0) -> dict[str, Any]:
    row = {
        "ok": False,
        "status": str(status),
        "reason": str(reason or ""),
        **_base(proposal_id=proposal_id, revision=revision),
    }
    row["diagnosis_result_digest"] = _digest(row)
    return row


def _validate_continuation_result(
    proposal_id: str,
    revision: int,
    expected_attempt_digest: str,
    expected_continuation_result_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    continuation = load_conversational_build_test_continuation(
        proposal_id, revision, runtime_root=runtime_root
    )
    if not continuation or continuation.get("phase") != "sealed":
        return None, _failure(
            "bounded_automatic_diagnosis_continuation_invalid",
            reason="sealed_continuation_required",
            proposal_id=proposal_id,
            revision=revision,
        )
    result = continuation.get("result")
    if not isinstance(result, Mapping):
        return None, _failure(
            "bounded_automatic_diagnosis_continuation_invalid",
            reason="sealed_result_required",
            proposal_id=proposal_id,
            revision=revision,
        )
    if str(continuation.get("result_digest") or "") != _digest(result):
        return None, _failure(
            "bounded_automatic_diagnosis_continuation_invalid",
            reason="continuation_result_record_invalid",
            proposal_id=proposal_id,
            revision=revision,
        )
    supplied_result_digest = _sha256(result.get("continuation_result_digest"))
    calculated_result_digest = _digest(
        {key: value for key, value in result.items() if key != "continuation_result_digest"}
    )
    if not supplied_result_digest or supplied_result_digest != calculated_result_digest:
        return None, _failure(
            "bounded_automatic_diagnosis_continuation_invalid",
            reason="continuation_result_digest_invalid",
            proposal_id=proposal_id,
            revision=revision,
        )
    if _sha256(result.get("attempt_digest")) != _sha256(expected_attempt_digest):
        return None, _failure(
            "bounded_automatic_diagnosis_stale_attempt",
            proposal_id=proposal_id,
            revision=revision,
        )
    if supplied_result_digest != _sha256(expected_continuation_result_digest):
        return None, _failure(
            "bounded_automatic_diagnosis_stale_result",
            proposal_id=proposal_id,
            revision=revision,
        )
    validated = dict(result)
    # A v1212 internal-error result may seal before child-loop lineage fields
    # exist. Preserve its exact signed result, then derive only a content-free
    # diagnostic binding from the already sealed attempt record.
    for key in (
        "proposal_revision_digest", "parent_loop_result_digest",
        "continuation_loop_result_digest", "project_kind", "selected_adapter_id",
    ):
        if not validated.get(key) and continuation.get(key):
            validated[key] = continuation.get(key)
    if _sha256(validated.get("lineage_digest")):
        validated["lineage_digest_source"] = "continuation_result"
    else:
        validated["lineage_digest"] = _digest({
            "attempt_number": int(validated.get("attempt_number") or continuation.get("attempt_number") or 0),
            "attempt_digest": _sha256(validated.get("attempt_digest") or continuation.get("attempt_digest")),
            "parent_loop_result_digest": _sha256(validated.get("parent_loop_result_digest")),
            "continuation_loop_result_digest": _sha256(validated.get("continuation_loop_result_digest")),
        })
        validated["lineage_digest_source"] = "derived_sealed_attempt_binding"
    return validated, None


def _evidence_from_result(result: Mapping[str, Any]) -> dict[str, Any]:
    evidence = {
        "proposal_id": str(result.get("proposal_id") or ""),
        "proposal_revision": int(result.get("proposal_revision") or 0),
        "proposal_revision_digest": _sha256(result.get("proposal_revision_digest")),
        "attempt_number": int(result.get("attempt_number") or 0),
        "attempt_digest": _sha256(result.get("attempt_digest")),
        "continuation_result_digest": _sha256(result.get("continuation_result_digest")),
        "parent_loop_result_digest": _sha256(result.get("parent_loop_result_digest")),
        "continuation_loop_result_digest": _sha256(result.get("continuation_loop_result_digest")),
        "lineage_digest": _sha256(result.get("lineage_digest")),
        "lineage_digest_source": str(result.get("lineage_digest_source") or "continuation_result"),
        "outcome_status": str(result.get("status") or ""),
        "completed_stage": str(result.get("completed_stage") or ""),
        "project_kind": str(result.get("project_kind") or ""),
        "selected_adapter_id": str(result.get("selected_adapter_id") or ""),
        "observed_provider_contacted": bool(result.get("provider_contacted")),
        "observed_tests_executed": bool(result.get("tests_executed")),
        "observed_test_passed": result.get("test_passed") if isinstance(result.get("test_passed"), bool) else None,
        "observed_cleanup_confirmed": result.get("cleanup_confirmed") if isinstance(result.get("cleanup_confirmed"), bool) else None,
        "content_free": True,
        "raw_output_included": False,
        "private_path_included": False,
    }
    evidence["evidence_digest"] = _digest(evidence)
    return evidence


def prepare_bounded_automatic_diagnosis(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_attempt_digest: str,
    expected_continuation_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Validate exact failure evidence and prepare one durable diagnosis."""

    proposal_id = str(proposal_id or "").strip().lower()
    result, failure = _validate_continuation_result(
        proposal_id,
        expected_revision,
        expected_attempt_digest,
        expected_continuation_result_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert result is not None
    outcome_status = str(result.get("status") or "")
    if outcome_status in NON_DIAGNOSABLE_OUTCOMES:
        row = {
            "ok": True,
            "status": "bounded_automatic_diagnosis_not_required",
            "reason": "continuation_completed_successfully",
            "attempt_number": int(result.get("attempt_number") or 0),
            "attempt_digest": _sha256(result.get("attempt_digest")),
            "continuation_result_digest": _sha256(result.get("continuation_result_digest")),
            **_base(proposal_id=proposal_id, revision=expected_revision),
        }
        row["diagnosis_result_digest"] = _digest(row)
        return row
    if outcome_status not in DIAGNOSABLE_OUTCOMES:
        return _failure(
            "bounded_automatic_diagnosis_outcome_unsupported",
            reason="unsupported_continuation_outcome",
            proposal_id=proposal_id,
            revision=expected_revision,
        )

    evidence = _evidence_from_result(result)
    if not all((
        evidence["attempt_number"] >= 2,
        bool(evidence["attempt_digest"]),
        bool(evidence["continuation_result_digest"]),
        bool(evidence["proposal_revision_digest"]),
        bool(evidence["lineage_digest"]),
    )):
        return _failure(
            "bounded_automatic_diagnosis_evidence_invalid",
            reason="required_digest_binding_missing",
            proposal_id=proposal_id,
            revision=expected_revision,
        )
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "proposal_revision_digest": evidence["proposal_revision_digest"],
        "attempt_number": evidence["attempt_number"],
        "attempt_digest": evidence["attempt_digest"],
        "continuation_result_digest": evidence["continuation_result_digest"],
        "continuation_loop_result_digest": evidence["continuation_loop_result_digest"],
        "lineage_digest": evidence["lineage_digest"],
        "outcome_status": outcome_status,
        "evidence_digest": evidence["evidence_digest"],
    }
    diagnosis_digest = _digest(binding)
    path = _diagnosis_path(proposal_id, expected_revision, evidence["attempt_number"], runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _record_valid(existing):
                return _failure(
                    "bounded_automatic_diagnosis_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                )
            if str(existing.get("diagnosis_digest") or "") != diagnosis_digest:
                return _failure(
                    "bounded_automatic_diagnosis_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                )
            return {**existing, "operation_status": "resumed"}
        record = {
            "ok": True,
            "status": "bounded_automatic_diagnosis_ready",
            **binding,
            "diagnosis_digest": diagnosis_digest,
            "evidence": evidence,
            "phase": "prepared",
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "recovery_count": 0,
            **_base(proposal_id=proposal_id, revision=expected_revision),
        }
        record = _seal(record)
        _atomic_json(path, record)
    return {**record, "operation_status": "created"}


def _diagnose_evidence(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    outcome = str(evidence.get("outcome_status") or "")
    template = DIAGNOSABLE_OUTCOMES.get(outcome)
    if not template:
        raise ValueError("unsupported_diagnosis_evidence")
    return [{
        "diagnosis_code": template["diagnosis_code"],
        "confidence": "high_observation_low_root_cause",
        "supported_conclusion": template["observed_conclusion"],
        "unknowns": list(template["unknowns"]),
        "suggested_next_step": template["suggested_next_step"],
    }]


def run_or_resume_bounded_automatic_diagnosis(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_attempt_digest: str,
    expected_continuation_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Automatically classify one exact failed result without repair authority."""

    proposal_id = str(proposal_id or "").strip().lower()
    prepared = prepare_bounded_automatic_diagnosis(
        proposal_id,
        expected_revision=expected_revision,
        expected_attempt_digest=expected_attempt_digest,
        expected_continuation_result_digest=expected_continuation_result_digest,
        runtime_root=runtime_root,
    )
    if prepared.get("status") == "bounded_automatic_diagnosis_not_required":
        return prepared
    if prepared.get("ok") is not True:
        return prepared

    attempt_number = int(prepared.get("attempt_number") or 0)
    path = _diagnosis_path(proposal_id, expected_revision, attempt_number, runtime_root)
    lease_token = uuid.uuid4().hex
    recovery_count = 0
    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _record_valid(current):
            return _failure(
                "bounded_automatic_diagnosis_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
            )
        if current.get("phase") == "sealed":
            result = current.get("result")
            if not isinstance(result, Mapping) or str(current.get("result_digest") or "") != _digest(result):
                return _failure(
                    "bounded_automatic_diagnosis_result_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                )
            return {**dict(result), "operation_status": "resumed"}
        if current.get("phase") == "running" and float(current.get("lease_expires_unix") or 0.0) > time.time():
            return _failure(
                "bounded_automatic_diagnosis_in_progress",
                proposal_id=proposal_id,
                revision=expected_revision,
            )
        if current.get("phase") not in {"prepared", "running"}:
            return _failure(
                "bounded_automatic_diagnosis_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
            )
        recovery_count = int(current.get("recovery_count") or 0) + int(current.get("phase") == "running")
        running = dict(current)
        running.update({
            "status": "bounded_automatic_diagnosis_running",
            "phase": "running",
            "lease_token": lease_token,
            "lease_expires_unix": time.time() + DIAGNOSIS_LEASE_SECONDS,
            "recovery_count": recovery_count,
            "diagnosis_authorized": True,
            "automatic_diagnosis": True,
        })
        _atomic_json(path, _seal(running))

    try:
        evidence = prepared.get("evidence")
        if not isinstance(evidence, Mapping) or str(evidence.get("evidence_digest") or "") != _digest(
            {key: value for key, value in evidence.items() if key != "evidence_digest"}
        ):
            raise ValueError("invalid_prepared_evidence")
        candidates = _diagnose_evidence(evidence)
        result = {
            "ok": True,
            "status": "bounded_automatic_diagnosis_completed",
            "proposal_revision_digest": str(prepared.get("proposal_revision_digest") or ""),
            "attempt_number": attempt_number,
            "attempt_digest": str(prepared.get("attempt_digest") or ""),
            "continuation_result_digest": str(prepared.get("continuation_result_digest") or ""),
            "continuation_loop_result_digest": str(prepared.get("continuation_loop_result_digest") or ""),
            "lineage_digest": str(prepared.get("lineage_digest") or ""),
            "outcome_status": str(prepared.get("outcome_status") or ""),
            "evidence_digest": str(prepared.get("evidence_digest") or ""),
            "diagnosis_digest": str(prepared.get("diagnosis_digest") or ""),
            "diagnosis_posture": "diagnosis_candidates_require_operator_review",
            "diagnosis_candidates": candidates,
            "diagnosis_count": len(candidates),
            "suggested_next_step": "operator_review_before_repair_proposal",
            "diagnosis_performed": True,
            "automatic_diagnosis": True,
            "diagnosis_authorized": True,
            "recovery_count": recovery_count,
            **_base(proposal_id=proposal_id, revision=expected_revision),
            "diagnosis_performed": True,
            "automatic_diagnosis": True,
            "diagnosis_authorized": True,
        }
    except Exception as error:
        result = {
            **_failure(
                "bounded_automatic_diagnosis_internal_error",
                reason=_digest({"type": type(error).__name__}),
                proposal_id=proposal_id,
                revision=expected_revision,
            ),
            "attempt_number": attempt_number,
            "attempt_digest": str(prepared.get("attempt_digest") or ""),
            "continuation_result_digest": str(prepared.get("continuation_result_digest") or ""),
            "evidence_digest": str(prepared.get("evidence_digest") or ""),
            "diagnosis_digest": str(prepared.get("diagnosis_digest") or ""),
            "automatic_diagnosis": True,
            "diagnosis_authorized": True,
            "retry_disposition": "same_evidence_may_resume",
            "recovery_count": recovery_count,
        }
    result["diagnosis_result_digest"] = _digest(
        {key: value for key, value in result.items() if key != "diagnosis_result_digest"}
    )

    with _proposal_lock(proposal_id, runtime_root):
        current = _read_json(path)
        if not current or not _record_valid(current) or str(current.get("lease_token") or "") != lease_token:
            return _failure(
                "bounded_automatic_diagnosis_lease_lost",
                proposal_id=proposal_id,
                revision=expected_revision,
            )
        sealed = dict(current)
        sealed.update({
            "status": str(result.get("status") or "bounded_automatic_diagnosis_internal_error"),
            "phase": "sealed",
            "lease_token": "",
            "lease_expires_unix": 0.0,
            "diagnosis_authorized": True,
            "automatic_diagnosis": True,
            "diagnosis_performed": bool(result.get("diagnosis_performed")),
            "result": result,
            "result_digest": _digest(result),
        })
        _atomic_json(path, _seal(sealed))
    return {**result, "operation_status": "recovered" if recovery_count else "created"}


def public_bounded_automatic_diagnosis(record: Mapping[str, Any]) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "proposal_revision_digest", "attempt_number", "attempt_digest",
        "continuation_result_digest", "continuation_loop_result_digest", "lineage_digest",
        "outcome_status", "evidence_digest", "diagnosis_digest", "diagnosis_result_digest",
        "diagnosis_posture", "diagnosis_candidates", "diagnosis_count", "suggested_next_step",
        "diagnosis_performed", "automatic_diagnosis", "diagnosis_authorized",
        "operator_authorized_diagnosis", "operator_review_required", "recovery_count",
        "operation_status", "retry_disposition", "provider_contacted", "tests_executed",
        "project_modified", "selected_project_modified", "source_modified", "patch_created",
        "repair_created", "runtime_records_external", "root_cause_proven", "retest_authorized",
        "repair_authorized", "apply_authorized", "rollback_authorized", "install_authorized",
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
    public["public_diagnosis_digest"] = _digest(public)
    return public


def bounded_automatic_diagnosis_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "bounded_automatic_diagnosis_completed":
        candidates = list(record.get("diagnosis_candidates") or [])
        code = str(candidates[0].get("diagnosis_code") or "observed_failure") if candidates else "observed_failure"
        return (
            f"A bounded automatic diagnosis classified the observed result as {code.replace('_', ' ')}. "
            "The root cause is not proven, and the diagnosis is ready for operator review. "
            "No repair, retest, apply, installation, promotion, or release action was authorized."
        )
    if status == "bounded_automatic_diagnosis_not_required":
        return "The continuation passed, so automatic failure diagnosis was not needed."
    if status == "bounded_automatic_diagnosis_in_progress":
        return "The exact bounded diagnosis is already running; no duplicate was started."
    return (
        "The bounded automatic diagnosis could not be completed from the exact reviewed evidence. "
        "No repair, retest, or project change was authorized."
    )


def attach_bounded_automatic_diagnosis(
    continuation_turn: Mapping[str, Any], *, runtime_root=None
) -> dict[str, Any]:
    """Attach automatic diagnosis to an ordinary-chat v1212 terminal turn."""

    turn = dict(continuation_turn)
    public_continuation = turn.get("build_test_continuation")
    if not isinstance(public_continuation, Mapping):
        return turn
    outcome = str(public_continuation.get("status") or "")
    if outcome not in set(DIAGNOSABLE_OUTCOMES) | set(NON_DIAGNOSABLE_OUTCOMES):
        return turn
    diagnosis = run_or_resume_bounded_automatic_diagnosis(
        str(public_continuation.get("proposal_id") or ""),
        expected_revision=int(public_continuation.get("proposal_revision") or 0),
        expected_attempt_digest=str(public_continuation.get("attempt_digest") or ""),
        expected_continuation_result_digest=str(public_continuation.get("continuation_result_digest") or ""),
        runtime_root=runtime_root,
    )
    turn["bounded_automatic_diagnosis"] = public_bounded_automatic_diagnosis(diagnosis)
    turn["conversation_response"] = " ".join(
        part for part in (
            str(turn.get("conversation_response") or "").strip(),
            bounded_automatic_diagnosis_response(diagnosis),
        ) if part
    )
    turn["public_digest"] = _digest({
        key: value for key, value in turn.items() if key not in {"conversation_response", "public_digest"}
    })
    return turn


def load_bounded_automatic_diagnosis(
    proposal_id: str, revision: int, attempt_number: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_diagnosis_path(proposal_id, revision, attempt_number, runtime_root)) or {}
    return record if record and _record_valid(record) else {}
