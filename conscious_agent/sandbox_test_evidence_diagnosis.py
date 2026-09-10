from __future__ import annotations

"""v1182.3-v1182.5 sandbox test evidence and diagnosis foundations.

Consumes one exact, content-free v1182.2 sandbox-test receipt and produces a
bounded evidence bundle plus conservative diagnosis candidates. Diagnosis is
not repair, approval, retry, promotion, or proof of root cause.
"""

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1182.5"
MAX_TEST_RESULTS = 8
MAX_DIAGNOSES = 8
_ALLOWED_EXECUTION_STATES = frozenset({"passed", "failed", "timed_out", "blocked"})
_ALLOWED_TESTS = frozenset({"python_compile", "content_digest_match"})
_ALLOWED_RESULT_STATES = frozenset({"passed", "failed", "timed_out"})
_ALLOWED_ERROR_CLASSES = frozenset({"", "python_compile_failed", "test_timeout"})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _text(value: Any, limit: int = 260) -> str:
    return " ".join(str(value or "").split())[:limit]


def _hex64(value: Any) -> str:
    text = _text(value, 64).lower()
    return text if len(text) == 64 and all(ch in "0123456789abcdef" for ch in text) else ""


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content_free": True,
        "sandbox_only": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "patch_created": False,
        "repair_created": False,
        "tests_rerun": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_granted": False,
        "promotion_authorized": False,
        "installation_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "operator_review_required": True,
    }


def _receipt_digest_valid(receipt: Mapping[str, Any]) -> bool:
    supplied = _hex64(receipt.get("test_receipt_digest"))
    if not supplied:
        return False
    unsigned = dict(receipt)
    unsigned.pop("test_receipt_digest", None)
    return _digest(unsigned) == supplied


