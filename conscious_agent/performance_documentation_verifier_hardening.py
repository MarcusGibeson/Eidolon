from __future__ import annotations
"""Content-free v1198.8 performance, documentation, and verifier reconciliation evidence."""
import hashlib, json
from typing import Any, Mapping, Sequence
CONTRACT_VERSION="v1198.8"
EVIDENCE_CLASSES=("startup_budget","profile_budget","documentation_consistency","verifier_registration","fixture_overlap","freeze_compliance","ownership_consistency","historical_truth")
OUTCOMES=("pass","blocked","deferred","inherited_debt")
PRIVATE_TOKENS=("prompt","conversation_text","memory_content","secret","password","raw_source","patch","stdout","stderr","provider_payload","private_reasoning","credential","api_key")
FORBIDDEN=("profiling_executed","verifier_executed","files_moved","files_deleted","modules_merged","imports_rewritten","documentation_rewritten","fixture_deleted","verifier_retired","approval_consumed","provider_contacted","model_contacted","process_started","thread_started","runtime_mutated","source_modified","installation_performed","promotion_performed","certification_performed","publication_performed","release_performed","automatic_continuation")

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _is_digest(v:object)->bool:
 t=str(v or "");return len(t)==64 and all(c in "0123456789abcdef" for c in t)
def _private(v:object,p=""):
 out=[]
 if isinstance(v,Mapping):
  for k,x in v.items():
   q=f"{p}.{k}" if p else str(k)
   if any(t in str(k).lower() for t in PRIVATE_TOKENS):out.append(q)
   out+=_private(x,q)
 elif isinstance(v,(list,tuple)):
  for i,x in enumerate(v):out+=_private(x,f"{p}[{i}]")
 return sorted(set(out))

def create_hardening_plan(*,plan_id:str,snapshot_digest:str,context_digest:str,architecture_digest:str,documentation_digest:str,verifier_registry_digest:str,freeze_review_digest:str,startup_budget_ms:int=30000,quick_budget_ms:int=420000,full_budget_ms:int=1800000,purpose_code:str="v1198_hardening"):
 row={"contract_version":CONTRACT_VERSION,"plan_id":plan_id,"snapshot_digest":snapshot_digest,"context_digest":context_digest,"architecture_digest":architecture_digest,"documentation_digest":documentation_digest,"verifier_registry_digest":verifier_registry_digest,"freeze_review_digest":freeze_review_digest,"startup_budget_ms":startup_budget_ms,"quick_budget_ms":quick_budget_ms,"full_budget_ms":full_budget_ms,"purpose_code":purpose_code,"content_free":True,"read_only":True,"feature_freeze_active":True,"global_profile_pass_claimed":False,"authority_state":"separate_not_granted"}
 row.update({k:False for k in FORBIDDEN});row["plan_digest"]=_digest(row);return row

def create_evidence(*,evidence_id:str,evidence_class:str,outcome:str,owner:str,sequence:int,observed_ms:int,budget_ms:int,artifact_digest:str,receipt_digest:str,prior_receipt_digest:str="",debt_id:str=""):
 row={"contract_version":CONTRACT_VERSION,"evidence_id":evidence_id,"evidence_class":evidence_class,"outcome":outcome,"owner":owner,"sequence":sequence,"observed_ms":observed_ms,"budget_ms":budget_ms,"artifact_digest":artifact_digest,"receipt_digest":receipt_digest,"prior_receipt_digest":prior_receipt_digest,"debt_id":debt_id,"content_free":True,"read_only":True,"historical_truth_preserved":True,"feature_freeze_active":True,"global_profile_pass_claimed":False,"authority_state":"separate_not_granted"}
 row.update({k:False for k in FORBIDDEN});row["evidence_digest"]=_digest(row);return row

