from __future__ import annotations

"""Content-free v1198.5 operator freeze-exception and consolidation review.

Review outcomes are presentation-only. They do not approve exceptions, move or
merge files, rewrite imports, execute startup profiling, or expand authority.
"""

import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION = "v1198.5"
REVIEW_ACTIONS = ("freeze_exception", "canonical_owner", "duplicate_alias", "overlap_merge", "startup_hotspot")
DECISIONS = ("approve", "reject", "defer")
PRIVATE_TOKENS = ("prompt", "conversation_text", "message", "memory_content", "secret", "password", "token_value", "raw_source", "source_text", "patch", "stdout", "stderr", "provider_payload", "private_reasoning", "credential", "api_key")
FORBIDDEN_FALSE = ("exception_applied", "files_moved", "modules_merged", "files_deleted", "imports_rewritten", "startup_executed", "runtime_mutated", "source_modified", "approval_created", "approval_consumed", "provider_contacted", "model_contacted", "process_started", "thread_started", "installation_performed", "promotion_performed", "certification_performed", "publication_performed", "release_performed", "automatic_continuation")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def _is_digest(value: object) -> bool:
    token = str(value or "")
    return len(token) == 64 and all(ch in "0123456789abcdef" for ch in token)


def _private_fields(value: object, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            if any(token in str(key).lower() for token in PRIVATE_TOKENS): found.append(label)
            found.extend(_private_fields(item, label))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value): found.extend(_private_fields(item, f"{prefix}[{index}]"))
    return sorted(set(found))


def create_review_request(*, request_id: str, action: str, snapshot_digest: str, context_digest: str,
                          assessment_digest: str, architecture_digest: str, target_id: str,
                          sequence: int, prior_review_receipt_digest: str | None,
                          purpose_code: str) -> dict[str, Any]:
    row = {
        "contract_version": CONTRACT_VERSION, "request_id": str(request_id), "action": str(action),
        "snapshot_digest": str(snapshot_digest), "context_digest": str(context_digest),
        "assessment_digest": str(assessment_digest), "architecture_digest": str(architecture_digest),
        "target_id": str(target_id), "sequence": sequence,
        "prior_review_receipt_digest": str(prior_review_receipt_digest or ""),
        "purpose_code": str(purpose_code), "content_free": True, "read_only": True,
        "feature_freeze_active": True, "exception_applied": False, "files_moved": False,
        "modules_merged": False, "files_deleted": False, "imports_rewritten": False,
        "startup_executed": False, "runtime_mutated": False, "source_modified": False,
        "approval_created": False, "approval_consumed": False, "provider_contacted": False,
        "model_contacted": False, "process_started": False, "thread_started": False,
        "installation_performed": False, "promotion_performed": False,
        "certification_performed": False, "publication_performed": False,
        "release_performed": False, "automatic_continuation": False,
        "authority_state": "separate_not_granted",
    }
    row["request_digest"] = _digest(row)
    return row


def review_freeze_or_consolidation(request: Mapping[str, Any], *, decision: str, operator_review_digest: str,
                                   current_snapshot_digest: str, current_context_digest: str,
                                   current_assessment_digest: str, current_architecture_digest: str,
                                   expected_sequence: int, expected_prior_review_receipt_digest: str | None) -> dict[str, Any]:
    req = dict(request); errors: list[str] = []
    errors.extend(f"private_field:{field}" for field in _private_fields(req))
    unsigned = dict(req); supplied = unsigned.pop("request_digest", None)
    if supplied != _digest(unsigned): errors.append("request_tamper")
    if req.get("contract_version") != CONTRACT_VERSION: errors.append("unsupported_contract")
    if req.get("action") not in REVIEW_ACTIONS: errors.append("unsupported_action")
    if decision not in DECISIONS: errors.append("unsupported_decision")
    if req.get("snapshot_digest") != current_snapshot_digest: errors.append("stale_snapshot")
    if req.get("context_digest") != current_context_digest: errors.append("stale_context")
    if req.get("assessment_digest") != current_assessment_digest: errors.append("stale_assessment")
    if req.get("architecture_digest") != current_architecture_digest: errors.append("stale_architecture")
    for field in ("snapshot_digest", "context_digest", "assessment_digest", "architecture_digest"):
        if not _is_digest(req.get(field)): errors.append(f"malformed_{field}")
    if not _is_digest(operator_review_digest): errors.append("malformed_operator_review_digest")
    if not str(req.get("request_id") or ""): errors.append("missing_request_id")
    if not str(req.get("target_id") or ""): errors.append("missing_target_id")
    if not str(req.get("purpose_code") or ""): errors.append("missing_purpose_code")
    if req.get("sequence") != expected_sequence or not isinstance(req.get("sequence"), int) or isinstance(req.get("sequence"), bool) or req.get("sequence", 0) < 1: errors.append("review_sequence_mismatch")
    expected_prior = str(expected_prior_review_receipt_digest or "")
    if str(req.get("prior_review_receipt_digest") or "") != expected_prior: errors.append("review_lineage_mismatch")
    if expected_prior and not _is_digest(expected_prior): errors.append("malformed_prior_review_receipt_digest")
    if req.get("content_free") is not True or req.get("read_only") is not True or req.get("feature_freeze_active") is not True: errors.append("review_boundary_loss")
    for field in FORBIDDEN_FALSE:
        if req.get(field) is not False: errors.append(f"forbidden_claim:{field}")
    if req.get("authority_state") != "separate_not_granted": errors.append("authority_expansion")

    status = "reviewed" if not errors else "blocked"
    eligible = not errors and decision == "approve"
    result = {
        "contract_version": CONTRACT_VERSION, "status": status, "errors": sorted(set(errors)),
        "request_id": req.get("request_id"), "action": req.get("action"), "decision": decision,
        "target_id": req.get("target_id"), "sequence": req.get("sequence"),
        "snapshot_digest": req.get("snapshot_digest"), "context_digest": req.get("context_digest"),
        "assessment_digest": req.get("assessment_digest"), "architecture_digest": req.get("architecture_digest"),
        "operator_review_digest": operator_review_digest, "content_free": True, "read_only": True,
        "presentation_outcome": ({"approve": "eligible_for_separate_application_review", "reject": "rejected", "defer": "deferred"}.get(decision, "blocked") if not errors else "blocked"),
        "separate_application_review_required": eligible,
        "feature_freeze_active": True, "exception_applied": False, "files_moved": False,
        "modules_merged": False, "files_deleted": False, "imports_rewritten": False,
        "startup_executed": False, "runtime_mutated": False, "source_modified": False,
        "approval_created": False, "approval_consumed": False, "provider_contacted": False,
        "model_contacted": False, "process_started": False, "thread_started": False,
        "installation_performed": False, "promotion_performed": False,
        "certification_performed": False, "publication_performed": False,
        "release_performed": False, "automatic_continuation": False,
        "authority_state": "separate_not_granted",
    }
    result["review_receipt_digest"] = _digest(result)
    return result


def public_review_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("contract_version", "status", "action", "decision", "target_id", "sequence", "presentation_outcome", "separate_application_review_required", "content_free", "read_only", "feature_freeze_active") + FORBIDDEN_FALSE + ("authority_state", "review_receipt_digest")
    return {key: result.get(key) for key in keys}
