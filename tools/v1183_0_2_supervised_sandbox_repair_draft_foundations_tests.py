from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.sandbox_test_evidence_diagnosis import build_sandbox_test_evidence, diagnose_sandbox_test_evidence
from conscious_agent.supervised_repair_planning import build_supervised_repair_plan, review_repair_diagnosis
from conscious_agent.supervised_sandbox_repair_draft_checkpoint import build_supervised_sandbox_repair_draft_checkpoint
from conscious_agent.supervised_sandbox_repair_draft_foundations import (
    CONTRACT_VERSION,
    MAX_CHANGED_LINES,
    MAX_CONTRACT_BYTES,
    MAX_EXISTING_DRAFT_DIGESTS,
    MAX_PATCH_BYTES,
    MAX_SOURCE_BYTES,
    draft_supervised_sandbox_repair,
    repair_draft_public_summary,
    repair_draft_review_prompt,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    if not value:
        raise AssertionError(f"check {len(checks)} failed")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def materialization(target: str, source_text: str) -> dict[str, Any]:
    target_digest = digest_text(source_text)
    result = {
        "schema_version": "1", "contract_version": "v1181.8",
        "source_read": False, "source_modified": False, "patch_applied_to_source": False,
        "tests_executed": False, "shell_invoked": False, "tool_invoked": False,
        "provider_contacted": False, "model_contacted": False, "approval_created": False,
        "source_application_authorized": False, "test_execution_authorized": False,
        "promotion_authorized": False, "release_authorized": False,
        "sandbox_only": True, "operator_review_required": True,
        "materialization_status": "materialized", "target_path": target,
        "draft_digest": digest({"draft": target}), "review_digest": digest({"review": target}),
        "patch_digest": digest({"patch": target}), "before_digest": digest({"before": target}),
        "after_digest": target_digest, "sandbox_target_digest": target_digest,
        "sandbox_marker_digest": digest({"target": target, "target_digest": target_digest}),
        "sandbox_file_written": True, "sandbox_materialized": True, "content_free": True,
    }
    result["materialization_receipt_digest"] = digest(result)
    return result


def test_receipt(mat: dict[str, Any], *, status: str, error_class: str = "", block_reason: str = "") -> dict[str, Any]:
    executed = status != "blocked"
    rows = [] if not executed else [{"test": "python_compile", "status": status, "error_class": error_class}]
    result = {
        "schema_version": "1", "contract_version": "v1182.2", "sandbox_only": True,
        "production_source_read": False, "production_source_modified": False, "source_modified": False,
        "patch_applied_to_source": False, "shell_invoked": False, "tool_invoked": False,
        "provider_contacted": False, "model_contacted": False, "installation_performed": False,
        "promotion_performed": False, "certification_performed": False, "release_authorized": False,
        "operator_review_required": True, "execution_status": status, "tests_executed": executed,
        "test_execution_authorized": executed, "target_path": mat["target_path"],
        "attempt_digest": digest({"attempt": mat["target_path"], "status": status}),
        "review_digest": digest({"test-review": mat["target_path"]}),
        "materialization_receipt_digest": mat["materialization_receipt_digest"],
        "sandbox_target_digest": mat["sandbox_target_digest"], "test_count": len(rows),
        "test_results": rows, "elapsed_ms": 1, "block_reason": block_reason,
        "content_free": True, "single_use_consumed": executed,
    }
    result["test_receipt_digest"] = digest(result)
    return result


def lineage(target: str, before: str, *, status: str, error_class: str = "", block_reason: str = "") -> tuple[dict[str, Any], ...]:
    mat = materialization(target, before)
    evidence = build_sandbox_test_evidence(test_receipt(mat, status=status, error_class=error_class, block_reason=block_reason))
    diagnosis = diagnose_sandbox_test_evidence(evidence)
    review = review_repair_diagnosis(diagnosis, "confirm", "bundle-a-operator")
    plan = build_supervised_repair_plan(diagnosis, review)
    return plan, diagnosis, review, mat, evidence


def re_receipt(value: dict[str, Any], field: str) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop(field, None)
    result[field] = digest(result)
    return result


def unsupported_lineage(before: str) -> tuple[dict[str, Any], ...]:
    plan, diagnosis, review, mat, evidence = lineage(
        "pkg/unsupported.py", before, status="failed", error_class="python_compile_failed",
    )
    bad_diag = copy.deepcopy(diagnosis)
    bad_diag["diagnosis_candidates"][0]["diagnosis_code"] = "invented_repair_code"
    bad_diag["diagnosis_digest"] = digest({"unsupported": "diagnosis", "evidence": bad_diag["evidence_digest"]})
    bad_diag = re_receipt(bad_diag, "diagnosis_receipt_digest")
    bad_review = review_repair_diagnosis(bad_diag, "confirm", "bundle-a-operator")
    bad_plan = copy.deepcopy(plan)
    bad_plan["diagnosis_digest"] = bad_diag["diagnosis_digest"]
    bad_plan["review_digest"] = bad_review["review_digest"]
    bad_plan["repair_steps"][0]["diagnosis_code"] = "invented_repair_code"
    bad_plan["plan_digest"] = digest({"unsupported": "plan"})
    bad_plan = re_receipt(bad_plan, "plan_receipt_digest")
    return bad_plan, bad_diag, bad_review, mat, evidence


def tree_signature(root: Path) -> str:
    h = hashlib.sha256()
    excluded = {"data", "sandbox", ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "reports", "dist", "build"}
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in excluded]
        for name in sorted(files):
            path = Path(base) / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            rel = path.relative_to(root).as_posix()
            h.update(rel.encode()); h.update(b"\0"); h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


