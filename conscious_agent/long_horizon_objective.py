from __future__ import annotations
"""Durable, bounded long-horizon objectives derived from established internal state."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from bounded_intention_formation import BoundedIntentionStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1109.0"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"objectives":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_objectives":256,"max_active":24,"max_resource_cost":0.8},"state_separation":{"attention_is_objective":False,"intention_is_objective":False,"objective_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class LongHorizonObjectiveStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"long_horizon_objectives.json";self.clock=clock or _now;self.intentions=BoundedIntentionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id,*,intention_id,purpose_category="follow_through",success_criteria=(),time_horizon="long",salience=.5,urgency=.4,confidence=.5,uncertainty=.5,resource_cost=.25,dependencies=(),blockers=(),eligible=True,reconsider_after=""):
  event_id=_clean(event_id,180); intention_id=_clean(intention_id,180); purpose=_clean(purpose_category,100)
  if not event_id or not intention_id: raise ValueError("event_id and intention_id required")
  criteria=tuple(_clean(x,300) for x in success_criteria if _clean(x,300)); deps=tuple(_clean(x,180) for x in dependencies if _clean(x,180)); blocks=tuple(_clean(x,180) for x in blockers if _clean(x,180))
  if not criteria: raise ValueError("at least one bounded success criterion required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   intention=next((x for x in self.intentions.snapshot().get("intentions",[]) if x.get("intention_id")==intention_id),None)
   if not intention or intention.get("active") is not True: result={"status":"objective_not_registered","reason":"intention_missing_or_inactive","objective_id":""}
   elif float(resource_cost)>float(s["controls"]["max_resource_cost"]): result={"status":"objective_not_registered","reason":"resource_cost_boundary","objective_id":""}
   elif sum(x.get("active_influence") is True for x in s["objectives"])>=int(s["controls"]["max_active"]): result={"status":"objective_not_registered","reason":"active_objective_limit","objective_id":""}
   else:
    key=_digest(intention_id,purpose,*criteria); existing=next((x for x in s["objectives"] if x.get("objective_key")==key),None)
    if existing: result={"status":"duplicate_objective_ignored","objective_id":existing["objective_id"]}
    else:
     now=self.clock(); oid=f"objective-{key[:24]}"; row={"objective_id":oid,"objective_key":key,"intention_id":intention_id,"agenda_id":intention.get("agenda_id"),"reflection_id":intention.get("reflection_id"),"subject_digest":intention.get("subject_digest"),"purpose_category":purpose,"success_criteria_digests":[_digest(x) for x in criteria],"success_criteria_count":len(criteria),"time_horizon":_clean(time_horizon,60),"salience":round(max(0,min(1,float(salience))),4),"urgency":round(max(0,min(1,float(urgency))),4),"confidence":round(max(0,min(1,float(confidence))),4),"uncertainty":round(max(0,min(1,float(uncertainty))),4),"resource_cost":round(max(0,min(1,float(resource_cost))),4),"dependencies":[_digest(x) for x in deps],"blockers":[_digest(x) for x in blocks],"eligible":bool(eligible),"active_influence":True,"state":"active" if not blocks else "blocked","created_at":now,"updated_at":now,"reconsider_after":_clean(reconsider_after,80),"review_count":0,"last_reviewed_at":"","deferral_count":0,"progress_evidence_count":0,"proposal_id":"","authorization_id":"","action_id":"","authority_granted":False,"provider_contacted":False,"update_history":[{"event_digest":_digest(event_id),"occurred_at":now,"change":"registered","content_free":True}]};s["objectives"]=(s["objectives"]+[row])[-int(s["controls"]["max_objectives"]):];result={"status":"objective_registered","objective_id":oid}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); rows=s["objectives"]; return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"objective_count":len(rows),"active_objective_count":sum(x.get("active_influence") is True for x in rows),"eligible_objective_count":sum(x.get("active_influence") is True and x.get("eligible") is True for x in rows),"blocked_objective_count":sum(x.get("state")=="blocked" for x in rows),"recent_objectives":[{k:x.get(k) for k in ("objective_id","intention_id","agenda_id","reflection_id","subject_digest","purpose_category","success_criteria_count","time_horizon","salience","urgency","confidence","uncertainty","resource_cost","state","eligible","active_influence","review_count","proposal_id","authorization_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_long_horizon_objective_inspection(runtime_root=None): return LongHorizonObjectiveStore(runtime_root).inspection_summary()
