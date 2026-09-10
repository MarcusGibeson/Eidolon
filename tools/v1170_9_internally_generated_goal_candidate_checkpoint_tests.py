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
from conscious_agent.internally_generated_goal_candidate_checkpoint import (
    build_internally_generated_goal_candidate_checkpoint,
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
        and "data" not in p.relative_to(root).parts[:1]
    ):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    source_before = signature(ROOT)
    runtime_before = signature(runtime)
    report = build_internally_generated_goal_candidate_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1170.9")
    require(report["checkpoint_id"] == "internally-generated-goal-candidate:v1170.9")
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 70)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["internally_generated_goal_candidate_checkpoint_completed"])
    require(report["goal_nomination_review_continuity_and_reliability_consolidated"])
    require(report["historical_v1133_goal_governance_preserved"])
    require(report["literal_current_request_precedence_preserved"])
    require(report["goal_activation_not_started"])
    require(report["hierarchical_planning_not_started"])
    require(report["tools_and_actions_not_started"])
    require(report["uncontrolled_self_training_not_started"])
    require(report["model_training_not_started"] and report["model_weights_unchanged"])
    require(report["automatic_memory_mutation_not_started"])
    require(report["automatic_lesson_commit_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    for key in (
        "goal_created", "goal_modified", "goal_activated", "plan_created", "tool_routed",
        "tool_executed", "action_executed", "source_edit_performed", "approval_granted",
        "memory_mutated", "lesson_committed", "model_training_performed",
        "model_weights_changed", "installation_performed", "promotion_performed",
        "certification_performed", "provider_contacted", "proactive_turn_created",
    ):
        require(report[key] is False)

    summary = report["summary"]
    require(summary["synthetic_contract_check_count"] >= 50)
    require(summary["projection_case_count"] == 12)
    require(summary["review_case_count"] == 5)
    require(summary["handoff_case_count"] == 3)
    require(summary["reliability_case_count"] == 5)
    require(summary["receipt_case_count"] == 5)
    require(summary["registered_checkpoint_count"] >= 197)
    require(summary["component_maximum_bytes"] == 262144)
    require(summary["current_message_maximum_bytes"] == 32768)
    require(summary["observation_row_maximum_count"] == 32)
    require(summary["prior_receipt_maximum_count"] == 64)
    require(summary["receipt_maximum_bytes"] == 16384)
    require(summary["prompt_maximum_chars"] == 3200)
    require(summary["evidence_maximum_count"] == 64)
    require(summary["reliability_fault_maximum_count"] == 64)
    require(summary["authoritative_conversation_path_count"] == 2)
    require(summary["open_limitation_count"] == 6)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)

    synthetic = report["evidence"]["synthetic_contracts"]
    require(synthetic["passed"] == synthetic["total"])
    require(all(row["content_free"] and row["authority_preserved"] for row in synthetic["projection_summaries"].values()))
    require(all(row["diagnostics_valid"] and row["candidate_valid"] for row in synthetic["projection_summaries"].values()))
    require(not synthetic["projection_summaries"]["no_candidate"]["candidate_available"])
    require(synthetic["projection_summaries"]["operator_problem"]["candidate_type"] == "reliability_improvement")
    require(synthetic["projection_summaries"]["missing_capability"]["candidate_type"] == "capability_improvement")
    require(synthetic["projection_summaries"]["repeated_failure"]["deficiency_class"] == "repeated_failure")
    require(synthetic["projection_summaries"]["test_failure"]["deficiency_class"] == "test_or_diagnostic_failure")
    require(synthetic["projection_summaries"]["contradiction"]["candidate_type"] == "coherence_repair")
    require(synthetic["projection_summaries"]["knowledge_gap"]["candidate_type"] == "knowledge_improvement")
    require(synthetic["projection_summaries"]["maintenance"]["candidate_type"] == "maintenance_improvement")
    require(not synthetic["projection_summaries"]["unrelated_human_problem"]["candidate_available"])
    require(synthetic["projection_summaries"]["repeated_correction"]["deficiency_class"] == "repeated_correction")
    require(synthetic["projection_summaries"]["recovered_alpha"]["candidate_type"] == "coherence_repair")
    require(synthetic["projection_summaries"]["stable_prior"]["verified_prior_receipt_count"] == 1)
    require(all(row["state_valid"] and row["packet_valid"] for row in synthetic["review_summaries"].values()))
    require(synthetic["review_summaries"]["emerging"]["stability_band"] == "emerging")
    require(synthetic["review_summaries"]["stable"]["stability_band"] == "stable")
    require(synthetic["review_summaries"]["replayed"]["replayed_prior_receipt_count"] == 11)
    require(not synthetic["review_summaries"]["none"]["candidate_available"])
    require(not synthetic["review_summaries"]["tampered"]["candidate_available"])
    require(synthetic["handoff_summaries"]["completed"]["valid"] and synthetic["handoff_summaries"]["completed"]["eligible"])
    require(not synthetic["handoff_summaries"]["before_provider"]["eligible"])
    require(not synthetic["handoff_summaries"]["before_memory_commit"]["eligible"])
    require(synthetic["reliability_summaries"]["reliable"]["ordinary_conversation_ready"])
    require(synthetic["reliability_summaries"]["replayed"]["ordinary_conversation_ready"])
    require(not synthetic["reliability_summaries"]["tampered"]["ordinary_conversation_ready"])
    require(synthetic["reliability_summaries"]["flood"]["receipt_budget_exceeded"])
    require(synthetic["reliability_summaries"]["recovered_residue"]["residual_candidate_detected"])
    require(synthetic["receipt_summaries"]["replayed"]["replayed_receipt_count"] == 1)
    require(synthetic["receipt_summaries"]["tampered"]["recovery_required"])
    require(synthetic["receipt_summaries"]["stale"]["stale_receipt_count"] == 1)
    require(synthetic["receipt_summaries"]["flood"]["receipt_budget_exceeded"])

    integration = report["evidence"]["ordinary_conversation_integration"]
    require(all(integration.values()))
    require(source_before == signature(ROOT))
    require(runtime_before == signature(runtime))
    require(not runtime.exists())

    old = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(runtime)
    try:
        dispatched = dispatch_registered_checkpoint(
            "internally-generated-goal-candidate-checkpoint", source_root=ROOT, runtime_root=runtime,
        )
        require(dispatched["read_only"])
        require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
        require(dispatched["checkpoint_summary"]["invocation_completed"])
        require(dispatched["checkpoint_summary"]["ok"])
        from conscious_agent.api_server import dispatch_api
        status, payload = dispatch_api("GET", "/api/cognition/internally-generated-goal-candidate-checkpoint")
        require(status == 200)
        require((payload.get("data") or {}).get("contract_version") == "v1170.9")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/internally-generated-goal-candidate-checkpoint", body={"confirm": True},
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
        [sys.executable, str(ROOT / "eidolon.py"), "internally-generated-goal-candidate-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1170.9")
    require(not runtime.exists())

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (row for row in registry["checkpoints"] if row["checkpoint_id"] == "internally-generated-goal-candidate-checkpoint"),
    None,
)
require(row is not None and row["builder"] == "build_internally_generated_goal_candidate_checkpoint")
require(registry["checkpoint_count"] >= 197)
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("internally-generated-goal-candidate-checkpoint-panel" in dashboard)
require("/api/cognition/internally-generated-goal-candidate-checkpoint" in dashboard)
require("refreshInternallyGeneratedGoalCandidateCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
working_version = tuple(map(int, working.groups()))
previous_version = tuple(map(int, previous.groups()))
require(working_version >= (1170, 9) and previous_version < working_version)
require("NEXT_RECOMMENDED_ARC" in metadata)

next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("Current working source:" in next_steps)
require("v1200" in next_steps)
require("v1170.9 Internally Generated Goal Candidate" in history)
require("No Desktop verification" in history)

print(f"v1170.9 internally generated goal candidate checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