source_before = tree_signature(ROOT)

# Valid compile-failure repair draft.
compile_before = "def broken(:\n    pass  # PRIVATE_COMPILE_SOURCE_1183\n"
compile_after = "def repaired():\n    return True  # PRIVATE_COMPILE_REPLACEMENT_1183\n"
compile_lineage = lineage("pkg/compile_case.py", compile_before, status="failed", error_class="python_compile_failed")
compile_draft = draft_supervised_sandbox_repair(*compile_lineage, compile_before, compile_after)
require(compile_draft["draft_status"] == "private_draft_ready")
require(compile_draft["failure_code"] == "python_compile_failure_observed")
require(compile_draft["original_failure_acceptance_check"] == "original_python_compile_failure_no_longer_observed")
require(compile_draft["later_retest_intent"] == "rerun_python_compile_and_digest_check")
require(compile_draft["baseline_target_digest"] == digest_text(compile_before))
require(compile_draft["replacement_digest"] == digest_text(compile_after))
require(compile_draft["rollback_digest"] == digest_text(compile_before))
require(compile_draft["patch_text"].startswith("--- a/pkg/compile_case.py"))
require("+++ b/pkg/compile_case.py" in compile_draft["patch_text"])
require(compile_draft["replacement_text"] == compile_after and compile_draft["rollback_text"] == compile_before)
require(compile_draft["minimal_change_verified"] and compile_draft["single_target"])
require(compile_draft["structural_plan_distinct_from_replacement"])
require(compile_draft["digest_binding_verified"] and compile_draft["fresh_sandbox_baseline_verified"])
require(compile_draft["rollback_required"] and compile_draft["rollback_content_digest_verified"])
require(compile_draft["operator_review_required"] and compile_draft["later_governed_retest_required"])
require(not compile_draft["repair_materialization_authorized"] and not compile_draft["retest_authorized"])
require(not compile_draft["source_application_authorized"] and not compile_draft["release_authorized"])
require(not compile_draft["production_source_modified"] and not compile_draft["sandbox_modified"])
require(not compile_draft["patch_written"] and not compile_draft["patch_applied"] and not compile_draft["repair_materialized"])
require(not compile_draft["tests_rerun"] and not compile_draft["shell_invoked"] and not compile_draft["tool_invoked"])
require(not compile_draft["provider_contacted"] and not compile_draft["model_contacted"])
require(compile_draft["private_artifact"] and compile_draft["contains_private_source_content"])
require(not compile_draft["public_diagnostics_safe"])
require(len(compile_draft["draft_digest"]) == 64 and len(compile_draft["draft_receipt_digest"]) == 64)
require(compile_draft["changed_line_count"] <= MAX_CHANGED_LINES)
require(len(compile_draft["patch_text"].encode()) <= MAX_PATCH_BYTES)

# Valid timeout repair draft.
timeout_before = "def work():\n    while True: pass  # PRIVATE_TIMEOUT_SOURCE_1183\n"
timeout_after = "def work():\n    return None  # PRIVATE_TIMEOUT_REPLACEMENT_1183\n"
timeout_lineage = lineage("pkg/timeout_case.py", timeout_before, status="timed_out", error_class="test_timeout")
timeout_draft = draft_supervised_sandbox_repair(*timeout_lineage, timeout_before, timeout_after)
require(timeout_draft["draft_status"] == "private_draft_ready")
require(timeout_draft["failure_code"] == "sandbox_test_timeout_observed")
require(timeout_draft["original_failure_acceptance_check"] == "original_timeout_no_longer_observed")
require(timeout_draft["later_retest_intent"] == "rerun_original_bounded_test_set")

