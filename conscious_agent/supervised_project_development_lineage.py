from __future__ import annotations

"""v1184.0-v1184.2 supervised project-development lineage foundations.

This module joins already-governed, content-free stage receipts into one exact
project-development lineage. It does not perform inspection, planning,
implementation, testing, repair, retesting, source application, or release.
"""

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "v1184.2"
SCHEMA_VERSION = "1"
MAX_CONTRACT_BYTES = 262_144
MAX_STAGES = 9
STAGES = (
    "inspection", "deficiency_review", "specification", "planning",
    "implementation", "testing", "diagnosis", "repair", "retest",
)
TERMINAL_STATUSES = frozenset({"accepted", "rejected", "deferred", "failed", "blocked", "completed"})
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()).hexdigest()


def _bounded(value: object) -> bool:
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode()) <= MAX_CONTRACT_BYTES


def create_project_stage_receipt(
    *, stage: str, status: str, artifact_digest: str, previous_receipt_digest: str = "",
    operator_review_digest: str = "", public_evidence_digest: str = "",
) -> dict[str, Any]:
    stage = str(stage or "").strip()
    status = str(status or "").strip()
    row = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "stage": stage,
        "status": status,
        "artifact_digest": str(artifact_digest or "").lower(),
        "previous_receipt_digest": str(previous_receipt_digest or "").lower(),
        "operator_review_digest": str(operator_review_digest or "").lower(),
        "public_evidence_digest": str(public_evidence_digest or "").lower(),
        "content_free": True,
        "private_content_included": False,
        "source_modified": False,
        "execution_invoked": False,
        "authority_granted": False,
    }
    row["receipt_digest"] = _digest(row)
    return row


def integrate_supervised_project_development(receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    base = {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "lineage_id": "supervised-project-development-lineage:v1184.2",
        "content_free": True,
        "private_content_included": False,
        "production_source_modified": False,
        "sandbox_modified": False,
        "execution_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_created": False,
        "authority_granted": False,
        "source_application_authorized": False,
        "installation_authorized": False,
        "promotion_authorized": False,
        "certification_authorized": False,
        "release_authorized": False,
        "autonomous_action_authorized": False,
        "operator_review_required_for_next_action": True,
    }
    rows = [dict(item) for item in receipts]
    errors: list[str] = []
    if not rows or len(rows) > MAX_STAGES:
        errors.append("invalid_stage_count")
    if not _bounded(rows):
        errors.append("oversized_contract")
    seen: set[str] = set()
    previous = ""
    expected_prefix = STAGES[:len(rows)]
    for index, row in enumerate(rows):
        stage = str(row.get("stage") or "")
        digest = str(row.get("receipt_digest") or "").lower()
        artifact = str(row.get("artifact_digest") or "").lower()
        status = str(row.get("status") or "")
        if index >= len(STAGES) or stage != expected_prefix[index]:
            errors.append("stage_order_mismatch")
        if stage in seen:
            errors.append("duplicate_stage")
        seen.add(stage)
        unsigned = dict(row)
        unsigned.pop("receipt_digest", None)
        if not DIGEST_RE.fullmatch(digest) or digest != _digest(unsigned):
            errors.append("tampered_receipt")
        if not DIGEST_RE.fullmatch(artifact):
            errors.append("invalid_artifact_digest")
        if index == 0:
            if str(row.get("previous_receipt_digest") or ""):
                errors.append("unexpected_initial_link")
        elif str(row.get("previous_receipt_digest") or "").lower() != previous:
            errors.append("lineage_link_mismatch")
        if row.get("content_free") is not True or row.get("private_content_included") is not False:
            errors.append("privacy_contract_violation")
        if any(row.get(key) is not False for key in ("source_modified", "execution_invoked", "authority_granted")):
            errors.append("authority_or_execution_expansion")
        if status not in TERMINAL_STATUSES:
            errors.append("unsupported_stage_status")
        if status in {"rejected", "deferred", "failed", "blocked"} and index != len(rows) - 1:
            errors.append("continued_after_terminal_stage")
        previous = digest
    errors = sorted(set(errors))
    completed_count = sum(1 for row in rows if row.get("status") in {"accepted", "completed"})
    full = len(rows) == len(STAGES) and not errors
    result_status = "complete_review_required" if full else ("blocked" if errors else "in_progress_review_required")
    result = {
        **base,
        "status": result_status,
        "stage_count": len(rows),
        "completed_stage_count": completed_count,
        "current_stage": rows[-1].get("stage", "") if rows else "",
        "next_stage": "" if full or errors else STAGES[len(rows)],
        "stage_receipt_digests": [str(row.get("receipt_digest") or "") for row in rows],
        "terminal_receipt_digest": previous,
        "error_count": len(errors),
        "errors": errors,
        "complete_lineage": full,
        "result_presentation_created": False,
        "learning_record_created": False,
    }
    result["lineage_digest"] = _digest(result)
    return result


def supervised_project_development_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": result.get("contract_version"),
        "lineage_id": result.get("lineage_id"),
        "status": result.get("status"),
        "stage_count": int(result.get("stage_count") or 0),
        "completed_stage_count": int(result.get("completed_stage_count") or 0),
        "current_stage": result.get("current_stage", ""),
        "next_stage": result.get("next_stage", ""),
        "error_count": int(result.get("error_count") or 0),
        "complete_lineage": result.get("complete_lineage") is True,
        "lineage_digest": result.get("lineage_digest", ""),
        "content_free": True,
        "operator_review_required_for_next_action": True,
        "authority_granted": False,
    }
