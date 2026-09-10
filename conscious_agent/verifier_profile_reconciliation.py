from __future__ import annotations
"""v1193.3-v1193.5 deterministic verifier profile and budget reconciliation."""
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_VERSION="v1193.5"
ALLOWED_PROFILES={"focused","quick","full"}
ALLOWED_CLASSES={"current_regression","retained_checkpoint","historical_debt"}
ALLOWED_OUTCOMES={"passed","failed","blocked","not_run"}
PRIVATE_KEYS={"prompt","conversation","memory","secret","raw_source","patch","stdout","stderr","provider_payload","private_reasoning","content","text"}

def _digest(value:object)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode("utf-8")).hexdigest()

def _is_digest(value:object)->bool:
 token=str(value or "");return len(token)==64 and all(c in "0123456789abcdef" for c in token)

def create_profile_result(*,verifier_id:str,classification:str,profile:str,sequence:int,expected_checks:int,actual_checks:int,budget_seconds:int,elapsed_milliseconds:int,outcome:str,debt_group:str="")->dict[str,Any]:
 row={"verifier_id":str(verifier_id),"classification":str(classification),"profile":str(profile),"sequence":int(sequence),"expected_checks":int(expected_checks),"actual_checks":int(actual_checks),"budget_seconds":int(budget_seconds),"elapsed_milliseconds":int(elapsed_milliseconds),"outcome":str(outcome),"debt_group":str(debt_group),"authority_state":"separate_not_granted"}
 row["result_digest"]=_digest(row);return row

def validate_profile_results(rows:Sequence[Mapping[str,Any]],*,max_results:int=256)->list[str]:
 errors=[];items=[dict(r) for r in rows];ids=[];seq=[]
 if not items:errors.append("empty_results")
 if len(items)>max_results:errors.append("oversized_results")
 for row in items:
  if {str(k).lower() for k in row}&PRIVATE_KEYS:errors.append("private_field")
  ids.append((str(row.get("profile")),str(row.get("verifier_id"))));seq.append((str(row.get("profile")),int(row.get("sequence",-1))))
  if row.get("profile") not in ALLOWED_PROFILES:errors.append("invalid_profile")
  if row.get("classification") not in ALLOWED_CLASSES:errors.append("invalid_classification")
  if row.get("outcome") not in ALLOWED_OUTCOMES:errors.append("invalid_outcome")
  if int(row.get("sequence",-1))<0:errors.append("invalid_sequence")
  if int(row.get("expected_checks",-1))<0 or int(row.get("actual_checks",-1))<0:errors.append("invalid_check_count")
  if not 1<=int(row.get("budget_seconds",0))<=1800:errors.append("invalid_budget")
  if not 0<=int(row.get("elapsed_milliseconds",-1))<=3_600_000:errors.append("invalid_elapsed")
  if row.get("classification")=="historical_debt" and not row.get("debt_group"):errors.append("missing_debt_group")
  if row.get("classification")!="historical_debt" and row.get("debt_group"):errors.append("unexpected_debt_group")
  if row.get("outcome")=="passed" and row.get("actual_checks")!=row.get("expected_checks"):errors.append("passed_check_mismatch")
  if row.get("authority_state")!="separate_not_granted":errors.append("authority_expansion")
  candidate=dict(row);claimed=candidate.pop("result_digest","")
  if not _is_digest(claimed) or claimed!=_digest(candidate):errors.append("result_tamper")
 if len(ids)!=len(set(ids)):errors.append("duplicate_profile_verifier")
 if len(seq)!=len(set(seq)):errors.append("duplicate_profile_sequence")
 return sorted(set(errors))

def reconcile_profile(*,profile:str,expected_verifiers:Sequence[str],results:Sequence[Mapping[str,Any]],profile_budget_seconds:int)->dict[str,Any]:
 rows=[dict(r) for r in results];errors=validate_profile_results(rows)
 if profile not in ALLOWED_PROFILES:errors.append("invalid_profile")
 if not 1<=int(profile_budget_seconds)<=7200:errors.append("invalid_profile_budget")
 expected=[str(x) for x in expected_verifiers]
 if len(expected)!=len(set(expected)):errors.append("duplicate_expected_verifier")
 if any(r.get("profile")!=profile for r in rows):errors.append("mixed_profile")
 actual=[str(r.get("verifier_id")) for r in sorted(rows,key=lambda r:r.get("sequence",-1))]
 if actual!=expected:errors.append("membership_or_order_mismatch")
 if errors:return {"status":"blocked","errors":sorted(set(errors)),"content_free":True,"execution_invoked":False,"authority_granted":False}
 elapsed=sum(int(r["elapsed_milliseconds"]) for r in rows);budget_ms=int(profile_budget_seconds)*1000
 current_failed=[r["verifier_id"] for r in rows if r["classification"]=="current_regression" and r["outcome"]!="passed"]
 retained_failed=[r["verifier_id"] for r in rows if r["classification"]=="retained_checkpoint" and r["outcome"]!="passed"]
 inherited_nonpass=[r["verifier_id"] for r in rows if r["classification"]=="historical_debt" and r["outcome"]!="passed"]
 current_pass=not current_failed and not retained_failed
 global_pass=current_pass and not inherited_nonpass and elapsed<=budget_ms and all(r["outcome"]=="passed" for r in rows)
 body={"contract_version":CONTRACT_VERSION,"profile":profile,"expected_verifiers":expected,"results":rows,"result_count":len(rows),"elapsed_milliseconds":elapsed,"profile_budget_seconds":int(profile_budget_seconds),"within_profile_budget":elapsed<=budget_ms,"current_regressions_passed":current_pass,"current_failure_ids":current_failed,"retained_failure_ids":retained_failed,"inherited_nonpass_ids":inherited_nonpass,"historical_debt_separate":True,"global_profile_pass":global_pass,"authority_state":"separate_not_granted"}
 return {"status":"reconciled","reconciliation":body,"reconciliation_digest":_digest(body),"errors":[],"content_free":True,"execution_invoked":False,"authority_granted":False}

def public_profile_summary(report:Mapping[str,Any])->dict[str,Any]:
 body=report.get("reconciliation") or {}
 return {"contract_version":CONTRACT_VERSION,"status":report.get("status"),"profile":body.get("profile",""),"result_count":body.get("result_count",0),"elapsed_milliseconds":body.get("elapsed_milliseconds",0),"profile_budget_seconds":body.get("profile_budget_seconds",0),"within_profile_budget":body.get("within_profile_budget") is True,"current_regressions_passed":body.get("current_regressions_passed") is True,"current_failure_count":len(body.get("current_failure_ids") or []),"retained_failure_count":len(body.get("retained_failure_ids") or []),"inherited_nonpass_count":len(body.get("inherited_nonpass_ids") or []),"historical_debt_separate":body.get("historical_debt_separate") is True,"global_profile_pass":body.get("global_profile_pass") is True,"content_free":True,"execution_invoked":False,"authority_granted":False}