def _normalize_results(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in list(values)[:MAX_TEST_RESULTS]:
        test = _text(raw.get("test"), 40)
        status = _text(raw.get("status"), 24)
        error_class = _text(raw.get("error_class"), 48)
        result_digest = _hex64(raw.get("result_digest"))
        if test not in _ALLOWED_TESTS or status not in _ALLOWED_RESULT_STATES or error_class not in _ALLOWED_ERROR_CLASSES:
            return []
        if status == "passed" and error_class:
            return []
        if status != "passed" and not error_class:
            return []
        if test == "content_digest_match" and status == "passed" and not result_digest:
            return []
        row = {"test": test, "status": status, "error_class": error_class}
        if result_digest:
            row["result_digest"] = result_digest
        rows.append(row)
    return rows


def build_sandbox_test_evidence(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and compact one exact v1182.2 test receipt."""
    base = _base()
    execution_status = _text(receipt.get("execution_status"), 24)
    target = _text(receipt.get("target_path"), 260)
    attempt_digest = _hex64(receipt.get("attempt_digest"))
    review_digest = _hex64(receipt.get("review_digest"))
    materialization_digest = _hex64(receipt.get("materialization_receipt_digest"))
    target_digest = _hex64(receipt.get("sandbox_target_digest"))
    block_reason = _text(receipt.get("block_reason"), 80)
    raw_results = receipt.get("test_results") or []
    results = _normalize_results(raw_results) if isinstance(raw_results, Sequence) and not isinstance(raw_results, (str, bytes)) else []

    valid_common = (
        receipt.get("contract_version") == "v1182.2"
        and receipt.get("content_free") is True
        and receipt.get("sandbox_only") is True
        and receipt.get("source_modified") is False
        and execution_status in _ALLOWED_EXECUTION_STATES
        and _receipt_digest_valid(receipt)
    )
    if not valid_common:
        result = {**base, "evidence_status": "blocked", "block_reason": "invalid_test_receipt"}
    elif execution_status in {"passed", "failed", "timed_out"} and not (
        receipt.get("tests_executed") is True
        and target and attempt_digest and review_digest and materialization_digest and target_digest
        and results and int(receipt.get("test_count") or 0) == len(results)
    ):
        result = {**base, "evidence_status": "blocked", "block_reason": "incomplete_executed_test_evidence"}
    elif execution_status == "blocked" and not block_reason:
        result = {**base, "evidence_status": "blocked", "block_reason": "incomplete_blocked_test_evidence"}
    else:
        structural = {
            "execution_status": execution_status,
            "target_path": target,
            "attempt_digest": attempt_digest,
            "review_digest": review_digest,
            "materialization_receipt_digest": materialization_digest,
            "sandbox_target_digest": target_digest,
            "test_receipt_digest": _hex64(receipt.get("test_receipt_digest")),
            "test_count": len(results),
            "test_results": results,
            "block_reason": block_reason,
        }
        evidence_digest = _digest(structural)
        result = {
            **base,
            **structural,
            "evidence_status": "verified",
            "evidence_id": f"sandbox-test-evidence-{evidence_digest[:20]}",
            "evidence_digest": evidence_digest,
            "root_cause_proven": False,
        }
    result["evidence_receipt_digest"] = _digest(result)
    return result


def diagnose_sandbox_test_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Produce conservative, content-free diagnosis candidates."""
    base = _base()
    valid = (
        evidence.get("contract_version") == CONTRACT_VERSION
        and evidence.get("evidence_status") == "verified"
        and evidence.get("content_free") is True
        and _hex64(evidence.get("evidence_digest"))
        and _hex64(evidence.get("evidence_receipt_digest"))
        and evidence.get("root_cause_proven") is False
    )
    if not valid:
        result = {**base, "diagnosis_status": "blocked", "block_reason": "invalid_evidence_contract"}
        result["diagnosis_receipt_digest"] = _digest(result)
        return result

    rows: list[dict[str, Any]] = []
    execution_status = _text(evidence.get("execution_status"), 24)
    block_reason = _text(evidence.get("block_reason"), 80)
    for test in list(evidence.get("test_results") or [])[:MAX_TEST_RESULTS]:
        name = _text(test.get("test"), 40)
        status = _text(test.get("status"), 24)
        error_class = _text(test.get("error_class"), 48)
        if status == "passed":
            continue
        if name == "python_compile" and error_class == "python_compile_failed":
            rows.append({
                "diagnosis_code": "python_compile_failure_observed",
                "confidence": "high_observation_low_root_cause",
                "supported_conclusion": "sandbox_target_did_not_compile",
                "unknowns": ["exact_syntax_or_import_cause", "required_repair"],
                "suggested_next_step": "operator_review_compile_failure_evidence",
            })
        elif error_class == "test_timeout":
            rows.append({
                "diagnosis_code": "sandbox_test_timeout_observed",
                "confidence": "high_observation_low_root_cause",
                "supported_conclusion": "bounded_test_did_not_finish_in_time",
                "unknowns": ["hang_or_resource_cause", "required_repair"],
                "suggested_next_step": "operator_review_timeout_evidence",
            })
    if execution_status == "blocked":
        rows.append({
            "diagnosis_code": "sandbox_test_execution_blocked",
            "confidence": "high_observation_low_root_cause",
            "supported_conclusion": block_reason or "test_execution_was_blocked",
            "unknowns": ["whether_target_would_pass", "required_repair"],
            "suggested_next_step": "repair_governance_or_evidence_binding_before_retest",
        })
    if execution_status == "passed" and not rows:
        posture = "no_diagnosed_failure"
        next_step = "operator_review_pass_evidence"
    elif rows:
        posture = "diagnosis_candidates_require_review"
        next_step = "operator_review_before_repair_planning"
    else:
        posture = "insufficient_evidence"
        next_step = "operator_review_evidence_contract"
    rows = rows[:MAX_DIAGNOSES]
    structural = {
        "evidence_digest": _hex64(evidence.get("evidence_digest")),
        "execution_status": execution_status,
        "diagnosis_posture": posture,
        "diagnosis_candidates": rows,
        "suggested_next_step": next_step,
        "root_cause_proven": False,
        "repair_authorized": False,
        "retest_authorized": False,
    }
    diagnosis_digest = _digest(structural)
    result = {
        **base,
        **structural,
        "diagnosis_status": "complete",
        "diagnosis_id": f"sandbox-test-diagnosis-{diagnosis_digest[:20]}",
        "diagnosis_digest": diagnosis_digest,
        "diagnosis_count": len(rows),
    }
    result["diagnosis_receipt_digest"] = _digest(result)
    return result


def sandbox_test_diagnosis_public_summary(diagnosis: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "schema_version", "contract_version", "diagnosis_status", "block_reason",
        "evidence_digest", "execution_status", "diagnosis_posture", "diagnosis_candidates",
        "diagnosis_count", "suggested_next_step", "root_cause_proven", "repair_authorized",
        "retest_authorized", "diagnosis_digest", "diagnosis_receipt_digest",
    }
    summary = {key: diagnosis[key] for key in allowed if key in diagnosis}
    summary.update({
        "content_free": True,
        "sandbox_only": True,
        "source_modified": False,
        "patch_created": False,
        "repair_created": False,
        "tests_rerun": False,
        "authority_granted": False,
    })
    summary["summary_digest"] = _digest(summary)
    return summary
