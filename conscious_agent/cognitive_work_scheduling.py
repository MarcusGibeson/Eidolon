from __future__ import annotations
"""Durable, content-free scheduling of admitted cognitive work."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_demand_records import CognitiveDemandStore
CONTRACT_VERSION="v1115.3"
STATES={"scheduled","running","paused","resumable","completed","stale","retired","superseded","blocked"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"work_items":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_work_items":384,"max_concurrent":2,"default_slice_budget":0.25,"max_slice_budget":0.5,"stale_after_seconds":172800},"authority_boundary":{"can_select_attention":False,"can_form_intention":False,"can_browse":False,"can_contact_provider":False,"can_execute":False,"can_authorize":False,"can_modify_files":False}}
class CognitiveWorkScheduler:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"cognitive_work_schedule.json"; self.clock=clock or _now; self.demands=CognitiveDemandStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def schedule(self,event_id:str,*,demand_id:str,allocation_id:str,slice_budget:float=.25,priority_band:str="normal",resume_token:str="") -> dict[str,Any]:
  event_id=_clean(event_id,180); demand_id=_clean(demand_id,220); allocation_id=_clean(allocation_id,220)
  if not event_id or not demand_id or not allocation_id: raise ValueError("event_id, demand_id, and allocation_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   demand=next((x for x in self.demands.snapshot()["records"] if x.get("demand_id")==demand_id),None)
   if not demand or demand.get("allocation_id")!=allocation_id or demand.get("state") not in {"admitted","reduced_budget"}: result={"status":"schedule_rejected","reason":"admitted_demand_with_exact_allocation_required","work_id":""}
   else:
    sem=_digest(demand_id,allocation_id); dup=next((x for x in s["work_items"] if x.get("semantic_key")==sem and x.get("state") not in {"completed","retired","stale","superseded"}),None)
    if dup: result={"status":"duplicate_work_ignored","reason":"semantic_duplicate","work_id":dup["work_id"]}
    else:
     now=self.clock(); wid=f"cognitive-work-{sem[:24]}"; budget=round(max(.01,min(float(slice_budget),float(s["controls"]["max_slice_budget"]))),4)
     row={"work_id":wid,"semantic_key":sem,"demand_id":demand_id,"allocation_id":allocation_id,"origin_type":demand.get("origin_type"),"origin_id":demand.get("origin_id"),"priority_band":_clean(priority_band,24),"slice_budget":budget,"state":"scheduled","interrupt_count":0,"resume_count":0,"resume_token_digest":_digest(resume_token) if resume_token else "","last_progress_digest":"","attention_id":"","intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"change":"scheduled","occurred_at":now,"content_free":True}]}
     s["work_items"]=(s["work_items"]+[row])[-int(s["controls"]["max_work_items"]):]; result={"status":"work_scheduled","reason":"bounded_schedule_created","work_id":wid}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def transition(self,event_id:str,*,work_id:str,state:str,progress_digest:str="",reason_code:str="bounded_transition"):
  if state not in STATES: raise ValueError("invalid work state")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["work_items"] if x.get("work_id")==work_id),None)
   if not row: result={"status":"transition_rejected","reason":"unknown_work"}
   else:
    now=self.clock(); row["state"]=state; row["updated_at"]=now
    if progress_digest: row["last_progress_digest"]=_clean(progress_digest,128)
    row["history"].append({"change":state,"reason_code":_clean(reason_code,80),"occurred_at":now,"content_free":True}); result={"status":"work_transitioned","work_id":work_id,"state":state}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={k:sum(x.get("state")==k for x in s["work_items"]) for k in STATES}; keys=("work_id","demand_id","allocation_id","origin_type","origin_id","priority_band","slice_budget","state","interrupt_count","resume_count","resume_token_digest","last_progress_digest","attention_id","intention_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"work_item_count":len(s["work_items"]),"state_counts":counts,"recent_work_items":[{k:x.get(k) for k in keys} for x in s["work_items"][-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"raw_content_exposed":False,"hidden_reasoning_exposed":False}
def build_cognitive_work_scheduling_inspection(runtime_root=None): return CognitiveWorkScheduler(runtime_root).inspection_summary()
