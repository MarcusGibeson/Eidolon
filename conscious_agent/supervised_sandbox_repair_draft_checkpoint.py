from __future__ import annotations

"""Read-only v1183.2 Supervised Sandbox Repair Draft Foundations checkpoint."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from sandbox_test_evidence_diagnosis import build_sandbox_test_evidence, diagnose_sandbox_test_evidence
from supervised_repair_planning import build_supervised_repair_plan, review_repair_diagnosis
from supervised_sandbox_repair_draft_foundations import CONTRACT_VERSION as DRAFT_CONTRACT_VERSION, MAX_CHANGED_LINES, MAX_CONTRACT_BYTES, MAX_PATCH_BYTES, MAX_SOURCE_BYTES, draft_supervised_sandbox_repair, repair_draft_public_summary

CONTRACT_VERSION = "v1183.2"
_CHECKPOINT_ID = "supervised-sandbox-repair-draft:v1183.2"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_PUBLIC_TEXT = (
    "V1183_PRIVATE_SOURCE_SENTINEL",
    "V1183_PRIVATE_REPLACEMENT_SENTINEL",
    "V1183_PRIVATE_ROLLBACK_SENTINEL",
    "stdout", "stderr", "raw_source_payload", "raw_patch_payload", "chain_of_thought_payload", "private_reasoning_payload",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _tree_signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return digest.hexdigest()
    paths: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in _EXCLUDED]
        for name in files:
            path = Path(base) / name
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                paths.append(path)
    for path in sorted(paths):
        try:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
        except OSError:
            continue
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def _materialization(target: str, source_text: str) -> dict[str, Any]:
    target_digest = _bytes_digest(source_text.encode())
    result = {
        "schema_version": "1",
        "contract_version": "v1181.8",
        "source_read": False,
        "source_modified": False,
        "patch_applied_to_source": False,
        "tests_executed": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "approval_created": False,
        "source_application_authorized": False,
        "test_execution_authorized": False,
        "promotion_authorized": False,
        "release_authorized": False,
        "sandbox_only": True,
        "operator_review_required": True,
        "materialization_status": "materialized",
        "target_path": target,
        "draft_digest": _digest({"draft": target}),
        "review_digest": _digest({"review": target}),
        "patch_digest": _digest({"patch": target}),
        "before_digest": _digest({"before": target}),
        "after_digest": target_digest,
        "sandbox_target_digest": target_digest,
        "sandbox_marker_digest": _digest({"target": target, "target_digest": target_digest}),
        "sandbox_file_written": True,
        "sandbox_materialized": True,
        "content_free": True,
    }
    result["materialization_receipt_digest"] = _digest(result)
    return result


def _test_receipt(materialization: dict[str, Any], *, status: str, error_class: str = "", block_reason: str = "") -> dict[str, Any]:
    target = materialization["target_path"]
    executed = status != "blocked"
    rows = [] if not executed else [{"test": "python_compile", "status": status, "error_class": error_class}]
    result = {
        "schema_version": "1",
        "contract_version": "v1182.2",
        "sandbox_only": True,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": False,
        "patch_applied_to_source": False,
        "shell_invoked": False,
        "tool_invoked": False,
        "provider_contacted": False,
        "model_contacted": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "operator_review_required": True,
        "execution_status": status,
        "tests_executed": executed,
        "test_execution_authorized": executed,
        "target_path": target,
        "attempt_digest": _digest({"attempt": target, "status": status}),
        "review_digest": _digest({"test-review": target}),
        "materialization_receipt_digest": materialization["materialization_receipt_digest"],
        "sandbox_target_digest": materialization["sandbox_target_digest"],
        "test_count": len(rows),
        "test_results": rows,
        "elapsed_ms": 1,
        "block_reason": block_reason,
        "content_free": True,
        "single_use_consumed": executed,
    }
    result["test_receipt_digest"] = _digest(result)
    return result


def _lineage(target: str, before: str, *, status: str, error_class: str = "", block_reason: str = "") -> tuple[dict[str, Any], ...]:
    materialization = _materialization(target, before)
    evidence = build_sandbox_test_evidence(_test_receipt(materialization, status=status, error_class=error_class, block_reason=block_reason))
    diagnosis = diagnose_sandbox_test_evidence(evidence)
    review = review_repair_diagnosis(diagnosis, "confirm", "checkpoint-operator")
    plan = build_supervised_repair_plan(diagnosis, review)
    return plan, diagnosis, review, materialization, evidence


def build_supervised_sandbox_repair_draft_checkpoint(
    *, source_root: str | Path | None = None, runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    cases = [
        ("compile", "pkg/compile_case.py", "def broken(:\n    pass  # V1183_PRIVATE_SOURCE_SENTINEL\n", "def repaired():\n    return True  # V1183_PRIVATE_REPLACEMENT_SENTINEL\n", "failed", "python_compile_failed", ""),
        ("timeout", "pkg/timeout_case.py", "def work():\n    while True: pass  # V1183_PRIVATE_SOURCE_SENTINEL\n", "def work():\n    return None  # V1183_PRIVATE_REPLACEMENT_SENTINEL\n", "timed_out", "test_timeout", ""),
        ("blocked", "pkg/blocked_case.py", "def work():\n    return 1  # V1183_PRIVATE_SOURCE_SENTINEL\n", "def work():\n    return 2  # V1183_PRIVATE_REPLACEMENT_SENTINEL\n", "blocked", "", "sandbox_target_drift"),
    ]
    drafts: list[dict[str, Any]] = []
    public: list[dict[str, Any]] = []
    for name, target, before, after, status, error_class, block_reason in cases:
        lineage = _lineage(target, before, status=status, error_class=error_class, block_reason=block_reason)
        plan, diagnosis, review, materialization, evidence = lineage
        require(plan.get("planning_status") == "candidate")
        require(review.get("review_status") == "confirmed_for_repair_planning")
        draft = draft_supervised_sandbox_repair(*lineage, before, after)
        drafts.append(draft)
        require(draft.get("draft_status") == "private_draft_ready")
        require(draft.get("failure_code") in {
            "python_compile_failure_observed", "sandbox_test_timeout_observed", "sandbox_test_execution_blocked",
        })
        require(draft.get("target_path") == target)
        require(draft.get("minimal_change_verified") is True)
        require(draft.get("fresh_sandbox_baseline_verified") is True)
        require(draft.get("rollback_required") is True)
        require(draft.get("structural_plan_distinct_from_replacement") is True)
        require(draft.get("repair_materialized") is False)
        require(draft.get("tests_rerun") is False)
        require(draft.get("provider_contacted") is False and draft.get("model_contacted") is False)
        require(draft.get("repair_authorized") is False and draft.get("retest_authorized") is False)
        summary = repair_draft_public_summary(draft)
        public.append(summary)
        require(summary.get("content_free") is True)
        require(summary.get("private_source_content_included") is False)
        require("replacement_text" not in summary and "rollback_text" not in summary and "patch_text" not in summary)
        require(summary.get("authority_granted") is False)
        require(summary.get("sandbox_modified") is False and summary.get("production_source_modified") is False)
        require(name in {"compile", "timeout", "blocked"})

    first_lineage = _lineage("pkg/negative.py", "def x():\n    return 1\n", status="failed", error_class="python_compile_failed")
    plan, diagnosis, review, materialization, evidence = first_lineage
    before = "def x():\n    return 1\n"
    after = "def x():\n    return 2\n"
    valid = draft_supervised_sandbox_repair(*first_lineage, before, after)
    require(draft_supervised_sandbox_repair(*first_lineage, before + "# drift\n", after).get("block_reason") == "stale_sandbox_state")
    require(draft_supervised_sandbox_repair(*first_lineage, before, before).get("block_reason") == "no_op_repair_draft")
    require(draft_supervised_sandbox_repair(*first_lineage, before, after, existing_draft_digests=[valid["draft_digest"]]).get("block_reason") == "duplicate_repair_draft")
    require(draft_supervised_sandbox_repair({**plan, "plan_digest": "0" * 64}, diagnosis, review, materialization, evidence, before, after).get("block_reason") == "invalid_or_tampered_repair_plan")
    require(draft_supervised_sandbox_repair(plan, {**diagnosis, "diagnosis_digest": "0" * 64}, review, materialization, evidence, before, after).get("block_reason") == "invalid_or_tampered_diagnosis")
    require(draft_supervised_sandbox_repair(plan, diagnosis, {**review, "review_digest": "0" * 64}, materialization, evidence, before, after).get("block_reason") == "invalid_or_tampered_diagnosis_review")
    require(draft_supervised_sandbox_repair(plan, diagnosis, review, {**materialization, "target_path": "../private.py"}, evidence, before, after).get("block_reason") == "invalid_or_tampered_materialization_receipt")
    require(draft_supervised_sandbox_repair(plan, diagnosis, review, materialization, {**evidence, "evidence_digest": "0" * 64}, before, after).get("block_reason") == "invalid_or_mismatched_failed_test_evidence")
    require(draft_supervised_sandbox_repair(*first_lineage, before + "\x00", after).get("block_reason") == "invalid_private_source_content")
    require(draft_supervised_sandbox_repair(*first_lineage, before, "x" * (MAX_SOURCE_BYTES + 1)).get("block_reason") == "oversized_private_source_content")

    public_text = json.dumps(public, sort_keys=True, separators=(",", ":")).lower()
    require(not any(token.lower() in public_text for token in _FORBIDDEN_PUBLIC_TEXT))
    require(all(len(str(row.get("summary_digest") or "")) == 64 for row in public))

    registry = inspect_checkpoint_registry(source_root=source)
    row = next((item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "supervised-sandbox-repair-draft-checkpoint"), None)
    require(row is not None)
    require((row or {}).get("builder") == "build_supervised_sandbox_repair_draft_checkpoint")
    require((row or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry.get("duplicate_checkpoint_ids") and not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    require(privacy.get("ok"))
    require(privacy.get("source_only"))
    require(int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0) == 0)
    require(int(privacy.get("private_content_finding_count", 0) or 0) == 0)

    source_modified = source_before != _tree_signature(source)
    runtime_mutated = runtime_before != _tree_signature(runtime)
    require(source_modified is False)
    require(runtime_mutated is False)

    evidence_report = {
        "case_draft_digests": [draft.get("draft_digest") for draft in drafts],
        "case_summary_digests": [row.get("summary_digest") for row in public],
        "maximum_contract_bytes": MAX_CONTRACT_BYTES,
        "maximum_source_bytes": MAX_SOURCE_BYTES,
        "maximum_patch_bytes": MAX_PATCH_BYTES,
        "maximum_changed_lines": MAX_CHANGED_LINES,
        "privacy_forbidden_entry_count": int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0),
        "privacy_content_finding_count": int(privacy.get("private_content_finding_count", 0) or 0),
    }
    forbidden_count = sum(1 for token in _FORBIDDEN_PUBLIC_TEXT if token.lower() in json.dumps(evidence_report, sort_keys=True).lower())
    require(forbidden_count == 0)

    report: dict[str, Any] = {
        "schema_version": "1",
        "contract_version": CONTRACT_VERSION,
        "checkpoint_id": _CHECKPOINT_ID,
        "status": "ready" if all(checks) else "review_required",
        "ok": all(checks),
        "passed": sum(checks),
        "total": len(checks),
        "read_only": True,
        "post_available": False,
        "content_free": True,
        "authority_preserved": True,
        "operator_review_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "supervised_sandbox_repair_draft_foundations_completed": True,
        "exact_repair_plan_lineage_exercised": True,
        "fresh_sandbox_baseline_binding_exercised": True,
        "compile_timeout_blocked_drafts_exercised": True,
        "private_replacement_and_public_summary_separation_exercised": True,
        "stale_drift_tamper_duplicate_boundary_rejection_exercised": True,
        "production_source_modified": False,
        "sandbox_modified": False,
        "repair_materialized": False,
        "tests_rerun": False,
        "shell_invoked": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "repair_authorized": False,
        "retest_authorized": False,
        "source_application_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "forbidden_report_value_count": forbidden_count,
        "summary": {
            "valid_repair_draft_case_count": len(drafts),
            "compile_failure_case_count": 1,
            "timeout_case_count": 1,
            "blocked_execution_case_count": 1,
            "negative_boundary_case_count": 10,
            "public_summary_case_count": len(public),
            "maximum_contract_bytes": MAX_CONTRACT_BYTES,
            "maximum_source_bytes": MAX_SOURCE_BYTES,
            "maximum_patch_bytes": MAX_PATCH_BYTES,
            "maximum_changed_lines": MAX_CHANGED_LINES,
            "privacy_forbidden_entry_count": evidence_report["privacy_forbidden_entry_count"],
            "privacy_content_finding_count": evidence_report["privacy_content_finding_count"],
            "open_limitation_count": 5,
        },
        "evidence": evidence_report,
    }
    report["structural_digest"] = _digest({key: value for key, value in report.items() if key != "structural_digest"})
    return report
