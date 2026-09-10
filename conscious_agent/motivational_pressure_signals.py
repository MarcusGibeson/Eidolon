from __future__ import annotations
"""Content-free v1122.0 motivational-pressure signals; never select attention or initiative."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1122.0"; SCHEMA_VERSION="1"
SIGNAL_TYPES={"objective_pull","curiosity_pull","identity_continuity_pull","unfinished_work_pull","acknowledged_need","transient_urgency","motivation_decay","motivation_conflict","false_urgency_risk","lineage_gap"}
SOURCE_TYPES={"objective","milestone","curiosity","active_inquiry","identity_claim","self_model_claim","cognitive_work","prospective_obligation","recovery_review","operator_acknowledgement"}
STATES={"active","corrected","retracted","merged","superseded","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_select_attention":False,"can_initiate_communication":False,"can_create_notification":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_contact_provider":False}}
class MotivationalPressureSignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"motivational_pressure_signals.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,signal_type:str,source_type:str,source_id:str,related_source_type:str="",related_source_id:str="",durability:float=.5,urgency:float=.5,importance:float=.5,confidence:float=.5,uncertainty:float=.5,transient:bool=False,sensitivity:str="normal",structural_digest:str=""):
  event_id=_clean(event_id,180); signal_type=_clean(signal_type,80); source_type=_clean(source_type,60); source_id=_clean(source_id,220); related_source_type=_clean(related_source_type,60); related_source_id=_clean(related_source_id,220)
  if not event_id or signal_type not in SIGNAL_TYPES or source_type not in SOURCE_TYPES or not source_id: raise ValueError("valid event, signal type, and source lineage required")
  if related_source_type and related_source_type not in SOURCE_TYPES: raise ValueError("invalid related source type")
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); semantic=_digest(signal_type,source_type,source_id,related_source_type,related_source_id,transient,structural_digest)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   dup=next((x for x in s["signals"] if x.get("semantic_key")==semantic and x.get("state")=="active"),None)
   if dup: result={"status":"duplicate_signal_ignored","signal_id":dup["signal_id"]}
   else:
    now=self.clock(); sid=f"motivational-pressure-signal-{semantic[:24]}"; row={"signal_id":sid,"semantic_key":semantic,"signal_type":signal_type,"source_type":source_type,"source_id":source_id,"related_source_type":related_source_type,"related_source_id":related_source_id,"durability":clamp(durability),"urgency":clamp(urgency),"importance":clamp(importance),"confidence":clamp(confidence),"uncertainty":clamp(uncertainty),"transient":bool(transient),"sensitivity":_clean(sensitivity,32),"structural_digest":_clean(structural_digest,128),"state":"active","created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True}],"attention_id":"","initiative_id":"","message_id":"","notification_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["signals"].append(row); result={"status":"motivational_pressure_signal_registered","signal_id":sid}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def revise(self,event_id:str,signal_id:str,*,new_state:str,replacement_id:str=""):
  if new_state not in STATES-{"active"}: raise ValueError("invalid state")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["signals"] if x.get("signal_id")==signal_id),None)
   if not row: raise ValueError("unknown signal")
   now=self.clock(); row["state"]=new_state; row["replacement_id"]=_clean(replacement_id,220); row["updated_at"]=now; row["history"].append({"change":new_state,"occurred_at":now,"content_free":True}); result={"status":"motivational_pressure_signal_revised","signal_id":signal_id,"state":new_state}; s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["signals"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("signal_id","signal_type","source_type","source_id","related_source_type","related_source_id","durability","urgency","importance","confidence","uncertainty","transient","sensitivity","structural_digest","state","replacement_id","attention_id","initiative_id","message_id","notification_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(s["signals"]),"state_counts":counts,"recent_signals":[{k:x.get(k) for k in keys} for x in s["signals"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"motivation_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_motivational_pressure_signal_inspection(runtime_root=None): return MotivationalPressureSignalStore(runtime_root).inspection_summary()
