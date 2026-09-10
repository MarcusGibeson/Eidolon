#!/usr/bin/env python3
import hashlib,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from conscious_agent.bounded_campaign_work_execution import *
from conscious_agent.bounded_campaign_work_execution_checkpoint import build_bounded_campaign_work_execution_checkpoint
checks=[]
def req(v,m=""):checks.append(bool(v));assert v,m
def h(s):return hashlib.sha256(s.encode()).hexdigest()
def signed(row,field):
 out=dict(row);out.pop(field,None);out[field]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return out
mr=signed({"campaign_id":"c1","session_id":"s2","status":"resumed_session_materialized_not_executing","resumed_session_digest":h("session"),"work_execution_eligible":True},"resume_materialization_receipt_digest")
rr=signed({"campaign_id":"c1","status":"restored_execution_eligible_not_executing","resumed_session_digest":h("session"),"work_execution_eligible":True},"restart_reconciliation_digest")
sel=signed({"selected_work_item_ids":["w1"],"status":"selected_not_executed"},"selection_digest")
with tempfile.TemporaryDirectory() as td:
 root=Path(td);(root/"ok.py").write_text("x=1\n",encoding="utf-8",newline="\n");d=h("x=1\n")
 for code in ("python_compile","content_digest_match"):
  c=create_work_execution_contract(restart_reconciliation=rr,materialization_receipt=mr,selection=sel,work_item_id="w1",execution_code=code,target_relative_path="ok.py",expected_target_digest=d,operator_contract_digest=h(code));req(c["status"]=="execution_review_required")
  a=create_work_execution_review(contract=c,decision="approve",operator_decision_digest=h("approve"+code));req(a["status"]=="approved_not_executed");r=execute_bounded_campaign_work(sandbox_root=root,contract=c,review=a);req(r["status"]=="executed");req(r["result_code"]=="passed");req(not r["sandbox_modified"]);req(not r["production_source_modified"]);req(not r["provider_contacted"]);req(not r["authority_granted"])
 c=create_work_execution_contract(restart_reconciliation=rr,materialization_receipt=mr,selection=sel,work_item_id="w1",execution_code="python_compile",target_relative_path="ok.py",expected_target_digest=d,operator_contract_digest=h("c"))
 req(execute_bounded_campaign_work(sandbox_root=root,contract=c,review=create_work_execution_review(contract=c,decision="reject",operator_decision_digest=h("r")))["status"]=="blocked")
 req(execute_bounded_campaign_work(sandbox_root=root,contract=c,review=create_work_execution_review(contract=c,decision="defer",operator_decision_digest=h("d")))["status"]=="blocked")
 (root/"bad.py").write_text("def x(:\n",encoding="utf-8",newline="\n");bd=h("def x(:\n");bc=create_work_execution_contract(restart_reconciliation=rr,materialization_receipt=mr,selection=sel,work_item_id="w1",execution_code="python_compile",target_relative_path="bad.py",expected_target_digest=bd,operator_contract_digest=h("bc"));br=create_work_execution_review(contract=bc,decision="approve",operator_decision_digest=h("ba"));req(execute_bounded_campaign_work(sandbox_root=root,contract=bc,review=br)["result_code"]=="failed")
 for kwargs in [
  dict(work_item_id="w2",execution_code="python_compile",target_relative_path="ok.py",expected_target_digest=d),
  dict(work_item_id="w1",execution_code="shell",target_relative_path="ok.py",expected_target_digest=d),
  dict(work_item_id="w1",execution_code="python_compile",target_relative_path="../ok.py",expected_target_digest=d),
  dict(work_item_id="w1",execution_code="python_compile",target_relative_path="ok.py",expected_target_digest="bad")]:
   req(create_work_execution_contract(restart_reconciliation=rr,materialization_receipt=mr,selection=sel,operator_contract_digest=h("x"),**kwargs)["status"]=="blocked")
cp=build_bounded_campaign_work_execution_checkpoint(source_root=ROOT);req(cp["ok"]);req(cp["passed"]==cp["total"]);req(not cp["automatic_execution"]);req(not cp["authority_granted"])
print(json.dumps({"ok":all(checks),"passed":sum(checks),"total":len(checks),"contract_version":"v1187.2"},sort_keys=True))
