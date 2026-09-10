from __future__ import annotations

"""v1183.0-v1183.2 supervised sandbox repair-draft foundations.

Consumes one exact v1182.8 repair plan together with its confirmed diagnosis
lineage, one exact v1181.8 sandbox materialization receipt, and one exact
v1182.5 failed-test evidence receipt. Caller-supplied sandbox target content may
be transformed into one bounded private in-memory replacement draft.

This module never reads or writes a repository or sandbox, applies a repair,
runs or reruns tests, invokes a shell/tool/provider/model, or grants approval,
repair, retest, source-application, promotion, installation, certification, or
release authority. Public summaries omit all source, replacement, rollback,
patch, output, and reasoning content.
"""

import difflib
import hashlib
import json
import re
from pathlib import PurePosixPath
from itertools import islice
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "1"
CONTRACT_VERSION = "v1183.2"
MAX_CONTRACT_BYTES = 131_072
MAX_SOURCE_BYTES = 262_144
MAX_PATCH_BYTES = 65_536
MAX_PATCH_LINES = 1_024
MAX_CHANGED_LINES = 128
MAX_EXISTING_DRAFT_DIGESTS = 64

_ALLOWED_SUFFIXES = frozenset({
    ".py", ".md", ".json", ".html", ".css", ".js", ".txt", ".toml", ".yaml", ".yml",
})
_BLOCKED_PARTS = frozenset({
    "data", "runtime", "private", "secrets", "secret", "credentials", "tokens",
    "sandbox", ".git", "__pycache__", ".venv", "venv", "node_modules",
    "conversations", "conversation", "memories", "memory", "providers", "provider_payloads",
})
_DRIVE = re.compile(r"^[A-Za-z]:")
_ALLOWED_FAILURE_CODES = {
    "python_compile_failure_observed": (
        "inspect_compile_failure_in_sandbox",
        "minimal_sandbox_source_correction",
        "rerun_python_compile_and_digest_check",
        "original_python_compile_failure_no_longer_observed",
    ),
    "sandbox_test_timeout_observed": (
        "inspect_timeout_evidence_and_resource_bounds",
        "bounded_timeout_or_code_path_correction",
        "rerun_original_bounded_test_set",
        "original_timeout_no_longer_observed",
    ),
    "sandbox_test_execution_blocked": (
        "repair_governance_or_binding_precondition",
        "restore_exact_test_preconditions",
        "request_new_test_review_before_retest",
        "original_execution_block_no_longer_observed",
    ),
}


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> str:
    return _digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def _text(value: Any, limit: int = 260) -> str:
    return " ".join(str(value or "").split())[:limit]


def _hex64(value: Any) -> str:
    token = _text(value, 64).lower()
    return token if len(token) == 64 and all(ch in "0123456789abcdef" for ch in token) else ""


def _safe_target(value: Any) -> str:
    raw = _text(value, 260).replace("\\", "/")
    if not raw or raw.startswith("/") or raw.startswith("//") or _DRIVE.match(raw):
        return ""
    path = PurePosixPath(raw)
    if any(part in {"", ".", ".."} or part.lower() in _BLOCKED_PARTS for part in path.parts):
        return ""
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        return ""
    return path.as_posix()


def _bounded_mapping(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    except (TypeError, ValueError, OverflowError):
        return False
    return len(encoded) <= MAX_CONTRACT_BYTES


def _receipt_valid(value: Mapping[str, Any], digest_field: str) -> bool:
    supplied = _hex64(value.get(digest_field))
    if not supplied or not _bounded_mapping(value):
        return False
    unsigned = dict(value)
    unsigned.pop(digest_field, None)
    return _digest(unsigned) == supplied


def _base() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "draft_mode": "bounded_private_in_memory_sandbox_repair",
        "sandbox_only": True,
        "production_source_read": False,
        "production_source_modified": False,
        "sandbox_read": False,
        "sandbox_modified": False,
        "source_modified": False,
        "patch_written": False,
        "patch_applied": False,
        "repair_materialized": False,
        "tests_rerun": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "automatic_approval_created": False,
        "automatic_authorization_created": False,
        "repair_authorized": False,
        "retest_authorized": False,
        "source_application_authorized": False,
        "promotion_authorized": False,
        "installation_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "operator_review_required": True,
        "later_governed_retest_required": True,
        "public_diagnostics_content_free": True,
    }


