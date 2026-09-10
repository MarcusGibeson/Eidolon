from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1220-c-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import operator_repaired_candidate_rollback_result_review as mod
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1220-reliability"); rt=f["runtime"]; p=f["proposal"]; review=f["rollback_result_review"]
try:
 phrase=review["decision_phrases"][0]
 wrong=phrase.replace(review["review_digest"],"0"*64)
 stale=mod.process_operator_repaired_candidate_rollback_result_review_control(wrong,runtime_root=rt)
 require(stale["active"] is True); require(stale["operator_repaired_candidate_rollback_result_review"]["status"]=="operator_repaired_candidate_rollback_result_decision_stale_review")
 escalated=phrase.replace("rollback attempt 1","rollback attempt 2")
 blocked=mod.process_operator_repaired_candidate_rollback_result_review_control(escalated,runtime_root=rt)
 require(blocked["operator_repaired_candidate_rollback_result_review"]["reason"]=="attempt_limit_exceeded")
 private=json.dumps(mod.public_operator_repaired_candidate_rollback_result_review(review))
 require(str(f["source_workspace_root"]) not in private)
 require(str(f["repaired_workspace_root"]) not in private)
 require('"rollback_authorized": true' not in private.lower())
 path=mod._review_path(p["proposal_id"],1,2,rt)
 raw=json.loads(path.read_text()); raw["review_digest"]="f"*64; path.write_text(json.dumps(raw))
 invalid=mod.load_operator_repaired_candidate_rollback_result_review(p["proposal_id"],1,2,runtime_root=rt)
 require(invalid=={})
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1220.8","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"tamper_closed":True,"private_paths_suppressed":True,"release_authorized":False},sort_keys=True))
