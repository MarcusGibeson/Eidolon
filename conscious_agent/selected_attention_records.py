from __future__ import annotations
"""v1124.0 durable selected-attention records; internal focus authority only."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1124.0"; SCHEMA_VERSION="1"
ELIGIBLE_OUTCOMES={"prioritize_for_bounded_attention"}
STATES={"active","suspended","completed","superseded","stale","retracted","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_create_reflection":False,"can_create_intention":False,"can_create_initiative":False,"can_send_message":False,"can_create_notification":False,"can_contact_provider":False,"can_browse":False,"can_change_schedule":False,"can_change_policy":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_promote":False,"can_certify":False}}
class SelectedAttentionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"selected_attention_records.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def select(self,event_id:str,*,outcome_id:str,candidate_id:str,session_id:str,outcome:str,importance:float=.5,relevance:float=.5,uncertainty:float=.5,recovery_compatible:bool=True,operator_review_required:bool=False,selection_reason:str="durable_salience_support"):
  event_id=_clean(event_id,180); outcome_id=_clean(outcome_id,220); candidate_id=_clean(candidate_id,220); session_id=_clean(session_id,220); outcome=_clean(outcome,80)
  if not all((event_id,outcome_id,candidate_id,session_id)): raise ValueError("exact attention lineage required")
  if outcome not in ELIGIBLE_OUTCOMES: return {"ok":True,"status":"attention_selection_ineligible","attention_selected":False}
  if operator_review_required: return {"ok":True,"status":"requires_operator_review","attention_selected":False}
  if not recovery_compatible: return {"ok":True,"status":"deferred_for_recovery","attention_selected":False}
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); importance=clamp(importance); relevance=clamp(relevance); uncertainty=clamp(uncertainty)
  if importance<.6 or relevance<.55 or uncertainty>.6: return {"ok":True,"status":"insufficient_selection_support","attention_selected":False}
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True,"attention_selected":prior["result"].get("attention_selected",False)}
   structural=_digest(outcome_id,candidate_id,session_id,selection_reason); existing=next((x for x in s["records"] if x.get("structural_digest")==structural),None)
   if existing: result={"status":"duplicate_selection_suppressed","attention_id":existing["attention_id"],"attention_selected":True}
   else:
    now=self.clock(); aid=f"selected-attention-{structural[:24]}"; row={"attention_id":aid,"outcome_id":outcome_id,"candidate_id":candidate_id,"session_id":session_id,"selection_reason":_clean(selection_reason,120),"importance":importance,"relevance":relevance,"uncertainty":uncertainty,"recovery_compatible":True,"state":"active","structural_digest":structural,"created_at":now,"updated_at":now,"superseded_by_attention_id":"","history":[{"change":"selected","occurred_at":now,"content_free":True}]}; s["records"].append(row); result={"status":"selected_attention_recorded","attention_id":aid,"attention_selected":True}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def transition(self,event_id:str,*,attention_id:str,state:str,successor_attention_id:str=""):
  state=_clean(state,60)
  if state not in STATES: raise ValueError("valid lifecycle state required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["records"] if x.get("attention_id")==attention_id),None)
   if not row: raise ValueError("known attention record required")
   now=self.clock(); row["state"]=state; row["updated_at"]=now
   if state=="superseded": row["superseded_by_attention_id"]=_clean(successor_attention_id,220)
   row["history"].append({"change":state,"successor_attention_id":_clean(successor_attention_id,220),"occurred_at":now,"content_free":True}); result={"status":"selected_attention_transition_recorded","attention_id":attention_id,"state":state,"history_preserved":True}; s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["records"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"attention_count":len(s["records"]),"state_counts":counts,"recent_attention":deepcopy(s["records"][-32:]),"authority_boundary":deepcopy(s["authority_boundary"]),"attention_selected":bool(s["records"]),"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"schedule_mutated":False,"policy_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"release_promoted":False,"release_certified":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_selected_attention_inspection(runtime_root=None): return SelectedAttentionStore(runtime_root).inspection_summary()
