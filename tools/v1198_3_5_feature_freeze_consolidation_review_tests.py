from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from conscious_agent.feature_freeze_consolidation_review_checkpoint import build_feature_freeze_consolidation_review_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import dispatch_api
checks=[]
def require(v): checks.append(bool(v))
with tempfile.TemporaryDirectory(prefix="eidolon-v1198-5-") as tmp:
    report=build_feature_freeze_consolidation_review_checkpoint(source_root=ROOT,runtime_root=tmp)
require(report["ok"]); require(report["review_count"]==15); require(report["action_count"]==5); require(report["decision_count"]==3)
require(len(report["blocked_cases"])>=20)
for review in report["reviews"]:
    require(review["status"]=="reviewed"); require(review["content_free"] is True); require(review["read_only"] is True)
    require(review["exception_applied"] is False); require(review["files_moved"] is False); require(review["modules_merged"] is False); require(review["files_deleted"] is False); require(review["imports_rewritten"] is False); require(review["startup_executed"] is False); require(review["runtime_mutated"] is False); require(review["source_modified"] is False); require(review["approval_consumed"] is False); require(review["release_performed"] is False); require(review["authority_state"]=="separate_not_granted")
registry=inspect_checkpoint_registry(source_root=ROOT); descriptor=next((r for r in registry["checkpoints"] if r["checkpoint_id"]=="feature-freeze-consolidation-review-checkpoint"),None)
require(bool(descriptor)); require(descriptor["contract_version"]=="v1198.5"); require(descriptor["read_only"] is True); require(descriptor["post_available"] is False)
p=subprocess.run([sys.executable,str(ROOT/"eidolon.py"),"feature-freeze-consolidation-review-checkpoint"],cwd=ROOT,text=True,capture_output=True)
require(p.returncode==0); payload=json.loads(p.stdout); require(payload["ok"]); require(payload["review_count"]==15)
status,payload=dispatch_api("GET","/api/cognition/feature-freeze-consolidation-review-checkpoint",{},None); require(status==200); require(payload["ok"]); require(payload["data"]["review_count"]==15)
status,payload=dispatch_api("POST","/api/cognition/feature-freeze-consolidation-review-checkpoint",{},{}); require(status in (404,405)); require(not payload.get("ok",False))
dashboard=(ROOT/"conscious_agent/dashboard_first_use.py").read_text(encoding="utf-8")
for token in ("feature-freeze-consolidation-review-panel","feature-freeze-consolidation-review-state","feature-freeze-consolidation-review-summary","/api/cognition/feature-freeze-consolidation-review-checkpoint","v1198.6-v1198.8"): require(token in dashboard)
for name in ("README.md","README_NEXT_STEPS.md","archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md","README_RELEASE_HISTORY.md"):
    text=(ROOT/name).read_text(encoding="utf-8"); require("v1198.5" in text); require("v1198.6-v1198.8" in text)
release=(ROOT/"tools/release_verify.py").read_text(encoding="utf-8"); require(release.count("v1198_3_5_feature_freeze_consolidation_review_tests.py")==1); require(release.count("v1198.5-feature-freeze-consolidation-review")==1)
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
