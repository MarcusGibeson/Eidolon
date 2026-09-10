from __future__ import annotations
"""v1196.3-v1196.5 content-free operator review of adversarial recovery evidence."""
import hashlib, json
from typing import Any, Mapping

CONTRACT_VERSION="v1196.5"
DECISIONS=("approve","reject","defer")
EVENT_CLASSES=("replay_attack","stale_state_attack","interruption","cancellation_race","recovery_abuse")
ACTIONS=("present_blocked","present_deferred","present_inconclusive","review_recovery_eligibility")
_PRIVATE=("prompt","conversation_text","memory_text","secret","credential","token","provider_payload","raw_source","patch_text","stdout","stderr","private_reasoning")

def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _hex(v:object)->bool:
 t=str(v or "");return len(t)==64 and all(c in "0123456789abcdef" for c in t)
def _private(v:Mapping[str,Any])->list[str]:return sorted(str(k) for k in v if any(t in str(k).lower() for t in _PRIVATE))

def build_review_request(*,review_id:str,event_class:str,action:str,sequence:int,snapshot_digest:str,context_digest:str,evidence_digest:str,prior_review_digest:str|None=None)->dict[str,Any]:
 r={"contract_version":CONTRACT_VERSION,"review_id":review_id,"event_class":event_class,"action":action,"sequence":sequence,"snapshot_digest":snapshot_digest,"context_digest":context_digest,"evidence_digest":evidence_digest,"prior_review_digest":prior_review_digest,"content_free":True,"operator_review_required":True,"automatic_recovery_requested":False,"automatic_retry_requested":False,"cancellation_executed":False,"execution_invoked":False,"runtime_mutated":False,"provider_contacted":False,"model_contacted":False,"thread_started":False,"process_started":False,"approval_created":False,"approval_consumed":False,"authority_requested":False}
 r["request_digest"]=_digest(r);return r

def build_review_decision(*,request_digest:str,decision:str,operator_review_digest:str,reason_code:str)->dict[str,Any]:
 r={"contract_version":CONTRACT_VERSION,"request_digest":request_digest,"decision":decision,"operator_review_digest":operator_review_digest,"reason_code":reason_code,"content_free":True,"recovery_executed":False,"retry_executed":False,"cancellation_executed":False,"execution_authorized":False,"authority_granted":False}
 r["decision_digest"]=_digest(r);return r

def review_adversarial_event(*,request:Mapping[str,Any],decision:Mapping[str,Any],expected_snapshot_digest:str,expected_context_digest:str,expected_evidence_digest:str,expected_prior_review_digest:str|None=None)->dict[str,Any]:
 q=dict(request);d=dict(decision);errors=[]
 errors += [f"private_field:{x}" for x in _private({**q,**d})]
 for row,field,label in ((q,"request_digest","request"),(d,"decision_digest","decision")):
  body=dict(row);sup=body.pop(field,None)
  if sup!=_digest(body):errors.append(f"{label}_tamper")
 if q.get("contract_version")!=CONTRACT_VERSION:errors.append("unsupported_request_contract")
 if d.get("contract_version")!=CONTRACT_VERSION:errors.append("unsupported_decision_contract")
 for f in ("snapshot_digest","context_digest","evidence_digest"):
  if not _hex(q.get(f)):errors.append(f"malformed_{f}")
 if not _hex(d.get("operator_review_digest")):errors.append("malformed_operator_review_digest")
 if q.get("snapshot_digest")!=expected_snapshot_digest:errors.append("stale_snapshot")
 if q.get("context_digest")!=expected_context_digest:errors.append("stale_context")
 if q.get("evidence_digest")!=expected_evidence_digest:errors.append("stale_evidence")
 if q.get("event_class") not in EVENT_CLASSES:errors.append("unsupported_event_class")
 if q.get("action") not in ACTIONS:errors.append("unsupported_action")
 if d.get("decision") not in DECISIONS:errors.append("unsupported_decision")
 if d.get("request_digest")!=q.get("request_digest"):errors.append("decision_request_mismatch")
 if not isinstance(q.get("sequence"),int) or isinstance(q.get("sequence"),bool) or not 1<=q["sequence"]<=10000:errors.append("invalid_sequence")
 prior=q.get("prior_review_digest")
 if expected_prior_review_digest is None:
  if prior not in (None,""):errors.append("unexpected_prior_review")
 elif prior!=expected_prior_review_digest:errors.append("broken_review_lineage")
 for f in ("content_free","operator_review_required"):
  if q.get(f) is not True:errors.append(f"invalid_{f}")
 for f in ("automatic_recovery_requested","automatic_retry_requested","cancellation_executed","execution_invoked","runtime_mutated","provider_contacted","model_contacted","thread_started","process_started","approval_created","approval_consumed","authority_requested"):
  if q.get(f) is not False:errors.append(f"invalid_{f}")
 for f in ("recovery_executed","retry_executed","cancellation_executed","execution_authorized","authority_granted"):
  if d.get(f) is not False:errors.append(f"invalid_{f}")
 status="blocked" if errors else {"approve":"review_presented","reject":"review_rejected","defer":"review_deferred"}[d["decision"]]
 out={"ok":not errors,"contract_version":CONTRACT_VERSION,"status":status,"errors":sorted(set(errors)),"event_class":q.get("event_class"),"action":q.get("action"),"decision":d.get("decision"),"sequence":q.get("sequence"),"content_free":True,"exact_lineage_verified":not errors,"original_evidence_preserved":True,"recovery_executed":False,"retry_executed":False,"cancellation_executed":False,"execution_invoked":False,"runtime_mutated":False,"provider_contacted":False,"authority_state":"separate_not_granted","authority_granted":False}
 out["review_receipt_digest"]=_digest(out);return out
