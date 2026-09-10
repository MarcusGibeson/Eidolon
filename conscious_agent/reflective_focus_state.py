from __future__ import annotations
"""v1124.1 content-free reflective focus-state lineage over selected attention."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1124.1"; SCHEMA_VERSION="1"; STATES={"engaged","paused","interrupted","resumable","completed","superseded","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"focus_states":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_create_reflection":False,"can_create_intention":False,"can_create_initiative":False,"can_send_message":False,"can_create_notification":False,"can_contact_provider":False,"can_browse":False,"can_execute":False}}
class ReflectiveFocusStateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflective_focus_state.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,attention_id:str,state:str="engaged",focus_budget:int=1,interruptible:bool=True,recovery_compatible:bool=True,predecessor_focus_id:str=""):
  event_id=_clean(event_id,180); attention_id=_clean(attention_id,220); state=_clean(state,60)
  if not event_id or not attention_id or state not in STATES: raise ValueError("valid focus lineage required")
  focus_budget=max(1,min(int(focus_budget),8))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   structural=_digest(attention_id,state,focus_budget,interruptible,recovery_compatible,predecessor_focus_id); existing=next((x for x in s["focus_states"] if x.get("structural_digest")==structural),None)
   if existing: result={"status":"duplicate_focus_state_suppressed","focus_id":existing["focus_id"]}
   else:
    now=self.clock(); fid=f"reflective-focus-{structural[:24]}"; row={"focus_id":fid,"attention_id":attention_id,"state":state,"focus_budget":focus_budget,"interruptible":bool(interruptible),"recovery_compatible":bool(recovery_compatible),"predecessor_focus_id":_clean(predecessor_focus_id,220),"structural_digest":structural,"created_at":now,"updated_at":now,"history":[{"change":state,"occurred_at":now,"content_free":True}]}; s["focus_states"].append(row); result={"status":"reflective_focus_state_recorded","focus_id":fid}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["focus_states"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"focus_count":len(s["focus_states"]),"state_counts":counts,"recent_focus_states":deepcopy(s["focus_states"][-32:]),"authority_boundary":deepcopy(s["authority_boundary"]),"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_reflective_focus_state_inspection(runtime_root=None): return ReflectiveFocusStateStore(runtime_root).inspection_summary()
