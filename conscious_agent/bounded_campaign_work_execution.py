from __future__ import annotations
"""v1187.0-v1187.2 bounded campaign work-execution foundations.

Binds one exact lease-backed resumed session and one selected campaign work item
to a separate operator execution review. Only narrowly allowlisted, in-process,
read-only sandbox checks may run. No shell, provider, model, production-source
mutation, installation, promotion, certification, release, or autonomous
execution authority is provided.
"""
import hashlib, json, re
from pathlib import Path
from typing import Any, Mapping

CONTRACT_VERSION="v1187.2"; SCHEMA_VERSION="1"; MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$"); ID_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ALLOWLIST={"content_digest_match","python_compile"}

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row); d=str(u.pop(field,"")).lower(); return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES
def _safe_target(root:str|Path,target:str)->Path:
 base=Path(root).expanduser().resolve(); p=(base/target).resolve()
 if Path(target).is_absolute() or base not in p.parents or any(part in {"data","private","secrets","runtime"} for part in Path(target).parts):raise ValueError("unsafe_target")
 return p

def create_work_execution_contract(*,restart_reconciliation:Mapping[str,Any],materialization_receipt:Mapping[str,Any],selection:Mapping[str,Any],work_item_id:str,execution_code:str,target_relative_path:str,expected_target_digest:str,operator_contract_digest:str)->dict[str,Any]:
 errors=[]; rr=dict(restart_reconciliation); mr=dict(materialization_receipt); sel=dict(selection)
 rd,rok=_verify(rr,"restart_reconciliation_digest"); md,mok=_verify(mr,"resume_materialization_receipt_digest"); sd,sok=_verify(sel,"selection_digest")
 if not rok:errors.append("tampered_restart_reconciliation")
 if not mok:errors.append("tampered_materialization_receipt")
 if not sok:errors.append("tampered_selection")
 if rr.get("status")!="restored_execution_eligible_not_executing" or not rr.get("work_execution_eligible"):errors.append("session_not_execution_eligible")
 if mr.get("status")!="resumed_session_materialized_not_executing" or not mr.get("work_execution_eligible"):errors.append("materialization_not_execution_eligible")
 if rr.get("resumed_session_digest")!=mr.get("resumed_session_digest"):errors.append("session_materialization_mismatch")
 if not ID_RE.fullmatch(str(work_item_id or "")):errors.append("unsafe_work_item_id")
 selected=list(sel.get("selected_work_item_ids") or sel.get("work_item_ids") or [])
 if work_item_id not in selected:errors.append("work_item_not_selected")
 if execution_code not in ALLOWLIST:errors.append("unsupported_execution_code")
 if not target_relative_path or Path(target_relative_path).is_absolute() or ".." in Path(target_relative_path).parts:errors.append("unsafe_target")
 expected=str(expected_target_digest or "").lower(); op=str(operator_contract_digest or "").lower()
 if not DIGEST_RE.fullmatch(expected):errors.append("invalid_expected_target_digest")
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_contract_digest")
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":mr.get("campaign_id",""),"session_id":mr.get("session_id",""),"restart_reconciliation_digest":rd,"resume_materialization_receipt_digest":md,"selection_digest":sd,"work_item_id":work_item_id,"execution_code":execution_code,"target_relative_path":target_relative_path,"expected_target_digest":expected,"operator_contract_digest":op,"status":"execution_review_required" if not errors else "blocked","errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_executed":False,"automatic_execution":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1)
 row["work_execution_contract_digest"]=_digest(row); return row

def create_work_execution_review(*,contract:Mapping[str,Any],decision:str,operator_decision_digest:str)->dict[str,Any]:
 row=dict(contract); cd,cok=_verify(row,"work_execution_contract_digest"); errors=[]
 if not cok:errors.append("tampered_execution_contract")
 if row.get("status")!="execution_review_required":errors.append("contract_not_reviewable")
 if decision not in {"approve","reject","defer"}:errors.append("unsupported_decision")
 op=str(operator_decision_digest or "").lower()
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_decision_digest")
 status={"approve":"approved_not_executed","reject":"rejected","defer":"deferred"}.get(decision,"blocked") if not errors else "blocked"
 out={"contract_version":CONTRACT_VERSION,"work_execution_contract_digest":cd,"decision":decision,"operator_decision_digest":op,"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_executed":False,"automatic_execution":False,"authority_granted":False};out["work_execution_review_digest"]=_digest(out);return out

def execute_bounded_campaign_work(*,sandbox_root:str|Path,contract:Mapping[str,Any],review:Mapping[str,Any])->dict[str,Any]:
 c=dict(contract);r=dict(review);cd,cok=_verify(c,"work_execution_contract_digest");rd,rok=_verify(r,"work_execution_review_digest");errors=[];result_code="blocked"
 if not cok:errors.append("tampered_execution_contract")
 if not rok:errors.append("tampered_execution_review")
 if r.get("work_execution_contract_digest")!=cd:errors.append("review_contract_mismatch")
 if r.get("status")!="approved_not_executed" or r.get("decision")!="approve":errors.append("execution_not_approved")
 try:target=_safe_target(sandbox_root,str(c.get("target_relative_path") or ""))
 except ValueError as exc:errors.append(str(exc));target=Path(sandbox_root)
 before=""
 if not errors:
  try: data=target.read_bytes();before=hashlib.sha256(data).hexdigest()
  except OSError:errors.append("target_unreadable");data=b""
 if not errors and before!=c.get("expected_target_digest"):errors.append("target_drift")
 if not errors:
  if c.get("execution_code")=="content_digest_match":result_code="passed"
  elif c.get("execution_code")=="python_compile":
   try:compile(data.decode("utf-8"),str(target),"exec");result_code="passed"
   except (UnicodeDecodeError,SyntaxError):result_code="failed"
 out={"contract_version":CONTRACT_VERSION,"campaign_id":c.get("campaign_id",""),"session_id":c.get("session_id",""),"work_item_id":c.get("work_item_id",""),"work_execution_contract_digest":cd,"work_execution_review_digest":rd,"execution_code":c.get("execution_code",""),"target_digest":before,"status":"executed" if not errors else "blocked","result_code":result_code,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_executed":not errors,"automatic_execution":False,"production_source_modified":False,"sandbox_modified":False,"provider_contacted":False,"model_contacted":False,"authority_granted":False,"release_authorized":False};out["work_execution_receipt_digest"]=_digest(out);return out

def work_execution_public_summary(contract:Mapping[str,Any],review:Mapping[str,Any],receipt:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":contract.get("campaign_id",""),"session_id":contract.get("session_id",""),"work_item_id":contract.get("work_item_id",""),"execution_code":contract.get("execution_code",""),"review_status":review.get("status",""),"execution_status":receipt.get("status",""),"result_code":receipt.get("result_code",""),"content_free":True,"automatic_execution":False,"production_source_modified":False,"sandbox_modified":False,"authority_granted":False}
