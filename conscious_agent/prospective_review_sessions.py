from __future__ import annotations
"""Bounded, content-free prospective review sessions without review or action authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from temporal_eligibility_arbitration import TemporalEligibilityArbitrator
CONTRACT_VERSION="v1117.3"
SESSION_STATES={"open","acknowledged","deferred","closed","superseded","expired","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"sessions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_sessions":512},"authority_boundary":{"can_perform_review":False,"can_change_obligation":False,"can_notify":False,"can_send_message":False,"can_change_schedule":False,"can_select_attention":False,"can_form_intention":False,"can_propose":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class ProspectiveReviewSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"prospective_review_sessions.json"; self.clock=clock or _now; self.eligibility=TemporalEligibilityArbitrator(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,eligibility_id:str,cognitive_budget:str="bounded",operator_review_required:bool=False):
  event_id=_clean(event_id,180); eligibility_id=_clean(eligibility_id,220)
  if not event_id or not eligibility_id: raise ValueError("event and eligibility required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   er=next((x for x in self.eligibility.snapshot()["eligibility_records"] if x.get("eligibility_id")==eligibility_id),None)
   if not er: raise ValueError("unknown eligibility")
   allowed={"eligible_for_bounded_review","eligible_reduced_budget","requires_operator_review","missed_window"}
   if er.get("outcome") not in allowed: raise ValueError("eligibility outcome cannot open review session")
   semantic=_digest(eligibility_id,er.get("obligation_id")); duplicate=next((x for x in s["sessions"] if x.get("semantic_key")==semantic and x.get("state")=="open"),None)
   if duplicate: result={"status":"duplicate_session_ignored","session_id":duplicate["session_id"],"reason":"active_semantic_duplicate"}
   else:
    now=self.clock(); sid=f"prospective-review-{semantic[:24]}"; row={"session_id":sid,"semantic_key":semantic,"eligibility_id":eligibility_id,"obligation_id":er.get("obligation_id"),"eligibility_outcome":er.get("outcome"),"cognitive_budget":"reduced" if er.get("outcome")=="eligible_reduced_budget" else _clean(cognitive_budget,32),"operator_review_required":bool(operator_review_required or er.get("outcome")=="requires_operator_review"),"state":"open","opened_at":now,"updated_at":now,"acknowledged_at":"","deferred_until":"","deferral_reason_digest":"","review_performed":False,"underlying_state_changed":False,"notification_id":"","attention_id":"","intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":"","history":[{"change":"opened","occurred_at":now,"content_free":True}]}; s["sessions"]=(s["sessions"]+[row])[-int(s["controls"]["max_sessions"]):]; result={"status":"review_session_opened","session_id":sid,"reason":"eligible_structural_review_session"}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-2048:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def transition(self,event_id:str,session_id:str,*,new_state:str,deferred_until:str="",reason_code:str=""):
  if new_state not in SESSION_STATES-{"open"}: raise ValueError("invalid session state")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["sessions"] if x.get("session_id")==session_id),None)
   if not row: raise ValueError("unknown session")
   now=self.clock();row["state"]=new_state;row["updated_at"]=now
   if new_state=="acknowledged":row["acknowledged_at"]=now
   if new_state=="deferred":row["deferred_until"]=_clean(deferred_until,64);row["deferral_reason_digest"]=_digest(reason_code)
   row["history"].append({"change":new_state,"occurred_at":now,"content_free":True});result={"status":"review_session_transitioned","session_id":session_id,"state":new_state}
   s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":"review_session_transitioned","result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["sessions"]:counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("session_id","eligibility_id","obligation_id","eligibility_outcome","cognitive_budget","operator_review_required","state","opened_at","acknowledged_at","deferred_until","deferral_reason_digest","review_performed","underlying_state_changed","notification_id","attention_id","intention_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"session_count":len(s["sessions"]),"state_counts":counts,"recent_sessions":[{k:x.get(k) for k in keys} for x in s["sessions"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"private_content_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_prospective_review_session_inspection(runtime_root=None): return ProspectiveReviewSessionStore(runtime_root).inspection_summary()
