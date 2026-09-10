from __future__ import annotations
"""v1186.6-v1186.8 durable resumed-session materialization and handoff.

Consumes one exact approved v1186.5 resume eligibility receipt, acquires a
bounded external-runtime lease, and materializes one content-free resumed
session handoff. It never executes campaign work or mutates production source.
"""
import hashlib,json,os,re,time
from pathlib import Path
from typing import Any,Mapping

CONTRACT_VERSION="v1186.8"; SCHEMA_VERSION="1"; MAX_BYTES=524_288
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$"); ID_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES
def _safe_root(root:str|Path)->Path:return Path(root).expanduser().resolve()
def _campaign_dir(root:str|Path,campaign_id:str)->Path:
 if not ID_RE.fullmatch(str(campaign_id or "")):raise ValueError("unsafe_campaign_id")
 base=_safe_root(root); path=(base/"persistent_campaigns"/campaign_id).resolve()
 if base not in path.parents:raise ValueError("unsafe_campaign_path")
 return path

def create_resume_materialization_contract(*,reconciliation:Mapping[str,Any],eligibility_review:Mapping[str,Any],session_id:str,session_generation:int,operator_materialization_digest:str,lease_ttl_seconds:int=300)->dict[str,Any]:
 errors=[]; rec=dict(reconciliation); review=dict(eligibility_review)
 rd,rok=_verify(rec,"resume_reconciliation_digest"); ed,eok=_verify(review,"resume_eligibility_review_digest")
 if not rok:errors.append("tampered_reconciliation")
 if not eok:errors.append("tampered_eligibility_review")
 if review.get("resume_reconciliation_digest")!=rd:errors.append("eligibility_reconciliation_mismatch")
 if review.get("status")!="eligible_not_resumed" or not review.get("resume_eligible"):errors.append("resume_not_eligible")
 campaign_id=str(rec.get("campaign_id") or "")
 if not ID_RE.fullmatch(campaign_id):errors.append("unsafe_campaign_id")
 if not ID_RE.fullmatch(str(session_id or "")):errors.append("unsafe_session_id")
 try:generation=int(session_generation)
 except (TypeError,ValueError):generation=0
 if generation<1:errors.append("invalid_session_generation")
 try:ttl=int(lease_ttl_seconds)
 except (TypeError,ValueError):ttl=0
 if ttl<30 or ttl>3600:errors.append("invalid_lease_ttl")
 op=str(operator_materialization_digest or "").lower()
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_materialization_digest")
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":campaign_id,"session_id":str(session_id or ""),"session_generation":generation,"resume_reconciliation_digest":rd,"resume_eligibility_review_digest":ed,"restored_record_digest":str(rec.get("restored_record_digest") or ""),"storage_generation":int(rec.get("storage_generation") or 0),"current_lineage_digests":dict(rec.get("current_lineage_digests") or {}),"operator_materialization_digest":op,"lease_ttl_seconds":ttl,"status":"materialization_ready" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_resumed":False,"work_executed":False,"automatic_resume":False,"execution_authorized":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1)
 row["resume_materialization_contract_digest"]=_digest(row);return row

