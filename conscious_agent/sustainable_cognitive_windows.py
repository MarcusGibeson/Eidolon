from __future__ import annotations
"""Content-free recovery outcome evidence and sustainable cognitive-window evaluation."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_recovery_lifecycle import CognitiveRecoveryLifecycleStore
CONTRACT_VERSION="v1116.4"
OUTCOMES={"effective","partially_effective","ineffective","unknown","corrected","retracted"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_observation_count":1,"effective_delta":0.2,"partial_delta":0.08,"max_outcomes":512},"authority_boundary":{"can_change_schedule":False,"can_pause_work":False,"can_resume_work":False,"can_adapt_behavior":False,"can_select_attention":False,"can_authorize":False,"can_execute":False}}
class SustainableCognitiveWindowStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"sustainable_cognitive_windows.json";self.clock=clock or _now;self.lifecycle=CognitiveRecoveryLifecycleStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def record(self,event_id:str,*,recovery_id:str,before_pressure:float|None=None,after_pressure:float|None=None,before_margin:float|None=None,after_margin:float|None=None,observation_count:int=0,corrects_outcome_id:str="",retracted:bool=False):
  event_id=_clean(event_id,180);recovery_id=_clean(recovery_id,220)
  if not event_id or not recovery_id:raise ValueError("event_id and recovery_id required")
  records=self.lifecycle.snapshot()["records"]
  if not any(x.get("recovery_id")==recovery_id for x in records):raise ValueError("unknown recovery_id")
  clamp=lambda x:None if x is None else round(max(0.0,min(float(x),1.0)),4)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   bp,ap,bm,am=map(clamp,(before_pressure,after_pressure,before_margin,after_margin));c=s["controls"]
   if retracted:outcome="retracted";reason="explicit_retraction"
   elif corrects_outcome_id:outcome="corrected";reason="explicit_correction"
   elif observation_count<int(c["minimum_observation_count"]) or None in {bp,ap,bm,am}:outcome="unknown";reason="missing_structural_feedback"
   else:
    improvement=(bp-ap)+(am-bm)
    if improvement>=float(c["effective_delta"]):outcome="effective";reason="pressure_reduced_and_margin_improved"
    elif improvement>=float(c["partial_delta"]):outcome="partially_effective";reason="bounded_partial_improvement"
    else:outcome="ineffective";reason="no_supported_improvement"
   semantic=_digest(recovery_id,bp,ap,bm,am,observation_count,corrects_outcome_id,retracted);dup=next((x for x in s["outcomes"] if x.get("semantic_key")==semantic and x.get("outcome")!="retracted"),None)
   if dup:result={"status":"duplicate_window_outcome_ignored","outcome_id":dup["outcome_id"],"reason":"semantic_duplicate"}
   else:
    now=self.clock();oid=f"sustainable-window-{semantic[:24]}";row={"outcome_id":oid,"semantic_key":semantic,"recovery_id":recovery_id,"before_pressure":bp,"after_pressure":ap,"before_margin":bm,"after_margin":am,"observation_count":max(0,int(observation_count)),"outcome":outcome,"reason":reason,"corrects_outcome_id":_clean(corrects_outcome_id,220),"created_at":now,"content_free":True,"schedule_changed":False,"work_paused":False,"work_resumed":False,"adaptation_applied":False,"attention_id":"","authorization_id":"","action_id":""};s["outcomes"]=(s["outcomes"]+[row])[-int(c["max_outcomes"]):];result={"status":"window_outcome_recorded","outcome_id":oid,"outcome":outcome,"reason":reason}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["outcomes"]:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  keys=("outcome_id","recovery_id","before_pressure","after_pressure","before_margin","after_margin","observation_count","outcome","reason","corrects_outcome_id","schedule_changed","work_paused","work_resumed","adaptation_applied","attention_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"outcome_count":len(s["outcomes"]),"outcome_counts":counts,"recent_outcomes":[{k:x.get(k) for k in keys} for x in s["outcomes"][-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"missing_feedback_is_positive":False,"raw_messages_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_sustainable_cognitive_window_inspection(runtime_root=None):return SustainableCognitiveWindowStore(runtime_root).inspection_summary()
