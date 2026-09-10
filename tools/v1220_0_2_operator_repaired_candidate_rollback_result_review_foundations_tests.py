from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1220-a-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import operator_repaired_candidate_rollback_result_review as review_mod
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1220-foundation"); rt=f["runtime"]; p=f["proposal"]; r=f["rollback_result"]; review=f["rollback_result_review"]
try:
 require(review["status"]=="operator_repaired_candidate_rollback_result_review_required",review)
 require(review["review_digest"] and len(review["review_digest"])==64)
 require(review["rollback_completed"] is True)
 require(review["pre_apply_state_restored"] is True)
 require(review["terminal_disposition_only"] is True)
 require(review["rollback_retry_available"] is False)
 require(set(review["available_decisions"])==set(review_mod.ROLLBACK_RESULT_REVIEW_DECISIONS))
 require(len(review["decision_phrases"])==3)
 require(review["supervised_repaired_candidate_rollback_result_digest"]==r["supervised_repaired_candidate_rollback_result_digest"])
 require(review["content_free"] is True)
 require(review["private_path_exposed"] is False)
 require(review["rollback_authorized"] is False)
 require(review["release_authorized"] is False)
 require(review["authority_granted"] is False)
 replay=review_mod.prepare_operator_repaired_candidate_rollback_result_review(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_execution_digest=r["supervised_repaired_candidate_rollback_digest"],expected_result_digest=r["supervised_repaired_candidate_rollback_result_digest"],runtime_root=rt)
 require(replay["operation_status"]=="resumed")
 stale=review_mod.prepare_operator_repaired_candidate_rollback_result_review(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_execution_digest="0"*64,expected_result_digest=r["supervised_repaired_candidate_rollback_result_digest"],runtime_root=rt)
 require(stale["status"]=="operator_repaired_candidate_rollback_result_review_stale_execution")
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1220.2","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"content_free_review":True,"release_authorized":False},sort_keys=True))
