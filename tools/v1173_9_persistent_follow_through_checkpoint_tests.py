from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.persistent_follow_through_checkpoint import build_persistent_follow_through_checkpoint

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_persistent_follow_through_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 120)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    require(report["persistent_follow_through_checkpoint_completed"])
    require(report["follow_through_review_continuity_and_reliability_consolidated"])
    require(report["historical_v1134_planning_governance_preserved"])
    require(report["plan_simulation_boundary_preserved"])
    require(report["literal_current_request_precedence_preserved"])
    require(report["goal_and_planning_alpha_not_started"])
    require(report["plan_activation_not_started"] and report["plan_persistence_not_started"])
    require(report["plan_execution_not_started"] and report["tool_routing_not_started"])
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
    require(summary["reliability_case_count"] == 4)
    require(summary["authoritative_conversation_path_count"] == 2)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    evidence = report["evidence"]["synthetic_contracts"]
    require(evidence["projection_summaries"]["emerging"]["follow_through_available"])
    require(evidence["projection_summaries"]["emerging"]["milestone_count"] == 3)
    require(evidence["projection_summaries"]["stable"]["continuity_disposition"] == "verified_resume_review")
    require(not evidence["projection_summaries"]["no_follow_through"]["follow_through_available"])
    require(evidence["projection_summaries"]["tampered_recovery"]["policy_recovered"])
    require(evidence["projection_summaries"]["receipt_flood"]["receipt_budget_exceeded"])
    require(evidence["review_summaries"]["stable"]["review_disposition"] == "stable_follow_through_review")
    require(evidence["review_summaries"]["replay"]["verified_prior_receipt_count"] == 1)
    require(evidence["review_summaries"]["replay"]["replayed_prior_receipt_count"] == 2)
    require(evidence["handoff_summaries"]["completed"]["eligible"])
    require(not evidence["handoff_summaries"]["before_provider"]["eligible"])
    require(not evidence["handoff_summaries"]["before_memory"]["eligible"])
    require(evidence["reliability_summaries"]["reliable"]["ready"])
    require(not evidence["reliability_summaries"]["tampered"]["ready"])
    require(evidence["reliability_summaries"]["flood"]["receipt_budget_exceeded"])
    require(not runtime.exists())
    dispatched = dispatch_registered_checkpoint(
        "persistent-follow-through-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched["read_only"])
    require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry["checkpoints"] if item["checkpoint_id"] == "persistent-follow-through-checkpoint"),
    None,
)
require(row is not None and row["builder"] == "build_persistent_follow_through_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "persistent-follow-through-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=480,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1173.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api("GET", "/api/cognition/persistent-follow-through-checkpoint")
require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1173.9")
post_status, _ = dispatch_api(
    "POST", "/api/cognition/persistent-follow-through-checkpoint", body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("persistent-follow-through-checkpoint-panel" in dashboard)
require("/api/cognition/persistent-follow-through-checkpoint" in dashboard)
require("refreshPersistentFollowThroughCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(tuple(map(int, working.groups())) >= (1173, 9))
require(tuple(map(int, previous.groups())) < tuple(map(int, working.groups())))
require("NEXT_RECOMMENDED_ARC" in metadata)
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("Current working source:" in next_steps and "v1200" in next_steps)
require("v1173.9 Persistent Follow-Through" in history and "No Desktop verification" in history)

print(f"v1173.9 persistent follow-through checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
