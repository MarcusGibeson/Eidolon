from __future__ import annotations
"""Evidence-disciplined objective completion, abandonment, and retirement review."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from long_horizon_objective import LongHorizonObjectiveStore
from objective_progress_evidence import ObjectiveProgressLedger
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1109.7"
ALLOWED_OUTCOMES={"continue","reconsider","suspend","resume","complete","abandon","replace","retire_obsolete","unresolved"}
ABANDONMENT_REASONS={"impossible","irrelevant","unsafe","superseded","voluntarily_dropped","resource_boundary","unknown"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"reviews":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_reviews":512},"state_separation":{"review_is_completion":False,"completion_is_execution":False,"abandonment_is_erasure":False,"replacement_is_authorization":False},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class ObjectiveLifecycleStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"objective_completion_abandonment.json";self.clock=clock or _now;self.objectives=LongHorizonObjectiveStore(self.runtime_root);self.progress=ObjectiveProgressLedger(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def review(self,event_id,*,objective_id,outcome,reason="unknown",completion_claim_id="",remaining_milestone_count=0,reconsideration_eligible=False):
  event_id=_clean(event_id,180);objective_id=_clean(objective_id,180);outcome=_clean(outcome,60);reason=_clean(reason,100);completion_claim_id=_clean(completion_claim_id,180)
  if not event_id or not objective_id:raise ValueError("event_id and objective_id required")
  if outcome not in ALLOWED_OUTCOMES:raise ValueError("invalid lifecycle outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_lifecycle_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   objective=next((x for x in self.objectives.snapshot().get("objectives",[]) if x.get("objective_id")==objective_id),None);claim=next((x for x in self.progress.snapshot().get("claims",[]) if x.get("claim_id")==completion_claim_id),None) if completion_claim_id else None
   why=""
   if not objective:why="objective_missing"
   elif outcome=="complete" and (not claim or claim.get("objective_id")!=objective_id or claim.get("progress_state")!="completed" or not claim.get("supported") or claim.get("criteria_count",0)<objective.get("success_criteria_count",1)):why="completion_evidence_insufficient"
   elif outcome=="abandon" and reason not in ABANDONMENT_REASONS:why="invalid_abandonment_reason"
   now=self.clock()
   if why:result={"status":"lifecycle_review_rejected","reason":why,"review_id":""}
   else:
    key=_digest(objective_id,outcome,reason,completion_claim_id,remaining_milestone_count,reconsideration_eligible);existing=next((x for x in s["reviews"] if x.get("review_key")==key),None)
    if existing:result={"status":"duplicate_lifecycle_review_ignored","review_id":existing["review_id"]}
    else:
     rid=f"objective-lifecycle-{key[:24]}";terminal=outcome in {"complete","abandon","replace","retire_obsolete"};row={"review_id":rid,"review_key":key,"objective_id":objective_id,"outcome":outcome,"reason_digest":_digest(reason),"completion_claim_id":completion_claim_id,"remaining_milestone_count":max(0,int(remaining_milestone_count)),"reconsideration_eligible":bool(reconsideration_eligible),"terminal":terminal,"active_influence":not terminal and outcome not in {"suspend"},"historical_record_preserved":True,"created_at":now,"proposal_id":"","authorization_id":"","action_id":"","authority_granted":False,"content_free":True};s["reviews"].append(row);result={"status":"lifecycle_review_recorded","review_id":rid}
   s["reviews"]=s["reviews"][-int(s["controls"]["max_reviews"]):];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result)}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["reviews"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"review_count":len(rows),"completed_count":sum(x.get("outcome")=="complete" for x in rows),"abandoned_count":sum(x.get("outcome")=="abandon" for x in rows),"suspended_count":sum(x.get("outcome")=="suspend" for x in rows),"unresolved_count":sum(x.get("outcome")=="unresolved" for x in rows),"recent_reviews":deepcopy(rows[-24:]),"allowed_outcomes":sorted(ALLOWED_OUTCOMES),"abandonment_reasons":sorted(ABANDONMENT_REASONS),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False}
def build_objective_lifecycle_inspection(runtime_root=None):return ObjectiveLifecycleStore(runtime_root).inspection_summary()
