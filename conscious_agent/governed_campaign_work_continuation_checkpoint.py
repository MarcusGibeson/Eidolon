from __future__ import annotations
"""Read-only v1187.8 governed campaign continuation and failure handling checkpoint."""
import hashlib,json,tempfile
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from governed_campaign_work_continuation import *
CONTRACT_VERSION="v1187.8"
def _h(s:str)->str:return hashlib.sha256(s.encode()).hexdigest()
def _signed(row:dict,field:str)->dict:
 out=dict(row);out.pop(field,None);out[field]=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest();return out
def build_governed_campaign_work_continuation_checkpoint(*,source_root:str|Path|None=None,runtime_root:str|Path|None=None)->dict[str,Any]:
 checks=[];req=lambda v:checks.append(bool(v))
 ledger=_signed({"campaign_id":"c1","work_item_ids":["w1","w2","w3"],"content_free":True},"ledger_digest")
 prior=_signed({"campaign_id":"c1","storage_generation":1,"campaign_state":"active","content_free":True},"storage_record_digest")
 for state,action in (("completed","select_followup"),("failed","hold_failure")):
  update=_signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","new_work_item_state":state,"status":"ledger_update_recorded","ledger_updated":True,"content_free":True},"ledger_update_receipt_digest")
  review=create_campaign_continuation_review(ledger_update_receipt=update,requested_action=action,decision="approve",operator_decision_digest=_h(state));req(review["status"]=="continuation_approved")
  selection=None
  if action=="select_followup":selection=create_followup_work_selection(ledger=ledger,ledger_update_receipt=update,continuation_review=review,candidate_work_item_ids=["w2"],max_items=1);req(selection["status"]=="followup_selection_ready")
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/"campaigns/c1";path.mkdir(parents=True);(path/"campaign_state.json").write_text(json.dumps(prior),encoding="utf-8")
   stored=persist_continuation_generation(runtime_root=td,prior_storage_record=prior,ledger_update_receipt=update,continuation_review=review,followup_selection=selection,operator_storage_digest=_h(action));req(stored["status"]=="continuation_stored");req(stored["runtime_written"]);req(not stored["work_executed"])
  req(continuation_public_summary(review,selection,stored)["content_free"])
 update=_signed({"campaign_id":"c1","session_id":"s1","work_item_id":"w1","new_work_item_state":"failed","status":"ledger_update_recorded","ledger_updated":True,"content_free":True},"ledger_update_receipt_digest")
 req(create_campaign_continuation_review(ledger_update_receipt=update,requested_action="complete_campaign",decision="approve",operator_decision_digest=_h("bad"))["status"]=="blocked")
 reg=inspect_checkpoint_registry(source_root=source_root);row=next((x for x in reg["checkpoints"] if x["checkpoint_id"]=="governed-campaign-work-continuation-checkpoint"),{});req(row.get("builder")=="build_governed_campaign_work_continuation_checkpoint");req(reg["duplicate_checkpoint_ids"]==[])
 return {"ok":all(checks),"contract_version":CONTRACT_VERSION,"checkpoint_id":"governed-campaign-work-continuation:v1187.8","passed":sum(checks),"total":len(checks),"read_only_source":True,"isolated_runtime_fixtures":True,"content_free":True,"automatic_retry":False,"automatic_resume":False,"work_executed":False,"production_source_modified":False,"sandbox_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"release_authorized":False,"desktop_verification_deferred_until_v1200":True}
