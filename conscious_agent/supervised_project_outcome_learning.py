from __future__ import annotations

"""v1184.3-v1184.5 operator-facing results and accountable outcome learning.

Creates content-free presentation and learning receipts from an exact v1184.2
lineage. It does not modify source, execute work, approve work, or grant authority.
"""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1184.5"
SCHEMA_VERSION = "1"
MAX_BYTES = 262_144
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
OUTCOMES = frozenset({"accepted", "rejected", "failed", "repaired"})
LESSON_CODES = frozenset({
    "retain_approach", "avoid_rejected_approach", "strengthen_failure_checks",
    "retain_repair_pattern", "require_more_evidence", "no_generalization",
})


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _bounded(value: object) -> bool:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()) <= MAX_BYTES


def create_project_result_presentation(*, lineage: Mapping[str, Any], outcome: str,
        operator_decision_digest: str, result_evidence_digest: str,
        rollback_available: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    outcome = str(outcome or "").strip()
    lineage_digest = str(lineage.get("lineage_digest") or "").lower()
    terminal_digest = str(lineage.get("terminal_receipt_digest") or "").lower()
    if lineage.get("complete_lineage") is not True or lineage.get("status") != "complete_review_required": errors.append("incomplete_lineage")
    if not DIGEST_RE.fullmatch(lineage_digest) or _digest({k:v for k,v in lineage.items() if k != "lineage_digest"}) != lineage_digest: errors.append("tampered_lineage")
    if outcome not in OUTCOMES: errors.append("unsupported_outcome")
    for name, value in (("operator_decision_digest", operator_decision_digest), ("result_evidence_digest", result_evidence_digest), ("terminal_receipt_digest", terminal_digest)):
        if not DIGEST_RE.fullmatch(str(value or "").lower()): errors.append(f"invalid_{name}")
    if not _bounded(lineage): errors.append("oversized_input")
    row = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "presentation_id": "supervised-project-result:v1184.5", "outcome": outcome,
        "lineage_digest": lineage_digest, "terminal_receipt_digest": terminal_digest,
        "operator_decision_digest": str(operator_decision_digest or "").lower(),
        "result_evidence_digest": str(result_evidence_digest or "").lower(),
        "rollback_available": bool(rollback_available), "error_count": len(set(errors)),
        "errors": sorted(set(errors)), "status": "ready_for_operator_review" if not errors else "blocked",
        "content_free": True, "private_content_included": False,
        "production_source_modified": False, "sandbox_modified": False,
        "execution_invoked": False, "learning_applied": False, "approval_created": False,
        "authority_granted": False, "source_application_authorized": False,
        "installation_authorized": False, "promotion_authorized": False,
        "certification_authorized": False, "release_authorized": False,
    }
    row["presentation_digest"] = _digest(row)
    return row


def create_accountable_outcome_learning(*, presentation: Mapping[str, Any], lesson_codes: Sequence[str],
        operator_learning_review_digest: str) -> dict[str, Any]:
    errors: list[str] = []
    unsigned = dict(presentation); presented_digest = str(unsigned.pop("presentation_digest", "")).lower()
    if not DIGEST_RE.fullmatch(presented_digest) or _digest(unsigned) != presented_digest: errors.append("tampered_presentation")
    if presentation.get("status") != "ready_for_operator_review": errors.append("presentation_not_ready")
    codes = [str(code or "").strip() for code in lesson_codes]
    if not codes or len(codes) > 4: errors.append("invalid_lesson_count")
    if len(codes) != len(set(codes)): errors.append("duplicate_lesson_code")
    if any(code not in LESSON_CODES for code in codes): errors.append("unsupported_lesson_code")
    outcome = str(presentation.get("outcome") or "")
    required = {"accepted":"retain_approach", "rejected":"avoid_rejected_approach", "failed":"strengthen_failure_checks", "repaired":"retain_repair_pattern"}.get(outcome)
    if required and required not in codes: errors.append("outcome_lesson_mismatch")
    review = str(operator_learning_review_digest or "").lower()
    if not DIGEST_RE.fullmatch(review): errors.append("invalid_operator_learning_review_digest")
    if not _bounded({"presentation": presentation, "codes": codes}): errors.append("oversized_input")
    row = {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "learning_id": "accountable-project-outcome-learning:v1184.5",
        "presentation_digest": presented_digest, "lineage_digest": presentation.get("lineage_digest", ""),
        "outcome": outcome, "lesson_codes": codes,
        "operator_learning_review_digest": review, "error_count": len(set(errors)),
        "errors": sorted(set(errors)), "status": "learning_recorded" if not errors else "blocked",
        "content_free": True, "private_content_included": False,
        "generalized_beyond_evidence": False, "historical_truth_preserved": True,
        "production_source_modified": False, "sandbox_modified": False,
        "execution_invoked": False, "approval_created": False, "authority_granted": False,
        "source_application_authorized": False, "release_authorized": False,
        "autonomous_action_authorized": False,
    }
    row["learning_digest"] = _digest(row)
    return row


def project_outcome_public_summary(presentation: Mapping[str, Any], learning: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION, "outcome": presentation.get("outcome", ""),
        "presentation_status": presentation.get("status", ""), "learning_status": learning.get("status", ""),
        "lesson_codes": list(learning.get("lesson_codes") or []),
        "rollback_available": presentation.get("rollback_available") is True,
        "presentation_digest": presentation.get("presentation_digest", ""),
        "learning_digest": learning.get("learning_digest", ""),
        "content_free": True, "historical_truth_preserved": True,
        "operator_review_required_for_next_action": True, "authority_granted": False,
    }
