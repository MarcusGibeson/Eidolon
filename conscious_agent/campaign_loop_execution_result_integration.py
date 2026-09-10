from __future__ import annotations
"""v1188.3-v1188.5 governed campaign loop execution and result integration."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1188.5";SCHEMA_VERSION="1";MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
EXECUTABLE_STAGES=("inspection","implementation","testing","diagnosis_repair","presentation","learning")
RESULTS=frozenset({"passed","failed","blocked"})
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_loop_execution_review(*,loop:Mapping[str,Any],decision:str,operator_decision_digest:str)->dict[str,Any]:
 l=dict(loop);ld,lok=_verify(l,"loop_digest");errors=[]
 if not lok:errors.append("tampered_loop")
 if l.get("status")!="complete_review_required" or not l.get("complete_loop"):errors.append("loop_not_complete")
 if decision not in {"approve","reject","defer"}:errors.append("unsupported_decision")
 od=str(operator_decision_digest or "").lower()
 if not DIGEST_RE.fullmatch(od):errors.append("invalid_operator_decision_digest")
 status={"approve":"execution_approved","reject":"execution_rejected","defer":"execution_deferred"}.get(decision,"blocked") if not errors else "blocked"
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":l.get("campaign_id",""),"work_item_id":l.get("work_item_id",""),"loop_digest":ld,"decision":decision,"operator_decision_digest":od,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"execution_started":False,"authority_granted":False}
 row["loop_execution_review_digest"]=_digest(row);return row

def create_loop_stage_result(*,loop:Mapping[str,Any],execution_review:Mapping[str,Any],stage:str,result_code:str,evidence_digest:str,observed_cost:Mapping[str,int])->dict[str,Any]:
 l=dict(loop);r=dict(execution_review);ld,lok=_verify(l,"loop_digest");rd,rok=_verify(r,"loop_execution_review_digest");errors=[]
 if not lok:errors.append("tampered_loop")
 if not rok:errors.append("tampered_execution_review")
 if r.get("loop_digest")!=ld:errors.append("review_loop_mismatch")
 if r.get("status")!="execution_approved" or r.get("decision")!="approve":errors.append("execution_not_approved")
 if stage not in EXECUTABLE_STAGES:errors.append("unsupported_stage")
 if result_code not in RESULTS:errors.append("unsupported_result_code")
 ev=str(evidence_digest or "").lower()
 if not DIGEST_RE.fullmatch(ev):errors.append("invalid_evidence_digest")
 costs=dict(observed_cost or {});allowed={"elapsed_seconds","disk_bytes","token_budget"}
 if set(costs)-allowed or any(not isinstance(v,int) or v<0 for v in costs.values()):errors.append("invalid_observed_cost")
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":l.get("campaign_id",""),"work_item_id":l.get("work_item_id",""),"loop_digest":ld,"loop_execution_review_digest":rd,"stage":stage,"result_code":result_code,"evidence_digest":ev,"observed_cost":costs,"status":"stage_result_recorded" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"production_source_modified":False,"sandbox_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1)
 row["loop_stage_result_digest"]=_digest(row);return row

def integrate_campaign_loop_results(*,loop:Mapping[str,Any],execution_review:Mapping[str,Any],stage_results:Sequence[Mapping[str,Any]],ledger:Mapping[str,Any],budget_receipt:Mapping[str,Any])->dict[str,Any]:
 l=dict(loop);r=dict(execution_review);rows=[dict(x) for x in stage_results];g=dict(ledger);b=dict(budget_receipt);errors=[]
 ld,lok=_verify(l,"loop_digest");rd,rok=_verify(r,"loop_execution_review_digest");gd,gok=_verify(g,"ledger_digest");bd,bok=_verify(b,"budget_receipt_digest")
 if not lok:errors.append("tampered_loop")
 if not rok:errors.append("tampered_execution_review")
 if not gok:errors.append("tampered_ledger")
 if not bok:errors.append("tampered_budget_receipt")
 if r.get("loop_digest")!=ld or r.get("status")!="execution_approved":errors.append("execution_review_mismatch")
 if not rows:errors.append("missing_stage_results")
 seen=set();total={"elapsed_seconds":0,"disk_bytes":0,"token_budget":0};terminal="passed"
 for row in rows:
  sd,sok=_verify(row,"loop_stage_result_digest")
  if not sok:errors.append("tampered_stage_result")
  stage=str(row.get("stage") or "")
  if stage in seen:errors.append("duplicate_stage_result")
  seen.add(stage)
  if stage not in EXECUTABLE_STAGES:errors.append("unsupported_stage")
  if row.get("loop_digest")!=ld or row.get("loop_execution_review_digest")!=rd:errors.append("stage_result_lineage_mismatch")
  if row.get("status")!="stage_result_recorded":errors.append("blocked_stage_result")
  rc=str(row.get("result_code") or "")
  if rc=="failed":terminal="failed"
  elif rc=="blocked" and terminal!="failed":terminal="blocked"
  for k,v in dict(row.get("observed_cost") or {}).items():total[k]=total.get(k,0)+int(v)
 wid=str(l.get("work_item_id") or "")
 if wid not in set(g.get("work_item_ids") or []):errors.append("unknown_work_item")
 prior=dict(b.get("observed") or b.get("consumed") or {});updated={k:int(prior.get(k,0) or 0)+int(total.get(k,0) or 0) for k in total}
 limits=dict(b.get("limits") or {});mapping={"elapsed_seconds":"max_elapsed_seconds","disk_bytes":"max_disk_bytes","token_budget":"max_token_budget"}
 exceeded=sorted(k for k,v in updated.items() if int(limits.get(mapping[k],2**63-1) or 0)<v)
 if exceeded:errors.append("budget_exceeded")
 new_state={"passed":"completed","failed":"failed","blocked":"blocked"}[terminal]
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":l.get("campaign_id",""),"work_item_id":wid,"loop_digest":ld,"loop_execution_review_digest":rd,"prior_ledger_digest":gd,"prior_budget_receipt_digest":bd,"stage_result_digests":[x.get("loop_stage_result_digest","") for x in rows],"result_code":terminal,"new_work_item_state":new_state,"observed_cost":total,"updated_consumption":updated,"exceeded_limits":exceeded,"status":"loop_result_integrated" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"ledger_updated":not errors,"budget_consumed":not errors,"automatic_continuation":False,"learning_applied":False,"production_source_modified":False,"sandbox_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"operator_review_required_for_next_action":True}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1,ledger_updated=False,budget_consumed=False)
 row["loop_result_receipt_digest"]=_digest(row);return row

def campaign_loop_result_public_summary(receipt:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":receipt.get("campaign_id",""),"work_item_id":receipt.get("work_item_id",""),"status":receipt.get("status",""),"result_code":receipt.get("result_code",""),"new_work_item_state":receipt.get("new_work_item_state",""),"error_count":receipt.get("error_count",0),"content_free":True,"automatic_continuation":False,"learning_applied":False,"authority_granted":False}
