from __future__ import annotations
"""Read-only v1199.8 final candidate reliability and handoff hardening."""
import hashlib, json
from typing import Any, Mapping
CONTRACT_VERSION="v1199.8"
EVENT_CLASSES=("candidate_manifest_drift","retained_verification_drift","unresolved_risk_drift","desktop_handoff_drift","native_provider_handoff_drift","privacy_boundary_drift","authority_boundary_drift","review_replay")
PRIVATE_TOKENS=("prompt","conversation_text","memory_content","secret","password","raw_source","patch","stdout","stderr","provider_payload","private_reasoning","credential","api_key")
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _is_digest(v:object)->bool:
 s=str(v or "");return len(s)==64 and all(c in "0123456789abcdef" for c in s)
def _private(v:object,prefix=""):
 out=[]
 if isinstance(v,Mapping):
  for k,x in v.items():
   p=f"{prefix}.{k}" if prefix else str(k)
   if any(t in str(k).lower() for t in PRIVATE_TOKENS):out.append(p)
   out.extend(_private(x,p))
 elif isinstance(v,(list,tuple)):
  for i,x in enumerate(v):out.extend(_private(x,f"{prefix}[{i}]"))
 return sorted(set(out))
def create_reliability_event(*,event_id:str,candidate_id:str,event_class:str,sequence:int,prior_event_receipt_digest:str|None,snapshot_digest:str,context_digest:str,candidate_assessment_digest:str,source_manifest_digest:str,retained_verification_digest:str,unresolved_risk_digest:str,desktop_handoff_digest:str,native_provider_handoff_digest:str,review_receipt_digest:str,artifact_digest:str,receipt_digest:str,foreground_latency_ms:int=0,latency_budget_ms:int=250)->dict[str,Any]:
 row={"contract_version":CONTRACT_VERSION,"event_id":event_id,"candidate_id":candidate_id,"event_class":event_class,"sequence":sequence,"prior_event_receipt_digest":prior_event_receipt_digest,"snapshot_digest":snapshot_digest,"context_digest":context_digest,"candidate_assessment_digest":candidate_assessment_digest,"source_manifest_digest":source_manifest_digest,"retained_verification_digest":retained_verification_digest,"unresolved_risk_digest":unresolved_risk_digest,"desktop_handoff_digest":desktop_handoff_digest,"native_provider_handoff_digest":native_provider_handoff_digest,"review_receipt_digest":review_receipt_digest,"artifact_digest":artifact_digest,"receipt_digest":receipt_digest,"foreground_latency_ms":foreground_latency_ms,"latency_budget_ms":latency_budget_ms,"content_free":True,"read_only":True,"source_only":True,"foreground_available":True,"original_candidate_preserved":True,"retained_verification_preserved":True,"unresolved_risks_preserved":True,"handoff_truth_preserved":True,"privacy_boundary_preserved":True,"authority_boundary_preserved":True,"candidate_accepted":False,"handoff_accepted":False,"risk_waived":False,"global_profile_pass_claimed":False,"approval_created":False,"approval_consumed":False,"candidate_modified":False,"source_modified":False,"runtime_mutated":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"publication_performed":False,"release_performed":False,"provider_contacted":False,"model_contacted":False,"process_started":False,"thread_started":False,"automatic_continuation":False,"automatic_recovery":False,"authority_state":"separate_not_granted"}
 row["event_digest"]=_digest(row);return row
