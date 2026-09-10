from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1219-b-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
import conversational_supervised_repaired_candidate_rollback as rollback
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from v1219_repaired_candidate_rollback_fixture import build_repaired_candidate_rollback_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_repaired_candidate_rollback_fixture("b-chat"); rt=f["runtime"]; p=f["proposal"]; rp=f["rollback_proposal"]
try:
 original={r["relative_path"]:r["content_digest"] for r in f["source_workspace_record"]["files"]}
 wrong=rollback.authorize_and_rollback_repaired_candidate(p["proposal_id"],expected_revision=1,expected_failed_attempt_number=2,expected_rollback_proposal_digest=rp["rollback_proposal_digest"],authorization_phrase="rollback it",runtime_root=rt)
 require(wrong["status"]=="supervised_repaired_candidate_rollback_exact_authorization_required")
 turn=process_ordinary_chat_development_turn(rp["authorization_phrase"],runtime_root=rt)
 require(turn["active"] is True,turn); require(turn["event"]=="supervised_repaired_candidate_rollback_completed",turn)
 result=turn["supervised_repaired_candidate_rollback"]
 require(result["ok"] is True); require(result["rollback_authorized"] is True)
 require(result["rollback_executed"] is True); require(result["authorization_consumption_count"]==1)
 require(result["restored_count"]==1); require(result["selected_project_modified"] is False)
 require(result["operator_review_required"] is True); require(result["rollback_result_review_required"] is True)
 require(result["provider_contacted"] is False); require(result["tests_executed"] is False)
 require(result["install_authorized"] is False); require(result["promotion_authorized"] is False)
 require(result["release_authorized"] is False); require(result["authority_granted"] is False)
 actual={x.relative_to(f["source_workspace_root"]).as_posix():__import__('hashlib').sha256(x.read_bytes()).hexdigest() for x in f["source_workspace_root"].rglob("*") if x.is_file() and "__pycache__" not in x.parts and x.suffix not in {".pyc",".pyo"}}
 require(actual==original,(actual,original))
 replay=process_ordinary_chat_development_turn(rp["authorization_phrase"],runtime_root=rt)
 require(replay["supervised_repaired_candidate_rollback"]["operation_status"]=="resumed")
 require(replay["supervised_repaired_candidate_rollback"]["authorization_consumption_count"]==1)
finally: shutil.rmtree(rt,ignore_errors=True)
for casual in ("It would be nice to undo that.","Could we roll it back?",'She said "Authorize repaired candidate rollback proposal".',"Rollback the fix."):
 require(rollback.process_supervised_repaired_candidate_rollback_control(casual)=={"active":False,"event":"inactive"})
print(json.dumps({"ok":True,"version":"1219.5","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"exact_authorization_consumed_once":True,"transactional_rollback":True,"operator_review_required":True,"release_authorized":False},sort_keys=True))
