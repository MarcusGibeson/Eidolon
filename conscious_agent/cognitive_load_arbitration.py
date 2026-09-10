from __future__ import annotations
"""Deterministic, bounded cognitive-load admission with fairness and deliberate idle capacity."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_demand_records import CognitiveDemandStore
CONTRACT_VERSION="v1115.1"
OUTCOMES={"admitted","reduced_budget","deferred","queued","superseded","merged","blocked_dependency","blocked_sensitivity","requires_operator_review","deliberate_idle"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"allocations":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"total_capacity":1.0,"max_admitted":3,"minimum_idle_reserve":0.10,"high_sensitivity":0.75,"starvation_age_bonus":0.18,"max_reflection_share":0.40,"minimum_admit_score":0.36},"authority_boundary":{"can_select_attention":False,"can_form_intention":False,"can_create_decision":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_contact_provider":False}}
class CognitiveLoadArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"cognitive_load_arbitration.json";self.clock=clock or _now;self.demands=CognitiveDemandStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def allocate(self,event_id:str,*,demand_ids:list[str],capacity:float=1.0,dependency_blocked:list[str]|None=None,operator_review_ids:list[str]|None=None,force_idle:bool=False):
  event_id=_clean(event_id,180);ids=list(dict.fromkeys(_clean(x,220) for x in demand_ids if _clean(x,220)))
  if not event_id:raise ValueError("event_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   rows=[x for x in self.demands.snapshot()["records"] if x.get("demand_id") in ids and x.get("state")=="candidate"]
   outcomes={};budgets={};reasons={};capacity=max(0.0,min(float(capacity),1.0));available=max(0.0,capacity-float(s["controls"]["minimum_idle_reserve"]));blocked=set(dependency_blocked or []);review=set(operator_review_ids or [])
   if force_idle or not rows:
    result={"status":"allocation_completed","allocation_id":f"cognitive-allocation-{_digest(event_id)[:24]}","outcomes":{},"budgets":{},"reason":"deliberate_idle_capacity","idle_capacity":round(capacity,4),"attention_id":"","intention_id":"","decision_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}
   else:
    scored=[]
    for row in rows:
     did=row["demand_id"]
     if did in blocked:outcomes[did]="blocked_dependency";budgets[did]=0.0;reasons[did]="dependency_blocked";continue
     if did in review:outcomes[did]="requires_operator_review";budgets[did]=0.0;reasons[did]="operator_review_required";continue
     if float(row["sensitivity"])>=s["controls"]["high_sensitivity"]:outcomes[did]="blocked_sensitivity";budgets[did]=0.0;reasons[did]="sensitivity_restraint";continue
     age_bonus=min(.18,.03*len(row.get("history",[])));score=round(.25*float(row["importance"])+.20*float(row["urgency"])+.15*float(row["deadline_pressure"])+.12*float(row["freshness"])+.10*(1-float(row["cognitive_cost"]))+.08*float(row["interruptibility"])+age_bonus,4);scored.append((score,did,row))
    scored.sort(key=lambda x:(-x[0],x[1]));admitted=0;used=0.0;seen_overlap={};reflection_used=0.0
    for score,did,row in scored:
     overlap=row.get("overlap_key") or row.get("semantic_key")
     if overlap in seen_overlap:outcomes[did]="merged";budgets[did]=0.0;reasons[did]="semantic_overlap";continue
     if score<s["controls"]["minimum_admit_score"]:outcomes[did]="deferred";budgets[did]=0.0;reasons[did]="below_admission_threshold";continue
     requested=max(.05,float(row["cognitive_cost"]));remaining=max(0.0,available-used)
     if row.get("origin_type")=="reflection" and reflection_used+requested>capacity*s["controls"]["max_reflection_share"]:outcomes[did]="queued";budgets[did]=0.0;reasons[did]="reflection_share_cap";continue
     if admitted>=int(s["controls"]["max_admitted"]) or remaining<=0:outcomes[did]="queued";budgets[did]=0.0;reasons[did]="capacity_exhausted";continue
     grant=min(requested,remaining);outcomes[did]="admitted" if grant>=requested else "reduced_budget";budgets[did]=round(grant,4);reasons[did]="bounded_capacity_allocation";used+=grant;admitted+=1;seen_overlap[overlap]=did
     if row.get("origin_type")=="reflection":reflection_used+=grant
    aid=f"cognitive-allocation-{_digest(event_id,*ids)[:24]}"
    for did,out in outcomes.items():self.demands.apply_allocation(did,allocation_id=aid,outcome=out,budget=budgets[did],reason=reasons[did])
    result={"status":"allocation_completed","allocation_id":aid,"outcomes":outcomes,"budgets":budgets,"reasons":reasons,"reason":"bounded_fair_allocation","idle_capacity":round(max(0.0,capacity-used),4),"attention_id":"","intention_id":"","decision_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}
   now=self.clock();s["allocations"]=(s["allocations"]+[{**result,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}])[-512:];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for row in s["allocations"]:
   for out in row.get("outcomes",{}).values():counts[out]=counts.get(out,0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"allocation_count":len(s["allocations"]),"outcome_counts":counts,"recent_allocations":[{k:x.get(k) for k in ("allocation_id","outcomes","budgets","reasons","reason","idle_capacity","attention_id","intention_id","decision_id","proposal_id","approval_id","authorization_id","action_id")} for x in s["allocations"][-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_cognitive_load_arbitration_inspection(runtime_root=None):return CognitiveLoadArbitrator(runtime_root).inspection_summary()