def assess_hardening(plan:Mapping[str,Any],evidence:Sequence[Mapping[str,Any]],*,current_snapshot_digest:str,current_context_digest:str,current_architecture_digest:str,current_documentation_digest:str,current_verifier_registry_digest:str,current_freeze_review_digest:str):
 p=dict(plan);rows=[dict(x) for x in evidence];errors=[]
 errors += [f"private_field:{x}" for x in _private({"plan":p,"evidence":rows})]
 u=dict(p);s=u.pop("plan_digest",None)
 if s!=_digest(u):errors.append("plan_tamper")
 if p.get("contract_version")!=CONTRACT_VERSION:errors.append("unsupported_plan_contract")
 for f,c in (("snapshot_digest",current_snapshot_digest),("context_digest",current_context_digest),("architecture_digest",current_architecture_digest),("documentation_digest",current_documentation_digest),("verifier_registry_digest",current_verifier_registry_digest),("freeze_review_digest",current_freeze_review_digest)):
  if not _is_digest(p.get(f)):errors.append(f"malformed_{f}")
  if p.get(f)!=c:errors.append(f"stale_{f}")
 for f,m in (("startup_budget_ms",120000),("quick_budget_ms",3600000),("full_budget_ms",14400000)):
  v=p.get(f)
  if not isinstance(v,int) or isinstance(v,bool) or v<1 or v>m:errors.append(f"malformed_{f}")
 if p.get("content_free") is not True or p.get("read_only") is not True or p.get("feature_freeze_active") is not True:errors.append("boundary_loss")
 if p.get("global_profile_pass_claimed") is not False:errors.append("false_global_pass_claim")
 if p.get("authority_state")!="separate_not_granted":errors.append("authority_expansion")
 for f in FORBIDDEN:
  if p.get(f) is not False:errors.append(f"plan_forbidden:{f}")
 ids=[];seq=[];classes=[];prior=""
 for i,r in enumerate(rows):
  u=dict(r);s=u.pop("evidence_digest",None)
  if s!=_digest(u):errors.append(f"evidence_tamper:{i}")
  ids.append(str(r.get("evidence_id") or ""));seq.append(r.get("sequence"));classes.append(r.get("evidence_class"))
  if r.get("evidence_class") not in EVIDENCE_CLASSES:errors.append(f"unsupported_class:{i}")
  if r.get("outcome") not in OUTCOMES:errors.append(f"unsupported_outcome:{i}")
  if not str(r.get("owner") or ""):errors.append(f"missing_owner:{i}")
  if r.get("prior_receipt_digest","")!=prior:errors.append(f"broken_lineage:{i}")
  if i and not _is_digest(r.get("prior_receipt_digest")):errors.append(f"malformed_prior:{i}")
  prior=str(r.get("receipt_digest") or "")
  for f in ("artifact_digest","receipt_digest"):
   if not _is_digest(r.get(f)):errors.append(f"malformed_{f}:{i}")
  for f in ("observed_ms","budget_ms"):
   v=r.get(f)
   if not isinstance(v,int) or isinstance(v,bool) or v<0:errors.append(f"malformed_{f}:{i}")
  if r.get("observed_ms",0)>r.get("budget_ms",0) and r.get("outcome")=="pass":errors.append(f"budget_truth_violation:{i}")
  if r.get("outcome")=="inherited_debt" and not str(r.get("debt_id") or ""):errors.append(f"missing_debt_id:{i}")
  if r.get("historical_truth_preserved") is not True or r.get("feature_freeze_active") is not True:errors.append(f"evidence_boundary_loss:{i}")
  if r.get("global_profile_pass_claimed") is not False:errors.append(f"false_global_pass_claim:{i}")
  if r.get("authority_state")!="separate_not_granted":errors.append(f"authority_expansion:{i}")
  for f in FORBIDDEN:
   if r.get(f) is not False:errors.append(f"evidence_forbidden:{f}:{i}")
 if len(ids)!=len(set(ids)):errors.append("duplicate_evidence_id")
 if seq!=list(range(1,len(rows)+1)):errors.append("non_deterministic_sequence")
 missing=sorted(set(EVIDENCE_CLASSES)-set(classes))
 if missing:errors.append("missing_evidence_classes:"+",".join(missing))
 result={"contract_version":CONTRACT_VERSION,"status":"ready" if not errors else "blocked","errors":sorted(set(errors)),"evidence_count":len(rows),"evidence_class_count":len(set(classes)),"current_health_pass":not errors and all(r.get("outcome") in ("pass","inherited_debt") for r in rows),"inherited_debt_count":sum(r.get("outcome")=="inherited_debt" for r in rows),"global_profile_pass_claimed":False,"content_free":True,"read_only":True,"feature_freeze_active":True,"historical_truth_preserved":True,"authority_state":"separate_not_granted"}
 result.update({k:False for k in FORBIDDEN});result["assessment_digest"]=_digest(result);return result
