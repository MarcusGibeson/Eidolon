from __future__ import annotations
"""Bounded internal milestone decomposition for durable objectives."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from long_horizon_objective import LongHorizonObjectiveStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1109.3"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"milestones":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_milestones":512,"max_active_per_objective":8,"max_depth":1,"max_resource_cost":0.45},"state_separation":{"objective_is_milestone":False,"milestone_is_task":False,"milestone_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class ObjectiveMilestoneStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"objective_milestones.json";self.clock=clock or _now;self.objectives=LongHorizonObjectiveStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def decompose(self,event_id,*,objective_id,milestones,resource_cost=.2):
  event_id=_clean(event_id,180);objective_id=_clean(objective_id,180);items=[_clean(x,300) for x in milestones if _clean(x,300)]
  if not event_id or not objective_id:raise ValueError("event_id and objective_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_decomposition_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   objective=next((x for x in self.objectives.snapshot().get("objectives",[]) if x.get("objective_id")==objective_id),None)
   if not objective or not objective.get("active_influence"):result={"status":"decomposition_rejected","reason":"objective_missing_or_inactive","milestone_ids":[]}
   elif not items:result={"status":"deliberate_no_decomposition","reason":"no_bounded_milestones","milestone_ids":[]}
   elif len(items)>int(s["controls"]["max_active_per_objective"]):result={"status":"decomposition_rejected","reason":"breadth_boundary","milestone_ids":[]}
   elif float(resource_cost)>float(s["controls"]["max_resource_cost"]):result={"status":"decomposition_rejected","reason":"resource_boundary","milestone_ids":[]}
   else:
    now=self.clock();ids=[]
    for index,text in enumerate(items):
     key=_digest(objective_id,text);existing=next((x for x in s["milestones"] if x.get("milestone_key")==key),None)
     if existing:ids.append(existing["milestone_id"]);continue
     mid=f"milestone-{key[:24]}";ids.append(mid);s["milestones"].append({"milestone_id":mid,"milestone_key":key,"objective_id":objective_id,"intention_id":objective.get("intention_id"),"subject_digest":objective.get("subject_digest"),"criterion_digest":_digest(text),"sequence":index+1,"depth":1,"state":"active","eligible":True,"active_influence":True,"resource_cost":round(max(0,min(1,float(resource_cost)/max(1,len(items)))),4),"dependency_ids":[ids[-2]] if len(ids)>1 else [],"progress_state":"unknown","progress_evidence_count":0,"created_at":now,"updated_at":now,"completed_at":"","proposal_id":"","authorization_id":"","action_id":"","authority_granted":False,"update_history":[{"event_digest":_digest(event_id),"occurred_at":now,"change":"registered","content_free":True}]})
    s["milestones"]=s["milestones"][-int(s["controls"]["max_milestones"]):];result={"status":"milestones_registered","milestone_ids":ids}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["milestones"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"milestone_count":len(rows),"active_milestone_count":sum(x.get("active_influence") is True for x in rows),"completed_milestone_count":sum(x.get("state")=="completed" for x in rows),"recent_milestones":[{k:x.get(k) for k in ("milestone_id","objective_id","intention_id","subject_digest","criterion_digest","sequence","depth","state","eligible","active_influence","resource_cost","dependency_ids","progress_state","progress_evidence_count","proposal_id","authorization_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_objective_milestone_inspection(runtime_root=None): return ObjectiveMilestoneStore(runtime_root).inspection_summary()
