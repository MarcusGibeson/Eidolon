from __future__ import annotations
"""v1121.6 durable, content-free objective-coherence outcome lineage; never mutates objectives."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1121.6"; SCHEMA_VERSION="1"
OUTCOMES={"retain","reprioritization_candidate","dependency_repair_candidate","milestone_revision_candidate","clarify_abandonment","unresolved","deliberate_no_repair","requires_operator_review"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_reprioritize":False,"can_abandon_objective":False,"can_modify_dependency":False,"can_modify_milestone":False,"can_delete_history":False,"can_select_attention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class ObjectiveCoherenceOutcomeLineageStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"objective_coherence_outcome_lineage.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,objective_id:str,session_id:str,outcome:str,predecessor_outcome_id:str="",replacement_dependency_id:str="",replacement_milestone_id:str="",confidence:float=.5,uncertainty:float=.5):
  event_id=_clean(event_id,180); objective_id=_clean(objective_id,220); session_id=_clean(session_id,220); outcome=_clean(outcome,80)
  if not event_id or not objective_id or not session_id or outcome not in OUTCOMES: raise ValueError("valid structural lineage required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   structural=_digest(objective_id,session_id,outcome,predecessor_outcome_id,replacement_dependency_id,replacement_milestone_id)
   existing=next((x for x in s["outcomes"] if x.get("structural_digest")==structural),None)
   if existing: result={"status":"duplicate_outcome_suppressed","outcome_id":existing["outcome_id"]}
   else:
    now=self.clock(); oid=f"objective-coherence-outcome-{structural[:24]}"; row={"outcome_id":oid,"objective_id":objective_id,"session_id":session_id,"outcome":outcome,"predecessor_outcome_id":_clean(predecessor_outcome_id,220),"replacement_dependency_id":_clean(replacement_dependency_id,220),"replacement_milestone_id":_clean(replacement_milestone_id,220),"confidence":max(0,min(float(confidence),1)),"uncertainty":max(0,min(float(uncertainty),1)),"structural_digest":structural,"state":"recorded","created_at":now,"superseded_by_outcome_id":"","history":[{"change":"recorded","occurred_at":now,"content_free":True}],"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False,"history_deleted":False}; s["outcomes"].append(row); result={"status":"objective_coherence_outcome_lineage_recorded","outcome_id":oid,"objectives_reprioritized":False,"objective_abandoned":False}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def supersede(self,event_id:str,*,outcome_id:str,successor_outcome_id:str):
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["outcomes"] if x.get("outcome_id")==outcome_id),None); successor=next((x for x in s["outcomes"] if x.get("outcome_id")==successor_outcome_id),None)
   if not row or not successor: raise ValueError("known outcomes required")
   now=self.clock(); row["state"]="superseded";row["superseded_by_outcome_id"]=successor_outcome_id;row["history"].append({"change":"superseded","successor_outcome_id":successor_outcome_id,"occurred_at":now,"content_free":True});result={"status":"objective_coherence_outcome_superseded","outcome_id":outcome_id,"history_preserved":True,"objectives_reprioritized":False,"objective_abandoned":False};s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["outcomes"]: counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  keys=("outcome_id","objective_id","session_id","outcome","predecessor_outcome_id","replacement_dependency_id","replacement_milestone_id","confidence","uncertainty","state","superseded_by_outcome_id","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"outcome_count":len(s["outcomes"]),"outcome_counts":counts,"recent_outcomes":[{k:x.get(k) for k in keys} for x in s["outcomes"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"history_preserved":True,"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False,"raw_messages_exposed":False,"objective_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_objective_coherence_outcome_lineage_inspection(runtime_root=None): return ObjectiveCoherenceOutcomeLineageStore(runtime_root).inspection_summary()
