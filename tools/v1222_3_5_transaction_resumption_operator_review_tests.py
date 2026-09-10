from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1222-b-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
import transaction_resumption_abandoned_work_reconciliation as resume
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1222-review"); rt=f["runtime"]; p=f["proposal"]
try:
 assessment=resume.build_transaction_resumption_assessment(p["proposal_id"],expected_revision=1,runtime_root=rt)
 phrase=next(x for x in assessment["decision_phrases"] if "resume-planning" in x)
 turn=process_ordinary_chat_development_turn(phrase,runtime_root=rt)
 require(turn["active"] is True,turn)
 require(turn["event"]=="transaction_resumption_decision_recorded",turn)
 row=turn["transaction_resumption_abandoned_work_reconciliation"]
 require(row["decision"]=="resume-planning")
 require(row["decision_state"]=="resumption_planning_proposed")
 proposal=row["continuation_proposal"]
 require(proposal["status"]=="transaction_resumption_continuation_proposal_ready",proposal)
 require(proposal["fresh_authority_required"] is True)
 require(proposal["prior_authority_reusable"] is False)
 require(proposal["approval_consumed"] is False)
 require(proposal["continuation_executed"] is False)
 require(proposal["approval_phrase"].startswith("Approve transaction resumption proposal "))
 require(row["continuation_execution_authorized"] is False)
 require(row["project_modified"] is False)
 replay=process_ordinary_chat_development_turn(phrase,runtime_root=rt)
 require(replay["transaction_resumption_abandoned_work_reconciliation"]["operation_status"]=="resumed",replay)
 conflict=next(x for x in assessment["decision_phrases"] if "close-as-abandoned" in x)
 conflict_turn=process_ordinary_chat_development_turn(conflict,runtime_root=rt)
 require(conflict_turn["event"]=="transaction_resumption_conflicting_decision",conflict_turn)
 stale=phrase.replace(assessment["history_digest"],"f"*64)
 stale_turn=process_ordinary_chat_development_turn(stale,runtime_root=rt)
 require(stale_turn["event"]=="transaction_resumption_decision_stale_or_mismatched",stale_turn)
finally: shutil.rmtree(rt,ignore_errors=True)
for casual in ("Resume my project.","It would be nice to resume later.",'She said "assess transaction resumption".'):
 require(resume.process_transaction_resumption_control(casual)=={"active":False,"event":"inactive"})
print(json.dumps({"ok":True,"version":"1222.5","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"approval_gated_continuation_proposal":True,"continuation_executed":False,"release_authorized":False},sort_keys=True))
