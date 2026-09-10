from __future__ import annotations

"""v1258.6-v1258.8 reliability and read-only operator handoff.

The reliability layer inspects sealed construction and per-attempt quality
records, verifies their lineage against v1254 execution evidence, and surfaces
missing/tampered/incomplete application-quality state without running providers,
tests, diagnostics, application, or rollback.
"""

from pathlib import Path
from typing import Any, Mapping

from complete_application_construction import load_complete_application_quality, public_complete_application_quality
from complete_application_construction_foundations import (
    DENIED_AUTHORITY,
    load_complete_application_construction,
    public_complete_application_construction,
)
from isolated_coding_execution import load_isolated_coding_execution, load_isolated_coding_review
from isolated_coding_execution_foundations import check_coding_source_freshness
from ordinary_chat_development_campaign import _digest, _read_json, _store_root

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1258.8"


def _attempt(request_id: str, number: int, runtime_root=None) -> dict[str, Any]:
    path = _store_root(runtime_root) / "isolated_coding_execution_attempts" / request_id / f"attempt-{int(number)}.json"
    row = _read_json(path)
    if not row:
        return {}
    supplied = str(row.get("attempt_record_digest") or "")
    expected = _digest({k: v for k, v in row.items() if k != "attempt_record_digest"})
    return row if supplied and supplied == expected else {}


