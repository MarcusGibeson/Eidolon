from __future__ import annotations

"""Operator review for exact terminal v1219 repaired-candidate rollback results.

One sealed rollback result may produce one durable, content-free review packet.
An exact conversational decision may accept, defer, or reject that result.  The
review is terminal-disposition only: it cannot retry rollback, contact a
provider, run tests, repair, apply, install, promote, release, manage models,
or grant authority.
"""

import re
from pathlib import Path
from typing import Any, Mapping

from conversational_supervised_repaired_candidate_rollback import (
    ROLLBACK_RESULT_STATUSES,
    load_supervised_repaired_candidate_rollback,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1220.8"
COMPLETED_ROLLBACK_STATUSES = frozenset({
    "supervised_repaired_candidate_rollback_completed",
    "supervised_repaired_candidate_rollback_completed_recovered",
})
APPLIED_STATE_RESTORED_STATUSES = frozenset({
    "supervised_repaired_candidate_rollback_failed_applied_state_restored",
    "interrupted_repaired_candidate_rollback_recovered_to_applied_state",
})
ROLLBACK_RESULT_REVIEW_DECISIONS = (
    "accept-rollback-result",
    "defer",
    "reject-rollback-result",
)

AUTHORITY_FLAGS = {
    "repair_execution_authorized": False,
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "retest_authorized": False,
    "apply_execution_authorized": False,
    "apply_authorized": False,
    "rollback_execution_authorized": False,
    "rollback_authorized": False,
    "install_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}

_REVIEW_DECISION = re.compile(
    r"^record\s+(?P<decision>accept-rollback-result|defer|reject-rollback-result)\s+"
    r"for\s+repaired\s+candidate\s+rollback\s+result\s+review\s+"
    r"(?P<review_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)\s+"
    r"failed\s+attempt\s+(?P<failed_attempt>[2-9][0-9]*)\s+repair\s+attempt\s+"
    r"(?P<repair_attempt>[1-9][0-9]*)\s+apply\s+attempt\s+"
    r"(?P<apply_attempt>[1-9][0-9]*)\s+rollback\s+attempt\s+"
    r"(?P<rollback_attempt>[1-9][0-9]*)[.!?]*$",
    re.I,
)


def _review_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_repaired_candidate_rollback_result_reviews"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1-apply-1-rollback-1.json"
    )


def _decision_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_repaired_candidate_rollback_result_decisions"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1-apply-1-rollback-1.json"
    )


