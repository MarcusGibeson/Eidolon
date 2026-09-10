from __future__ import annotations
"""v1185.6-v1185.8 bounded campaign reliability, budgets, stale work, outage and restart recovery.

Produces content-free evidence receipts only. It performs no work, durable resume,
provider/model action, source mutation, rollback, installation, promotion, or release.
"""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION="v1185.8";SCHEMA_VERSION="1";MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
RECOVERY_REASONS=frozenset({"interruption","provider_outage","process_restart","operator_pause"})
WORK_STATES=frozenset({"current","stale","completed","cancelled","blocked"})
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_campaign_budget_receipt(*,charter:Mapping[str,Any],snapshot:Mapping[str,Any],observed:Mapping[str,int])->dict[str,Any]:
 errors=[];charter=dict(charter);snapshot=dict(snapshot);observed=dict(observed or {})
 cd,cok=_verify(charter,"charter_digest");sd,sok=_verify(snapshot,"snapshot_digest")
 if not cok:errors.append("tampered_charter")
 if not sok:errors.append("tampered_snapshot")
 if snapshot.get("charter_digest")!=cd:errors.append("lineage_mismatch")
 allowed={"work_items","sessions","elapsed_seconds","disk_bytes","token_budget"}
 if set(observed)-allowed or any(not isinstance(v,int) or v<0 for v in observed.values()):errors.append("invalid_observed_budget")
 limits=dict(charter.get("limits") or {});mapping={"work_items":"max_work_items","sessions":"max_sessions","elapsed_seconds":"max_elapsed_seconds","disk_bytes":"max_disk_bytes","token_budget":"max_token_budget"}
 exceeded=sorted(k for k,v in observed.items() if k in mapping and int(limits.get(mapping[k],0) or 0)>0 and v>int(limits[mapping[k]]))
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":charter.get("campaign_id",""),"charter_digest":cd,"snapshot_digest":sd,"observed":observed,"exceeded_limits":exceeded,"status":"budget_within_limits" if not errors and not exceeded else ("budget_exhausted" if not errors else "blocked"),"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"budget_enforced":not errors,"work_executed":False,"source_modified":False,"authority_granted":False}
 if not _bounded(row):row.update(errors=["oversized_contract"],error_count=1,status="blocked")
 row["budget_receipt_digest"]=_digest(row);return row

def create_stale_work_assessment(*,snapshot:Mapping[str,Any],selection:Mapping[str,Any],current_source_digest:str,work_states:Mapping[str,str])->dict[str,Any]:
 errors=[];snapshot=dict(snapshot);selection=dict(selection);sd,sok=_verify(snapshot,"snapshot_digest");qd,qok=_verify(selection,"selection_digest")
 if not sok:errors.append("tampered_snapshot")
 if not qok:errors.append("tampered_selection")
 if selection.get("snapshot_digest")!=sd:errors.append("lineage_mismatch")
 if not DIGEST_RE.fullmatch(str(current_source_digest or "").lower()):errors.append("invalid_current_source_digest")
 states={str(k):str(v) for k,v in dict(work_states or {}).items()};selected=set(selection.get("selected_work_item_ids") or [])
 if set(states)!=selected or any(v not in WORK_STATES for v in states.values()):errors.append("invalid_work_states")
 stale=sorted(k for k,v in states.items() if v=="stale")
 source_drift=str(current_source_digest or "").lower()!=str(snapshot.get("source_baseline_digest") or "").lower()
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":snapshot.get("campaign_id",""),"snapshot_digest":sd,"selection_digest":qd,"current_source_digest":str(current_source_digest or "").lower(),"source_drift":source_drift,"stale_work_item_ids":stale,"status":"reconciliation_required" if not errors and (source_drift or stale) else ("work_current" if not errors else "blocked"),"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_executed":False,"automatic_reselection":False,"operator_review_required":True,"authority_granted":False}
 row["stale_assessment_digest"]=_digest(row);return row

def create_campaign_recovery_receipt(*,snapshot:Mapping[str,Any],budget_receipt:Mapping[str,Any],stale_assessment:Mapping[str,Any],reason:str,prior_runtime_digest:str,restarted_runtime_digest:str)->dict[str,Any]:
 errors=[];snapshot=dict(snapshot);budget_receipt=dict(budget_receipt);stale_assessment=dict(stale_assessment)
 sd,sok=_verify(snapshot,"snapshot_digest");bd,bok=_verify(budget_receipt,"budget_receipt_digest");ad,aok=_verify(stale_assessment,"stale_assessment_digest")
 for ok,name in ((sok,"snapshot"),(bok,"budget_receipt"),(aok,"stale_assessment")):
  if not ok:errors.append(f"tampered_{name}")
 if budget_receipt.get("snapshot_digest")!=sd or stale_assessment.get("snapshot_digest")!=sd:errors.append("lineage_mismatch")
 if reason not in RECOVERY_REASONS:errors.append("unsupported_recovery_reason")
 for name,value in (("prior_runtime_digest",prior_runtime_digest),("restarted_runtime_digest",restarted_runtime_digest)):
  if not DIGEST_RE.fullmatch(str(value or "").lower()):errors.append(f"invalid_{name}")
 if budget_receipt.get("status") in {"budget_exhausted","blocked"}:errors.append("budget_not_recoverable")
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":snapshot.get("campaign_id",""),"snapshot_digest":sd,"budget_receipt_digest":bd,"stale_assessment_digest":ad,"reason":str(reason or ""),"prior_runtime_digest":str(prior_runtime_digest or "").lower(),"restarted_runtime_digest":str(restarted_runtime_digest or "").lower(),"status":"recovery_review_required" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"durable_resume_performed":False,"work_executed":False,"provider_contacted":False,"model_contacted":False,"operator_review_required":True,"authority_granted":False}
 row["recovery_receipt_digest"]=_digest(row);return row

def reliability_public_summary(budget:Mapping[str,Any],stale:Mapping[str,Any],recovery:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"budget_status":budget.get("status",""),"exceeded_limit_count":len(budget.get("exceeded_limits") or []),"stale_status":stale.get("status",""),"stale_work_count":len(stale.get("stale_work_item_ids") or []),"source_drift":bool(stale.get("source_drift")),"recovery_status":recovery.get("status",""),"recovery_reason":recovery.get("reason",""),"content_free":True,"work_executed":False,"durable_resume_performed":False,"operator_review_required":True,"authority_granted":False}
