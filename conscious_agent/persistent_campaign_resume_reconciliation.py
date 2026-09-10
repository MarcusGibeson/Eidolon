from __future__ import annotations
"""v1186.3-v1186.5 durable campaign resume review and reconciliation.

Consumes exact v1186.2 restoration evidence and produces a bounded, content-free
resume eligibility decision. It never resumes or executes campaign work.
"""
import hashlib,json,re
from typing import Any,Mapping
CONTRACT_VERSION="v1186.5"; SCHEMA_VERSION="1"; MAX_BYTES=524_288
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$"); DECISIONS=frozenset({"approve","reject","defer"})

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _verify(row:Mapping[str,Any],field:str)->tuple[str,bool]:
 u=dict(row);d=str(u.pop(field,"")).lower();return d,bool(DIGEST_RE.fullmatch(d) and d==_digest(u))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_resume_reconciliation(*,restoration:Mapping[str,Any],restoration_review:Mapping[str,Any],current_charter_digest:str,current_review_digest:str,current_ledger_digest:str,current_snapshot_digest:str,current_selection_digest:str="",current_budget_receipt_digest:str="",current_stale_assessment_digest:str="",current_recovery_receipt_digest:str="")->dict[str,Any]:
 errors=[]; restoration=dict(restoration); review=dict(restoration_review)
 rd,rok=_verify(restoration,"restoration_digest"); rvd,rvok=_verify(review,"restoration_review_digest")
 if not rok:errors.append("tampered_restoration")
 if not rvok:errors.append("tampered_restoration_review")
 if review.get("restoration_digest")!=rd:errors.append("restoration_review_mismatch")
 if review.get("status")!="approved_not_resumed":errors.append("restoration_not_approved")
 if restoration.get("status") not in {"restoration_review_required","reconciliation_required"}:errors.append("restoration_not_reconcilable")
 supplied={"charter":current_charter_digest,"review":current_review_digest,"ledger":current_ledger_digest,"snapshot":current_snapshot_digest,"selection":current_selection_digest,"budget_receipt":current_budget_receipt_digest,"stale_assessment":current_stale_assessment_digest,"recovery_receipt":current_recovery_receipt_digest}
 for name,d in supplied.items():
  if d and not DIGEST_RE.fullmatch(str(d).lower()):errors.append(f"invalid_{name}_digest")
 required=("charter","review","ledger","snapshot")
 for name in required:
  if not supplied[name]:errors.append(f"missing_{name}_digest")
 source_drift=bool(restoration.get("source_drift")); lineage_changed=False
 stored=str(restoration.get("restored_record_digest") or "")
 if not DIGEST_RE.fullmatch(stored):errors.append("invalid_restored_record_digest")
 status="blocked"
 if not errors: status="operator_reconciliation_required" if source_drift else "resume_review_required"
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":restoration.get("campaign_id",""),"restoration_digest":rd,"restoration_review_digest":rvd,"restored_record_digest":stored,"storage_generation":int(restoration.get("storage_generation") or 0),"source_drift":source_drift,"lineage_changed":lineage_changed,"current_lineage_digests":{k:str(v).lower() for k,v in supplied.items()},"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"work_resumed":False,"automatic_resume":False,"execution_authorized":False,"authority_granted":False}
 if not _bounded(row):row.update(status="blocked",errors=["oversized_contract"],error_count=1)
 row["resume_reconciliation_digest"]=_digest(row);return row

def create_resume_eligibility_review(*,reconciliation:Mapping[str,Any],decision:str,operator_decision_digest:str,acknowledge_source_drift:bool=False)->dict[str,Any]:
 errors=[]; rec=dict(reconciliation); dg,ok=_verify(rec,"resume_reconciliation_digest")
 if not ok:errors.append("tampered_reconciliation")
 decision=str(decision or "")
 if decision not in DECISIONS:errors.append("unsupported_decision")
 if rec.get("status") not in {"resume_review_required","operator_reconciliation_required"}:errors.append("reconciliation_not_reviewable")
 if rec.get("source_drift") and decision=="approve" and not acknowledge_source_drift:errors.append("source_drift_not_acknowledged")
 op=str(operator_decision_digest or "").lower()
 if not DIGEST_RE.fullmatch(op):errors.append("invalid_operator_decision_digest")
 status=("eligible_not_resumed" if decision=="approve" else "rejected" if decision=="reject" else "deferred") if not errors else "blocked"
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"campaign_id":rec.get("campaign_id",""),"resume_reconciliation_digest":dg,"decision":decision,"operator_decision_digest":op,"source_drift_acknowledged":bool(acknowledge_source_drift),"status":status,"errors":sorted(set(errors)),"error_count":len(set(errors)),"content_free":True,"resume_eligible":status=="eligible_not_resumed","work_resumed":False,"automatic_resume":False,"execution_authorized":False,"authority_granted":False}
 row["resume_eligibility_review_digest"]=_digest(row);return row

def resume_public_summary(reconciliation:Mapping[str,Any],review:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"campaign_id":reconciliation.get("campaign_id",""),"reconciliation_status":reconciliation.get("status",""),"source_drift":bool(reconciliation.get("source_drift")),"review_status":review.get("status",""),"resume_eligible":bool(review.get("resume_eligible")),"content_free":True,"work_resumed":False,"automatic_resume":False,"authority_granted":False}
