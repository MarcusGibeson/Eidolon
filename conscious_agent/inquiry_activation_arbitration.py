from __future__ import annotations
"""Deterministic, restrained arbitration for registered active-inquiry records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from active_inquiry_records import ActiveInquiryStore
CONTRACT_VERSION="v1113.1"
OUTCOMES={"active_internal","deferred","internal_only","awaiting_operator_review","awaiting_natural_evidence","merged","suspended","abandoned","deliberate_non_inquiry"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"decisions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_activation_score":.52,"max_sensitivity":.65,"max_intrusion":.35,"max_resource_budget":.70,"repeat_penalty":.18},"authority_boundary":{"can_browse":False,"can_contact_provider":False,"can_ask_user":False,"can_send_message":False,"can_execute":False,"can_authorize":False,"can_create_research_proposal":False}}
class InquiryActivationArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"inquiry_activation_arbitration.json";self.clock=clock or _now;self.inquiries=ActiveInquiryStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def decide(self,event_id:str,*,active_inquiry_id:str,relevance:float=.5,answerability:float=.5,novelty:float=.5,importance:float=.5,staleness:float=0,repetition:float=0,natural_evidence_expected:bool=False,operator_review_required:bool=False,merge_target_id:str=""):
  event_id=_clean(event_id,180);iid=_clean(active_inquiry_id,220)
  if not event_id or not iid:raise ValueError("event_id and active_inquiry_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   inquiry=next((x for x in self.inquiries.snapshot()["records"] if x.get("active_inquiry_id")==iid),None)
   if not inquiry or inquiry.get("state")!="pending_activation":result={"status":"arbitration_rejected","reason":"pending_inquiry_required","arbitration_id":"","outcome":""}
   else:
    vals=[max(0,min(float(x),1)) for x in (relevance,answerability,novelty,importance,staleness,repetition)]; rel,ans,nov,imp,stale,repeat=vals
    score=round(.30*rel+.25*ans+.20*nov+.25*imp-.20*stale-.18*repeat,4);sens=float(inquiry.get("sensitivity",0));intr=float(inquiry.get("intrusion",0));budget=float(inquiry.get("resource_budget",0))
    if merge_target_id:outcome,reason="merged","semantic_overlap"
    elif operator_review_required or sens>s["controls"]["max_sensitivity"]:outcome,reason="awaiting_operator_review","sensitivity_or_policy_review"
    elif intr>s["controls"]["max_intrusion"]:outcome,reason="internal_only","intrusion_restraint"
    elif budget>s["controls"]["max_resource_budget"]:outcome,reason="deferred","resource_limit"
    elif stale>=.75:outcome,reason="abandoned","stale_or_obsolete"
    elif repeat>=.75:outcome,reason="deliberate_non_inquiry","repetition_suppression"
    elif natural_evidence_expected:outcome,reason="awaiting_natural_evidence","passive_evidence_preferred"
    elif score>=s["controls"]["minimum_activation_score"]:outcome,reason="active_internal","bounded_internal_inquiry"
    elif score>=.35:outcome,reason="deferred","insufficient_current_value"
    else:outcome,reason="deliberate_non_inquiry","low_value_or_answerability"
    now=self.clock();aid=f"inquiry-arbitration-{_digest(event_id)[:24]}";result={"status":"activation_decided","arbitration_id":aid,"active_inquiry_id":iid,"outcome":outcome,"reason":reason,"score":score,"causation_claimed":False,"research_proposal_id":"","approval_id":"","authorization_id":"","browse_receipt_id":"","provider_receipt_id":"","user_prompt_id":"","action_id":""};self.inquiries.apply_arbitration(iid,arbitration_id=aid,outcome=outcome,merge_target_id=merge_target_id);s["decisions"]=(s["decisions"]+[{**result,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}])[-512:]
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["decisions"];counts={}
  for x in rows:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"decision_count":len(rows),"outcome_counts":counts,"recent_decisions":[{k:x.get(k) for k in ("arbitration_id","active_inquiry_id","outcome","reason","score","causation_claimed","research_proposal_id","approval_id","authorization_id","browse_receipt_id","provider_receipt_id","user_prompt_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_inquiry_activation_arbitration_inspection(runtime_root=None):return InquiryActivationArbitrator(runtime_root).inspection_summary()
