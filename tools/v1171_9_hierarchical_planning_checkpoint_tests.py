from __future__ import annotations
import json, os, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from conscious_agent.hierarchical_planning_checkpoint import build_hierarchical_planning_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint

checks=[]
def require(v): checks.append(bool(v))
with tempfile.TemporaryDirectory() as td:
    runtime=Path(td)/"runtime"
    report=build_hierarchical_planning_checkpoint(source_root=ROOT,runtime_root=runtime)
    require(report["ok"] and report["passed"]==report["total"])
    require(report["total"]>=70); require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"]); require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"]); require(report["hierarchical_planning_checkpoint_completed"])
    require(report["historical_v1134_planning_governance_preserved"]); require(report["literal_current_request_precedence_preserved"])
    require(report["goal_activation_not_started"] and report["plan_activation_not_started"])
    require(report["plan_persistence_not_started"] and report["plan_execution_not_started"])
    require(report["simulation_and_risk_comparison_not_started"] and report["tools_and_actions_not_started"])
    require(report["forbidden_report_value_count"]==0); require(len(report["structural_digest"])==64)
    for key in ("goal_created","goal_activated","plan_created","plan_activated","plan_persisted","schedule_created","tool_routed","tool_executed","action_executed","source_edit_performed","approval_granted","memory_mutated","lesson_committed","model_training_performed","model_weights_changed","installation_performed","promotion_performed","certification_performed","provider_contacted","proactive_turn_created"):
        require(report[key] is False)
    s=report["summary"]
    require(s["projection_case_count"]==7); require(s["review_case_count"]==5); require(s["handoff_case_count"]==3); require(s["reliability_case_count"]==4)
    require(s["authoritative_conversation_path_count"]==2); require(s["milestone_maximum_count"]==8); require(s["dependency_maximum_count"]==12)
    require(s["privacy_forbidden_entry_count"]==0 and s["privacy_content_finding_count"]==0)
    syn=report["evidence"]["synthetic_contracts"]
    require(syn["projection_summaries"]["emerging"]["plan_candidate_available"])
    require(not syn["projection_summaries"]["no_plan"]["plan_candidate_available"])
    require(syn["projection_summaries"]["tampered_recovery"]["policy_recovered"])
    require(syn["review_summaries"]["stable"]["review_disposition"]=="stable_plan_review")
    require(syn["review_summaries"]["replay"]["verified_prior_receipt_count"]==1)
    require(syn["review_summaries"]["replay"]["replayed_prior_receipt_count"]==2)
    require(syn["handoff_summaries"]["completed"]["eligible"])
    require(not syn["handoff_summaries"]["before_provider"]["eligible"])
    require(syn["reliability_summaries"]["reliable"]["ready"])
    require(not syn["reliability_summaries"]["tampered"]["ready"])
    require(syn["reliability_summaries"]["flood"]["receipt_budget_exceeded"])
    require(not runtime.exists())
    dispatched=dispatch_registered_checkpoint("hierarchical-planning-checkpoint",source_root=ROOT,runtime_root=runtime)
    require(dispatched["read_only"] and not dispatched["source_modified"] and not dispatched["runtime_mutated"])

registry=inspect_checkpoint_registry(source_root=ROOT)
row=next((r for r in registry["checkpoints"] if r["checkpoint_id"]=="hierarchical-planning-checkpoint"),None)
require(row is not None and row["builder"]=="build_hierarchical_planning_checkpoint")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

old=os.environ.get("EIDOLON_DATA_DIR")
with tempfile.TemporaryDirectory() as td:
    env=dict(os.environ); env["PYTHONPATH"]=str(ROOT); env["EIDOLON_DATA_DIR"]=str(Path(td)/"runtime"); env["PYTHONDONTWRITEBYTECODE"]="1"; env["PYTHONPYCACHEPREFIX"]=str(Path(td)/"pycache")
    cli=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"hierarchical-planning-checkpoint"],cwd=ROOT,env=env,text=True,capture_output=True,timeout=480)
    require(cli.returncode==0); require(json.loads(cli.stdout)["contract_version"]=="v1171.9")

from conscious_agent.api_server import dispatch_api
status,payload=dispatch_api("GET","/api/cognition/hierarchical-planning-checkpoint")
require(status==200 and (payload.get("data") or {}).get("contract_version")=="v1171.9")
post_status,_=dispatch_api("POST","/api/cognition/hierarchical-planning-checkpoint",body={"confirm":True})
require(post_status in (404,405))

dash=(ROOT/"conscious_agent"/"dashboard_first_use.py").read_text(encoding="utf-8")
require("hierarchical-planning-checkpoint-panel" in dash); require("/api/cognition/hierarchical-planning-checkpoint" in dash); require("refreshHierarchicalPlanningCheckpoint" in dash); require("Desktop review deferred to v1200" in dash)
metadata=(ROOT/"conscious_agent"/"release_metadata.py").read_text(encoding="utf-8")
working=re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"',metadata); previous=re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"',metadata)
require(tuple(map(int,working.groups())) >= (1171,9) and tuple(map(int,previous.groups())) < tuple(map(int,working.groups()))); require("NEXT_RECOMMENDED_ARC" in metadata)
next_steps=(ROOT/"README_NEXT_STEPS.md").read_text(encoding="utf-8"); history=(ROOT/"README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("Current working source:" in next_steps and "v1200" in next_steps)
require("v1171.9 Hierarchical Planning" in history and "No Desktop verification" in history)
print(f"v1171.9 hierarchical planning checkpoint tests: {sum(checks)}/{len(checks)}")
if not all(checks):
    print([i+1 for i,v in enumerate(checks) if not v]); raise SystemExit(1)
