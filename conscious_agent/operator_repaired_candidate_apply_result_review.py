from __future__ import annotations

"""Operator review and rollback-proposal preparation for v1217 apply results.

One exact sealed repaired-candidate apply result may produce one durable,
content-free operator review packet. An exact conversational decision may
accept the result, defer, reject it, or (only when the repaired candidate is
still applied and sealed rollback evidence remains available) propose a later
rollback. The rollback proposal is separately authorization gated. This module
never reads project or rollback contents, runs tests, applies or rolls back
files, installs, promotes, releases, manages models, or grants authority.
"""

import re
from pathlib import Path
from typing import Any, Mapping

from conversational_supervised_repaired_candidate_apply import (
    APPLY_RESULT_STATUSES,
    load_supervised_repaired_candidate_apply,
)
from ordinary_chat_development_campaign import (
    _atomic_json,
    _digest,
    _proposal_lock,
    _read_json,
    _store_root,
)

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1218.8"

APPLIED_RESULT_STATUSES = frozenset({
    "supervised_repaired_candidate_apply_completed",
    "supervised_repaired_candidate_apply_completed_recovered",
})
ROLLED_BACK_RESULT_STATUSES = frozenset({
    "supervised_repaired_candidate_apply_failed_rolled_back",
    "interrupted_repaired_candidate_apply_recovered_by_rollback",
})
BASE_REVIEW_DECISIONS = (
    "accept-apply-result",
    "defer",
    "reject-apply-result",
)
ROLLBACK_REVIEW_DECISIONS = (*BASE_REVIEW_DECISIONS, "propose-rollback")

AUTHORITY_FLAGS = {
    "repair_execution_authorized": False,
    "provider_contact_authorized": False,
    "test_execution_authorized": False,
    "retest_authorized": False,
    "apply_authorized": False,
    "rollback_authorized": False,
    "install_authorized": False,
    "promotion_authorized": False,
    "release_authorized": False,
    "model_management_authorized": False,
    "authority_granted": False,
}

_REVIEW_DECISION = re.compile(
    r"^record\s+(?P<decision>accept-apply-result|defer|reject-apply-result|propose-rollback)\s+"
    r"for\s+repaired\s+candidate\s+apply\s+result\s+review\s+"
    r"(?P<review_digest>[a-f0-9]{64})\s+proposal\s+"
    r"(?P<proposal_id>devc_[a-f0-9]{24})\s+revision\s+(?P<revision>[1-9][0-9]*)\s+"
    r"failed\s+attempt\s+(?P<failed_attempt>[2-9][0-9]*)\s+repair\s+attempt\s+"
    r"(?P<repair_attempt>[1-9][0-9]*)\s+apply\s+attempt\s+"
    r"(?P<apply_attempt>[1-9][0-9]*)[.!?]*$",
    re.I,
)


def _review_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_repaired_candidate_apply_result_reviews"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1-apply-1.json"
    )


def _decision_path(proposal_id: str, revision: int, failed_attempt: int, runtime_root=None) -> Path:
    return (
        _store_root(runtime_root)
        / "operator_repaired_candidate_apply_result_decisions"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1-apply-1.json"
    )


def _rollback_proposal_path(
    proposal_id: str, revision: int, failed_attempt: int, runtime_root=None
) -> Path:
    return (
        _store_root(runtime_root)
        / "bounded_repaired_candidate_rollback_proposals"
        / proposal_id
        / f"revision-{int(revision)}"
        / f"failed-attempt-{int(failed_attempt)}"
        / "repair-1-apply-1.json"
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
        "operator_review_required": True,
        "apply_result_review_required": True,
        "rollback_proposal_created": False,
        "rollback_authorization_required": False,
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
        "status": str(status or "operator_repaired_candidate_apply_result_review_blocked"),
        "reason": str(reason or ""),
        **_base(proposal_id=proposal_id, revision=revision, failed_attempt=failed_attempt),
    }
    row["operator_repaired_candidate_apply_result_review_result_digest"] = _digest(row)
    return row


