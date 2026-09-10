from __future__ import annotations

"""Content-free v1197.5 operator review for runtime lifecycle application.

The contract reviews caller-supplied evidence for backup, migration, upgrade,
rollback, and isolated fresh-install application. Approve, reject, and defer are
presentation outcomes only. This module never reads or writes runtime data,
creates or consumes approval, applies an operation, or grants authority.
"""

from typing import Any, Mapping

from runtime_lifecycle_migration import LIFECYCLE_OPERATIONS, _digest, _is_digest, _private_fields

CONTRACT_VERSION = "v1197.5"
DECISIONS = ("approve", "reject", "defer")
REVIEW_ACTION_BY_OPERATION = {
    "backup": "review_backup_application",
    "migration": "review_migration_application",
    "upgrade": "review_upgrade_application",
    "rollback": "review_rollback_application",
    "fresh_install": "review_fresh_install_application",
}
REVIEW_ACTIONS = tuple(REVIEW_ACTION_BY_OPERATION[operation] for operation in LIFECYCLE_OPERATIONS)
REASON_CODES = (
    "evidence_sufficient",
    "evidence_rejected",
    "more_evidence_required",
    "operator_boundary_preserved",
)

_REQUEST_FALSE_FIELDS = (
    "runtime_read",
    "backup_created",
    "migration_applied",
    "upgrade_applied",
    "rollback_applied",
    "fresh_install_performed",
    "files_written",
    "files_deleted",
    "runtime_mutated",
    "source_modified",
    "provider_contacted",
    "model_contacted",
    "thread_started",
    "process_started",
    "approval_created",
    "approval_consumed",
    "automatic_continuation",
    "application_authority_requested",
)
_DECISION_FALSE_FIELDS = (
    "operation_executed",
    "runtime_read",
    "files_written",
    "files_deleted",
    "runtime_mutated",
    "source_modified",
    "provider_contacted",
    "model_contacted",
    "thread_started",
    "process_started",
    "approval_created",
    "approval_consumed",
    "automatic_continuation",
    "application_authorized",
    "authority_granted",
)


def build_lifecycle_application_review_request(
    *,
    review_id: str,
    lifecycle_id: str,
    operation: str,
    sequence: int,
    snapshot_digest: str,
    context_digest: str,
    plan_digest: str,
    evidence_digest: str,
    assessment_digest: str,
    previous_review_receipt_digest: str,
    purpose_code: str,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "review_id": str(review_id),
        "lifecycle_id": str(lifecycle_id),
        "operation": str(operation),
        "action": REVIEW_ACTION_BY_OPERATION.get(str(operation), "unsupported"),
        "sequence": sequence,
        "snapshot_digest": str(snapshot_digest),
        "context_digest": str(context_digest),
        "plan_digest": str(plan_digest),
        "evidence_digest": str(evidence_digest),
        "assessment_digest": str(assessment_digest),
        "previous_review_receipt_digest": str(previous_review_receipt_digest),
        "purpose_code": str(purpose_code),
        "content_free": True,
        "operator_review_required": True,
        "presentation_only": True,
        "original_runtime_preserved": True,
        "backup_truth_preserved": True,
        "rollback_truth_preserved": True,
        "fresh_install_isolation_preserved": True,
        "authority_state": "separate_not_granted",
    }
    request.update({field: False for field in _REQUEST_FALSE_FIELDS})
    request["request_digest"] = _digest(request)
    return request


def build_lifecycle_application_review_decision(
    *,
    request_digest: str,
    decision: str,
    operator_review_digest: str,
    reason_code: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "request_digest": str(request_digest),
        "decision": str(decision),
        "operator_review_digest": str(operator_review_digest),
        "reason_code": str(reason_code),
        "content_free": True,
        "presentation_only": True,
        "authority_state": "separate_not_granted",
    }
    row.update({field: False for field in _DECISION_FALSE_FIELDS})
    row["decision_digest"] = _digest(row)
    return row


