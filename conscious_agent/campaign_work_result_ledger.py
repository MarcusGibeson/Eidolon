from __future__ import annotations
"""v1187.3-v1187.5 governed campaign work results and ledger integration."""
import hashlib,json,re
from typing import Any,Mapping
CONTRACT_VERSION="v1187.5";SCHEMA_VERSION="1";MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
TERMINAL_RESULTS={"passed":"completed","failed":"failed"}
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_work_result_review(*,execution_receipt:Mapping[str,Any],decision:str,operator_decision_digest:str)->dict[str,Any]:
 e=dict(execution_receipt);ed,eok=_verify(e,"work_execution_receipt_digest");errors=[]
 if not eok:errors.append("tampered_execution_receipt")
 if e.get("status")!="executed" or not e.get("work_executed"):errors.append("execution_not_completed")
 if e.get("result_code") not in TERMINAL_RESULTS:errors.append("unsupported_result_code")
 if decision not in {"accept","reject","defer"}:errors.append("unsupported_decision")
 op=str(operator_decision_digest or "").lower()
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_decision_digest")
 status={"accept":"accepted_for_ledger","reject":"rejected_result","defer":"deferred_result"}.get(decision,"blocked") if not errors else "blocked"
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":e.get("campaign_id",""),"session_id":e.get("session_id",""),"work_item_id":e.get("work_item_id",""),"work_execution_receipt_digest":ed,"result_code":e.get("result_code",""),"decision":decision,"operator_decision_digest":op,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"ledger_updated":False,"budget_consumed":False,"retry_authorized":False,"authority_granted":False}
 row["work_result_review_digest"]=_digest(row);return row

def create_ledger_update_receipt(*,ledger:Mapping[str,Any],budget_receipt:Mapping[str,Any],execution_receipt:Mapping[str,Any],result_review:Mapping[str,Any],observed_cost:Mapping[str,int])->dict[str,Any]:
 l=dict(ledger);b=dict(budget_receipt);e=dict(execution_receipt);r=dict(result_review);errors=[]
 ld,lok=_verify(l,"ledger_digest");bd,bok=_verify(b,"budget_receipt_digest");ed,eok=_verify(e,"work_execution_receipt_digest");rd,rok=_verify(r,"work_result_review_digest")
 if not lok:errors.append("tampered_ledger")
 if not bok:errors.append("tampered_budget_receipt")
 if not eok:errors.append("tampered_execution_receipt")
 if not rok:errors.append("tampered_result_review")
 if r.get("work_execution_receipt_digest")!=ed:errors.append("review_execution_mismatch")
 if r.get("status")!="accepted_for_ledger" or r.get("decision")!="accept":errors.append("result_not_accepted")
 wid=str(e.get("work_item_id") or "")
 if wid not in set(l.get("work_item_ids") or []):errors.append("unknown_work_item")
 costs={str(k):v for k,v in dict(observed_cost or {}).items()}
 allowed={"work_items","elapsed_seconds","disk_bytes","token_budget"}
 if set(costs)-allowed or any(not isinstance(v,int) or v<0 for v in costs.values()):errors.append("invalid_observed_cost")
 if costs.get("work_items",0)!=1:errors.append("work_item_cost_must_equal_one")
 prior=dict(b.get("observed") or b.get("consumed") or {})
 updated={k:int(prior.get(k,0) or 0)+int(costs.get(k,0) or 0) for k in allowed}
 limits=dict(b.get("limits") or {})
 mapn={"work_items":"max_work_items","elapsed_seconds":"max_elapsed_seconds","disk_bytes":"max_disk_bytes","token_budget":"max_token_budget"}
 exceeded=sorted(k for k,v in updated.items() if int(limits.get(mapn[k],2**63-1) or 0)<v)
 if exceeded:errors.append("budget_exceeded")
 next_state=TERMINAL_RESULTS.get(str(e.get("result_code") or ""),"blocked")
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":e.get("campaign_id",""),"session_id":e.get("session_id",""),"work_item_id":wid,"prior_ledger_digest":ld,"prior_budget_receipt_digest":bd,"work_execution_receipt_digest":ed,"work_result_review_digest":rd,"prior_work_item_state":"queued","new_work_item_state":next_state,"observed_cost":costs,"updated_consumption":updated,"exceeded_limits":exceeded,"status":"ledger_update_recorded" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"ledger_updated":not errors,"budget_consumed":not errors,"work_retried":False,"automatic_reselection":False,"production_source_modified":False,"sandbox_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1,ledger_updated=False,budget_consumed=False)
 row["ledger_update_receipt_digest"]=_digest(row);return row

def work_result_ledger_public_summary(review:Mapping[str,Any],receipt:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":receipt.get("campaign_id",""),"session_id":receipt.get("session_id",""),"work_item_id":receipt.get("work_item_id",""),"review_status":review.get("status",""),"ledger_status":receipt.get("status",""),"new_work_item_state":receipt.get("new_work_item_state",""),"budget_limit_exceeded":bool(receipt.get("exceeded_limits")),"content_free":True,"work_retried":False,"automatic_reselection":False,"authority_granted":False}
