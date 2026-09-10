from __future__ import annotations
"""Durable, content-free cognitive demand records with no external authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1115.0"
ORIGIN_TYPES={"agenda","reflection","intention","objective","milestone","active_inquiry","reconsideration","decision_commitment","behavioral_review","governance_obligation"}
STATES={"candidate","admitted","reduced_budget","deferred","queued","superseded","merged","blocked_dependency","blocked_sensitivity","requires_operator_review","deliberate_idle","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_records":384,"max_cost":1.0,"max_urgency":1.0,"max_importance":1.0,"max_deadline_pressure":1.0},"state_separation":{"demand_is_attention":False,"attention_is_intention":False,"intention_is_decision":False,"decision_is_proposal":False,"proposal_is_approval":False,"approval_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_select_attention":False,"can_browse":False,"can_contact_provider":False,"can_ask_user":False,"can_send_message":False,"can_execute":False,"can_authorize":False,"can_modify_files":False}}
class CognitiveDemandStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"cognitive_demands.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_type:str,origin_id:str,urgency:float=.5,importance:float=.5,cognitive_cost:float=.5,freshness:float=.5,deadline_pressure:float=0.0,interruptibility:float=.5,sensitivity:float=0.0,dependency_digests:list[str]|None=None,deadline_at:str="",overlap_key:str="") -> dict[str,Any]:
  event_id=_clean(event_id,180); origin_type=_clean(origin_type,48); origin_id=_clean(origin_id,220)
  if not event_id or origin_type not in ORIGIN_TYPES or not origin_id: raise ValueError("valid event_id, origin_type, and origin_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   semantic=_digest(origin_type,origin_id,_clean(overlap_key,128),*(sorted(dependency_digests or [])))
   dup=next((x for x in s["records"] if x.get("semantic_key")==semantic and x.get("state")!="retired"),None)
   if dup: result={"status":"duplicate_demand_ignored","reason":"semantic_duplicate","demand_id":dup["demand_id"]}
   else:
    clamp=lambda x: round(max(0.0,min(float(x),1.0)),4); now=self.clock(); did=f"cognitive-demand-{semantic[:24]}"
    row={"demand_id":did,"semantic_key":semantic,"overlap_key":_clean(overlap_key,128),"origin_type":origin_type,"origin_id":origin_id,"urgency":clamp(urgency),"importance":clamp(importance),"cognitive_cost":clamp(cognitive_cost),"freshness":clamp(freshness),"deadline_pressure":clamp(deadline_pressure),"interruptibility":clamp(interruptibility),"sensitivity":clamp(sensitivity),"dependency_digests":sorted(set(_clean(x,128) for x in (dependency_digests or []) if _clean(x,128))),"deadline_at":_clean(deadline_at,64),"state":"candidate","allocation_id":"","attention_id":"","intention_id":"","decision_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"change":"registered_candidate","occurred_at":now,"content_free":True}]}
    s["records"]=(s["records"]+[row])[-int(s["controls"]["max_records"]):]; result={"status":"demand_registered","reason":"structural_demand_registered","demand_id":did}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def apply_allocation(self,demand_id:str,*,allocation_id:str,outcome:str,budget:float=0.0,reason:str=""):
  if outcome not in STATES-{"candidate"}: raise ValueError("invalid allocation outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); row=next((x for x in s["records"] if x.get("demand_id")==demand_id),None)
   if not row:return False
   now=self.clock();row["state"]=outcome;row["allocation_id"]=_clean(allocation_id,220);row["allocated_budget"]=round(max(0.0,min(float(budget),1.0)),4);row["updated_at"]=now;row["history"].append({"change":outcome,"reason":_clean(reason,96),"allocated_budget":row["allocated_budget"],"occurred_at":now,"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return True
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["records"]:counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("demand_id","origin_type","origin_id","urgency","importance","cognitive_cost","freshness","deadline_pressure","interruptibility","sensitivity","dependency_digests","deadline_at","state","allocation_id","allocated_budget","attention_id","intention_id","decision_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"record_count":len(s["records"]),"candidate_count":counts.get("candidate",0),"state_counts":counts,"recent_records":[{k:x.get(k) for k in keys} for x in s["records"][-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_cognitive_demand_inspection(runtime_root=None): return CognitiveDemandStore(runtime_root).inspection_summary()
