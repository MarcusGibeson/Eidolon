from __future__ import annotations
"""Read-only v1187.2 bounded campaign work execution foundations checkpoint."""
import hashlib,tempfile
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from bounded_campaign_work_execution import *
CONTRACT_VERSION="v1187.2"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _signed(row:dict,field:str)->dict:
 import json
 out=dict(row);out.pop(field,None);out[field]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return out
def build_bounded_campaign_work_execution_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 checks=[];req=lambda x:checks.append(bool(x))
 with tempfile.TemporaryDirectory(prefix="eidolon-v1187-2-") as td:
  root=Path(td);(root/"sandbox").mkdir();target=root/"sandbox"/"sample.py";target.write_text("value = 1\n",encoding="utf-8",newline="\n");digest=_h("value = 1\n")
  mr={"contract_version":"v1186.8","campaign_id":"c1","session_id":"s2","status":"resumed_session_materialized_not_executing","resumed_session_digest":_h("session"),"work_execution_eligible":True,"work_executed":False};mr=_signed(mr,"resume_materialization_receipt_digest")
  rr={"contract_version":"v1186.8","campaign_id":"c1","status":"restored_execution_eligible_not_executing","resumed_session_digest":_h("session"),"lease_digest":_h("lease"),"content_free":True,"work_execution_eligible":True,"work_executed":False,"automatic_execution":False,"authority_granted":False};rr=_signed(rr,"restart_reconciliation_digest")
  sel={"contract_version":"v1185.5","selected_work_item_ids":["w1"],"status":"selected_not_executed","content_free":True};sel=_signed(sel,"selection_digest")
  c=create_work_execution_contract(restart_reconciliation=rr,materialization_receipt=mr,selection=sel,work_item_id="w1",execution_code="python_compile",target_relative_path="sample.py",expected_target_digest=digest,operator_contract_digest=_h("contract"));req(c["status"]=="execution_review_required")
  review=create_work_execution_review(contract=c,decision="approve",operator_decision_digest=_h("approve"));req(review["status"]=="approved_not_executed")
  receipt=execute_bounded_campaign_work(sandbox_root=root/"sandbox",contract=c,review=review);req(receipt["status"]=="executed");req(receipt["result_code"]=="passed");req(receipt["work_executed"]);req(not receipt["sandbox_modified"]);req(not receipt["production_source_modified"]);req(not receipt["authority_granted"])
  req(create_work_execution_review(contract=c,decision="reject",operator_decision_digest=_h("reject"))["status"]=="rejected")
  req(create_work_execution_review(contract=c,decision="defer",operator_decision_digest=_h("defer"))["status"]=="deferred")
  req(create_work_execution_contract(restart_reconciliation=rr,materialization_receipt=mr,selection=sel,work_item_id="w2",execution_code="python_compile",target_relative_path="sample.py",expected_target_digest=digest,operator_contract_digest=_h("x"))["status"]=="blocked")
  req(create_work_execution_contract(restart_reconciliation=rr,materialization_receipt=mr,selection=sel,work_item_id="w1",execution_code="shell",target_relative_path="sample.py",expected_target_digest=digest,operator_contract_digest=_h("x"))["status"]=="blocked")
  drift=dict(c);drift["expected_target_digest"]=_h("wrong");drift=_signed(drift,"work_execution_contract_digest");dr=create_work_execution_review(contract=drift,decision="approve",operator_decision_digest=_h("a"));req(execute_bounded_campaign_work(sandbox_root=root/"sandbox",contract=drift,review=dr)["status"]=="blocked")
  summary=work_execution_public_summary(c,review,receipt);req(summary["content_free"] and not summary["authority_granted"])
 reg=inspect_checkpoint_registry(source_root=source_root);row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="bounded-campaign-work-execution-checkpoint"),{});req(row.get("builder")=="build_bounded_campaign_work_execution_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
 return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"bounded-campaign-work-execution:v1187.2","passed":sum(checks),"total":len(checks),"read_only_source":True,"content_free":True,"production_source_modified":False,"sandbox_modified":False,"work_executed_in_isolated_fixture":True,"automatic_execution":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