def _review_phrase(
    decision: str,
    review_digest: str,
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    repair_attempt: int = 1,
    apply_attempt: int = 1,
) -> str:
    return (
        f"Record {decision} for repaired candidate apply result review {review_digest} "
        f"proposal {proposal_id} revision {int(revision)} failed attempt "
        f"{int(failed_attempt)} repair attempt {int(repair_attempt)} apply attempt "
        f"{int(apply_attempt)}."
    )


def _rollback_authorization_phrase(
    rollback_proposal_digest: str,
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    repair_attempt: int = 1,
    apply_attempt: int = 1,
) -> str:
    return (
        f"Authorize repaired candidate rollback proposal {rollback_proposal_digest} "
        f"proposal {proposal_id} revision {int(revision)} failed attempt "
        f"{int(failed_attempt)} repair attempt {int(repair_attempt)} apply attempt "
        f"{int(apply_attempt)}."
    )


def _validated_apply_result(
    proposal_id: str,
    revision: int,
    failed_attempt: int,
    expected_execution_digest: str,
    expected_result_digest: str,
    *,
    runtime_root=None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    record = load_supervised_repaired_candidate_apply(
        proposal_id, revision, failed_attempt, runtime_root=runtime_root
    )
    if not record or record.get("phase") != "sealed":
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_apply_invalid",
            reason="sealed_apply_result_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    result = record.get("result")
    if not isinstance(result, Mapping) or str(record.get("result_digest") or "") != _digest(result):
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_apply_invalid",
            reason="sealed_apply_result_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    calculated = _digest({
        key: value for key, value in result.items()
        if key != "supervised_repaired_candidate_apply_result_digest"
    })
    if _sha256(result.get("supervised_repaired_candidate_apply_result_digest")) != calculated:
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_apply_invalid",
            reason="apply_result_digest_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    status = str(result.get("status") or "")
    if status not in APPLY_RESULT_STATUSES:
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_not_available",
            reason="terminal_apply_result_required",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if (
        int(result.get("proposal_revision") or 0) != int(revision)
        or int(result.get("failed_attempt_number") or 0) != int(failed_attempt)
        or int(result.get("repair_attempt_number") or 0) != 1
        or int(result.get("apply_attempt_number") or 0) != 1
        or int(result.get("apply_attempt_limit") or 0) != 1
        or result.get("apply_result_review_required") is not True
        or result.get("source_modified") is not False
        or result.get("rollback_authorized") is not False
        or result.get("authority_granted") is not False
    ):
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_apply_invalid",
            reason="apply_authority_or_attempt_boundary_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    required = (
        "supervised_repaired_candidate_apply_digest",
        "supervised_repaired_candidate_apply_result_digest",
        "apply_proposal_digest",
        "source_workspace_digest",
        "repair_workspace_digest",
        "apply_plan_digest",
        "authorization_receipt_digest",
        "rollback_manifest_digest",
    )
    if not all(_sha256(result.get(key)) for key in required):
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_apply_invalid",
            reason="exact_apply_binding_missing",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if _sha256(result.get("supervised_repaired_candidate_apply_digest")) != _sha256(expected_execution_digest):
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_stale_execution",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if calculated != _sha256(expected_result_digest):
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_stale_result",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    applied = status in APPLIED_RESULT_STATUSES
    if applied and (
        result.get("ok") is not True
        or result.get("rollback_prepared") is not True
        or result.get("rollback_available") is not True
        or result.get("rollback_executed") is not False
        or result.get("project_modified") is not True
        or result.get("selected_project_modified") is not True
        or int(result.get("authorization_consumption_count") or 0) != 1
        or int(result.get("applied_count") or 0) < 1
    ):
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_apply_invalid",
            reason="applied_result_evidence_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    if not applied and (
        status not in ROLLED_BACK_RESULT_STATUSES
        or result.get("ok") is not False
        or result.get("rollback_prepared") is not True
        or result.get("rollback_available") is not False
        or result.get("rollback_executed") is not True
        or result.get("project_modified") is not False
        or result.get("selected_project_modified") is not False
    ):
        return None, _failure(
            "operator_repaired_candidate_apply_result_review_apply_invalid",
            reason="rolled_back_result_evidence_invalid",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    return dict(result), None


def prepare_operator_repaired_candidate_apply_result_review(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_execution_digest: str,
    expected_result_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one exact, non-executing review packet for an apply result."""

    proposal_id = str(proposal_id or "").strip().lower()
    result, failure = _validated_apply_result(
        proposal_id,
        expected_revision,
        expected_failed_attempt_number,
        expected_execution_digest,
        expected_result_digest,
        runtime_root=runtime_root,
    )
    if failure:
        return failure
    assert result is not None
    rollback_eligible = str(result.get("status") or "") in APPLIED_RESULT_STATUSES
    decisions = ROLLBACK_REVIEW_DECISIONS if rollback_eligible else BASE_REVIEW_DECISIONS
    binding = {
        "contract_version": CONTRACT_VERSION,
        "proposal_id": proposal_id,
        "proposal_revision": int(expected_revision),
        "failed_attempt_number": int(expected_failed_attempt_number),
        "repair_attempt_number": 1,
        "apply_attempt_number": 1,
        "supervised_repaired_candidate_apply_digest": _sha256(
            result.get("supervised_repaired_candidate_apply_digest")
        ),
        "supervised_repaired_candidate_apply_result_digest": _sha256(
            result.get("supervised_repaired_candidate_apply_result_digest")
        ),
        "apply_proposal_digest": _sha256(result.get("apply_proposal_digest")),
        "source_workspace_digest": _sha256(result.get("source_workspace_digest")),
        "repair_workspace_digest": _sha256(result.get("repair_workspace_digest")),
        "apply_plan_digest": _sha256(result.get("apply_plan_digest")),
        "authorization_receipt_digest": _sha256(result.get("authorization_receipt_digest")),
        "rollback_manifest_digest": _sha256(result.get("rollback_manifest_digest")),
        "apply_result_status": str(result.get("status") or ""),
    }
    review_digest = _digest(binding)
    row = {
        "ok": True,
        "status": "operator_repaired_candidate_apply_result_review_required",
        **binding,
        "review_digest": review_digest,
        "apply_completed": rollback_eligible,
        "rollback_available": bool(result.get("rollback_available")),
        "rollback_eligible": rollback_eligible,
        "available_decisions": list(decisions),
        "decision_phrases": [
            _review_phrase(
                decision,
                review_digest,
                proposal_id,
                expected_revision,
                expected_failed_attempt_number,
            )
            for decision in decisions
        ],
        **_base(
            proposal_id=proposal_id,
            revision=expected_revision,
            failed_attempt=expected_failed_attempt_number,
        ),
    }
    row = _sealed(row, "operator_repaired_candidate_apply_result_review_record_digest")
    path = _review_path(proposal_id, expected_revision, expected_failed_attempt_number, runtime_root)
    with _proposal_lock(proposal_id, runtime_root):
        existing = _read_json(path)
        if existing:
            if not _valid(existing, "operator_repaired_candidate_apply_result_review_record_digest"):
                return _failure(
                    "operator_repaired_candidate_apply_result_review_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("review_digest") or "") != review_digest:
                return _failure(
                    "operator_repaired_candidate_apply_result_review_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def record_operator_repaired_candidate_apply_result_decision(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_review_digest: str,
    decision: str,
    decision_phrase: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Record one exact apply-result disposition without rolling back."""

    proposal_id = str(proposal_id or "").strip().lower()
    decision = str(decision or "").strip().lower()
    review_path = _review_path(
        proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
    )
    with _proposal_lock(proposal_id, runtime_root):
        review = _read_json(review_path)
        if not review or not _valid(
            review, "operator_repaired_candidate_apply_result_review_record_digest"
        ):
            return _failure(
                "operator_repaired_candidate_apply_result_review_record_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if str(review.get("review_digest") or "") != _sha256(expected_review_digest):
            return _failure(
                "operator_repaired_candidate_apply_result_decision_stale_review",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        available = tuple(str(value) for value in review.get("available_decisions") or [])
        if decision not in available:
            return _failure(
                "operator_repaired_candidate_apply_result_decision_not_allowed",
                reason="available_rollback_required" if decision == "propose-rollback" else "decision_unavailable",
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
                "operator_repaired_candidate_apply_result_exact_decision_required",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        decision_path = _decision_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        )
        existing = _read_json(decision_path)
        if existing:
            if not _valid(
                existing, "operator_repaired_candidate_apply_result_decision_record_digest"
            ):
                return _failure(
                    "operator_repaired_candidate_apply_result_decision_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("review_digest") or "") != expected_review_digest:
                return _failure(
                    "operator_repaired_candidate_apply_result_decision_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("decision") or "") != decision:
                return _failure(
                    "operator_repaired_candidate_apply_result_conflicting_decision",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        state = {
            "accept-apply-result": "apply_result_accepted",
            "defer": "apply_result_deferred",
            "reject-apply-result": "apply_result_rejected",
            "propose-rollback": "rollback_proposal_requested",
        }[decision]
        row = {
            "ok": True,
            "status": "operator_repaired_candidate_apply_result_decision_recorded",
            "review_digest": expected_review_digest,
            "supervised_repaired_candidate_apply_digest": str(
                review.get("supervised_repaired_candidate_apply_digest") or ""
            ),
            "supervised_repaired_candidate_apply_result_digest": str(
                review.get("supervised_repaired_candidate_apply_result_digest") or ""
            ),
            "rollback_manifest_digest": str(review.get("rollback_manifest_digest") or ""),
            "apply_result_status": str(review.get("apply_result_status") or ""),
            "rollback_eligible": bool(review.get("rollback_eligible")),
            "decision": decision,
            "decision_state": state,
            "rollback_proposal_requested": decision == "propose-rollback",
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            ),
        }
        row["operator_repaired_candidate_apply_result_decision_digest"] = _digest(row)
        row = _sealed(row, "operator_repaired_candidate_apply_result_decision_record_digest")
        _atomic_json(decision_path, row)
    return {**row, "operation_status": "created"}


def prepare_bounded_repaired_candidate_rollback_proposal(
    proposal_id: str,
    *,
    expected_revision: int,
    expected_failed_attempt_number: int,
    expected_review_digest: str,
    expected_decision_digest: str,
    runtime_root=None,
) -> dict[str, Any]:
    """Prepare one separately gated rollback proposal; never execute it."""

    proposal_id = str(proposal_id or "").strip().lower()
    with _proposal_lock(proposal_id, runtime_root):
        review = _read_json(_review_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        ))
        decision = _read_json(_decision_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        ))
        if not review or not _valid(
            review, "operator_repaired_candidate_apply_result_review_record_digest"
        ):
            return _failure(
                "bounded_rollback_proposal_review_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if not decision or not _valid(
            decision, "operator_repaired_candidate_apply_result_decision_record_digest"
        ):
            return _failure(
                "bounded_rollback_proposal_decision_invalid",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if str(review.get("review_digest") or "") != _sha256(expected_review_digest):
            return _failure(
                "bounded_rollback_proposal_stale_review",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if str(decision.get("operator_repaired_candidate_apply_result_decision_digest") or "") != _sha256(
            expected_decision_digest
        ):
            return _failure(
                "bounded_rollback_proposal_stale_decision",
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            )
        if (
            str(decision.get("review_digest") or "") != str(review.get("review_digest") or "")
            or decision.get("decision") != "propose-rollback"
            or decision.get("rollback_proposal_requested") is not True
            or review.get("rollback_eligible") is not True
            or review.get("rollback_available") is not True
            or review.get("apply_result_status") not in APPLIED_RESULT_STATUSES
            or not _sha256(review.get("rollback_manifest_digest"))
        ):
            return _failure(
                "bounded_rollback_proposal_not_eligible",
                reason="reviewed_applied_result_with_rollback_required",
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
            "supervised_repaired_candidate_apply_digest": str(
                review.get("supervised_repaired_candidate_apply_digest") or ""
            ),
            "supervised_repaired_candidate_apply_result_digest": str(
                review.get("supervised_repaired_candidate_apply_result_digest") or ""
            ),
            "apply_proposal_digest": str(review.get("apply_proposal_digest") or ""),
            "source_workspace_digest": str(review.get("source_workspace_digest") or ""),
            "repair_workspace_digest": str(review.get("repair_workspace_digest") or ""),
            "apply_plan_digest": str(review.get("apply_plan_digest") or ""),
            "authorization_receipt_digest": str(review.get("authorization_receipt_digest") or ""),
            "rollback_manifest_digest": str(review.get("rollback_manifest_digest") or ""),
            "review_digest": str(review.get("review_digest") or ""),
            "operator_repaired_candidate_apply_result_decision_digest": str(
                decision.get("operator_repaired_candidate_apply_result_decision_digest") or ""
            ),
        }
        rollback_digest = _digest(binding)
        row = {
            "ok": True,
            "status": "bounded_repaired_candidate_rollback_proposal_authorization_required",
            **binding,
            "rollback_proposal_digest": rollback_digest,
            "rollback_scope": "one_selected_project_rollback_attempt",
            "rollback_target": "exact_pre_apply_project_state",
            "maximum_rollback_attempts": 1,
            "requires_exact_authorization": True,
            "authorization_phrase": _rollback_authorization_phrase(
                rollback_digest,
                proposal_id,
                expected_revision,
                expected_failed_attempt_number,
            ),
            **_base(
                proposal_id=proposal_id,
                revision=expected_revision,
                failed_attempt=expected_failed_attempt_number,
            ),
            "rollback_proposal_created": True,
            "rollback_authorization_required": True,
        }
        row = _sealed(row, "bounded_repaired_candidate_rollback_proposal_record_digest")
        path = _rollback_proposal_path(
            proposal_id, expected_revision, expected_failed_attempt_number, runtime_root
        )
        existing = _read_json(path)
        if existing:
            if not _valid(
                existing, "bounded_repaired_candidate_rollback_proposal_record_digest"
            ):
                return _failure(
                    "bounded_rollback_proposal_record_invalid",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            if str(existing.get("rollback_proposal_digest") or "") != rollback_digest:
                return _failure(
                    "bounded_rollback_proposal_binding_changed",
                    proposal_id=proposal_id,
                    revision=expected_revision,
                    failed_attempt=expected_failed_attempt_number,
                )
            return {**existing, "operation_status": "resumed"}
        _atomic_json(path, row)
    return {**row, "operation_status": "created"}


def public_operator_repaired_candidate_apply_result_review(
    record: Mapping[str, Any]
) -> dict[str, Any]:
    if not record:
        return {}
    allowed = {
        "ok", "schema_version", "contract_version", "status", "reason", "proposal_id",
        "proposal_revision", "failed_attempt_number", "repair_attempt_number",
        "repair_attempt_limit", "apply_attempt_number", "apply_attempt_limit",
        "supervised_repaired_candidate_apply_digest",
        "supervised_repaired_candidate_apply_result_digest", "apply_proposal_digest",
        "source_workspace_digest", "repair_workspace_digest", "apply_plan_digest",
        "authorization_receipt_digest", "rollback_manifest_digest", "apply_result_status",
        "review_digest", "apply_completed", "rollback_available", "rollback_eligible",
        "available_decisions", "decision_phrases",
        "operator_repaired_candidate_apply_result_review_record_digest", "decision",
        "decision_state", "rollback_proposal_requested",
        "operator_repaired_candidate_apply_result_decision_digest",
        "operator_repaired_candidate_apply_result_decision_record_digest",
        "rollback_proposal_digest", "rollback_scope", "rollback_target",
        "maximum_rollback_attempts", "requires_exact_authorization", "authorization_phrase",
        "bounded_repaired_candidate_rollback_proposal_record_digest", "operation_status",
        "operator_review_required", "apply_result_review_required",
        "rollback_proposal_created", "rollback_authorization_required",
        "runtime_records_external", "provider_contacted", "tests_executed",
        "retest_executed", "repair_executed", "apply_executed", "rollback_executed",
        "project_modified", "selected_project_modified", "source_modified",
        "repair_execution_authorized", "provider_contact_authorized",
        "test_execution_authorized", "retest_authorized", "apply_authorized",
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
    public["public_operator_repaired_candidate_apply_result_review_digest"] = _digest(public)
    return public


def operator_repaired_candidate_apply_result_review_response(record: Mapping[str, Any]) -> str:
    status = str(record.get("status") or "")
    if status == "operator_repaired_candidate_apply_result_review_required":
        choices = " ".join(f"[{phrase}]" for phrase in record.get("decision_phrases") or [])
        eligibility = (
            "Sealed rollback evidence is available for a separately gated rollback proposal."
            if record.get("rollback_eligible") is True
            else "The project is already restored, so no rollback proposal is available."
        )
        return (
            f"The exact repaired-candidate apply result is ready for operator review. "
            f"{eligibility} No rollback has been authorized. Choose one exact disposition: {choices}"
        )
    if status == "operator_repaired_candidate_apply_result_decision_recorded":
        return (
            f"The apply-result decision {record.get('decision', '')} was recorded exactly once. "
            "No rollback, installation, promotion, or release was authorized."
        )
    if status == "bounded_repaired_candidate_rollback_proposal_authorization_required":
        return (
            "One exact repaired-candidate rollback proposal is prepared, but no rollback has run. "
            f"A later supervised rollback stage requires this separate phrase: "
            f"{record.get('authorization_phrase', '')}"
        )
    if status == "operator_repaired_candidate_apply_result_conflicting_decision":
        return "A different apply-result disposition is already sealed, so this conflict was rejected."
    return (
        "The repaired-candidate apply-result review control was rejected because its exact "
        "evidence binding was invalid. No rollback, installation, promotion, or release was authorized."
    )


def attach_operator_repaired_candidate_apply_result_review(
    apply_turn: Mapping[str, Any], *, runtime_root=None
) -> dict[str, Any]:
    turn = dict(apply_turn)
    public_apply = turn.get("supervised_repaired_candidate_apply")
    if not isinstance(public_apply, Mapping):
        return turn
    if str(public_apply.get("status") or "") not in APPLY_RESULT_STATUSES:
        return turn
    try:
        review = prepare_operator_repaired_candidate_apply_result_review(
            str(public_apply.get("proposal_id") or ""),
            expected_revision=int(public_apply.get("proposal_revision") or 0),
            expected_failed_attempt_number=int(public_apply.get("failed_attempt_number") or 0),
            expected_execution_digest=str(
                public_apply.get("supervised_repaired_candidate_apply_digest") or ""
            ),
            expected_result_digest=str(
                public_apply.get("supervised_repaired_candidate_apply_result_digest") or ""
            ),
            runtime_root=runtime_root,
        )
        turn["operator_repaired_candidate_apply_result_review"] = (
            public_operator_repaired_candidate_apply_result_review(review)
        )
        if review.get("ok") is True:
            turn["conversation_response"] = " ".join(
                part for part in (
                    str(turn.get("conversation_response") or "").strip(),
                    operator_repaired_candidate_apply_result_review_response(review),
                ) if part
            )
    except Exception as error:
        turn["operator_repaired_candidate_apply_result_review"] = {
            "ok": False,
            "status": "operator_repaired_candidate_apply_result_review_preparation_blocked",
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


def process_operator_repaired_candidate_apply_result_review_control(
    user_text: str, *, runtime_root=None
) -> dict[str, Any]:
    match = _REVIEW_DECISION.fullmatch(str(user_text or "").strip())
    if not match:
        return {"active": False, "event": "inactive"}
    proposal_id = match.group("proposal_id").lower()
    revision = int(match.group("revision"))
    failed_attempt = int(match.group("failed_attempt"))
    if int(match.group("repair_attempt")) != 1 or int(match.group("apply_attempt")) != 1:
        result = _failure(
            "operator_repaired_candidate_apply_result_decision_not_allowed",
            reason="attempt_limit_exceeded",
            proposal_id=proposal_id,
            revision=revision,
            failed_attempt=failed_attempt,
        )
    else:
        result = record_operator_repaired_candidate_apply_result_decision(
            proposal_id,
            expected_revision=revision,
            expected_failed_attempt_number=failed_attempt,
            expected_review_digest=match.group("review_digest").lower(),
            decision=match.group("decision").lower(),
            decision_phrase=str(user_text or "").strip(),
            runtime_root=runtime_root,
        )
    public = public_operator_repaired_candidate_apply_result_review(result)
    turn = {
        "active": True,
        "event": str(
            result.get("status")
            or "operator_repaired_candidate_apply_result_review_control_blocked"
        ),
        "operator_repaired_candidate_apply_result_review": public,
        "conversation_response": operator_repaired_candidate_apply_result_review_response(result),
        "public_digest": _digest(public),
    }
    if result.get("ok") is True and result.get("decision") == "propose-rollback":
        try:
            proposal = prepare_bounded_repaired_candidate_rollback_proposal(
                proposal_id,
                expected_revision=revision,
                expected_failed_attempt_number=failed_attempt,
                expected_review_digest=str(result.get("review_digest") or ""),
                expected_decision_digest=str(
                    result.get("operator_repaired_candidate_apply_result_decision_digest") or ""
                ),
                runtime_root=runtime_root,
            )
            turn["bounded_repaired_candidate_rollback_proposal"] = (
                public_operator_repaired_candidate_apply_result_review(proposal)
            )
            turn["conversation_response"] = (
                operator_repaired_candidate_apply_result_review_response(proposal)
            )
        except Exception as error:
            turn["bounded_repaired_candidate_rollback_proposal"] = {
                "ok": False,
                "status": "bounded_rollback_proposal_preparation_blocked",
                "reason_digest": _digest({"type": type(error).__name__}),
                "content_free": True,
                "rollback_authorized": False,
                "authority_granted": False,
            }
            turn["conversation_response"] = (
                "The rollback proposal could not be prepared. No project change was authorized."
            )
    turn["public_digest"] = _digest({
        key: value for key, value in turn.items()
        if key not in {"conversation_response", "public_digest"}
    })
    return turn


def load_operator_repaired_candidate_apply_result_review(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_review_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return record if record and _valid(
        record, "operator_repaired_candidate_apply_result_review_record_digest"
    ) else {}


def load_operator_repaired_candidate_apply_result_decision(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(_decision_path(proposal_id, revision, failed_attempt, runtime_root)) or {}
    return record if record and _valid(
        record, "operator_repaired_candidate_apply_result_decision_record_digest"
    ) else {}


def load_bounded_repaired_candidate_rollback_proposal(
    proposal_id: str, revision: int, failed_attempt: int, *, runtime_root=None
) -> dict[str, Any]:
    record = _read_json(
        _rollback_proposal_path(proposal_id, revision, failed_attempt, runtime_root)
    ) or {}
    return record if record and _valid(
        record, "bounded_repaired_candidate_rollback_proposal_record_digest"
    ) else {}
