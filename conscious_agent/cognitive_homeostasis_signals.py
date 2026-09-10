from __future__ import annotations
"""Durable, content-free cognitive homeostasis pressure signals with no authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1116.0"
ORIGINS={"load_checkpoint","work_checkpoint","coordination_review","consolidated_coordination","operator_constraint"}
STATES={"observed","superseded","corrected","retracted","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_signals":384,"high_pressure":0.72,"high_fragmentation":0.68,"low_recovery_margin":0.28},"authority_boundary":{"can_change_schedule":False,"can_select_attention":False,"can_form_intention":False,"can_create_decision":False,"can_browse":False,"can_contact_provider":False,"can_send_message":False,"can_authorize":False,"can_execute":False,"can_modify_files":False}}
class CognitiveHomeostasisSignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"cognitive_homeostasis_signals.json";self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_type:str,origin_id:str,load_pressure:float,fragmentation:float,recovery_margin:float,interruption_density:float=0.0,stale_work_ratio:float=0.0,uncertainty:float=0.5,structural_digest:str="") -> dict[str,Any]:
  event_id=_clean(event_id,180);origin_type=_clean(origin_type,64);origin_id=_clean(origin_id,220)
  if not event_id or origin_type not in ORIGINS or not origin_id: raise ValueError("valid event_id, origin_type, and origin_id required")
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   semantic=_digest(origin_type,origin_id,_clean(structural_digest,128))
   dup=next((x for x in s["signals"] if x.get("semantic_key")==semantic and x.get("state") not in {"retracted","retired"}),None)
   if dup: result={"status":"duplicate_signal_ignored","signal_id":dup["signal_id"],"reason":"semantic_duplicate"}
   else:
    now=self.clock();sid=f"homeostasis-signal-{semantic[:24]}";row={"signal_id":sid,"semantic_key":semantic,"origin_type":origin_type,"origin_id":origin_id,"structural_digest":_clean(structural_digest,128),"load_pressure":clamp(load_pressure),"fragmentation":clamp(fragmentation),"recovery_margin":clamp(recovery_margin),"interruption_density":clamp(interruption_density),"stale_work_ratio":clamp(stale_work_ratio),"uncertainty":clamp(uncertainty),"state":"observed","created_at":now,"updated_at":now,"history":[{"change":"observed","occurred_at":now,"content_free":True}],"schedule_id":"","attention_id":"","intention_id":"","decision_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""};s["signals"]=(s["signals"]+[row])[-int(s["controls"]["max_signals"]):];result={"status":"signal_registered","signal_id":sid,"reason":"structural_homeostasis_signal"}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["signals"]:counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("signal_id","origin_type","origin_id","structural_digest","load_pressure","fragmentation","recovery_margin","interruption_density","stale_work_ratio","uncertainty","state","schedule_id","attention_id","intention_id","decision_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"signal_count":len(s["signals"]),"state_counts":counts,"recent_signals":[{k:x.get(k) for k in keys} for x in s["signals"][-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_cognitive_homeostasis_signal_inspection(runtime_root=None): return CognitiveHomeostasisSignalStore(runtime_root).inspection_summary()
