from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.memory_experiential_learning_alpha_checkpoint import (
    build_memory_experiential_learning_alpha_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


def signature(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        digest.update(b"missing")
        return digest.hexdigest()
    for path in sorted(
        p for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
        and ".pytest_cache" not in p.parts and p.suffix not in {".pyc", ".pyo"}
    ):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_memory_experiential_learning_alpha_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1169.9")
    require(report["checkpoint_id"] == "memory-experiential-learning-alpha:v1169.9")
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 50)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["memory_experiential_learning_alpha_checkpoint_completed"])
    require(report["unified_memory_retrieval_learning_and_lessons_consolidated"])
    require(report["historical_truth_preserved"])
    require(report["literal_current_request_precedence_preserved"])
    require(report["uncontrolled_self_training_not_started"])
    require(report["model_training_not_started"] and report["model_weights_unchanged"])
    require(report["automatic_memory_mutation_not_started"])
    require(report["automatic_lesson_commit_not_started"])
    require(report["automatic_generalization_not_started"])
    require(report["goals_and_plans_not_started"] and report["tools_and_actions_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)

    summary = report["summary"]
    require(summary["synthetic_contract_check_count"] >= 30)
    require(summary["projection_case_count"] == 9)
    require(summary["handoff_case_count"] == 3)
    require(summary["audit_case_count"] == 2)
    require(summary["reliability_case_count"] == 2)
    require(summary["receipt_case_count"] == 3)
    require(summary["registered_checkpoint_count"] >= 196)
    require(summary["selected_record_maximum_count"] == 12)
    require(summary["domain_maximum_count"] == 5)
    require(summary["alpha_prompt_maximum_chars"] == 3600)
    require(summary["prior_alpha_receipt_maximum_count"] == 64)
    require(summary["alpha_receipt_maximum_bytes"] == 16384)
    require(summary["authoritative_conversation_path_count"] == 2)
    require(summary["open_limitation_count"] == 6)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"])
    require(all(row["content_free"] and row["authority_preserved"] for row in synthetic["projection_summaries"].values()))
    require(all(row["diagnostics_valid"] for row in synthetic["projection_summaries"].values()))
    require(synthetic["projection_summaries"]["current_correction"]["selected_count"] == 0)
    require(synthetic["projection_summaries"]["retraction"]["historical_truth_preserved"])
    require(synthetic["projection_summaries"]["temporary_preference"]["learning_candidate_scope"] == "temporary")
    require(synthetic["projection_summaries"]["durable_preference"]["lesson_candidate_type"] == "preference_lesson")
    require(synthetic["projection_summaries"]["stale_memory"]["selected_count"] == 0)
    require(synthetic["projection_summaries"]["repeated_success"]["lesson_candidate_type"] == "repeatable_success_lesson")
    require(synthetic["projection_summaries"]["malformed_component"]["policy_recovered"])
    require(synthetic["handoff_summaries"]["completed"]["valid"])
    require(not synthetic["handoff_summaries"]["before_provider"]["eligible_for_future_structural_continuity"])
    require(not synthetic["handoff_summaries"]["before_memory_commit"]["eligible_for_future_structural_continuity"])
    require(synthetic["audit_summaries"]["compliant"]["valid"] and synthetic["audit_summaries"]["compliant"]["compliant"])
    require(synthetic["audit_summaries"]["forged_injection"]["prompt_injection_count"] >= 1)
    require(synthetic["reliability_summaries"]["reliable"]["ordinary_conversation_ready"])
    require(not synthetic["reliability_summaries"]["tampered_handoff"]["ordinary_conversation_ready"])
    require(synthetic["receipt_summaries"]["replayed"]["replayed_receipt_count"] == 1)
    require(synthetic["receipt_summaries"]["tampered"]["recovery_required"])

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "memory-experiential-learning-alpha-checkpoint", source_root=ROOT, runtime_root=runtime
        )
        require(dispatched["read_only"])
        require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"])
        require(dispatched["checkpoint_summary"]["ok"])
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/memory-experiential-learning-alpha-checkpoint")
        require(status == 200)
        require((payload.get("data") or {}).get("contract_version") == "v1169.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/memory-experiential-learning-alpha-checkpoint", body={"confirm": True}
        )
        require(post_status in (404, 405))
    finally:
        if old is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old

with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(runtime)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(td) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "memory-experiential-learning-alpha-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1169.9")
    require(not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (row for row in registry["checkpoints"] if row["checkpoint_id"] == "memory-experiential-learning-alpha-checkpoint"),
    None,
)
require(row is not None and row["builder"] == "build_memory_experiential_learning_alpha_checkpoint")
require(registry["checkpoint_count"] >= 196)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("memory-experiential-learning-alpha-checkpoint-panel" in dashboard)
require("/api/cognition/memory-experiential-learning-alpha-checkpoint" in dashboard)
require("refreshMemoryExperientialLearningAlphaCheckpoint" in dashboard)
require("deferred to v1200" in dashboard)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
working_version = tuple(map(int, working.groups()))
previous_version = tuple(map(int, previous.groups()))
require(working_version >= (1169, 9) and previous_version < working_version)
require("NEXT_RECOMMENDED_ARC" in metadata)

next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("Current working source:" in next_steps)
require("v1200" in next_steps)
require("v1169.9 Memory and Experiential Learning Alpha" in history)

print(f"v1169.9 memory experiential learning alpha checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
