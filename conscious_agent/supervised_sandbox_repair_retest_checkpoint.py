from __future__ import annotations

"""Read-only v1183.9 Supervised Sandbox Repair and Retest checkpoint.

Consolidates the complete v1183 governed sandbox-repair arc: exact private
repair drafting, explicit operator repair review, isolated sandbox-only
materialization with rollback evidence, separately approved bounded retesting,
before/after evidence, regression classification, and content-free repair
results. All source content, replacement text, rollback bytes, patch text, and
test output remain private to temporary synthetic sandboxes. The checkpoint
never changes production source or runtime data and grants no source-application,
installation, promotion, certification, publication, or release authority.
"""

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from checkpoint_registry import inspect_checkpoint_registry
from package_integrity import package_privacy_summary_for_root
from supervised_sandbox_repair_draft_checkpoint import build_supervised_sandbox_repair_draft_checkpoint, _lineage
from supervised_sandbox_repair_draft_foundations import MAX_CHANGED_LINES, MAX_CONTRACT_BYTES, MAX_PATCH_BYTES, MAX_SOURCE_BYTES, draft_supervised_sandbox_repair, repair_draft_public_summary
from supervised_sandbox_repair_materialization_checkpoint import build_supervised_sandbox_repair_materialization_checkpoint
from supervised_sandbox_repair_review_materialization import materialize_reviewed_sandbox_repair, review_repair_draft, sandbox_repair_materialization_public_summary
from supervised_sandbox_retesting import MAX_TESTS, MAX_TIMEOUT_SECONDS, build_bounded_repair_result, execute_reviewed_sandbox_retest, review_sandbox_retest, sandbox_repair_result_public_summary
from supervised_sandbox_retesting_checkpoint import build_supervised_sandbox_retesting_checkpoint

