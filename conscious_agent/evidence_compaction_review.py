from __future__ import annotations
"""v1192.3-v1192.5 operator review for bounded evidence compaction.

Records content-free review decisions only. It never replaces, deletes, mutates,
or promotes retained evidence and never grants execution or release authority.
"""
import hashlib, json, re
from collections.abc import Mapping
from typing import Any

CONTRACT_VERSION = "v1192.5"
SCHEMA_VERSION = "1"
DECISIONS = ("approve", "reject", "defer")
PURPOSE_CODES = {"retain_compaction", "request_rebuild", "preserve_original", "operator_review"}
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
MAX_CONTRACT_BYTES = 262_144
FORBIDDEN = {"prompt", "conversation", "memory", "secret", "raw_source", "raw_patch", "stdout", "stderr", "provider_payload", "private_reasoning", "content", "text", "release_authority"}

def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")).hexdigest()

def _is_digest(value: object) -> bool:
    return bool(DIGEST_RE.fullmatch(str(value or "").lower()))

def _forbidden(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(str(key).lower() in FORBIDDEN or _forbidden(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_forbidden(item) for item in value)
    return False

def _verify(row: Mapping[str, Any], field: str) -> bool:
    item = dict(row); claimed = str(item.pop(field, "")).lower()
    return _is_digest(claimed) and claimed == _digest(item)

def create_compaction_review_request(*, request_id: str, compaction_digest: str, terminal_evidence_digest: str,
                                     snapshot_digest: str, context_digest: str, record_count: int,
                                     equivalence_digest: str, purpose_code: str = "operator_review") -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "request_id": str(request_id or ""), "compaction_digest": str(compaction_digest or "").lower(),
        "terminal_evidence_digest": str(terminal_evidence_digest or "").lower(),
        "snapshot_digest": str(snapshot_digest or "").lower(), "context_digest": str(context_digest or "").lower(),
        "record_count": int(record_count), "equivalence_digest": str(equivalence_digest or "").lower(),
        "purpose_code": str(purpose_code or ""), "content_free": True,
        "replacement_requested": False, "deletion_requested": False, "execution_requested": False,
        "automatic_acceptance": False, "authority_requested": False,
    }
    row["request_digest"] = _digest(row)
    return row

def create_compaction_review(*, request_digest: str, decision: str, review_id: str,
                             operator_review_digest: str, reason_code: str = "operator_reviewed") -> dict[str, Any]:
    row = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "request_digest": str(request_digest or "").lower(), "decision": str(decision or ""),
        "review_id": str(review_id or ""), "operator_review_digest": str(operator_review_digest or "").lower(),
        "reason_code": str(reason_code or ""), "content_free": True,
        "approval_created": False, "approval_consumed": False, "replacement_performed": False,
        "deletion_performed": False, "authority_granted": False,
    }
    row["review_digest"] = _digest(row)
    return row

def review_compaction(*, request: Mapping[str, Any], review: Mapping[str, Any],
                      current_snapshot_digest: str, current_context_digest: str,
                      current_compaction_digest: str, current_terminal_evidence_digest: str,
                      equivalence_verified: bool) -> dict[str, Any]:
    req, rev = dict(request), dict(review); errors: list[str] = []
    if len(json.dumps([req, rev], sort_keys=True, default=str).encode("utf-8")) > MAX_CONTRACT_BYTES: errors.append("oversized_contract")
    if _forbidden([req, rev]): errors.append("private_or_authority_content_present")
    if not _verify(req, "request_digest"): errors.append("tampered_request")
    if not _verify(rev, "review_digest"): errors.append("tampered_review")
    if req.get("contract_version") != CONTRACT_VERSION or rev.get("contract_version") != CONTRACT_VERSION: errors.append("contract_mismatch")
    if not ID_RE.fullmatch(str(req.get("request_id") or "")): errors.append("invalid_request_id")
    if not ID_RE.fullmatch(str(rev.get("review_id") or "")): errors.append("invalid_review_id")
    for field in ("compaction_digest", "terminal_evidence_digest", "snapshot_digest", "context_digest", "equivalence_digest"):
        if not _is_digest(req.get(field)): errors.append("invalid_" + field)
    if not _is_digest(rev.get("operator_review_digest")): errors.append("invalid_operator_review_digest")
    if rev.get("request_digest") != req.get("request_digest"): errors.append("review_request_mismatch")
    if rev.get("decision") not in DECISIONS: errors.append("unsupported_decision")
    if req.get("purpose_code") not in PURPOSE_CODES: errors.append("unsupported_purpose_code")
    if req.get("record_count", 0) < 1 or req.get("record_count", 0) > 64: errors.append("invalid_record_count")
    if req.get("snapshot_digest") != str(current_snapshot_digest or "").lower(): errors.append("stale_snapshot")
    if req.get("context_digest") != str(current_context_digest or "").lower(): errors.append("stale_context")
    if req.get("compaction_digest") != str(current_compaction_digest or "").lower(): errors.append("stale_compaction")
    if req.get("terminal_evidence_digest") != str(current_terminal_evidence_digest or "").lower(): errors.append("stale_terminal_evidence")
    if equivalence_verified is not True: errors.append("equivalence_not_verified")
    for field in ("replacement_requested", "deletion_requested", "execution_requested", "automatic_acceptance", "authority_requested"):
        if req.get(field) is not False: errors.append("hidden_mutation_or_authority_claim")
    for field in ("approval_created", "approval_consumed", "replacement_performed", "deletion_performed", "authority_granted"):
        if rev.get(field) is not False: errors.append("hidden_mutation_or_authority_claim")
    if req.get("content_free") is not True or rev.get("content_free") is not True: errors.append("privacy_contract_violation")
    errors = sorted(set(errors)); decision = str(rev.get("decision") or "")
    accepted = not errors and decision == "approve"
    status = "review_approved" if accepted else ("review_rejected" if not errors and decision == "reject" else ("review_deferred" if not errors and decision == "defer" else "blocked"))
    result = {
        "contract_version": CONTRACT_VERSION, "request_id": req.get("request_id", ""), "review_id": rev.get("review_id", ""),
        "decision": decision, "status": status, "errors": errors, "error_count": len(errors),
        "compaction_retention_presented": accepted, "original_evidence_preserved": True,
        "equivalence_verified": equivalence_verified is True, "content_free": True,
        "replacement_performed": False, "deletion_performed": False, "runtime_modified": False,
        "execution_invoked": False, "approval_created": False, "approval_consumed": False,
        "provider_contacted": False, "model_contacted": False, "thread_started": False, "process_started": False,
        "authority_granted": False,
    }
    result["review_result_digest"] = _digest(result)
    return result

def public_compaction_review_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: result.get(key) for key in ("contract_version", "status", "decision", "compaction_retention_presented", "original_evidence_preserved", "equivalence_verified", "content_free", "replacement_performed", "deletion_performed", "execution_invoked", "authority_granted")}
