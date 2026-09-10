from __future__ import annotations
import json, os, shutil, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault("EIDOLON_DATA_DIR",tempfile.mkdtemp(prefix="eidolon-v1222-a-data-"))
sys.path[:0]=[str(ROOT/"conscious_agent"),str(ROOT/"tools")]
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
import transaction_resumption_abandoned_work_reconciliation as resume
from v1220_rollback_result_review_fixture import build_rollback_result_review_fixture
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
f=build_rollback_result_review_fixture("v1222-foundations"); rt=f["runtime"]; p=f["proposal"]
try:
 command=f"Assess supervised development transaction resumption proposal {p['proposal_id']} revision 1."
 turn=process_ordinary_chat_development_turn(command,runtime_root=rt)
 require(turn["active"] is True,turn)
 require(turn["event"]=="transaction_resumption_assessment_ready",turn)
 row=turn["transaction_resumption_abandoned_work_reconciliation"]
 require(row["ok"] is True,row)
 require(row["classification"]=="review_required",row)
 require(row["last_trustworthy_stage"]=="rollback-result-review",row)
 require(row["unfinished_work_detected"] is True)
 require(row["old_authority_reuse_forbidden"] is True)
 require(row["new_approval_required_before_continuation"] is True)
 require(row["prior_approval_reusable"] is False)
 require(row["prior_authorization_reusable"] is False)
 require("resume-planning" in row["eligible_decisions"])
 require("begin-fresh-attempt" in row["eligible_decisions"])
 require(len(row["assessment_digest"])==64)
 require(len(row["history_digest"])==64)
 require(len(row["decision_phrases"])==4)
 require(str(rt) not in json.dumps(row))
 require(row["private_path_exposed"] is False)
 require(row["authority_granted"] is False)
 replay=resume.build_transaction_resumption_assessment(p["proposal_id"],expected_revision=1,runtime_root=rt)
 require(replay["operation_status"]=="resumed",replay)
 require(replay["assessment_generation"]==1)
 require(resume.load_transaction_resumption_assessment(p["proposal_id"],1,runtime_root=rt)["assessment_digest"]==row["assessment_digest"])
finally: shutil.rmtree(rt,ignore_errors=True)
print(json.dumps({"ok":True,"version":"1222.2","checks":len(CHECKS),"passed":sum(CHECKS),"elapsed_seconds":round(time.monotonic()-START,4),"assessment_classes":4,"old_authority_reuse_forbidden":True,"release_authorized":False},sort_keys=True))
