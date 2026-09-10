from __future__ import annotations
"""Durable, content-free repeated-overload pattern evidence without scheduling authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sustainable_cognitive_windows import SustainableCognitiveWindowStore
CONTRACT_VERSION="v1116.6"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"patterns":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_outcomes":2,"minimum_ineffective":2,"max_patterns":384},"authority_boundary":{"can_change_schedule":False,"can_pause_work":False,"can_resume_work":False,"can_adapt_behavior":False,"can_select_attention":False,"can_authorize":False,"can_execute":False}}
class CognitiveOverloadPatternStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"cognitive_overload_patterns.json"; self.clock=clock or _now; self.windows=SustainableCognitiveWindowStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def evaluate(self,event_id:str,*,recovery_id:str="",window_outcome_ids:list[str]|None=None):
  event_id=_clean(event_id,180); ids=sorted({_clean(x,220) for x in (window_outcome_ids or []) if _clean(x,220)})
  if not event_id: raise ValueError("event_id required")
  outcomes=self.windows.snapshot()["outcomes"]
  eligible=[x for x in outcomes if (not recovery_id or x.get("recovery_id")==recovery_id) and (not ids or x.get("outcome_id") in ids) and x.get("outcome") not in {"corrected","retracted"}]
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   ineffective=sum(x.get("outcome")=="ineffective" for x in eligible); unknown=sum(x.get("outcome")=="unknown" for x in eligible); c=s["controls"]
   if len(eligible)<int(c["minimum_outcomes"]): status,reason="insufficient_evidence","too_few_outcomes"
   elif ineffective<int(c["minimum_ineffective"]): status,reason="pattern_not_supported","insufficient_repeated_overload"
   else: status,reason="repeated_overload_supported","multiple_ineffective_recovery_windows"
   semantic=_digest(recovery_id,*(x.get("outcome_id") for x in eligible),status); dup=next((x for x in s["patterns"] if x.get("semantic_key")==semantic and x.get("active",True)),None)
   if dup: result={"status":"duplicate_pattern_ignored","pattern_id":dup["pattern_id"],"reason":"semantic_duplicate"}
   else:
    now=self.clock(); pid=f"overload-pattern-{semantic[:24]}"; row={"pattern_id":pid,"semantic_key":semantic,"recovery_id":_clean(recovery_id,220),"window_outcome_ids":[x.get("outcome_id") for x in eligible],"outcome_count":len(eligible),"ineffective_count":ineffective,"unknown_count":unknown,"status":status,"reason":reason,"confidence":round(min(0.9,ineffective/max(1,len(eligible))),4) if status=="repeated_overload_supported" else 0.0,"active":status=="repeated_overload_supported","created_at":now,"content_free":True,"schedule_changed":False,"work_paused":False,"work_resumed":False,"adaptation_applied":False,"authorization_id":"","action_id":""}; s["patterns"]=(s["patterns"]+[row])[-int(c["max_patterns"]):]; result={"status":"overload_pattern_evaluated","pattern_id":pid,"pattern_status":status,"reason":reason}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:]; s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["patterns"]: counts[x.get("status")]=counts.get(x.get("status"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"pattern_count":len(s["patterns"]),"status_counts":counts,"recent_patterns":deepcopy(s["patterns"][-24:]),"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"missing_feedback_is_success":False,"raw_messages_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_cognitive_overload_pattern_inspection(runtime_root=None): return CognitiveOverloadPatternStore(runtime_root).inspection_summary()