def _sha256(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if len(token) == 64 and all(char in "0123456789abcdef" for char in token) else ""


def _sealed(record: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    row = dict(record)
    row[digest_field] = _digest({key: value for key, value in row.items() if key != digest_field})
    return row


def _valid(record: Mapping[str, Any], digest_field: str) -> bool:
    supplied = str(record.get(digest_field) or "")
    return bool(
        supplied
        and supplied == _digest({key: value for key, value in record.items() if key != digest_field})
    )


def _base(*, proposal_id: str = "", revision: int = 0, failed_attempt: int = 0) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "proposal_id": str(proposal_id or ""),
        "proposal_revision": int(revision or 0),
        "failed_attempt_number": int(failed_attempt or 0),
        "repair_attempt_number": 1,
        "repair_attempt_limit": 1,
        "apply_attempt_number": 1,
        "apply_attempt_limit": 1,
        "rollback_attempt_number": 1,
        "rollback_attempt_limit": 1,
        "operator_review_required": True,
        "rollback_result_review_required": True,
        "terminal_disposition_only": True,
        "rollback_retry_available": False,
        "provider_contacted": False,
        "tests_executed": False,
        "retest_executed": False,
        "repair_executed": False,
        "apply_executed": False,
        "rollback_executed": False,
        "project_modified": False,
        "selected_project_modified": False,
        "source_modified": False,
        "runtime_records_external": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "rollback_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
        **AUTHORITY_FLAGS,
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
        "status": str(status or "operator_repaired_candidate_rollback_result_review_blocked"),
        "reason": str(reason or ""),
        **_base(proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt),
    }
    row["operator_repaired_candidate_rollback_result_review_result_digest"] = _digest(row)
    return row


def _review_phrase(
    decision: str,
    review_digest: str,
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    repair_attempt: int = 1,
    apply_attempt: int = 1,
    rollback_attempt: int = 1,
) -> str:
    return (
        f"Record {decision} for repaired candidate rollback result review {review_digest} "
        f"proposal {proposal_id} revision {int(revision)} failed attempt "
        f"{int(failed_attempt)} repair attempt {int(repair_attempt)} apply attempt "
        f"{int(apply_attempt)} rollback attempt {int(rollback_attempt)}."
    )


def _validated_rollback_result(
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    expected_execution_digest: str,
    expected_result_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    record = load_supervised_repaired_candidate_rollback(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root
    )
    if not record or record.get("phase") != "sealed":
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_rollback_invalid",
            reason="sealed_rollback_result_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    result = record.get("result")
    if not isinstance(result, Mapping) or str(record.get("result_digest") or "") != _digest(result):
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_rollback_invalid",
            reason="sealed_rollback_result_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    calculated = _digest({
        key: value for key, value in result.items()
        if key != "supervised_repaired_candidate_rollback_result_digest"
    })
    if _sha256(result.get("supervised_repaired_candidate_rollback_result_digest")) != calculated:
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_rollback_invalid",
            reason="rollback_result_digest_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    status = str(result.get("status") or "")
    if status not in ROLLBACK_RESULT_STATUSES:
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_not_available",
            reason="terminal_rollback_result_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if (
        int(result.get("proposal_revision") or 0) != int(revision)
        or int(result.get("failed_attempt_number") or 0) != int(failed_attempt)
        or int(result.get("repair_attempt_number") or 0) != 1
        or int(result.get("apply_attempt_number") or 0) != 1
        or int(result.get("rollback_attempt_number") or 0) != 1
        or int(result.get("rollback_attempt_limit") or 0) != 1
        or result.get("rollback_result_review_required") is not True
        or result.get("source_modified") is not False
        or result.get("rollback_authorized") is not True
        or result.get("rollback_execution_authorized") is not True
        or int(result.get("authorization_consumption_count") or 0) != 1
        or result.get("authority_granted") is not False
    ):
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_rollback_invalid",
            reason="rollback_authority_or_attempt_boundary_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    required_result = (
        "supervised_repaired_candidate_rollback_digest",
        "supervised_repaired_candidate_rollback_result_digest",
        "rollback_proposal_digest",
        "supervised_repaired_candidate_apply_digest",
        "supervised_repaired_candidate_apply_result_digest",
        "source_workspace_digest",
        "repair_workspace_digest",
        "rollback_manifest_digest",
        "authorization_receipt_digest",
    )
    required_record = (
        "apply_plan_digest",
        "apply_authorization_receipt_digest",
        "operator_apply_result_review_digest",
        "operator_apply_result_decision_digest",
    )
    if not all(_sha256(result.get(key)) for key in required_result) or not all(
        _sha256(record.get(key)) for key in required_record
    ):
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_rollback_invalid",
            reason="exact_rollback_binding_missing",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if _sha256(result.get("supervised_repaired_candidate_rollback_digest")) != _sha256(
        expected_execution_digest
    ):
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_stale_execution",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if calculated != _sha256(expected_result_digest):
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_stale_result",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    completed = status in COMPLETED_ROLLBACK_STATUSES
    if completed and (
        result.get("ok") is not True
        or result.get("rollback_executed") is not True
        or result.get("project_modified") is not False
        or result.get("selected_project_modified") is not False
        or int(result.get("restored_count") or 0) < 1
    ):
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_rollback_invalid",
            reason="completed_rollback_evidence_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if not completed and (
        status not in APPLIED_STATE_RESTORED_STATUSES
        or result.get("ok") is not False
        or result.get("rollback_executed") is not False
        or result.get("project_modified") is not True
        or result.get("selected_project_modified") is not True
        or int(result.get("restored_count") or 0) != 0
    ):
        return None, None, _failure(
            "operator_repaired_candidate_rollback_result_review_rollback_invalid",
            reason="applied_state_restoration_evidence_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    return dict(record), dict(result), None


def prepare_operator_repaired_candidate_rollback_result_review(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_execution_digest: str,
    expected_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one exact, non-executing review packet for a rollback result."""

    proposal_id = str(proposal_id or "").strip().lower()
    record, result, failure = _validated_rollback_result(
        proposal_id,
        expected_revision,
        expected_failed_attempt_number,
        expected_execution_digest,
        expected_result_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert record is not None and result is not None
    completed = str(result.get("status") or "") in COMPLETED_ROLLBACK_STATUSES
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "failed_attempt_number": int(expected_failed_attempt_number),
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "rollback_attempt_number": 1,
        "supervised_repaired_candidate_rollback_digest": _sha256(
            result.get("supervised_repaired_candidate_rollback_digest")
        ),
        "supervised_repaired_candidate_rollback_result_digest": _sha256(
            result.get("supervised_repaired_candidate_rollback_result_digest")
        ),
        "rollback_proposal_digest": _sha256(result.get("rollback_proposal_digest")),
        "supervised_repaired_candidate_apply_digest": _sha256(
            result.get("supervised_repaired_candidate_apply_digest")
        ),
        "supervised_repaired_candidate_apply_result_digest": _sha256(
            result.get("supervised_repaired_candidate_apply_result_digest")
        ),
        "source_workspace_digest": _sha256(result.get("source_workspace_digest")),
        "repair_workspace_digest": _sha256(result.get("repair_workspace_digest")),
        "apply_plan_digest": _sha256(record.get("apply_plan_digest")),
        "apply_authorization_receipt_digest": _sha256(
            record.get("apply_authorization_receipt_digest")
        ),
        "rollback_manifest_digest": _sha256(result.get("rollback_manifest_digest")),
        "rollback_authorization_receipt_digest": _sha256(
            result.get("authorization_receipt_digest")
        ),
        "operator_apply_result_review_digest": _sha256(
            record.get("operator_apply_result_review_digest")
        ),
        "operator_apply_result_decision_digest": _sha256(
            record.get("operator_apply_result_decision_digest")
        ),
        "rollback_result_status": str(result.get("status") or ""),
    }
    review_digest = _digest(binding)
    row = {
        "ok": True,
        "status": "operator_repaired_candidate_rollback_result_review_required",
        **binding,
        "review_digest": review_digest,
        "rollback_completed": completed,
        "pre_apply_state_restored": completed,
        "applied_repaired_candidate_state_restored": not completed,
        "outcome_class": (
            "pre_apply_state_restored"
            if completed
            else "rollback_failed_applied_repaired_candidate_state_restored"
        ),
        "reviewed_rollback_authorization_consumed": True,
        "reviewed_rollback_execution_completed": completed,
        "available_decisions": list(ROLLBACK_RESULT_REVIEW_DECISIONS),
        "decision_phrases": [
            _review_phrase(
                decision,
                review_digest,
                proposal_id,
                expected_revision,
                expected_failed_attempt_number,
            )
            for decision in ROLLBACK_RESULT_REVIEW_DECISIONS
        ],
        **_base(
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        ),
    }
    row = _sealed(row, "operator_repaired_candidate_rollback_result_review_record_digest")
    path = _review_path(proposal_id, expected_revision, expected_failed_attempt_number, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_repaired_candidate_rollback_result_review_record_digest"):
                return _failure(
                    "operator_repaired_candidate_rollback_result_review_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("review_digest") or "") != review_digest:
                return _failure(
                    "operator_repaired_candidate_rollback_result_review_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def record_operator_repaired_candidate_rollback_result_decision(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_review_digest: str,
    decision: str,
    decision_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Record one exact terminal rollback-result disposition without executing work."""

    proposal_id = str(proposal_id or "").strip().lower()
    decision = str(decision or "").strip().lower()
    with _proposal_lock(proposal_id, runtime_root):
        review = _read_json(
            _review_path(proposal_id, expected_revision, expected_failed_attempt_number, runtime_root)
        )
        if not review or not _valid(
            review, "operator_repaired_candidate_rollback_result_review_record_digest"
        ):
            return _failure(
                "operator_repaired_candidate_rollback_result_review_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if str(review.get("review_digest") or "") != _sha256(expected_review_digest):
            return _failure(
                "operator_repaired_candidate_rollback_result_decision_stale_review",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        available = tuple(str(value) for value in review.get("available_decisions") or [])
        if decision not in available:
            return _failure(
                "operator_repaired_candidate_rollback_result_decision_not_allowed",
                reason="decision_unavailable",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        expected_phrase = _review_phrase(
            decision,
            expected_review_digest,
            proposal_id,
            expected_revision,
            expected_failed_attempt_number,
        )
        if str(decision_phrase or "").strip().casefold() != expected_phrase.casefold():
            return _failure(
                "operator_repaired_candidate_rollback_result_exact_decision_required",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        path = _decision_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        )
        existing = _read_json(path)
        if existing:
            if not _valid(
                existing, "operator_repaired_candidate_rollback_result_decision_record_digest"
            ):
                return _failure(
                    "operator_repaired_candidate_rollback_result_decision_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("review_digest") or "") != expected_review_digest:
                return _failure(
                    "operator_repaired_candidate_rollback_result_decision_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("decision") or "") != decision:
                return _failure(
                    "operator_repaired_candidate_rollback_result_conflicting_decision",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        state = {
            "accept-rollback-result": "rollback_result_accepted",
            "defer": "rollback_result_deferred",
            "reject-rollback-result": "rollback_result_rejected",
        }[decision]
        row = {
            "ok": True,
            "status": "operator_repaired_candidate_rollback_result_decision_recorded",
            "review_digest": expected_review_digest,
            "supervised_repaired_candidate_rollback_digest": str(
                review.get("supervised_repaired_candidate_rollback_digest") or ""
            ),
            "supervised_repaired_candidate_rollback_result_digest": str(
                review.get("supervised_repaired_candidate_rollback_result_digest") or ""
            ),
            "rollback_result_status": str(review.get("rollback_result_status") or ""),
            "outcome_class": str(review.get("outcome_class") or ""),
            "decision": decision,
            "decision_state": state,
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            ),
        }
        row["operator_repaired_candidate_rollback_result_decision_digest"] = _digest(row)
        row = _sealed(row, "operator_repaired_candidate_rollback_result_decision_record_digest")
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def public_operator_repaired_candidate_rollback_result_review(
    record: Mapping[str, Any]
) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "failed_attempt_number", "repair_attempt_number",
        "repair_attempt_limit", "apply_attempt_number", "apply_attempt_limit",
        "rollback_attempt_number", "rollback_attempt_limit",
        "supervised_repaired_candidate_rollback_digest",
        "supervised_repaired_candidate_rollback_result_digest", "rollback_proposal_digest",
        "supervised_repaired_candidate_apply_digest",
        "supervised_repaired_candidate_apply_result_digest", "source_workspace_digest",
        "repair_workspace_digest", "apply_plan_digest", "apply_authorization_receipt_digest",
        "rollback_manifest_digest", "rollback_authorization_receipt_digest",
        "operator_apply_result_review_digest", "operator_apply_result_decision_digest",
        "rollback_result_status", "review_digest", "rollback_completed",
        "pre_apply_state_restored", "applied_repaired_candidate_state_restored",
        "outcome_class", "reviewed_rollback_authorization_consumed",
        "reviewed_rollback_execution_completed", "available_decisions", "decision_phrases",
        "operator_repaired_candidate_rollback_result_review_record_digest", "decision",
        "decision_state", "operator_repaired_candidate_rollback_result_decision_digest",
        "operator_repaired_candidate_rollback_result_decision_record_digest", "operation_status",
        "operator_review_required", "rollback_result_review_required",
        "terminal_disposition_only", "rollback_retry_available", "runtime_records_external",
        "provider_contacted", "tests_executed", "retest_executed", "repair_executed",
        "apply_executed", "rollback_executed", "project_modified",
        "selected_project_modified", "source_modified", "repair_execution_authorized",
        "provider_contact_authorized", "test_execution_authorized", "retest_authorized",
        "apply_execution_authorized", "apply_authorized", "rollback_execution_authorized",
        "rollback_authorized", "install_authorized", "promotion_authorized",
        "release_authorized", "model_management_authorized", "authority_granted",
    }
    public = {key: record.get(key) for key in allowed if key in record}
    public.update({
        "content_free": True,
        "private_request_exposed": False,
        "private_path_exposed": False,
        "private_content_exposed": False,
        "rollback_content_exposed": False,
        "raw_provider_output_exposed": False,
        "raw_test_output_exposed": False,
    })
    public["public_operator_repaired_candidate_rollback_result_review_digest"] = _digest(public)
    return public


def operator_repaired_candidate_rollback_result_review_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "operator_repaired_candidate_rollback_result_review_required":
        choices = " ".join(f"[{phrase}]" for phrase in record.get("decision_phrases") or [])
        outcome = (
            "The exact pre-apply project state was restored and verified."
            if record.get("pre_apply_state_restored") is True
            else "The rollback failed safely and the exact applied repaired-candidate state was restored."
        )
        return (
            f"The exact repaired-candidate rollback result is ready for operator review. {outcome} "
            f"No retry or additional authority is available from this review. Choose one exact disposition: {choices}"
        )
    if status == "operator_repaired_candidate_rollback_result_decision_recorded":
        return (
            f"The rollback-result decision {record.get('decision', '')} was recorded exactly once. "
            "No retry, provider work, project mutation, installation, promotion, or release was authorized."
        )
    if status == "operator_repaired_candidate_rollback_result_conflicting_decision":
        return "A different rollback-result disposition is already sealed, so this conflict was rejected."
    return (
        "The repaired-candidate rollback-result review control was rejected because its exact "
        "evidence binding was invalid. No retry, installation, promotion, or release was authorized."
    )


def attach_operator_repaired_candidate_rollback_result_review(
    rollback_turn: Mapping[str, Any], *, runtime_root=None
) -> dict[str, Any]:
    turn = dict(rollback_turn)
    public_rollback = turn.get("supervised_repaired_candidate_rollback")
    if not isinstance(public_rollback, Mapping):
        return turn
    if str(public_rollback.get("status") or "") not in ROLLBACK_RESULT_STATUSES:
        return turn
    try:
        review = prepare_operator_repaired_candidate_rollback_result_review(
            str(public_rollback.get("proposal_id") or ""),
            expected_revision=int(public_rollback.get("proposal_revision") or 0),
            expected_failed_attempt_number=int(public_rollback.get("failed_attempt_number") or 0),
            expected_execution_digest=str(
                public_rollback.get("supervised_repaired_candidate_rollback_digest") or ""
            ),
            expected_result_digest=str(
                public_rollback.get("supervised_repaired_candidate_rollback_result_digest") or ""
            ),
            runtime_root=runtime_root,
        )
        turn["operator_repaired_candidate_rollback_result_review"] = (
            public_operator_repaired_candidate_rollback_result_review(review)
        )
        if review.get("ok") is True:
            turn["conversation_response"] = " ".join(
                part for part in (
                    str(turn.get("conversation_response") or "").strip(),
                    operator_repaired_candidate_rollback_result_review_response(review),
                ) if part
            )
    except Exception as error:
        turn["operator_repaired_candidate_rollback_result_review"] = {
            "ok": False,
            "status": "operator_repaired_candidate_rollback_result_review_preparation_blocked",
            "reason_digest": _digest({"type": type(error).__name__}),
            "content_free": True,
            "rollback_authorized": False,
            "authority_granted": False,
        }
    turn["public_digest"] = _digest({
        key: value for key, value in turn.items()
        if key not in {"conversation_response", "public_digest"}
    })
    return turn


def process_operator_repaired_candidate_rollback_result_review_control(
    user_text: str, *, runtime_root=None
) -> dict[str, Any]:
    match = _REVIEW_DECISION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision = int(match.group("revision"))
    failed_attempt = int(match.group("failed_attempt"))
    if any(int(match.group(name)) != 1 for name in (
        "repair_attempt", "apply_attempt", "rollback_attempt"
    )):
        result = _failure(
            "operator_repaired_candidate_rollback_result_decision_not_allowed",
            reason="attempt_limit_exceeded",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    else:
        result = record_operator_repaired_candidate_rollback_result_decision(
            proposal_id,
            expected_revision=revision,
            expected_failed_attempt_number=failed_attempt,
            expected_review_digest=match.group("review_digest").lower(),
            decision=match.group("decision").lower(),
            decision_phrase=str(user_text or "").strip(),
            runtime_root=runtime_root,
        )
    public = public_operator_repaired_candidate_rollback_result_review(result)
    return {
        "active": True,
        "event": str(
            result.get("status")
            or "operator_repaired_candidate_rollback_result_review_control_blocked"
        ),
        "operator_repaired_candidate_rollback_result_review": public,
        "conversation_response": operator_repaired_candidate_rollback_result_review_response(result),
        "public_digest": _digest(public),
    }


def load_operator_repaired_candidate_rollback_result_review(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_review_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return record if record and _valid(
        record, "operator_repaired_candidate_rollback_result_review_record_digest"
    ) else {}


def load_operator_repaired_candidate_rollback_result_decision(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_decision_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return record if record and _valid(
        record, "operator_repaired_candidate_rollback_result_decision_record_digest"
    ) else {}