# Valid blocked-execution repair draft with exact target lineage retained.
blocked_before = "def blocked():\n    return 1  # PRIVATE_BLOCKED_SOURCE_1183\n"
blocked_after = "def blocked():\n    return 2  # PRIVATE_BLOCKED_REPLACEMENT_1183\n"
blocked_lineage = lineage("pkg/blocked_case.py", blocked_before, status="blocked", block_reason="sandbox_target_drift")
blocked_draft = draft_supervised_sandbox_repair(*blocked_lineage, blocked_before, blocked_after)
require(blocked_draft["draft_status"] == "private_draft_ready")
require(blocked_draft["failure_code"] == "sandbox_test_execution_blocked")
require(blocked_draft["original_failure_acceptance_check"] == "original_execution_block_no_longer_observed")
require(blocked_draft["later_retest_intent"] == "request_new_test_review_before_retest")

# Content-free public summary.
summary = repair_draft_public_summary(compile_draft)
encoded_summary = json.dumps(summary, sort_keys=True)
require(summary["content_free"] and not summary["private_source_content_included"])
require(not summary["replacement_text_included"] and not summary["rollback_text_included"] and not summary["patch_text_included"])
require("replacement_text" not in summary and "rollback_text" not in summary and "patch_text" not in summary)
require("PRIVATE_COMPILE_SOURCE_1183" not in encoded_summary and "PRIVATE_COMPILE_REPLACEMENT_1183" not in encoded_summary)
require("stdout" not in encoded_summary.lower() and "stderr" not in encoded_summary.lower())
require(not summary["raw_test_output_included"] and not summary["private_reasoning_included"])
require(not summary["sandbox_modified"] and not summary["production_source_modified"] and not summary["source_modified"])
require(not summary["repair_materialized"] and not summary["tests_rerun"])
require(not summary["provider_contacted"] and not summary["model_contacted"] and not summary["authority_granted"])
require("exact private replacement remains separate" in repair_draft_review_prompt(summary))

# Stale state, target drift, lineage mismatches, and tamper rejection.
require(draft_supervised_sandbox_repair(*compile_lineage, compile_before + "# drift\n", compile_after)["block_reason"] == "stale_sandbox_state")
plan, diagnosis, review, mat, evidence = compile_lineage
mismatch_plan = re_receipt({**plan, "diagnosis_digest": "f" * 64}, "plan_receipt_digest")
require(draft_supervised_sandbox_repair(mismatch_plan, diagnosis, review, mat, evidence, compile_before, compile_after)["block_reason"] == "mismatched_diagnosis_or_plan_digest")
mismatch_evidence = re_receipt({**evidence, "sandbox_target_digest": "f" * 64}, "evidence_receipt_digest")
require(draft_supervised_sandbox_repair(plan, diagnosis, review, mat, mismatch_evidence, compile_before, compile_after)["block_reason"] == "sandbox_target_digest_mismatch")
mismatch_materialization = re_receipt({**mat, "sandbox_target_digest": "f" * 64}, "materialization_receipt_digest")
require(draft_supervised_sandbox_repair(plan, diagnosis, review, mismatch_materialization, evidence, compile_before, compile_after)["block_reason"] == "materialization_evidence_digest_mismatch")
require(draft_supervised_sandbox_repair({**plan, "plan_digest": "0" * 64}, diagnosis, review, mat, evidence, compile_before, compile_after)["block_reason"] == "invalid_or_tampered_repair_plan")
require(draft_supervised_sandbox_repair(plan, {**diagnosis, "diagnosis_digest": "0" * 64}, review, mat, evidence, compile_before, compile_after)["block_reason"] == "invalid_or_tampered_diagnosis")
require(draft_supervised_sandbox_repair(plan, diagnosis, {**review, "review_digest": "0" * 64}, mat, evidence, compile_before, compile_after)["block_reason"] == "invalid_or_tampered_diagnosis_review")
require(draft_supervised_sandbox_repair(plan, diagnosis, review, {**mat, "materialization_receipt_digest": "0" * 64}, evidence, compile_before, compile_after)["block_reason"] == "invalid_or_tampered_materialization_receipt")
require(draft_supervised_sandbox_repair(plan, diagnosis, review, mat, {**evidence, "evidence_receipt_digest": "0" * 64}, compile_before, compile_after)["block_reason"] == "invalid_or_mismatched_failed_test_evidence")