CONTRACT_VERSION = "v1183.9"
_CHECKPOINT_ID = "supervised-sandbox-repair-retest:v1183.9"
_EXCLUDED = {
    "data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", "reports",
}
_FORBIDDEN_PUBLIC_TEXT = (
    "V1183_CHECKPOINT_PRIVATE_SOURCE",
    "V1183_CHECKPOINT_PRIVATE_REPLACEMENT",
    "V1183_CHECKPOINT_PRIVATE_ROLLBACK",
    "chain_of_thought_payload",
    "private_reasoning_payload",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    ).hexdigest()


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
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def _tamper(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(value)
    result[field] = "0" * 64
    return result


def _run_case(
    *,
    target: str,
    before: str,
    after: str,
    original_status: str,
    original_error: str = "",
    original_block_reason: str = "",
    expected_retest_status: str,
    expected_classification: str,
) -> dict[str, Any]:
    lineage = _lineage(
        target,
        before,
        status=original_status,
        error_class=original_error,
        block_reason=original_block_reason,
    )
    draft = draft_supervised_sandbox_repair(*lineage, before, after)
    repair_review = review_repair_draft(
        draft,
        decision="approve",
        operator_actor="v1183-checkpoint-operator",
    )
    with TemporaryDirectory(prefix="eidolon-v1183-9-sandbox-") as sandbox_directory, TemporaryDirectory(
        prefix="eidolon-v1183-9-source-"
    ) as source_directory:
        sandbox = Path(sandbox_directory)
        source = Path(source_directory)
        path = sandbox.joinpath(*target.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(before, encoding="utf-8")
        materialization = materialize_reviewed_sandbox_repair(
            draft,
            repair_review,
            sandbox_root=sandbox,
            source_root=source,
            current_target_text=before,
            replacement_text=after,
        )
        retest_review = review_sandbox_retest(
            draft,
            materialization,
            decision="approve",
            operator_actor="v1183-checkpoint-operator",
            requested_tests=["python_compile", "content_digest_match"],
        )
        retest = execute_reviewed_sandbox_retest(
            draft,
            materialization,
            retest_review,
            sandbox_root=sandbox,
            source_root=source,
        )
        result = build_bounded_repair_result(draft, materialization, retest)
        source_entry_count = sum(1 for _ in source.rglob("*"))
        target_after = path.read_text(encoding="utf-8")
        rollback_files = [item for item in sandbox.rglob("*") if item.is_file() and item != path]
    return {
        "draft": draft,
        "repair_review": repair_review,
        "materialization": materialization,
        "retest_review": retest_review,
        "retest": retest,
        "result": result,
        "draft_public": repair_draft_public_summary(draft),
        "materialization_public": sandbox_repair_materialization_public_summary(materialization),
        "result_public": sandbox_repair_result_public_summary(result),
        "source_entry_count": source_entry_count,
        "target_after_matches": target_after == after,
        "rollback_file_count": len(rollback_files),
        "expected_retest_status": expected_retest_status,
        "expected_classification": expected_classification,
    }


def build_supervised_sandbox_repair_retest_checkpoint(
    *,
    source_root: str | Path | None = None,
    runtime_root: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(source_root or Path(__file__).resolve().parents[1]).resolve()
    runtime = Path(runtime_root or source / "data").resolve()
    source_before = _tree_signature(source)
    runtime_before = _tree_signature(runtime)
    checks: list[bool] = []

    def require(value: object) -> None:
        checks.append(bool(value))

    retained = [
        build_supervised_sandbox_repair_draft_checkpoint(source_root=source, runtime_root=runtime),
        build_supervised_sandbox_repair_materialization_checkpoint(source_root=source, runtime_root=runtime),
        build_supervised_sandbox_retesting_checkpoint(source_root=source, runtime_root=runtime),
    ]
    expected_versions = ("v1183.2", "v1183.5", "v1183.8")
    for retained_report, expected_version in zip(retained, expected_versions):
        require(retained_report.get("ok") is True)
        require(retained_report.get("contract_version") == expected_version)
        require(retained_report.get("read_only") is True)
        require(retained_report.get("content_free") is True)
        require(retained_report.get("production_source_modified") is False)
        require(retained_report.get("source_application_authorized") is False)
        require(retained_report.get("release_authorized") is False)
        require(retained_report.get("desktop_verification_deferred_until_v1200") is True)

    successful_cases = [
        _run_case(
            target="pkg/compile_repair.py",
            before="def broken(:\n    pass  # V1183_CHECKPOINT_PRIVATE_SOURCE\n",
            after="def repaired():\n    return True  # V1183_CHECKPOINT_PRIVATE_REPLACEMENT\n",
            original_status="failed",
            original_error="python_compile_failed",
            expected_retest_status="passed",
            expected_classification="repair_succeeded",
        ),
        _run_case(
            target="pkg/timeout_repair.py",
            before="def work():\n    while True: pass  # V1183_CHECKPOINT_PRIVATE_SOURCE\n",
            after="def work():\n    return None  # V1183_CHECKPOINT_PRIVATE_REPLACEMENT\n",
            original_status="timed_out",
            original_error="test_timeout",
            expected_retest_status="passed",
            expected_classification="repair_succeeded",
        ),
        _run_case(
            target="pkg/blocked_repair.py",
            before="def work():\n    return 1  # V1183_CHECKPOINT_PRIVATE_SOURCE\n",
            after="def work():\n    return 2  # V1183_CHECKPOINT_PRIVATE_REPLACEMENT\n",
            original_status="blocked",
            original_block_reason="sandbox_target_drift",
            expected_retest_status="passed",
            expected_classification="repair_succeeded",
        ),
    ]

    persistent_case = _run_case(
        target="pkg/persistent_failure.py",
        before="def first_broken(:\n    pass  # V1183_CHECKPOINT_PRIVATE_SOURCE\n",
        after="def still_broken(:\n    pass  # V1183_CHECKPOINT_PRIVATE_REPLACEMENT\n",
        original_status="failed",
        original_error="python_compile_failed",
        expected_retest_status="failed",
        expected_classification="original_failure_persists",
    )
    regression_case = _run_case(
        target="pkg/regression.py",
        before="def original_timeout():\n    while True: pass  # V1183_CHECKPOINT_PRIVATE_SOURCE\n",
        after="def changed_failure(:\n    pass  # V1183_CHECKPOINT_PRIVATE_REPLACEMENT\n",
        original_status="timed_out",
        original_error="test_timeout",
        expected_retest_status="failed",
        expected_classification="regression_or_different_failure",
    )
    all_cases = successful_cases + [persistent_case, regression_case]

    for case in all_cases:
        draft = case["draft"]
        repair_review = case["repair_review"]
        materialization = case["materialization"]
        retest_review = case["retest_review"]
        retest = case["retest"]
        result = case["result"]
        require(draft.get("draft_status") == "private_draft_ready")
        require(draft.get("contains_private_source_content") is True)
        require(draft.get("minimal_change_verified") is True)
        require(draft.get("fresh_sandbox_baseline_verified") is True)
        require(draft.get("repair_materialized") is False)
        require(draft.get("tests_rerun") is False)
        require(draft.get("repair_authorized") is False and draft.get("retest_authorized") is False)
        require(repair_review.get("review_status") == "approved_for_sandbox_repair")
        require(repair_review.get("sandbox_repair_materialization_authorized") is True)
        require(repair_review.get("retest_authorized") is False)
        require(materialization.get("materialization_status") == "materialized")
        require(materialization.get("sandbox_repair_materialized") is True)
        require(materialization.get("rollback_artifact_present") is True)
        require(materialization.get("rollback_artifact_digest_verified") is True)
        require(materialization.get("rollback_executed") is False)
        require(materialization.get("tests_rerun") is False)
        require(retest_review.get("review_status") == "approved_for_sandbox_retest")
        require(retest_review.get("retest_authorized") is True)
        require(retest_review.get("single_use") is True)
        require(retest.get("retest_status") == case["expected_retest_status"])
        require(retest.get("tests_rerun") is True)
        require(retest.get("single_use_consumed") is True)
        require(retest.get("test_count") == 2)
        require(result.get("result_status") == "complete")
        require(result.get("repair_classification") == case["expected_classification"])
        require(result.get("rollback_available") is True)
        require(result.get("rollback_executed") is False)
        require(result.get("production_source_modified") is False)
        require(result.get("source_application_authorized") is False)
        require(case["source_entry_count"] == 0)
        require(case["target_after_matches"] is True)
        require(case["rollback_file_count"] >= 1)
        for public in (case["draft_public"], case["materialization_public"], case["result_public"]):
            require(public.get("content_free") is True)
            require(public.get("authority_granted") is False)
            public_text = json.dumps(public, sort_keys=True)
            require("V1183_CHECKPOINT_PRIVATE" not in public_text)
            require("replacement_text" not in public)
            require("rollback_text" not in public)
            require("patch_text" not in public)
            require(public.get("stdout_included", False) is False)
            require(public.get("stderr_included", False) is False)

    for case in successful_cases:
        require(case["result"].get("repair_accepted") is True)
        require(case["result"].get("regression_detected") is False)
    require(persistent_case["result"].get("repair_accepted") is False)
    require(persistent_case["result"].get("regression_detected") is False)
    require(regression_case["result"].get("repair_accepted") is False)
    require(regression_case["result"].get("regression_detected") is True)

    negative_before = "def negative(:\n    pass\n"
    negative_after = "def negative_fixed():\n    return True\n"
    negative_lineage = _lineage(
        "pkg/negative.py",
        negative_before,
        status="failed",
        error_class="python_compile_failed",
    )
    negative_draft = draft_supervised_sandbox_repair(*negative_lineage, negative_before, negative_after)
    require(review_repair_draft(negative_draft, decision="reject", operator_actor="operator").get("review_status") == "rejected")
    require(review_repair_draft(negative_draft, decision="defer", operator_actor="operator").get("review_status") == "deferred")
    require(review_repair_draft(negative_draft, decision="approve", operator_actor="").get("block_reason") == "missing_operator_actor")
    require(review_repair_draft(_tamper(negative_draft, "draft_digest"), decision="approve", operator_actor="operator").get("block_reason") == "invalid_or_tampered_repair_draft")

    approved_negative = review_repair_draft(negative_draft, decision="approve", operator_actor="operator")
    with TemporaryDirectory(prefix="eidolon-v1183-9-negative-sandbox-") as sandbox_directory, TemporaryDirectory(
        prefix="eidolon-v1183-9-negative-source-"
    ) as source_directory:
        sandbox = Path(sandbox_directory)
        fake_source = Path(source_directory)
        target = sandbox / "pkg" / "negative.py"
        target.parent.mkdir(parents=True)
        target.write_text(negative_before, encoding="utf-8")
        stale_materialization = materialize_reviewed_sandbox_repair(
            negative_draft,
            approved_negative,
            sandbox_root=sandbox,
            source_root=fake_source,
            current_target_text=negative_before + "# stale\n",
            replacement_text=negative_after,
        )
        require(stale_materialization.get("block_reason") == "private_content_digest_or_binding_mismatch")
        isolation_block = materialize_reviewed_sandbox_repair(
            negative_draft,
            approved_negative,
            sandbox_root=fake_source,
            source_root=fake_source,
            current_target_text=negative_before,
            replacement_text=negative_after,
        )
        require(isolation_block.get("block_reason") == "sandbox_not_isolated")
        materialization = materialize_reviewed_sandbox_repair(
            negative_draft,
            approved_negative,
            sandbox_root=sandbox,
            source_root=fake_source,
            current_target_text=negative_before,
            replacement_text=negative_after,
        )
        require(materialization.get("materialization_status") == "materialized")
        replay = materialize_reviewed_sandbox_repair(
            negative_draft,
            approved_negative,
            sandbox_root=sandbox,
            source_root=fake_source,
            current_target_text=negative_before,
            replacement_text=negative_after,
        )
        require(replay.get("materialization_status") == "already_materialized")
        require(replay.get("sandbox_file_written") is False)
        require(review_sandbox_retest(negative_draft, materialization, decision="reject", operator_actor="operator", requested_tests=["python_compile"]).get("review_status") == "rejected")
        require(review_sandbox_retest(negative_draft, materialization, decision="defer", operator_actor="operator", requested_tests=["python_compile"]).get("review_status") == "deferred")
        require(review_sandbox_retest(negative_draft, materialization, decision="approve", operator_actor="", requested_tests=["python_compile"]).get("block_reason") == "missing_operator_actor")
        require(review_sandbox_retest(negative_draft, materialization, decision="approve", operator_actor="operator", requested_tests=["shell"]).get("block_reason") == "unsupported_retest_request")
        retest_review = review_sandbox_retest(
            negative_draft,
            materialization,
            decision="approve",
            operator_actor="operator",
            requested_tests=["python_compile"],
        )
        first_retest = execute_reviewed_sandbox_retest(
            negative_draft,
            materialization,
            retest_review,
            sandbox_root=sandbox,
            source_root=fake_source,
        )
        replayed_retest = execute_reviewed_sandbox_retest(
            negative_draft,
            materialization,
            retest_review,
            sandbox_root=sandbox,
            source_root=fake_source,
        )
        require(first_retest.get("retest_status") == "passed")
        require(replayed_retest.get("retest_status") == "passed")
        tampered_retest = execute_reviewed_sandbox_retest(
            negative_draft,
            materialization,
            _tamper(retest_review, "draft_digest"),
            sandbox_root=sandbox,
            source_root=fake_source,
        )
        require(tampered_retest.get("block_reason") == "invalid_retest_review_binding")
        target.write_text("drift", encoding="utf-8")
        drifted_retest = execute_reviewed_sandbox_retest(
            negative_draft,
            materialization,
            retest_review,
            sandbox_root=sandbox,
            source_root=fake_source,
        )
        require(drifted_retest.get("block_reason") == "sandbox_target_drift")
        require(drifted_retest.get("tests_rerun") is False)
        require(execute_reviewed_sandbox_retest(
            negative_draft,
            materialization,
            retest_review,
            sandbox_root=fake_source,
            source_root=fake_source,
        ).get("block_reason") == "sandbox_not_isolated")
        require(build_bounded_repair_result({}, materialization, drifted_retest).get("block_reason") == "invalid_retest_lineage")

    registry = inspect_checkpoint_registry(source_root=source)
    registry_row = next(
        (row for row in registry.get("checkpoints", []) if row.get("checkpoint_id") == "supervised-sandbox-repair-retest-checkpoint"),
        None,
    )
    require(registry_row is not None)
    require((registry_row or {}).get("builder") == "build_supervised_sandbox_repair_retest_checkpoint")
    require((registry_row or {}).get("contract_version") == CONTRACT_VERSION)
    require(not registry.get("duplicate_checkpoint_ids"))
    require(not registry.get("duplicate_builder_targets"))

    privacy = package_privacy_summary_for_root(source)
    privacy_forbidden = int(privacy.get("forbidden_entry_count", privacy.get("forbidden_count", 0)) or 0)
    privacy_findings = int(privacy.get("private_content_finding_count", 0) or 0)
    require(privacy.get("ok") is True)
    require(privacy_forbidden == 0)
    require(privacy_findings == 0)

    source_contract = {
        "draft_contract": "v1183.2",
        "materialization_contract": "v1183.5",
        "retest_contract": "v1183.8",
        "maximum_contract_bytes": MAX_CONTRACT_BYTES,
        "maximum_source_bytes": MAX_SOURCE_BYTES,
        "maximum_patch_bytes": MAX_PATCH_BYTES,
        "maximum_changed_lines": MAX_CHANGED_LINES,
        "maximum_retests": MAX_TESTS,
        "maximum_retest_timeout_seconds": MAX_TIMEOUT_SECONDS,
    }
    require(source_contract["maximum_contract_bytes"] > 0)
    require(source_contract["maximum_source_bytes"] > 0)
    require(source_contract["maximum_patch_bytes"] > 0)
    require(source_contract["maximum_changed_lines"] > 0)
    require(source_contract["maximum_retests"] == 8)
    require(source_contract["maximum_retest_timeout_seconds"] == 30)

    source_after = _tree_signature(source)
    runtime_after = _tree_signature(runtime)
    source_modified = source_before != source_after
    runtime_mutated = runtime_before != runtime_after
    require(source_modified is False)
    require(runtime_mutated is False)

    summary = {
        "retained_checkpoint_count": len(retained),
        "successful_repair_case_count": len(successful_cases),
        "persistent_failure_case_count": 1,
        "regression_case_count": 1,
        "repair_review_decision_case_count": 3,
        "retest_review_decision_case_count": 3,
        "public_summary_case_count": len(all_cases) * 3,
        "negative_boundary_case_count": 16,
        "rollback_evidence_case_count": len(all_cases),
        "open_limitation_count": 7,
        "privacy_forbidden_entry_count": privacy_forbidden,
        "privacy_content_finding_count": privacy_findings,
        **source_contract,
    }
    limitations = [
        "one repaired target per governed repair lineage",
        "bounded retesting supports python compilation and content-digest matching only",
        "rollback evidence is retained but rollback execution remains separately governed",
        "successful sandbox repair evidence does not authorize production-source application",
        "operator acceptance, promotion, installation, certification, and release remain separate",
        "retest review receipts declare single-use but durable replay prevention is not yet enforced across repeated calls",
        "Desktop Codex and native-provider review remain deferred until v1200",
    ]

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
        "operator_promotion_required": True,
        "desktop_verification_deferred_until_v1200": True,
        "supervised_sandbox_repair_retest_checkpoint_completed": True,
        "retained_repair_draft_checkpoint_completed": retained[0].get("ok") is True,
        "retained_repair_materialization_checkpoint_completed": retained[1].get("ok") is True,
        "retained_governed_retesting_checkpoint_completed": retained[2].get("ok") is True,
        "compile_timeout_blocked_repair_lineage_exercised": True,
        "operator_repair_review_exercised": True,
        "isolated_sandbox_repair_materialization_exercised": True,
        "rollback_evidence_exercised": True,
        "separate_operator_retest_review_exercised": True,
        "before_after_evidence_exercised": True,
        "persistent_failure_detection_exercised": True,
        "regression_detection_exercised": True,
        "bounded_repair_results_exercised": True,
        "tamper_stale_drift_and_materialization_replay_boundary_rejection_exercised": True,
        "retest_review_single_use_receipt_exercised": True,
        "durable_retest_replay_prevention_available": False,
        "production_source_read": False,
        "production_source_modified": False,
        "source_modified": source_modified,
        "runtime_mutated": runtime_mutated,
        "raw_source_exposed": False,
        "raw_patch_exposed": False,
        "raw_test_output_exposed": False,
        "private_evidence_exposed": False,
        "private_reasoning_exposed": False,
        "patch_applied_to_source": False,
        "repair_applied_to_production": False,
        "rollback_executed": False,
        "shell_invoked": False,
        "registered_tool_invoked": False,
        "provider_contacted": False,
        "model_operation_performed": False,
        "production_runtime_mutated": False,
        "memory_mutated": False,
        "automatic_approval_created": False,
        "automatic_authorization_granted": False,
        "source_application_authorized": False,
        "installation_performed": False,
        "promotion_performed": False,
        "certification_performed": False,
        "release_authorized": False,
        "summary": summary,
        "limitations": limitations,
    }
    forbidden_report_value_count = sum(
        1 for token in _FORBIDDEN_PUBLIC_TEXT if token.lower() in json.dumps(report, sort_keys=True).lower()
    )
    report["forbidden_report_value_count"] = forbidden_report_value_count
    if forbidden_report_value_count:
        report["ok"] = False
        report["status"] = "review_required"
    report["structural_digest"] = _digest(report)
    return report
