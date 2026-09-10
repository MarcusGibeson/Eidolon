from __future__ import annotations
"""Durable, content-free prospective obligations without reminder or action authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1117.0"
ORIGIN_TYPES={"objective","milestone","intention_reconsideration","active_inquiry","decision_commitment","scheduled_cognitive_work","recovery_review","belief_reconsideration","self_model_reconsideration","operator_confirmed_review"}
CATEGORIES={"review","reconsideration","evidence_follow_up","commitment_check","recovery_check","milestone_check","operator_review"}
STATES={"active","corrected","retracted","superseded","stale","obsolete","expired","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"obligations":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_obligations":512},"authority_boundary":{"can_notify":False,"can_send_message":False,"can_browse":False,"can_contact_provider":False,"can_execute":False,"can_modify_schedule":False,"can_select_attention":False,"can_form_intention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False}}
class ProspectiveObligationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"prospective_obligations.json"; self.clock=clock or _now
 def _load(self):
  state=load_json_file(self.path,_default(),expected_type=dict)
  if state.get("schema_version")!="1": state=_default()
  for k,v in _default().items(): state.setdefault(k,deepcopy(v))
  return state
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_type:str,origin_id:str,category:str,earliest_review_at:str,target_window_start:str,target_window_end:str,stale_after:str="",expires_at:str="",precondition_ids:list[str]|None=None,dependency_ids:list[str]|None=None,importance:float=.5,urgency:float=.5,sensitivity:str="normal",interruptibility:str="interruptible",confidence:float=.5,uncertainty:float=.5,structural_digest:str="") -> dict[str,Any]:
  event_id=_clean(event_id,180); origin_type=_clean(origin_type,64); origin_id=_clean(origin_id,220); category=_clean(category,64)
  if not event_id or origin_type not in ORIGIN_TYPES or not origin_id or category not in CATEGORIES: raise ValueError("valid event, origin, and category required")
  ids=lambda xs:list(dict.fromkeys(_clean(x,220) for x in (xs or []) if _clean(x,220)))
  preconditions,dependencies=ids(precondition_ids),ids(dependency_ids)
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4)
  semantic=_digest(origin_type,origin_id,category,earliest_review_at,target_window_start,target_window_end,stale_after,expires_at,structural_digest)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in state["obligations"] if x.get("semantic_key")==semantic and x.get("state")=="active"),None)
   if duplicate: result={"status":"duplicate_obligation_ignored","obligation_id":duplicate["obligation_id"],"reason":"semantic_duplicate"}
   else:
    now=self.clock(); oid=f"prospective-obligation-{semantic[:24]}"; row={"obligation_id":oid,"semantic_key":semantic,"origin_type":origin_type,"origin_id":origin_id,"category":category,"earliest_review_at":_clean(earliest_review_at,64),"target_window_start":_clean(target_window_start,64),"target_window_end":_clean(target_window_end,64),"stale_after":_clean(stale_after,64),"expires_at":_clean(expires_at,64),"precondition_ids":preconditions,"dependency_ids":dependencies,"importance":clamp(importance),"urgency":clamp(urgency),"sensitivity":_clean(sensitivity,32),"interruptibility":_clean(interruptibility,32),"confidence":clamp(confidence),"uncertainty":clamp(uncertainty),"structural_digest":_clean(structural_digest,128),"state":"active","created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True}],"notification_id":"","attention_id":"","intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; state["obligations"]=(state["obligations"]+[row])[-int(state["controls"]["max_obligations"]):]; result={"status":"obligation_registered","obligation_id":oid,"reason":"structural_future_review_obligation"}
   now=self.clock(); state["processed_events"]=(state["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-2048:]; state["revision"]+=1; state["updated_at"]=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def revise(self,event_id:str,obligation_id:str,*,new_state:str,replacement_id:str=""):
  if new_state not in STATES-{"active"}: raise ValueError("invalid lifecycle state")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in state["obligations"] if x.get("obligation_id")==obligation_id),None)
   if not row: raise ValueError("unknown obligation")
   now=self.clock(); row["state"]=new_state; row["updated_at"]=now; row["replacement_id"]=_clean(replacement_id,220); row["history"].append({"change":new_state,"occurred_at":now,"content_free":True}); result={"status":"obligation_revised","obligation_id":obligation_id,"state":new_state}
   state["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); state["revision"]+=1; state["updated_at"]=now; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {"ok":True,"status":"obligation_revised","result":result,"idempotent":False}
 def inspection_summary(self):
  state=self._load(); counts={}
  for row in state["obligations"]: counts[row.get("state")]=counts.get(row.get("state"),0)+1
  keys=("obligation_id","origin_type","origin_id","category","earliest_review_at","target_window_start","target_window_end","stale_after","expires_at","precondition_ids","dependency_ids","importance","urgency","sensitivity","interruptibility","confidence","uncertainty","structural_digest","state","replacement_id","notification_id","attention_id","intention_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":state["revision"],"obligation_count":len(state["obligations"]),"state_counts":counts,"recent_obligations":[{k:x.get(k) for k in keys} for x in state["obligations"][-24:]],"authority_boundary":deepcopy(state["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_prospective_obligation_inspection(runtime_root=None): return ProspectiveObligationStore(runtime_root).inspection_summary()
