from __future__ import annotations
"""Privacy-safe completion and interruption outcome evidence for cognitive work."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_work_scheduling import CognitiveWorkScheduler
CONTRACT_VERSION="v1115.6"
OUTCOMES={"completed_useful","completed_partial","completed_no_gain","interrupted_resumed","interrupted_abandoned","stale_retired","blocked","unknown"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_outcomes":512},"authority_boundary":{"can_select_attention":False,"can_form_intention":False,"can_change_schedule":False,"can_execute":False,"can_authorize":False}}
class CognitiveWorkOutcomeLedger:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"cognitive_work_outcomes.json"; self.clock=clock or _now; self.scheduler=CognitiveWorkScheduler(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,work_id:str,outcome:str,evidence_digest:str="",confidence:float=.5,corrects_outcome_id:str="",retracted:bool=False):
  if outcome not in OUTCOMES: raise ValueError("invalid outcome")
  event_id=_clean(event_id,180); work_id=_clean(work_id,220)
  if not event_id or not work_id: raise ValueError("event_id and work_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   work=next((x for x in self.scheduler.snapshot()["work_items"] if x.get("work_id")==work_id),None)
   if not work: result={"status":"outcome_rejected","reason":"unknown_work","outcome_id":""}
   elif outcome.startswith("completed") and work.get("state")!="completed": result={"status":"outcome_rejected","reason":"completed_state_required","outcome_id":""}
   else:
    sem=_digest(work_id,outcome,evidence_digest,corrects_outcome_id,retracted); dup=next((x for x in s["outcomes"] if x.get("semantic_key")==sem),None)
    if dup: result={"status":"duplicate_outcome_ignored","reason":"semantic_duplicate","outcome_id":dup["outcome_id"]}
    else:
     now=self.clock(); oid=f"cognitive-work-outcome-{sem[:24]}"; row={"outcome_id":oid,"semantic_key":sem,"work_id":work_id,"demand_id":work.get("demand_id"),"allocation_id":work.get("allocation_id"),"outcome":outcome,"confidence":round(max(0,min(float(confidence),1)),4),"evidence_digest":_clean(evidence_digest,128),"corrects_outcome_id":_clean(corrects_outcome_id,220),"retracted":bool(retracted),"active_influence":not retracted,"created_at":now,"content_free":True}
     if corrects_outcome_id:
      old=next((x for x in s["outcomes"] if x.get("outcome_id")==corrects_outcome_id),None)
      if old: old["active_influence"]=False; old["corrected_by_outcome_id"]=oid
     s["outcomes"]=(s["outcomes"]+[row])[-int(s["controls"]["max_outcomes"]):]; result={"status":"outcome_recorded","reason":"structural_evidence_recorded","outcome_id":oid}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={k:sum(x.get("outcome")==k for x in s["outcomes"] if x.get("active_influence")) for k in OUTCOMES}; keys=("outcome_id","work_id","demand_id","allocation_id","outcome","confidence","evidence_digest","corrects_outcome_id","retracted","active_influence")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"outcome_count":len(s["outcomes"]),"active_outcome_count":sum(bool(x.get("active_influence")) for x in s["outcomes"]),"outcome_counts":counts,"recent_outcomes":[{k:x.get(k) for k in keys} for x in s["outcomes"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"raw_content_exposed":False,"hidden_reasoning_exposed":False}
def build_cognitive_work_outcome_inspection(runtime_root=None): return CognitiveWorkOutcomeLedger(runtime_root).inspection_summary()