def _blocked(reason: str, *, status: str = "blocked", **details: Any) -> dict[str, Any]:
    result = {**_base(), "draft_status": status, "block_reason": reason, **details}
    result["draft_receipt_digest"] = _digest(result)
    return result


def _validate_lineage(
    repair_plan: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    diagnosis_review: Mapping[str, Any],
    materialization: Mapping[str, Any],
    failed_test_evidence: Mapping[str, Any],
) -> tuple[str, str] | tuple[None, str]:
    mappings = (repair_plan, diagnosis, diagnosis_review, materialization, failed_test_evidence)
    if not all(_bounded_mapping(value) for value in mappings):
        return None, "oversized_or_malformed_contract"

    if not (
        repair_plan.get("contract_version") == "v1182.8"
        and repair_plan.get("planning_status") == "candidate"
        and repair_plan.get("content_free") is True
        and repair_plan.get("sandbox_only") is True
        and repair_plan.get("source_modified") is False
        and repair_plan.get("patch_created") is False
        and repair_plan.get("tests_rerun") is False
        and repair_plan.get("repair_authorized") is False
        and repair_plan.get("retest_authorized") is False
        and _hex64(repair_plan.get("plan_digest"))
        and _receipt_valid(repair_plan, "plan_receipt_digest")
    ):
        return None, "invalid_or_tampered_repair_plan"

    if not (
        diagnosis.get("contract_version") == "v1182.5"
        and diagnosis.get("diagnosis_status") == "complete"
        and diagnosis.get("content_free") is True
        and diagnosis.get("root_cause_proven") is False
        and diagnosis.get("repair_authorized") is False
        and diagnosis.get("retest_authorized") is False
        and _hex64(diagnosis.get("diagnosis_digest"))
        and _receipt_valid(diagnosis, "diagnosis_receipt_digest")
    ):
        return None, "invalid_or_tampered_diagnosis"

    if not (
        diagnosis_review.get("contract_version") == "v1182.8"
        and diagnosis_review.get("review_status") == "confirmed_for_repair_planning"
        and diagnosis_review.get("decision") == "confirm"
        and diagnosis_review.get("content_free") is True
        and diagnosis_review.get("repair_authorized") is False
        and diagnosis_review.get("retest_authorized") is False
        and _hex64(diagnosis_review.get("review_digest"))
        and _receipt_valid(diagnosis_review, "review_receipt_digest")
    ):
        return None, "invalid_or_tampered_diagnosis_review"

    diagnosis_digest = _hex64(diagnosis.get("diagnosis_digest"))
    review_digest = _hex64(diagnosis_review.get("review_digest"))
    if not (
        _hex64(repair_plan.get("diagnosis_digest")) == diagnosis_digest
        and _hex64(repair_plan.get("review_digest")) == review_digest
        and _hex64(diagnosis_review.get("diagnosis_digest")) == diagnosis_digest
    ):
        return None, "mismatched_diagnosis_or_plan_digest"

    if not (
        failed_test_evidence.get("contract_version") == "v1182.5"
        and failed_test_evidence.get("evidence_status") == "verified"
        and failed_test_evidence.get("content_free") is True
        and failed_test_evidence.get("sandbox_only") is True
        and failed_test_evidence.get("source_modified") is False
        and failed_test_evidence.get("tests_rerun") is False
        and failed_test_evidence.get("execution_status") in {"failed", "timed_out", "blocked"}
        and _hex64(failed_test_evidence.get("evidence_digest"))
        and _receipt_valid(failed_test_evidence, "evidence_receipt_digest")
        and _hex64(diagnosis.get("evidence_digest")) == _hex64(failed_test_evidence.get("evidence_digest"))
    ):
        return None, "invalid_or_mismatched_failed_test_evidence"

    if not (
        materialization.get("contract_version") == "v1181.8"
        and materialization.get("materialization_status") in {"materialized", "already_materialized"}
        and materialization.get("content_free") is True
        and materialization.get("sandbox_only") is True
        and materialization.get("sandbox_materialized") is True
        and materialization.get("source_modified") is False
        and materialization.get("patch_applied_to_source") is False
        and materialization.get("tests_executed") is False
        and _hex64(materialization.get("sandbox_target_digest"))
        and _hex64(materialization.get("sandbox_marker_digest"))
        and _receipt_valid(materialization, "materialization_receipt_digest")
    ):
        return None, "invalid_or_tampered_materialization_receipt"

    target = _safe_target(materialization.get("target_path"))
    if not target:
        return None, "unsafe_sandbox_target"
    if _safe_target(failed_test_evidence.get("target_path")) != target:
        return None, "failed_test_target_mismatch"
    if _hex64(failed_test_evidence.get("materialization_receipt_digest")) != _hex64(materialization.get("materialization_receipt_digest")):
        return None, "materialization_evidence_digest_mismatch"
    target_digest = _hex64(materialization.get("sandbox_target_digest"))
    if _hex64(failed_test_evidence.get("sandbox_target_digest")) != target_digest:
        return None, "sandbox_target_digest_mismatch"

    diagnosis_rows = list(diagnosis.get("diagnosis_candidates") or [])
    repair_steps = list(repair_plan.get("repair_steps") or [])
    if len(diagnosis_rows) != 1 or len(repair_steps) != 1 or int(repair_plan.get("repair_step_count") or 0) != 1:
        return None, "repair_plan_must_bind_one_failure"
    code = _text(diagnosis_rows[0].get("diagnosis_code"), 64)
    if code not in _ALLOWED_FAILURE_CODES:
        return None, "unsupported_repair_code"
    inspect_step, repair_step, retest_step, _ = _ALLOWED_FAILURE_CODES[code]
    step = repair_steps[0]
    required_acceptance = {
        "original_failure_no_longer_observed",
        "content_digest_matches_reviewed_sandbox_target",
        "no_production_source_change",
    }
    acceptance = {_text(item, 80) for item in list(repair_plan.get("acceptance_criteria") or [])[:12]}
    retest_intents = {_text(item, 80) for item in list(repair_plan.get("retest_intents") or [])[:8]}
    if not (
        _text(step.get("diagnosis_code"), 64) == code
        and _text(step.get("inspection_step"), 80) == inspect_step
        and _text(step.get("repair_step"), 80) == repair_step
        and _text(step.get("retest_step"), 80) == retest_step
        and step.get("minimal_change_required") is True
        and step.get("sandbox_only_required") is True
        and step.get("rollback_required") is True
        and required_acceptance.issubset(acceptance)
        and retest_step in retest_intents
    ):
        return None, "malformed_or_unsupported_repair_contract"

    execution_status = _text(failed_test_evidence.get("execution_status"), 24)
    result_rows = list(failed_test_evidence.get("test_results") or [])[:8]
    observed = {(_text(row.get("test"), 40), _text(row.get("status"), 24), _text(row.get("error_class"), 48)) for row in result_rows}
    failure_matches = (
        code == "python_compile_failure_observed"
        and execution_status == "failed"
        and ("python_compile", "failed", "python_compile_failed") in observed
    ) or (
        code == "sandbox_test_timeout_observed"
        and execution_status == "timed_out"
        and any(status == "timed_out" and error_class == "test_timeout" for _, status, error_class in observed)
    ) or (
        code == "sandbox_test_execution_blocked"
        and execution_status == "blocked"
        and bool(_text(failed_test_evidence.get("block_reason"), 80))
    )
    if not failure_matches:
        return None, "diagnosis_does_not_match_failed_test_evidence"
    return target, code


