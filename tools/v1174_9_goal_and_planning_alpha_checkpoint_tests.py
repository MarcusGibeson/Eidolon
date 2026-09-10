from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.goal_and_planning_alpha_checkpoint import build_goal_and_planning_alpha_checkpoint

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_goal_and_planning_alpha_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 180)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["goal_and_planning_alpha_checkpoint_completed"])
    require(report["goal_planning_simulation_follow_through_consolidated"])
    require(report["historical_v1133_goal_governance_preserved"])
    require(report["historical_v1134_planning_governance_preserved"])
    require(report["literal_current_request_precedence_preserved"])
    require(report["natural_language_tool_routing_not_started"])
    require(report["tool_intent_routing_not_started"])
    require(report["tools_and_actions_not_started"])
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    for key in (
        "goal_created", "goal_activated", "plan_created", "plan_activated", "plan_persisted",
        "alternative_selected", "schedule_created", "tool_routed", "tool_executed",
        "action_executed", "source_edit_performed", "approval_granted", "memory_mutated",
        "lesson_committed", "model_training_performed", "model_weights_changed",
        "installation_performed", "promotion_performed", "certification_performed",
        "provider_contacted", "proactive_turn_created",
    ):
        require(report[key] is False)
    summary = report["summary"]
    require(summary["projection_case_count"] == 7)
    require(summary["review_case_count"] == 5)
    require(summary["handoff_case_count"] == 3)
    require(summary["reliability_case_count"] == 6)
    require(summary["receipt_case_count"] == 2)
    require(summary["consolidated_stage_count"] == 4)
    require(summary["authoritative_conversation_path_count"] == 2)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    evidence = report["evidence"]["synthetic_contracts"]
    require(not evidence["projection_summaries"]["no_candidate"]["alpha_available"])
    require(evidence["projection_summaries"]["emerging"]["alpha_available"])
    require(evidence["projection_summaries"]["emerging"]["available_stage_count"] == 4)
    require(evidence["projection_summaries"]["emerging"]["coherent_stage_count"] == 4)
    require(evidence["projection_summaries"]["stable"]["continuity_disposition"] == "verified_alpha_resume")
    require(evidence["projection_summaries"]["stable"]["verified_receipt_count"] == 1)
    require(evidence["projection_summaries"]["replay"]["replayed_receipt_count"] == 2)
    require(evidence["projection_summaries"]["tampered_recovery"]["policy_recovered"])
    require(evidence["projection_summaries"]["receipt_flood"]["receipt_budget_exceeded"])
    require(evidence["projection_summaries"]["missing_constraints"]["policy_recovered"])
    require(evidence["review_summaries"]["emerging"]["review_disposition"] == "emerging_goal_and_planning_alpha_review")
    require(evidence["review_summaries"]["stable"]["review_disposition"] == "stable_goal_and_planning_alpha_review")
    require(evidence["review_summaries"]["replay"]["verified_prior_receipt_count"] == 1)
    require(evidence["review_summaries"]["replay"]["replayed_prior_receipt_count"] == 2)
    require(evidence["handoff_summaries"]["completed"]["eligible"])
    require(not evidence["handoff_summaries"]["before_provider"]["eligible"])
    require(not evidence["handoff_summaries"]["before_memory"]["eligible"])
    require(evidence["reliability_summaries"]["no_candidate"]["ready"])
    require(not evidence["reliability_summaries"]["no_candidate"]["alpha_available"])
    require(evidence["reliability_summaries"]["reliable"]["ready"])
    require(evidence["reliability_summaries"]["replayed"]["verified_prior_receipt_count"] == 1)
    require(evidence["reliability_summaries"]["replayed"]["replayed_prior_receipt_count"] == 2)
    require(not evidence["reliability_summaries"]["tampered"]["ready"])
    require(evidence["reliability_summaries"]["flood"]["receipt_budget_exceeded"])
    require(evidence["reliability_summaries"]["residual"]["residual_alpha_detected"])
    require(not runtime.exists())
    dispatched = dispatch_registered_checkpoint(
        "goal-and-planning-alpha-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched["read_only"])
    require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
    require(dispatched["checkpoint_summary"]["ok"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry["checkpoints"] if item["checkpoint_id"] == "goal-and-planning-alpha-checkpoint"),
    None,
)
require(row is not None and row["builder"] == "build_goal_and_planning_alpha_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "goal-and-planning-alpha-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1174.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api("GET", "/api/cognition/goal-and-planning-alpha-checkpoint")
require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1174.9")
post_status, _ = dispatch_api(
    "POST", "/api/cognition/goal-and-planning-alpha-checkpoint", body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("goal-and-planning-alpha-checkpoint-panel" in dashboard)
require("/api/cognition/goal-and-planning-alpha-checkpoint" in dashboard)
require("refreshGoalAndPlanningAlphaCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working_match = __import__("re").search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous_match = __import__("re").search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(bool(working_match) and tuple(map(int, working_match.groups())) >= (1174, 9))
require(bool(previous_match) and tuple(map(int, previous_match.groups())) >= (1174, 8))
require("v1175" in metadata or tuple(map(int, working_match.groups())) > (1175, 9))
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require(("v1175.2" in next_steps or "v1176.2" in next_steps or "v1176.5" in next_steps or "v1176.8" in next_steps or "v1176.9" in next_steps or "v1177.2" in next_steps or "v1177.5" in next_steps or "v1177.8" in next_steps or "v1177.9" in next_steps or "v1178.2" in next_steps or "v1178.8" in next_steps or "v1178.9" in next_steps or "v1179.2" in next_steps or "v1179.5" in next_steps or "v1179.8" in next_steps or "v1179.9" in next_steps) and ("v1175.3-v1175.5" in next_steps or "v1176.3-v1176.5" in next_steps or "v1176.6-v1176.8" in next_steps or "v1176.9" in next_steps or "v1177.0-v1177.2" in next_steps or "v1177.3-v1177.5" in next_steps or "v1178.3-v1178.5" in next_steps or "v1179.3-v1179.5" in next_steps) and "v1200" in next_steps)
require("v1174.9 Goal and Planning Alpha" in history and "Desktop" in history)

print(f"v1174.9 goal and planning alpha checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