def acquire_resume_lease(*,runtime_root:str|Path,contract:Mapping[str,Any],lease_owner_digest:str,now_epoch:int|None=None,stale_takeover_digest:str="")->dict[str,Any]:
 errors=[]; contract=dict(contract); cd,cok=_verify(contract,"resume_materialization_contract_digest")
 if not cok:errors.append("tampered_materialization_contract")
 if contract.get("status")!="materialization_ready":errors.append("materialization_not_ready")
 owner=str(lease_owner_digest or "").lower()
 if not DIGEST_RE.fullmatch(owner):errors.append("invalid_lease_owner_digest")
 takeover=str(stale_takeover_digest or "").lower()
 if takeover and not DIGEST_RE.fullmatch(takeover):errors.append("invalid_stale_takeover_digest")
 now=int(time.time() if now_epoch is None else now_epoch); lease_path=None; prior=None
 if not errors:
  try:
   directory=_campaign_dir(runtime_root,str(contract.get("campaign_id") or ""));directory.mkdir(parents=True,exist_ok=True);lease_path=directory/"resume.lease.json"
   lease={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":contract["campaign_id"],"session_id":contract["session_id"],"session_generation":contract["session_generation"],"resume_materialization_contract_digest":cd,"lease_owner_digest":owner,"acquired_epoch":now,"expires_epoch":now+int(contract["lease_ttl_seconds"]),"released":False,"content_free":True}
   lease["lease_digest"]=_digest(lease)
   try:
    fd=os.open(str(lease_path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   except FileExistsError:
    try:prior=json.loads(lease_path.read_text(encoding="utf-8"))
    except Exception:errors.append("malformed_existing_lease");prior={}
    if prior:
     pd,pok=_verify(prior,"lease_digest")
     if not pok:errors.append("tampered_existing_lease")
     elif not prior.get("released") and int(prior.get("expires_epoch") or 0)>now:errors.append("active_lease_exists")
     elif not takeover:errors.append("stale_takeover_not_authorized")
     else:
      temp=lease_path.with_suffix(".tmp");temp.write_text(json.dumps(lease,sort_keys=True,separators=(",",":")),encoding="utf-8");os.replace(temp,lease_path);fd=None
    else:fd=None
   if 'fd' in locals() and fd is not None:
    with os.fdopen(fd,"w",encoding="utf-8") as handle:json.dump(lease,handle,sort_keys=True,separators=(",",":"));handle.flush();os.fsync(handle.fileno())
  except (OSError,ValueError) as exc:errors.append(str(exc) or "lease_io_error")
 status="lease_acquired" if not errors else "blocked"
 result={"contract_version":CONTRACT_VERSION,"campaign_id":contract.get("campaign_id",""),"session_id":contract.get("session_id",""),"resume_materialization_contract_digest":cd,"lease_owner_digest":owner,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"lease_digest":lease.get("lease_digest","") if status=="lease_acquired" else "","expires_epoch":lease.get("expires_epoch",0) if status=="lease_acquired" else 0,"content_free":True,"work_executed":False,"automatic_resume":False,"authority_granted":False}
 result["lease_receipt_digest"]=_digest(result);return result

def materialize_resumed_session(*,runtime_root:str|Path,contract:Mapping[str,Any],lease_receipt:Mapping[str,Any])->dict[str,Any]:
 errors=[]; contract=dict(contract); receipt=dict(lease_receipt);cd,cok=_verify(contract,"resume_materialization_contract_digest");lr,lok=_verify(receipt,"lease_receipt_digest")
 if not cok:errors.append("tampered_materialization_contract")
 if not lok:errors.append("tampered_lease_receipt")
 if receipt.get("resume_materialization_contract_digest")!=cd:errors.append("lease_contract_mismatch")
 if receipt.get("status")!="lease_acquired":errors.append("lease_not_acquired")
 handoff={}
 if not errors:
  try:
   directory=_campaign_dir(runtime_root,str(contract.get("campaign_id") or ""));lease_path=directory/"resume.lease.json";lease=json.loads(lease_path.read_text(encoding="utf-8"));ld,lok2=_verify(lease,"lease_digest")
   if not lok2 or ld!=receipt.get("lease_digest"):errors.append("lease_state_mismatch")
   elif lease.get("released"):errors.append("lease_released")
   else:
    handoff={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":contract["campaign_id"],"session_id":contract["session_id"],"session_generation":contract["session_generation"],"resume_materialization_contract_digest":cd,"lease_digest":ld,"restored_record_digest":contract["restored_record_digest"],"current_lineage_digests":contract["current_lineage_digests"],"status":"resumed_session_materialized_not_executing","content_free":True,"work_execution_eligible":True,"work_executed":False,"automatic_execution":False,"authority_granted":False};handoff["resumed_session_digest"]=_digest(handoff)
    target=directory/"resumed_session.json";tmp=target.with_suffix(".tmp");tmp.write_text(json.dumps(handoff,sort_keys=True,separators=(",",":")),encoding="utf-8");os.replace(tmp,target)
  except (OSError,ValueError,json.JSONDecodeError):errors.append("materialization_io_error")
 status=handoff.get("status","blocked") if not errors else "blocked"
 result={"contract_version":CONTRACT_VERSION,"campaign_id":contract.get("campaign_id",""),"session_id":contract.get("session_id",""),"resume_materialization_contract_digest":cd,"lease_receipt_digest":lr,"resumed_session_digest":handoff.get("resumed_session_digest",""),"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_execution_eligible":status=="resumed_session_materialized_not_executing","work_executed":False,"automatic_execution":False,"provider_contacted":False,"model_contacted":False,"production_source_modified":False,"authority_granted":False}
 result["resume_materialization_receipt_digest"]=_digest(result);return result

def reconcile_materialized_session(*,runtime_root:str|Path,campaign_id:str,expected_session_digest:str,expected_lease_digest:str)->dict[str,Any]:
 errors=[];session={};lease={}
 if not DIGEST_RE.fullmatch(str(expected_session_digest or "").lower()):errors.append("invalid_expected_session_digest")
 if not DIGEST_RE.fullmatch(str(expected_lease_digest or "").lower()):errors.append("invalid_expected_lease_digest")
 if not errors:
  try:
   directory=_campaign_dir(runtime_root,campaign_id);session=json.loads((directory/"resumed_session.json").read_text(encoding="utf-8"));lease=json.loads((directory/"resume.lease.json").read_text(encoding="utf-8"));sd,sok=_verify(session,"resumed_session_digest");ld,lok=_verify(lease,"lease_digest")
   if not sok or sd!=expected_session_digest:errors.append("session_digest_mismatch")
   if not lok or ld!=expected_lease_digest:errors.append("lease_digest_mismatch")
   if session.get("lease_digest")!=ld:errors.append("session_lease_mismatch")
  except (OSError,ValueError,json.JSONDecodeError):errors.append("missing_or_malformed_runtime_state")
 status="restored_execution_eligible_not_executing" if not errors else "blocked"
 row={"contract_version":CONTRACT_VERSION,"campaign_id":campaign_id,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"resumed_session_digest":str(expected_session_digest or ""),"lease_digest":str(expected_lease_digest or ""),"content_free":True,"work_execution_eligible":status.startswith("restored_"),"work_executed":False,"automatic_execution":False,"authority_granted":False};row["restart_reconciliation_digest"]=_digest(row);return row

def release_resume_lease(*,runtime_root:str|Path,campaign_id:str,expected_lease_digest:str,operator_release_digest:str)->dict[str,Any]:
 errors=[];op=str(operator_release_digest or "").lower()
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_release_digest")
 try:
  directory=_campaign_dir(runtime_root,campaign_id);path=directory/"resume.lease.json";lease=json.loads(path.read_text(encoding="utf-8"));ld,lok=_verify(lease,"lease_digest")
  if not lok or ld!=expected_lease_digest:errors.append("lease_digest_mismatch")
  if lease.get("released"):errors.append("lease_already_released")
  if not errors:
   lease["released"]=True;lease["operator_release_digest"]=op;lease["lease_digest"]=_digest({k:v for k,v in lease.items() if k!="lease_digest"});tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(lease,sort_keys=True,separators=(",",":")),encoding="utf-8");os.replace(tmp,path)
 except (OSError,ValueError,json.JSONDecodeError):errors.append("lease_release_io_error")
 row={"contract_version":CONTRACT_VERSION,"campaign_id":campaign_id,"status":"lease_released" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_executed":False,"authority_granted":False};row["lease_release_receipt_digest"]=_digest(row);return row

def resume_materialization_public_summary(contract:Mapping[str,Any],receipt:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":contract.get("campaign_id",""),"session_id":contract.get("session_id",""),"contract_status":contract.get("status",""),"materialization_status":receipt.get("status",""),"work_execution_eligible":bool(receipt.get("work_execution_eligible")),"content_free":True,"work_executed":False,"automatic_execution":False,"authority_granted":False}
