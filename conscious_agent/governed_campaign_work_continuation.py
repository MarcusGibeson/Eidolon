from __future__ import annotations
"""v1187.6-v1187.8 governed campaign work continuation and failure handling.

Records operator-reviewed continuation choices, bounded follow-up selection, and one
atomic content-free campaign generation. It never retries or executes work.
"""
import hashlib, json, os, re, tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION="v1187.8"; SCHEMA_VERSION="1"; MAX_BYTES=262_144; MAX_ITEMS=32
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$"); ID_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ACTIONS={"completed":{"select_followup","pause_campaign","complete_campaign"},"failed":{"hold_failure","select_followup","pause_campaign","abandon_campaign"}}
DECISIONS={"approve","reject","defer"}

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_campaign_continuation_review(*,ledger_update_receipt:Mapping[str,Any],requested_action:str,decision:str,operator_decision_digest:str)->dict[str,Any]:
 r=dict(ledger_update_receipt);rd,ok=_verify(r,"ledger_update_receipt_digest");errors=[]
 if not ok:errors.append("tampered_ledger_update_receipt")
 if r.get("status")!="ledger_update_recorded" or not r.get("ledger_updated"):errors.append("ledger_result_not_recorded")
 state=str(r.get("new_work_item_state") or "");action=str(requested_action or "")
 if action not in ACTIONS.get(state,set()):errors.append("unsupported_continuation_action")
 if decision not in DECISIONS:errors.append("unsupported_decision")
 op=str(operator_decision_digest or "").lower()
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_decision_digest")
 status=("continuation_approved" if decision=="approve" else "continuation_rejected" if decision=="reject" else "continuation_deferred") if not errors else "blocked"
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":r.get("campaign_id",""),"session_id":r.get("session_id",""),"completed_work_item_id":r.get("work_item_id",""),"ledger_update_receipt_digest":rd,"result_state":state,"requested_action":action,"decision":decision,"operator_decision_digest":op,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"automatic_retry":False,"automatic_reselection":False,"work_executed":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1)
 row["continuation_review_digest"]=_digest(row);return row

def create_followup_work_selection(*,ledger:Mapping[str,Any],ledger_update_receipt:Mapping[str,Any],continuation_review:Mapping[str,Any],candidate_work_item_ids:Sequence[str],max_items:int=1)->dict[str,Any]:
 l=dict(ledger);u=dict(ledger_update_receipt);r=dict(continuation_review);errors=[]
 ld,lok=_verify(l,"ledger_digest");ud,uok=_verify(u,"ledger_update_receipt_digest");rd,rok=_verify(r,"continuation_review_digest")
 if not lok:errors.append("tampered_ledger")
 if not uok:errors.append("tampered_ledger_update_receipt")
 if not rok:errors.append("tampered_continuation_review")
 if r.get("ledger_update_receipt_digest")!=ud:errors.append("review_result_mismatch")
 if r.get("status")!="continuation_approved" or r.get("requested_action")!="select_followup":errors.append("followup_not_approved")
 ids=[str(x or "").strip() for x in candidate_work_item_ids]
 if not ids or len(ids)>MAX_ITEMS or len(set(ids))!=len(ids):errors.append("invalid_candidate_work_items")
 if not isinstance(max_items,int) or max_items<1 or max_items>MAX_ITEMS:errors.append("invalid_selection_limit")
 known=set(l.get("work_item_ids") or [])
 if any(x not in known for x in ids):errors.append("unknown_work_item")
 if str(u.get("work_item_id") or "") in ids:errors.append("terminal_work_item_reselected")
 selected=ids[:max_items] if not errors else []
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":u.get("campaign_id",""),"session_id":u.get("session_id",""),"prior_ledger_digest":ld,"ledger_update_receipt_digest":ud,"continuation_review_digest":rd,"candidate_work_item_ids":ids,"selected_work_item_ids":selected,"selected_count":len(selected),"status":"followup_selection_ready" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"operator_review_required_before_execution":True,"work_executed":False,"automatic_retry":False,"authority_granted":False}
 row["followup_selection_digest"]=_digest(row);return row

