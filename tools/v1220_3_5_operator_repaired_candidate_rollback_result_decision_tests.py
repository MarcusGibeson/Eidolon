from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1220-b-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
import operator_repaired_candidate_rollback_result_review as review_mod
from ordinary_chat_development_campaign import _atomic_json
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1220-decisions"); rt=f["runtime"]; base_private=review_mod.load_operator_repaired_candidate_rollback_result_review(f["proposal"]["proposal_id"],1,2,runtime_root=rt)
try:
 for index,decision in enumerate(("accept-rollback-result","defer","reject-rollback-result"),start=1):
  pid=f"devc_{index:024x}"
  private=dict(base_private); private["proposal_id"]=pid
  private["decision_phrases"]=[review_mod._review_phrase(value,private["review_digest"],pid,1,2) for value in review_mod.ROLLBACK_RESULT_REVIEW_DECISIONS]
  private=review_mod._sealed(private,"operator_repaired_candidate_rollback_result_review_record_digest")
  _atomic_json(review_mod._review_path(pid,1,2,rt),private)
  phrase=review_mod._review_phrase(decision,private["review_digest"],pid,1,2)
  turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt)
  row=turn["operator_repaired_candidate_rollback_result_review"]
  require(turn["active"] is True,turn); require(row["status"]=="operator_repaired_candidate_rollback_result_decision_recorded",row)
  require(row["decision"]==decision); require(row["rollback_executed"] is False)
  require(row["project_modified"] is False); require(row["authority_granted"] is False)
  replay=process_ordinary_chat_development_turn(phrase,runtime_root=rt)
  require(replay["operator_repaired_candidate_rollback_result_review"]["operation_status"]=="resumed")
  other=review_mod._review_phrase("defer" if decision!="defer" else "accept-rollback-result",private["review_digest"],pid,1,2)
  conflict=process_ordinary_chat_development_turn(other,runtime_root=rt)
  require(conflict["operator_repaired_candidate_rollback_result_review"]["status"]=="operator_repaired_candidate_rollback_result_conflicting_decision")
finally: shutil.rmtree(rt,ignore_errors=True)
for casual in ("Accept the rollback result.","It would be nice to review that.",'She said "record defer for repaired candidate rollback result review".'):
 require(review_mod.process_operator_repaired_candidate_rollback_result_review_control(casual)=={"active":False,"event":"inactive"})
print(json.dumps({"ok":True,"version":"1220.5","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"exact_dispositions":True,"release_authorized":False},sort_keys=True))
