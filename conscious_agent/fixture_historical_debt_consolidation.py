from __future__ import annotations
"""v1193.6-v1193.8 fixture and historical-debt consolidation contracts."""
import hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_VERSION="v1193.8"
ALLOWED_OWNERS={"conversation","cognition","planning","campaign","runtime","release","privacy","platform"}
ALLOWED_OVERLAP={"unique","exact_duplicate","partial_overlap","checkpoint_overlap"}
ALLOWED_DISPOSITIONS={"retain_canonical","retain_alias","defer_consolidation","retain_independent"}
ALLOWED_SEVERITIES={"low","medium","high"}
PRIVATE_KEYS={"prompt","conversation","memory","secret","raw_source","patch","stdout","stderr","provider_payload","private_reasoning","content","text"}

def _digest(value:object)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode("utf-8")).hexdigest()

def _is_digest(value:object)->bool:
 token=str(value or "");return len(token)==64 and all(c in "0123456789abcdef" for c in token)

def create_fixture_record(*,fixture_id:str,owner:str,cleanup_owner:str,fixture_group:str,suite_path:str,source_version:str,overlap_class:str,canonical_fixture_id:str="",disposition:str="retain_independent",historical_debt_id:str="",debt_severity:str="low",expected_checks:int=0)->dict[str,Any]:
 row={"fixture_id":str(fixture_id),"owner":str(owner),"cleanup_owner":str(cleanup_owner),"fixture_group":str(fixture_group),"suite_path":str(suite_path),"source_version":str(source_version),"overlap_class":str(overlap_class),"canonical_fixture_id":str(canonical_fixture_id),"disposition":str(disposition),"historical_debt_id":str(historical_debt_id),"debt_severity":str(debt_severity),"expected_checks":int(expected_checks),"historical_truth_preserved":True,"fixture_deleted":False,"verifier_retired":False,"authority_state":"separate_not_granted"}
 row["record_digest"]=_digest(row);return row

def validate_fixture_records(records:Sequence[Mapping[str,Any]],*,max_records:int=256)->list[str]:
 errors=[];rows=[dict(r) for r in records];ids=[];paths=[]
 if not rows:errors.append("empty_registry")
 if len(rows)>max_records:errors.append("oversized_registry")
 for row in rows:
  if {str(k).lower() for k in row}&PRIVATE_KEYS:errors.append("private_field")
  ids.append(str(row.get("fixture_id") or ""));paths.append(str(row.get("suite_path") or ""))
  if row.get("owner") not in ALLOWED_OWNERS:errors.append("invalid_owner")
  if row.get("cleanup_owner") not in ALLOWED_OWNERS:errors.append("invalid_cleanup_owner")
  if not str(row.get("suite_path") or "").startswith("tools/"):errors.append("invalid_suite_path")
  if row.get("overlap_class") not in ALLOWED_OVERLAP:errors.append("invalid_overlap_class")
  if row.get("disposition") not in ALLOWED_DISPOSITIONS:errors.append("invalid_disposition")
  if row.get("debt_severity") not in ALLOWED_SEVERITIES:errors.append("invalid_severity")
  if int(row.get("expected_checks",-1))<0:errors.append("invalid_expected_checks")
  overlap=row.get("overlap_class");canonical=str(row.get("canonical_fixture_id") or "")
  if overlap in {"exact_duplicate","partial_overlap","checkpoint_overlap"} and not canonical:errors.append("missing_canonical_fixture")
  if overlap=="unique" and canonical:errors.append("unexpected_canonical_fixture")
  if row.get("disposition")=="retain_alias" and overlap!="exact_duplicate":errors.append("alias_requires_exact_duplicate")
  if row.get("disposition")=="retain_canonical" and canonical and canonical!=row.get("fixture_id"):errors.append("canonical_identity_mismatch")
  if row.get("historical_debt_id") and row.get("debt_severity")=="low":errors.append("debt_severity_required")
  if row.get("debt_severity")!="low" and not row.get("historical_debt_id"):errors.append("missing_debt_id")
  if row.get("historical_truth_preserved") is not True:errors.append("historical_truth_loss")
  if row.get("fixture_deleted") is not False:errors.append("fixture_deletion_claim")
  if row.get("verifier_retired") is not False:errors.append("verifier_retirement_claim")
  if row.get("authority_state")!="separate_not_granted":errors.append("authority_expansion")
  candidate=dict(row);claimed=candidate.pop("record_digest","")
  if not _is_digest(claimed) or claimed!=_digest(candidate):errors.append("record_tamper")
 if len(ids)!=len(set(ids)):errors.append("duplicate_fixture_id")
 if len(paths)!=len(set(paths)):errors.append("duplicate_suite_path")
 known=set(ids)
 for row in rows:
  canonical=str(row.get("canonical_fixture_id") or "")
  if canonical and canonical not in known:errors.append("unknown_canonical_fixture")
  if canonical==row.get("fixture_id") and row.get("overlap_class")!="unique" and row.get("disposition")!="retain_canonical":errors.append("self_reference_not_canonical")
 return sorted(set(errors))

def consolidate_fixture_records(records:Sequence[Mapping[str,Any]])->dict[str,Any]:
 rows=[dict(r) for r in records];errors=validate_fixture_records(rows)
 if errors:return {"status":"blocked","errors":errors,"content_free":True,"execution_invoked":False,"fixture_deleted":False,"verifier_retired":False,"authority_granted":False}
 aliases={r["fixture_id"]:r["canonical_fixture_id"] for r in rows if r["disposition"]=="retain_alias"}
 groups={}
 for row in rows:groups.setdefault(row["fixture_group"],[]).append(row["fixture_id"])
 body={"contract_version":CONTRACT_VERSION,"records":rows,"record_count":len(rows),"fixture_group_count":len(groups),"alias_map":dict(sorted(aliases.items())),"alias_count":len(aliases),"deferred_count":sum(r["disposition"]=="defer_consolidation" for r in rows),"historical_debt_count":sum(bool(r["historical_debt_id"]) for r in rows),"cleanup_owners":sorted({r["cleanup_owner"] for r in rows}),"historical_truth_preserved":all(r["historical_truth_preserved"] for r in rows),"fixture_deleted":False,"verifier_retired":False,"authority_state":"separate_not_granted"}
 return {"status":"consolidated","consolidation":body,"consolidation_digest":_digest(body),"errors":[],"content_free":True,"execution_invoked":False,"fixture_deleted":False,"verifier_retired":False,"authority_granted":False}

def public_consolidation_summary(report:Mapping[str,Any])->dict[str,Any]:
 body=report.get("consolidation") or {}
 return {"contract_version":CONTRACT_VERSION,"status":report.get("status"),"record_count":body.get("record_count",0),"fixture_group_count":body.get("fixture_group_count",0),"alias_count":body.get("alias_count",0),"deferred_count":body.get("deferred_count",0),"historical_debt_count":body.get("historical_debt_count",0),"cleanup_owner_count":len(body.get("cleanup_owners") or []),"historical_truth_preserved":body.get("historical_truth_preserved") is True,"fixture_deleted":False,"verifier_retired":False,"content_free":True,"execution_invoked":False,"authority_granted":False}
