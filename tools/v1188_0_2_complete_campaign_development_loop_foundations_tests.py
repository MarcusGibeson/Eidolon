from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from conscious_agent.complete_campaign_development_loop_checkpoint import build_complete_campaign_development_loop_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[]
def require(v):checks.append(bool(v))
report=build_complete_campaign_development_loop_checkpoint(source_root=ROOT)
require(report["ok"]); require(report["contract_version"]=="v1188.2"); require(report["passed"]==report["total"]); require(report["read_only"]); require(report["post_available"] is False); require(report["summary"]["complete_loop"]); require(report["summary"]["stage_count"]==10); require(report["production_source_modified"] is False); require(report["sandbox_modified"] is False); require(report["execution_invoked"] is False); require(report["provider_contacted"] is False); require(report["model_contacted"] is False); require(report["learning_applied"] is False); require(report["authority_granted"] is False)
registry=inspect_checkpoint_registry(source_root=ROOT); row=next((x for x in registry["checkpoints"] if x["checkpoint_id"]=="complete-campaign-development-loop-checkpoint"),{}); require(row.get("contract_version")=="v1188.2"); require(row.get("read_only") is True); require(row.get("post_available") is False); require(registry["duplicate_checkpoint_ids"]==[])
api=(ROOT/"conscious_agent/api_server.py").read_text(); require('complete-campaign-development-loop-checkpoint' in api)
metadata=(ROOT/"conscious_agent/release_metadata.py").read_text(); require('WORKING_SOURCE_VERSION = "1188.2"' in metadata); require('v1188.2 Complete Campaign Development Loop Foundations' in metadata)
release=(ROOT/"tools/release_verify.py").read_text(); require(release.count('v1188.2-complete-campaign-development-loop-foundations')==1); require(release.count('tools/v1188_0_2_complete_campaign_development_loop_foundations_tests.py')==1)
for name in ("README.md","README_NEXT_STEPS.md","archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md","README_RELEASE_HISTORY.md"): require("v1188.2" in (ROOT/name).read_text())
print(json.dumps({"suite":"v1188.0-v1188.2-complete-campaign-development-loop-foundations","passed":sum(checks),"total":len(checks),"ok":all(checks)},sort_keys=True))