def draft_supervised_sandbox_repair(
    repair_plan: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    diagnosis_review: Mapping[str, Any],
    materialization: Mapping[str, Any],
    failed_test_evidence: Mapping[str, Any],
    current_target_text: str,
    replacement_text: str,
    *,
    existing_draft_digests: Sequence[str] | Iterable[str] = (),
) -> dict[str, Any]:
    """Create one exact, bounded, private replacement draft in memory only."""
    target, code_or_reason = _validate_lineage(
        repair_plan, diagnosis, diagnosis_review, materialization, failed_test_evidence,
    )
    if target is None:
        return _blocked(code_or_reason)
    failure_code = code_or_reason

    if not isinstance(current_target_text, str) or not isinstance(replacement_text, str):
        return _blocked("invalid_private_source_content")
    if "\x00" in current_target_text or "\x00" in replacement_text:
        return _blocked("invalid_private_source_content")
    before_bytes = current_target_text.encode("utf-8")
    after_bytes = replacement_text.encode("utf-8")
    if len(before_bytes) > MAX_SOURCE_BYTES or len(after_bytes) > MAX_SOURCE_BYTES:
        return _blocked("oversized_private_source_content", target_path=target)

    expected_target_digest = _hex64(materialization.get("sandbox_target_digest"))
    current_target_digest = _digest_bytes(before_bytes)
    if current_target_digest != expected_target_digest:
        return _blocked(
            "stale_sandbox_state",
            status="stale_sandbox",
            target_path=target,
            expected_target_digest=expected_target_digest,
            observed_target_digest=current_target_digest,
        )
    if current_target_text == replacement_text:
        return _blocked("no_op_repair_draft", target_path=target)

    before_lines = current_target_text.splitlines(keepends=True)
    after_lines = replacement_text.splitlines(keepends=True)
    patch_lines = list(difflib.unified_diff(
        before_lines, after_lines, fromfile=f"a/{target}", tofile=f"b/{target}", lineterm="",
    ))
    patch_text = "\n".join(patch_lines)
    patch_bytes = patch_text.encode("utf-8")
    added_lines = sum(1 for line in patch_lines if line.startswith("+") and not line.startswith("+++"))
    removed_lines = sum(1 for line in patch_lines if line.startswith("-") and not line.startswith("---"))
    changed_lines = added_lines + removed_lines
    if (
        not patch_lines
        or len(patch_lines) > MAX_PATCH_LINES
        or len(patch_bytes) > MAX_PATCH_BYTES
        or changed_lines > MAX_CHANGED_LINES
    ):
        return _blocked(
            "repair_draft_exceeds_minimal_change_bounds",
            target_path=target,
            patch_line_count=len(patch_lines),
            changed_line_count=changed_lines,
        )

    replacement_digest = _digest_bytes(after_bytes)
    patch_digest = _digest_bytes(patch_bytes)
    rollback_digest = current_target_digest
    _, _, retest_step, failure_acceptance = _ALLOWED_FAILURE_CODES[failure_code]
    structural = {
        "plan_id": _text(repair_plan.get("plan_id"), 100),
        "plan_digest": _hex64(repair_plan.get("plan_digest")),
        "plan_receipt_digest": _hex64(repair_plan.get("plan_receipt_digest")),
        "diagnosis_digest": _hex64(diagnosis.get("diagnosis_digest")),
        "diagnosis_review_digest": _hex64(diagnosis_review.get("review_digest")),
        "evidence_digest": _hex64(failed_test_evidence.get("evidence_digest")),
        "evidence_receipt_digest": _hex64(failed_test_evidence.get("evidence_receipt_digest")),
        "materialization_receipt_digest": _hex64(materialization.get("materialization_receipt_digest")),
        "sandbox_marker_digest": _hex64(materialization.get("sandbox_marker_digest")),
        "target_path": target,
        "baseline_target_digest": current_target_digest,
        "replacement_digest": replacement_digest,
        "rollback_digest": rollback_digest,
        "patch_digest": patch_digest,
        "failure_code": failure_code,
        "patch_line_count": len(patch_lines),
        "added_line_count": added_lines,
        "removed_line_count": removed_lines,
        "changed_line_count": changed_lines,
        "minimal_change_verified": True,
        "single_target": True,
        "exact_replacement_content": True,
        "structural_plan_distinct_from_replacement": True,
        "digest_binding_verified": True,
        "fresh_sandbox_baseline_verified": True,
        "rollback_required": True,
        "rollback_content_digest_verified": True,
        "original_failure_acceptance_check": failure_acceptance,
        "plan_acceptance_criteria": list(repair_plan.get("acceptance_criteria") or [])[:12],
        "later_retest_intent": retest_step,
        "operator_review_required": True,
        "repair_materialization_authorized": False,
        "retest_authorized": False,
        "source_application_authorized": False,
    }
    draft_digest = _digest(structural)

    try:
        existing = list(islice(iter(existing_draft_digests), MAX_EXISTING_DRAFT_DIGESTS + 1))
    except TypeError:
        return _blocked("malformed_existing_draft_ledger", target_path=target)
    if len(existing) > MAX_EXISTING_DRAFT_DIGESTS or any(not _hex64(item) for item in existing):
        return _blocked("malformed_existing_draft_ledger", target_path=target)
    if draft_digest in {_hex64(item) for item in existing}:
        return _blocked("duplicate_repair_draft", target_path=target, duplicate_draft_digest=draft_digest)

    result = {
        **_base(),
        **structural,
        "draft_status": "private_draft_ready",
        "draft_id": f"sandbox-repair-draft-{draft_digest[:20]}",
        "draft_digest": draft_digest,
        "private_repair_draft_created": True,
        "contains_private_source_content": True,
        "private_artifact": True,
        "public_diagnostics_safe": False,
        "replacement_text": replacement_text,
        "rollback_text": current_target_text,
        "patch_text": patch_text,
    }
    receipt_basis = {key: value for key, value in result.items() if key not in {"replacement_text", "rollback_text", "patch_text"}}
    result["draft_receipt_digest"] = _digest(receipt_basis)
    return result