def review_runtime_lifecycle_application(
    *,
    request: Mapping[str, Any],
    decision: Mapping[str, Any],
    expected_lifecycle_id: str,
    expected_operation: str,
    expected_sequence: int,
    expected_snapshot_digest: str,
    expected_context_digest: str,
    expected_plan_digest: str,
    expected_evidence_digest: str,
    expected_assessment_digest: str,
    expected_previous_review_receipt_digest: str,
) -> dict[str, Any]:
    req = dict(request)
    dec = dict(decision)
    errors: list[str] = []

    for field in _private_fields({"request": req, "decision": dec}):
        errors.append(f"private_field:{field}")

    supplied_request_digest = req.get("request_digest")
    unsigned_request = dict(req)
    unsigned_request.pop("request_digest", None)
    if supplied_request_digest != _digest(unsigned_request):
        errors.append("request_tamper")
    supplied_decision_digest = dec.get("decision_digest")
    unsigned_decision = dict(dec)
    unsigned_decision.pop("decision_digest", None)
    if supplied_decision_digest != _digest(unsigned_decision):
        errors.append("decision_tamper")

    if req.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported_request_contract")
    if dec.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported_decision_contract")
    if not str(req.get("review_id") or ""):
        errors.append("missing_review_id")
    if req.get("lifecycle_id") != expected_lifecycle_id:
        errors.append("lifecycle_mismatch")
    if req.get("operation") != expected_operation:
        errors.append("operation_mismatch")
    if expected_operation not in LIFECYCLE_OPERATIONS:
        errors.append("unsupported_expected_operation")
    if req.get("action") != REVIEW_ACTION_BY_OPERATION.get(expected_operation):
        errors.append("action_mismatch")
    if req.get("action") not in REVIEW_ACTIONS:
        errors.append("unsupported_action")
    if req.get("sequence") != expected_sequence:
        errors.append("sequence_mismatch")
    if not isinstance(req.get("sequence"), int) or isinstance(req.get("sequence"), bool) or not 1 <= req["sequence"] <= len(LIFECYCLE_OPERATIONS):
        errors.append("invalid_sequence")

    expected_digests = {
        "snapshot_digest": expected_snapshot_digest,
        "context_digest": expected_context_digest,
        "plan_digest": expected_plan_digest,
        "evidence_digest": expected_evidence_digest,
        "assessment_digest": expected_assessment_digest,
    }
    for field, expected in expected_digests.items():
        if not _is_digest(req.get(field)):
            errors.append(f"malformed_{field}")
        if req.get(field) != expected:
            errors.append(f"stale_{field}")

    previous = req.get("previous_review_receipt_digest")
    if expected_previous_review_receipt_digest:
        if not _is_digest(previous):
            errors.append("malformed_previous_review_receipt_digest")
        if previous != expected_previous_review_receipt_digest:
            errors.append("broken_review_lineage")
    elif previous not in ("", None):
        errors.append("unexpected_previous_review_receipt")

    if dec.get("request_digest") != req.get("request_digest"):
        errors.append("decision_request_mismatch")
    if dec.get("decision") not in DECISIONS:
        errors.append("unsupported_decision")
    if not _is_digest(dec.get("operator_review_digest")):
        errors.append("malformed_operator_review_digest")
    if dec.get("reason_code") not in REASON_CODES:
        errors.append("unsupported_reason_code")

    for field in ("content_free", "operator_review_required", "presentation_only", "original_runtime_preserved", "backup_truth_preserved", "rollback_truth_preserved", "fresh_install_isolation_preserved"):
        if req.get(field) is not True:
            errors.append(f"invalid_request_{field}")
    for field in _REQUEST_FALSE_FIELDS:
        if req.get(field) is not False:
            errors.append(f"forbidden_request_claim:{field}")
    if req.get("authority_state") != "separate_not_granted":
        errors.append("request_authority_expansion")

    for field in ("content_free", "presentation_only"):
        if dec.get(field) is not True:
            errors.append(f"invalid_decision_{field}")
    for field in _DECISION_FALSE_FIELDS:
        if dec.get(field) is not False:
            errors.append(f"forbidden_decision_claim:{field}")
    if dec.get("authority_state") != "separate_not_granted":
        errors.append("decision_authority_expansion")

    decision_name = str(dec.get("decision") or "")
    status = "blocked" if errors else {
        "approve": "application_review_approved",
        "reject": "application_review_rejected",
        "defer": "application_review_deferred",
    }[decision_name]
    result: dict[str, Any] = {
        "ok": not errors,
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "errors": sorted(set(errors)),
        "review_id": req.get("review_id"),
        "lifecycle_id": req.get("lifecycle_id"),
        "operation": req.get("operation"),
        "action": req.get("action"),
        "sequence": req.get("sequence"),
        "decision": dec.get("decision"),
        "content_free": True,
        "presentation_only": True,
        "exact_lineage_verified": not errors,
        "original_runtime_preserved": True,
        "backup_truth_preserved": True,
        "rollback_truth_preserved": True,
        "fresh_install_isolation_preserved": True,
        "separate_application_authorization_required": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "application_authorized": False,
        "operation_executed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
    result["review_receipt_digest"] = _digest(result)
    return result


def public_lifecycle_application_review_summary(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in results]
    return {
        "contract_version": CONTRACT_VERSION,
        "review_count": len(rows),
        "operation_count": len({row.get("operation") for row in rows}),
        "operations": list(LIFECYCLE_OPERATIONS),
        "decision_count": len({row.get("decision") for row in rows}),
        "decisions": list(DECISIONS),
        "all_reviews_valid": all(row.get("ok") is True for row in rows),
        "content_free": True,
        "presentation_only": True,
        "exact_lineage_verified": all(row.get("exact_lineage_verified") is True for row in rows),
        "original_runtime_preserved": True,
        "backup_truth_preserved": True,
        "rollback_truth_preserved": True,
        "fresh_install_isolation_preserved": True,
        "separate_application_authorization_required": True,
        "runtime_read": False,
        "backup_created": False,
        "migration_applied": False,
        "upgrade_applied": False,
        "rollback_applied": False,
        "fresh_install_performed": False,
        "files_written": False,
        "files_deleted": False,
        "runtime_mutated": False,
        "source_modified": False,
        "provider_contacted": False,
        "model_contacted": False,
        "thread_started": False,
        "process_started": False,
        "approval_created": False,
        "approval_consumed": False,
        "automatic_continuation": False,
        "application_authorized": False,
        "operation_executed": False,
        "global_profile_pass_claimed": False,
        "authority_state": "separate_not_granted",
        "authority_granted": False,
    }