def persist_continuation_generation(*,runtime_root:str|Path,prior_storage_record:Mapping[str,Any],ledger_update_receipt:Mapping[str,Any],continuation_review:Mapping[str,Any],followup_selection:Mapping[str,Any]|None,operator_storage_digest:str)->dict[str,Any]:
 p=dict(prior_storage_record);u=dict(ledger_update_receipt);r=dict(continuation_review);s=dict(followup_selection or {});errors=[]
 pd,pok=_verify(p,"storage_record_digest");ud,uok=_verify(u,"ledger_update_receipt_digest");rd,rok=_verify(r,"continuation_review_digest")
 if not pok:errors.append("tampered_prior_storage_record")
 if not uok:errors.append("tampered_ledger_update_receipt")
 if not rok:errors.append("tampered_continuation_review")
 sd=""
 if s:
  sd,sok=_verify(s,"followup_selection_digest")
  if not sok:errors.append("tampered_followup_selection")
 if r.get("ledger_update_receipt_digest")!=ud:errors.append("continuation_lineage_mismatch")
 if r.get("status")!="continuation_approved":errors.append("continuation_not_approved")
 if r.get("requested_action")=="select_followup" and (not s or s.get("status")!="followup_selection_ready"):errors.append("missing_followup_selection")
 cid=str(u.get("campaign_id") or "")
 if not ID_RE.fullmatch(cid):errors.append("unsafe_campaign_id")
 if p.get("campaign_id")!=cid:errors.append("campaign_id_mismatch")
 op=str(operator_storage_digest or "").lower()
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_storage_digest")
 generation=int(p.get("storage_generation") or 0)+1
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":cid,"storage_generation":generation,"prior_record_digest":pd,"ledger_update_receipt_digest":ud,"continuation_review_digest":rd,"followup_selection_digest":sd,"operator_storage_digest":op,"campaign_state":"paused" if r.get("requested_action") in {"pause_campaign","hold_failure"} else "completed" if r.get("requested_action")=="complete_campaign" else "abandoned" if r.get("requested_action")=="abandon_campaign" else "active","selected_work_item_ids":list(s.get("selected_work_item_ids") or []),"status":"ready_for_continuation_storage" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"automatic_retry":False,"automatic_resume":False,"work_executed":False,"authority_granted":False}
 row["storage_record_digest"]=_digest(row)
 if errors:return {**row,"runtime_written":False}
 root=Path(runtime_root).expanduser().resolve();path=root/"campaigns"/cid/"campaign_state.json";path.parent.mkdir(parents=True,exist_ok=True)
 lock=path.parent/".continuation.lock"
 try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 except FileExistsError:return {**row,"status":"blocked","errors":["concurrent_writer"],"error_count":1,"runtime_written":False}
 try:
  os.close(fd)
  if path.exists():
   try:current=json.loads(path.read_text(encoding="utf-8"))
   except Exception:return {**row,"status":"blocked","errors":["malformed_existing_record"],"error_count":1,"runtime_written":False}
   if str(current.get("storage_record_digest") or "")!=pd:return {**row,"status":"blocked","errors":["stale_storage_generation"],"error_count":1,"runtime_written":False}
  payload=json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
  fd,tmp=tempfile.mkstemp(prefix=".campaign_state.",suffix=".tmp",dir=str(path.parent))
  try:
   with os.fdopen(fd,"wb") as h:h.write(payload);h.flush();os.fsync(h.fileno())
   os.replace(tmp,path)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  return {**row,"status":"continuation_stored","runtime_written":True,"relative_runtime_path":f"campaigns/{cid}/campaign_state.json"}
 finally:
  try:lock.unlink()
  except FileNotFoundError:pass

def continuation_public_summary(review:Mapping[str,Any],selection:Mapping[str,Any]|None,stored:Mapping[str,Any]|None)->dict[str,Any]:
 s=dict(selection or {});p=dict(stored or {})
 return {"contract_version":CONTRACT_VERSION,"campaign_id":review.get("campaign_id",""),"review_status":review.get("status",""),"requested_action":review.get("requested_action",""),"selection_status":s.get("status",""),"selected_count":s.get("selected_count",0),"storage_status":p.get("status",""),"content_free":True,"automatic_retry":False,"automatic_resume":False,"work_executed":False,"authority_granted":False}
