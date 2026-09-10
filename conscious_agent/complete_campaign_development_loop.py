from __future__ import annotations
"""v1188.0-v1188.2 complete campaign development-loop foundations.

Joins one operator-approved persistent campaign and one exact selected work item to
an ordered, content-free inspect-through-learn development lineage. This module
validates evidence only; it performs no stage, execution, repair, persistence, or
source mutation.
"""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION="v1188.2"; SCHEMA_VERSION="1"; MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
STAGES=("inspection","deficiency_review","specification","planning","approval","implementation","testing","diagnosis_repair","presentation","learning")
TERMINAL=frozenset({"completed","accepted","rejected","deferred","failed","blocked"})

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row); d=str(u.pop(field,"")).lower(); return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_campaign_development_stage(*,campaign_id:str,work_item_id:str,stage:str,status:str,artifact_digest:str,previous_stage_digest:str="",operator_review_digest:str="")->dict[str,Any]:
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":str(campaign_id),"work_item_id":str(work_item_id),"stage":str(stage),"status":str(status),"artifact_digest":str(artifact_digest).lower(),"previous_stage_digest":str(previous_stage_digest).lower(),"operator_review_digest":str(operator_review_digest).lower(),"content_free":True,"private_content_included":False,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False}
 row["stage_receipt_digest"]=_digest(row); return row

def integrate_complete_campaign_development_loop(*,campaign_charter:Mapping[str,Any],campaign_review:Mapping[str,Any],session_snapshot:Mapping[str,Any],work_selection:Mapping[str,Any],stages:Sequence[Mapping[str,Any]])->dict[str,Any]:
 c=dict(campaign_charter); r=dict(campaign_review); s=dict(session_snapshot); w=dict(work_selection); rows=[dict(x) for x in stages]; errors=[]
 cd,cok=_verify(c,"charter_digest"); rd,rok=_verify(r,"review_digest"); sd,sok=_verify(s,"session_snapshot_digest"); wd,wok=_verify(w,"selection_digest")
 if not cok:errors.append("tampered_campaign_charter")
 if not rok:errors.append("tampered_campaign_review")
 if not sok:errors.append("tampered_session_snapshot")
 if not wok:errors.append("tampered_work_selection")
 cid=str(c.get("campaign_id") or ""); selected=list(w.get("selected_work_item_ids") or []); wid=selected[0] if len(selected)==1 else ""
 if r.get("campaign_id")!=cid or s.get("campaign_id")!=cid or w.get("campaign_id")!=cid:errors.append("campaign_lineage_mismatch")
 if r.get("status") not in {"campaign_approved","approved_not_started"} and r.get("decision")!="approve":errors.append("campaign_not_approved")
 if s.get("campaign_state") not in {"active","ready"}:errors.append("campaign_session_not_active")
 if w.get("status") not in {"selected_not_executed","selection_approved"}:errors.append("work_not_selected")
 if len(selected)!=1:errors.append("exactly_one_work_item_required")
 if len(rows)!=len(STAGES):errors.append("incomplete_stage_lineage")
 if not _bounded([c,r,s,w,rows]):errors.append("oversized_contract")
 previous=""; seen=set()
 for i,row in enumerate(rows):
  digest,ok=_verify(row,"stage_receipt_digest")
  if not ok:errors.append("tampered_stage_receipt")
  stage=str(row.get("stage") or "")
  if i>=len(STAGES) or stage!=STAGES[i]:errors.append("stage_order_mismatch")
  if stage in seen:errors.append("duplicate_stage")
  seen.add(stage)
  if row.get("campaign_id")!=cid or row.get("work_item_id")!=wid:errors.append("stage_campaign_or_work_mismatch")
  if i==0 and row.get("previous_stage_digest"):errors.append("unexpected_initial_stage_link")
  if i>0 and row.get("previous_stage_digest")!=previous:errors.append("stage_link_mismatch")
  if not DIGEST_RE.fullmatch(str(row.get("artifact_digest") or "")):errors.append("invalid_artifact_digest")
  if stage=="approval" and not DIGEST_RE.fullmatch(str(row.get("operator_review_digest") or "")):errors.append("missing_stage_approval")
  if row.get("content_free") is not True or row.get("private_content_included") is not False:errors.append("privacy_contract_violation")
  if any(row.get(k) is not False for k in ("production_source_modified","sandbox_modified","execution_invoked","provider_contacted","model_contacted","authority_granted")):errors.append("authority_or_execution_expansion")
  status=str(row.get("status") or "")
  if status not in TERMINAL:errors.append("unsupported_stage_status")
  if status in {"rejected","deferred","failed","blocked"} and i!=len(rows)-1:errors.append("continued_after_terminal_stage")
  previous=digest
 errors=sorted(set(errors)); complete=len(rows)==len(STAGES) and not errors and all(x.get("status") in {"completed","accepted"} for x in rows)
 out={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"loop_id":"complete-campaign-development-loop:v1188.2","campaign_id":cid,"work_item_id":wid,"campaign_charter_digest":cd,"campaign_review_digest":rd,"session_snapshot_digest":sd,"work_selection_digest":wd,"stage_receipt_digests":[x.get("stage_receipt_digest","") for x in rows],"terminal_stage_digest":previous,"stage_count":len(rows),"complete_loop":complete,"status":"complete_review_required" if complete else "blocked" if errors else "in_progress_review_required","errors":errors,"error_count":len(errors),"content_free":True,"private_content_included":False,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"provider_contacted":False,"model_contacted":False,"automatic_continuation":False,"learning_applied":False,"authority_granted":False,"operator_review_required_for_next_action":True}
 out["loop_digest"]=_digest(out); return out

def complete_campaign_development_loop_public_summary(loop:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":loop.get("campaign_id",""),"work_item_id":loop.get("work_item_id",""),"status":loop.get("status",""),"stage_count":loop.get("stage_count",0),"complete_loop":loop.get("complete_loop") is True,"error_count":loop.get("error_count",0),"loop_digest":loop.get("loop_digest",""),"content_free":True,"learning_applied":False,"authority_granted":False}