def inspect_complete_application_health(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    contract = load_complete_application_construction(request_id, runtime_root=runtime_root)
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    review = load_isolated_coding_review(request_id, runtime_root=runtime_root)
    freshness = check_coding_source_freshness(request_id, runtime_root=runtime_root)
    errors: list[str] = []
    warnings: list[str] = []
    if not contract:
        errors.append("construction_contract_missing_or_invalid")
    if not execution:
        errors.append("isolated_execution_missing_or_invalid")
    result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
    attempt_count = int(result.get("attempt_count") or execution.get("attempt_count") or 0)
    quality_chain: list[dict[str, Any]] = []
    for number in range(1, attempt_count + 1):
        attempt = _attempt(request_id, number, runtime_root)
        if not attempt:
            errors.append(f"attempt_{number}_missing_or_invalid")
            continue
        verification = dict(attempt.get("verification") or {})
        quality = load_complete_application_quality(request_id, number, runtime_root=runtime_root)
        quality_path = _store_root(runtime_root) / "complete_application_quality" / request_id / f"attempt-{number}.json"
        if not quality:
            if quality_path.exists():
                errors.append(f"quality_result_{number}_invalid")
            elif verification.get("construction_quality_digest"):
                errors.append(f"quality_result_{number}_missing")
            else:
                warnings.append(f"attempt_{number}_has_no_construction_quality_record")
            continue
        if contract and str(quality.get("construction_contract_digest") or "") != str(contract.get("construction_contract_digest") or ""):
            errors.append(f"quality_result_{number}_contract_binding_mismatch")
        if str(verification.get("construction_quality_digest") or "") and str(verification.get("construction_quality_digest") or "") != str(quality.get("quality_result_digest") or ""):
            errors.append(f"quality_result_{number}_verification_binding_mismatch")
        if any(quality.get(key) is not expected for key, expected in DENIED_AUTHORITY.items()):
            errors.append(f"quality_result_{number}_authority_boundary_invalid")
        quality_chain.append({
            "attempt_number": number,
            "attempt_digest": str(attempt.get("attempt_record_digest") or ""),
            "verification_digest": str(verification.get("verification_digest") or ""),
            "quality_result_digest": str(quality.get("quality_result_digest") or ""),
            "passed": bool(quality.get("passed")),
            "failed_finding_codes": list(quality.get("failed_finding_codes") or []),
            "dimension_results": dict(quality.get("dimension_results") or {}),
        })
    final_quality = quality_chain[-1] if quality_chain else {}
    if result.get("test_passed") is True and quality_chain and not final_quality.get("passed"):
        errors.append("execution_claims_pass_with_failed_construction_quality")
    if result.get("test_passed") is True and contract and not quality_chain:
        errors.append("completed_construction_missing_quality_evidence")
    if review and result.get("test_passed") is True and review.get("reviewable_diff_available") is not True:
        errors.append("completed_construction_missing_reviewable_diff")
    if freshness.get("ok") is not True:
        warnings.append("selected_project_source_not_fresh_for_handoff")
    chain_digest = _digest(quality_chain)
    row = {
        "ok": not errors,
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "complete_application_construction_healthy" if not errors else "complete_application_construction_health_blocked",
        "request_id": request_id,
        "construction_contract_digest": str(contract.get("construction_contract_digest") or ""),
        "execution_digest": str(execution.get("execution_digest") or ""),
        "execution_status": str(result.get("status") or execution.get("status") or ""),
        "attempt_count": attempt_count,
        "quality_chain": quality_chain,
        "quality_chain_digest": chain_digest,
        "final_quality_passed": bool(final_quality.get("passed")),
        "review_digest": str(review.get("review_record_digest") or ""),
        "reviewable_diff_available": bool(review.get("reviewable_diff_available")),
        "source_fresh": bool(freshness.get("ok")),
        "errors": errors,
        "warnings": warnings,
        "read_only": True,
        "content_minimized": True,
        "provider_contacted_by_inspection": False,
        "tests_executed_by_inspection": False,
        "diagnostics_executed_by_inspection": False,
        "selected_project_modified": False,
        "source_modified": False,
        "native_windows_path_and_browser_validation": "desktop_review_required",
        **DENIED_AUTHORITY,
    }
    row["health_digest"] = _digest(row)
    return row


def build_complete_application_operator_handoff(request_id: str, *, runtime_root=None) -> dict[str, Any]:
    request_id = str(request_id or "").lower()
    health = inspect_complete_application_health(request_id, runtime_root=runtime_root)
    contract = load_complete_application_construction(request_id, runtime_root=runtime_root)
    execution = load_isolated_coding_execution(request_id, runtime_root=runtime_root)
    review = load_isolated_coding_review(request_id, runtime_root=runtime_root)
    result = execution.get("result") if isinstance(execution.get("result"), Mapping) else {}
    final_quality = {}
    if health.get("quality_chain"):
        number = int(health["quality_chain"][-1].get("attempt_number") or 0)
        final_quality = load_complete_application_quality(request_id, number, runtime_root=runtime_root)
    limitations = [
        "Structural accessibility checks do not replace assistive-technology or human accessibility review.",
        "Responsive checks prove bounded structural signals, not every viewport or browser rendering outcome.",
        "No new dependency is installed; dependency installation remains separately governed and currently denied.",
        "The selected project remains unchanged until the separate v1255 controlled-application authorization is explicitly used.",
        "Native Windows path, NTFS reparse, and real browser behavior still require Desktop Codex validation.",
    ]
    row = {
        "ok": bool(health.get("ok")) and bool(health.get("final_quality_passed")),
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": "complete_application_operator_handoff_ready" if health.get("ok") and health.get("final_quality_passed") else "complete_application_operator_handoff_blocked",
        "request_id": request_id,
        "construction": public_complete_application_construction(contract) if contract else {},
        "final_quality": public_complete_application_quality(final_quality) if final_quality else {},
        "execution_status": str(result.get("status") or execution.get("status") or ""),
        "attempt_count": int(result.get("attempt_count") or 0),
        "repair_attempt_count": int(result.get("repair_attempt_count") or 0),
        "review_digest": str(review.get("review_record_digest") or ""),
        "diff_digest": str(review.get("diff_digest") or ""),
        "changed_file_count": len(review.get("changed_paths") or []),
        "reviewable_diff_available": bool(review.get("reviewable_diff_available")),
        "health_digest": str(health.get("health_digest") or ""),
        "limitations": limitations,
        "operator_review_required": True,
        "read_only": True,
        "content_minimized": True,
        "provider_contacted_by_handoff": False,
        "tests_executed_by_handoff": False,
        "selected_project_modified": False,
        "source_modified": False,
        **DENIED_AUTHORITY,
    }
    row["handoff_digest"] = _digest(row)
    return row


__all__ = ["CONTRACT_VERSION", "build_complete_application_operator_handoff", "inspect_complete_application_health"]