def inspect_reliability_event(event:Mapping[str,Any],*,expected_candidate_id:str,expected_sequence:int,expected_prior_event_receipt_digest:str|None,expected_snapshot_digest:str,expected_context_digest:str,expected_candidate_assessment_digest:str,expected_source_manifest_digest:str,expected_retained_verification_digest:str,expected_unresolved_risk_digest:str,expected_desktop_handoff_digest:str,expected_native_provider_handoff_digest:str,expected_review_receipt_digest:str)->dict[str,Any]:
 r=dict(event);errors=[f"private_field:{x}" for x in _private(r)];u=dict(r);supplied=u.pop("event_digest",None)
 if supplied!=_digest(u):errors.append("event_tamper")
 if r.get("contract_version")!=CONTRACT_VERSION:errors.append("unsupported_contract")
 if r.get("candidate_id")!=expected_candidate_id:errors.append("stale_candidate")
 if r.get("event_class") not in EVENT_CLASSES:errors.append("unsupported_event")
 if r.get("sequence")!=expected_sequence:errors.append("invalid_sequence")
 if r.get("prior_event_receipt_digest")!=expected_prior_event_receipt_digest:errors.append("broken_lineage")
 if expected_sequence>1 and not _is_digest(r.get("prior_event_receipt_digest")):errors.append("malformed_prior_event_receipt_digest")
 expected={"snapshot_digest":expected_snapshot_digest,"context_digest":expected_context_digest,"candidate_assessment_digest":expected_candidate_assessment_digest,"source_manifest_digest":expected_source_manifest_digest,"retained_verification_digest":expected_retained_verification_digest,"unresolved_risk_digest":expected_unresolved_risk_digest,"desktop_handoff_digest":expected_desktop_handoff_digest,"native_provider_handoff_digest":expected_native_provider_handoff_digest,"review_receipt_digest":expected_review_receipt_digest}
 for k,v in expected.items():
  if r.get(k)!=v:errors.append(f"stale_{k}")
 for k in (*expected.keys(),"artifact_digest","receipt_digest"):
  if not _is_digest(r.get(k)):errors.append(f"malformed_{k}")
 try:
  if int(r.get("foreground_latency_ms",-1))<0 or int(r.get("latency_budget_ms",0))<=0:errors.append("malformed_latency")
  elif int(r["foreground_latency_ms"])>int(r["latency_budget_ms"]):errors.append("latency_budget_exceeded")
 except Exception:errors.append("malformed_latency")
 for f in ("content_free","read_only","source_only","foreground_available","original_candidate_preserved","retained_verification_preserved","unresolved_risks_preserved","handoff_truth_preserved","privacy_boundary_preserved","authority_boundary_preserved"):
  if r.get(f) is not True:errors.append(f"boundary_loss:{f}")
 forbidden=("candidate_accepted","handoff_accepted","risk_waived","global_profile_pass_claimed","approval_created","approval_consumed","candidate_modified","source_modified","runtime_mutated","installation_performed","promotion_performed","certification_performed","publication_performed","release_performed","provider_contacted","model_contacted","process_started","thread_started","automatic_continuation","automatic_recovery")
 for f in forbidden:
  if r.get(f) is not False:errors.append(f"forbidden_claim:{f}")
 if r.get("authority_state")!="separate_not_granted":errors.append("authority_expansion")
 status="reliability_evidence_ready" if not errors else "blocked"
 receipt=_digest({"event_digest":r.get("event_digest"),"status":status,"errors":sorted(set(errors)),"sequence":r.get("sequence")})
 return {"ok":not errors,"status":status,"errors":sorted(set(errors)),"reliability_receipt_digest":receipt,"event_class":r.get("event_class"),"sequence":r.get("sequence"),"foreground_available":not errors and r.get("foreground_available") is True,"original_candidate_preserved":r.get("original_candidate_preserved") is True,"retained_verification_preserved":r.get("retained_verification_preserved") is True,"unresolved_risks_preserved":r.get("unresolved_risks_preserved") is True,"handoff_truth_preserved":r.get("handoff_truth_preserved") is True,"privacy_boundary_preserved":r.get("privacy_boundary_preserved") is True,"authority_boundary_preserved":r.get("authority_boundary_preserved") is True,"candidate_accepted":False,"handoff_accepted":False,"risk_waived":False,"global_profile_pass_claimed":False,"candidate_modified":False,"source_modified":False,"runtime_mutated":False,"release_performed":False,"provider_contacted":False,"automatic_recovery":False,"authority_state":"separate_not_granted"}