# Unsafe targets: traversal, absolute, drive-qualified, private, and runtime paths.
for unsafe in ("../secret.py", "/etc/passwd.py", "C:/secret.py", "private/secret.py", "runtime/state.py", "data/state.py", "conversations/raw.py", "memories/raw.py"):
    unsafe_lineage = lineage(unsafe, compile_before, status="failed", error_class="python_compile_failed")
    require(draft_supervised_sandbox_repair(*unsafe_lineage, compile_before, compile_after)["block_reason"] == "unsafe_sandbox_target")

# Malformed contracts, unsupported codes, duplicate drafts, no-op changes, and bounded input.
require(draft_supervised_sandbox_repair({}, diagnosis, review, mat, evidence, compile_before, compile_after)["block_reason"] == "invalid_or_tampered_repair_plan")
malformed_plan = re_receipt({**plan, "acceptance_criteria": ["original_failure_no_longer_observed"]}, "plan_receipt_digest")
require(draft_supervised_sandbox_repair(malformed_plan, diagnosis, review, mat, evidence, compile_before, compile_after)["block_reason"] == "malformed_or_unsupported_repair_contract")
contradictory_diagnosis = copy.deepcopy(diagnosis)
contradictory_diagnosis["diagnosis_candidates"][0]["diagnosis_code"] = "sandbox_test_timeout_observed"
contradictory_diagnosis["diagnosis_digest"] = digest({"contradictory": "timeout", "evidence": contradictory_diagnosis["evidence_digest"]})
contradictory_diagnosis = re_receipt(contradictory_diagnosis, "diagnosis_receipt_digest")
contradictory_review = review_repair_diagnosis(contradictory_diagnosis, "confirm", "bundle-a-operator")
contradictory_plan = build_supervised_repair_plan(contradictory_diagnosis, contradictory_review)
require(draft_supervised_sandbox_repair(contradictory_plan, contradictory_diagnosis, contradictory_review, mat, evidence, compile_before, compile_after)["block_reason"] == "diagnosis_does_not_match_failed_test_evidence")
oversized_plan = {**plan, "padding": "x" * (MAX_CONTRACT_BYTES + 1)}
require(draft_supervised_sandbox_repair(oversized_plan, diagnosis, review, mat, evidence, compile_before, compile_after)["block_reason"] == "oversized_or_malformed_contract")
unsupported = unsupported_lineage(compile_before)
require(draft_supervised_sandbox_repair(*unsupported, compile_before, compile_after)["block_reason"] == "unsupported_repair_code")
require(draft_supervised_sandbox_repair(*compile_lineage, compile_before, compile_after, existing_draft_digests=[compile_draft["draft_digest"]])["block_reason"] == "duplicate_repair_draft")
require(draft_supervised_sandbox_repair(*compile_lineage, compile_before, compile_after, existing_draft_digests=["bad"])["block_reason"] == "malformed_existing_draft_ledger")
require(draft_supervised_sandbox_repair(*compile_lineage, compile_before, compile_after, existing_draft_digests=["a" * 64] * (MAX_EXISTING_DRAFT_DIGESTS + 1))["block_reason"] == "malformed_existing_draft_ledger")
require(draft_supervised_sandbox_repair(*compile_lineage, compile_before, compile_before)["block_reason"] == "no_op_repair_draft")
require(draft_supervised_sandbox_repair(*compile_lineage, compile_before + "\x00", compile_after)["block_reason"] == "invalid_private_source_content")
require(draft_supervised_sandbox_repair(*compile_lineage, compile_before, "x" * (MAX_SOURCE_BYTES + 1))["block_reason"] == "oversized_private_source_content")
large_before = "".join(f"value_{i} = 0\n" for i in range(MAX_CHANGED_LINES // 2 + 2))
large_after = "".join(f"value_{i} = 1\n" for i in range(MAX_CHANGED_LINES // 2 + 2))
large_lineage = lineage("pkg/large_change.py", large_before, status="failed", error_class="python_compile_failed")
require(draft_supervised_sandbox_repair(*large_lineage, large_before, large_after)["block_reason"] == "repair_draft_exceeds_minimal_change_bounds")

# Checkpoint, registry, dispatcher, CLI, GET-only API, dashboard, metadata, docs, and release wiring.
with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    checkpoint = build_supervised_sandbox_repair_draft_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(checkpoint["ok"] and checkpoint["passed"] == checkpoint["total"])
    require(checkpoint["total"] >= 75)
    require(checkpoint["read_only"] and checkpoint["post_available"] is False)
    require(checkpoint["content_free"] and checkpoint["authority_preserved"])
    require(checkpoint["supervised_sandbox_repair_draft_foundations_completed"])
    require(checkpoint["compile_timeout_blocked_drafts_exercised"])
    require(checkpoint["private_replacement_and_public_summary_separation_exercised"])
    require(not checkpoint["production_source_modified"] and not checkpoint["sandbox_modified"])
    require(not checkpoint["repair_materialized"] and not checkpoint["tests_rerun"])
    require(not checkpoint["provider_contacted"] and not checkpoint["model_operation_performed"])
    require(not checkpoint["automatic_approval_created"] and not checkpoint["automatic_authorization_granted"])
    require(not checkpoint["repair_authorized"] and not checkpoint["retest_authorized"])
    require(not checkpoint["release_authorized"] and checkpoint["forbidden_report_value_count"] == 0)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "supervised-sandbox-repair-draft-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])
    require(dispatched["checkpoint_summary"]["ok"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry["checkpoints"] if item["checkpoint_id"] == "supervised-sandbox-repair-draft-checkpoint"), None)
require(row is not None)
require(row["builder"] == "build_supervised_sandbox_repair_draft_checkpoint")
require(row["contract_version"] == CONTRACT_VERSION)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "supervised-sandbox-repair-draft-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=900,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == CONTRACT_VERSION)

status, payload = dispatch_api("GET", "/api/cognition/supervised-sandbox-repair-draft-checkpoint")
require(status == 200 and (payload.get("data") or {}).get("contract_version") == CONTRACT_VERSION)
post_status, _ = dispatch_api("POST", "/api/cognition/supervised-sandbox-repair-draft-checkpoint", body={"confirm": True})
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("supervised-sandbox-repair-draft-checkpoint-panel" in dashboard)
require("/api/cognition/supervised-sandbox-repair-draft-checkpoint" in dashboard)
require("refreshSupervisedSandboxRepairDraftCheckpoint" in dashboard)
require("Public diagnostics remain content-free" in dashboard)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1183.5"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1183.2"' in metadata)
require("v1183.3-v1183.5" in metadata and "v1200" not in metadata or "v1183.3-v1183.5" in metadata)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1183.2 Supervised Sandbox Repair Draft Foundations" in readme)
require("Current source: v1183.2" in next_steps and "v1183.3-v1183.5" in next_steps and "v1200" in next_steps)
require("Current source: v1183.2" in roadmap and "v1184" in roadmap and "v1200" in roadmap)
require("v1183.2 Supervised Sandbox Repair Draft Foundations" in history)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1183.0-v1183.2-supervised-sandbox-repair-draft-foundations") == 1)
require(release_verify.count("tools/v1183_0_2_supervised_sandbox_repair_draft_foundations_tests.py") == 1)

core_source = (ROOT / "conscious_agent" / "supervised_sandbox_repair_draft_foundations.py").read_text(encoding="utf-8")
require("read_text(" not in core_source and "read_bytes(" not in core_source and "write_text(" not in core_source and "write_bytes(" not in core_source)
require("subprocess" not in core_source and "os.system" not in core_source)
require('"tests_rerun": False' in core_source and '"provider_contacted": False' in core_source and '"model_contacted": False' in core_source)
require('"repair_authorized": False' in core_source and '"retest_authorized": False' in core_source)

with tempfile.TemporaryDirectory() as directory:
    empty_sandbox = Path(directory) / "sandbox"
    before_empty = list(Path(directory).rglob("*"))
    _ = draft_supervised_sandbox_repair(*compile_lineage, compile_before, compile_after)
    after_empty = list(Path(directory).rglob("*"))
    require(before_empty == after_empty and not empty_sandbox.exists())

source_after = tree_signature(ROOT)
require(source_before == source_after)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1183.0-v1183.2-supervised-sandbox-repair-draft-foundations",
    "passed": sum(checks),
    "total": len(checks),
    "production_source_modified": False,
    "sandbox_modified": False,
    "tests_rerun": False,
    "provider_contacted": False,
    "model_contacted": False,
    "authority_expanded": False,
}, sort_keys=True))