def repair_draft_public_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    """Publish a bounded content-free summary and omit every private content field."""
    allowed = {
        "schema_version", "contract_version", "draft_status", "block_reason", "draft_id", "draft_digest",
        "draft_receipt_digest", "plan_id", "plan_digest", "plan_receipt_digest", "diagnosis_digest",
        "diagnosis_review_digest", "evidence_digest", "evidence_receipt_digest",
        "materialization_receipt_digest", "sandbox_marker_digest", "target_path", "baseline_target_digest",
        "replacement_digest", "rollback_digest", "patch_digest", "failure_code", "patch_line_count",
        "added_line_count", "removed_line_count", "changed_line_count", "minimal_change_verified",
        "single_target", "exact_replacement_content", "structural_plan_distinct_from_replacement",
        "digest_binding_verified", "fresh_sandbox_baseline_verified", "rollback_required",
        "rollback_content_digest_verified", "original_failure_acceptance_check", "plan_acceptance_criteria",
        "later_retest_intent", "operator_review_required", "repair_materialization_authorized",
        "retest_authorized", "source_application_authorized", "expected_target_digest",
        "observed_target_digest", "duplicate_draft_digest",
    }
    summary = {key: result[key] for key in allowed if key in result}
    summary.update({
        "content_free": True,
        "private_source_content_included": False,
        "replacement_text_included": False,
        "rollback_text_included": False,
        "patch_text_included": False,
        "raw_test_output_included": False,
        "private_reasoning_included": False,
        "sandbox_modified": False,
        "production_source_modified": False,
        "source_modified": False,
        "repair_materialized": False,
        "tests_rerun": False,
        "provider_contacted": False,
        "model_contacted": False,
        "authority_granted": False,
        "operator_review_required": True,
        "later_governed_retest_required": True,
    })
    summary["summary_digest"] = _digest(summary)
    return summary


def repair_draft_review_prompt(summary: Mapping[str, Any]) -> str:
    return (
        "Supervised sandbox repair draft:\n"
        f"- Status: {_text(summary.get('draft_status'), 48) or 'blocked'}.\n"
        f"- Target: {_text(summary.get('target_path'), 180) or 'none'}.\n"
        "- The exact private replacement remains separate from the structural plan.\n"
        "- Operator review, later sandbox materialization, and separately governed retesting are still required."
    )
