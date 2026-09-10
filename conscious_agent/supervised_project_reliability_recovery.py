from __future__ import annotations
"""v1184.6-v1184.8 adversarial reliability, drift, recovery, rollback, and privacy hardening."""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION="v1184.8"; SCHEMA_VERSION="1"; MAX_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
RECOVERY_STATES=frozenset({"not_interrupted","paused","resumed","abandoned"})

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_BYTES

def create_project_reliability_receipt(*,lineage:Mapping[str,Any],presentation:Mapping[str,Any],learning:Mapping[str,Any],expected_source_digest:str,observed_source_digest:str,expected_terminal_digest:str,interruption_state:str,interruption_receipt_digest:str,rollback_expected_digest:str="",rollback_observed_digest:str="",privacy_findings:Sequence[str]=())->dict[str,Any]:
 errors=[]
 def valid_signed(obj,key,label):
  unsigned=dict(obj); d=str(unsigned.pop(key,"")).lower()
  if not DIGEST_RE.fullmatch(d) or _digest(unsigned)!=d: errors.append(f"tampered_{label}")
  return d
 ld=valid_signed(lineage,"lineage_digest","lineage")
 pd=valid_signed(presentation,"presentation_digest","presentation")
 learn=valid_signed(learning,"learning_digest","learning")
 if presentation.get("lineage_digest")!=ld or learning.get("lineage_digest")!=ld or learning.get("presentation_digest")!=pd: errors.append("lineage_binding_mismatch")
 if str(lineage.get("terminal_receipt_digest") or "").lower()!=str(expected_terminal_digest or "").lower(): errors.append("terminal_digest_mismatch")
 for name,val in (("expected_source_digest",expected_source_digest),("observed_source_digest",observed_source_digest),("expected_terminal_digest",expected_terminal_digest),("interruption_receipt_digest",interruption_receipt_digest)):
  if not DIGEST_RE.fullmatch(str(val or "").lower()): errors.append(f"invalid_{name}")
 stale=bool(DIGEST_RE.fullmatch(str(expected_source_digest).lower()) and str(expected_source_digest).lower()!=str(observed_source_digest).lower())
 if stale: errors.append("stale_source_or_drift")
 state=str(interruption_state or "").strip()
 if state not in RECOVERY_STATES: errors.append("unsupported_interruption_state")
 rollback_required=bool(presentation.get("rollback_available"))
 if rollback_required:
  if not DIGEST_RE.fullmatch(str(rollback_expected_digest or "").lower()) or not DIGEST_RE.fullmatch(str(rollback_observed_digest or "").lower()): errors.append("invalid_rollback_digest")
  elif str(rollback_expected_digest).lower()!=str(rollback_observed_digest).lower(): errors.append("rollback_verification_failed")
 findings=[str(x or "").strip() for x in privacy_findings]
 if findings: errors.append("privacy_findings_present")
 if not _bounded({"lineage":lineage,"presentation":presentation,"learning":learning,"findings":findings}): errors.append("oversized_input")
 errors=sorted(set(errors))
 status="recovery_review_ready" if not errors else "blocked"
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"reliability_id":"supervised-project-reliability-recovery:v1184.8","status":status,"lineage_digest":ld,"presentation_digest":pd,"learning_digest":learn,"expected_source_digest":str(expected_source_digest).lower(),"observed_source_digest":str(observed_source_digest).lower(),"expected_terminal_digest":str(expected_terminal_digest).lower(),"interruption_state":state,"interruption_receipt_digest":str(interruption_receipt_digest).lower(),"stale_source_detected":stale,"rollback_required":rollback_required,"rollback_verified":rollback_required and not any(e.startswith("invalid_rollback") or e=="rollback_verification_failed" for e in errors),"privacy_finding_count":len(findings),"error_count":len(errors),"errors":errors,"content_free":True,"private_content_included":False,"historical_truth_preserved":True,"production_source_modified":False,"sandbox_modified":False,"execution_invoked":False,"rollback_executed":False,"provider_contacted":False,"model_contacted":False,"approval_created":False,"authority_granted":False,"source_application_authorized":False,"installation_authorized":False,"promotion_authorized":False,"certification_authorized":False,"release_authorized":False,"autonomous_action_authorized":False,"operator_review_required_for_next_action":True}
 row["reliability_digest"]=_digest(row);return row

def supervised_project_reliability_public_summary(row:Mapping[str,Any])->dict[str,Any]:
 return {"contract_version":CONTRACT_VERSION,"status":row.get("status",""),"interruption_state":row.get("interruption_state",""),"stale_source_detected":row.get("stale_source_detected") is True,"rollback_required":row.get("rollback_required") is True,"rollback_verified":row.get("rollback_verified") is True,"privacy_finding_count":int(row.get("privacy_finding_count") or 0),"error_count":int(row.get("error_count") or 0),"reliability_digest":row.get("reliability_digest",""),"content_free":True,"operator_review_required_for_next_action":True,"authority_granted":False}
