from __future__ import annotations
"""Bounded accountable revision of persistent identity claims."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from persistent_identity_model import PersistentIdentityModelStore
from identity_change_detection import IdentityChangeDetector
CONTRACT_VERSION="v1110.4"
OUTCOMES={"retain","revise","suspend","retract","unresolved"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"revisions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_revisions":512,"max_confidence_delta":0.2,"max_uncertainty_delta":0.25},"state_separation":{"detection_is_revision":False,"revision_is_identity_reset":False,"identity_revision_is_intention":False,"revision_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class SelfModelRevisionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"self_model_revision.json";self.clock=clock or _now;self.claims=PersistentIdentityModelStore(self.runtime_root,clock=self.clock);self.detections=IdentityChangeDetector(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def revise(self,event_id,*,detection_id,outcome="unresolved",confidence_delta=0.0,uncertainty_delta=0.0,reason_code="bounded_review"):
  event_id=_clean(event_id,180);detection_id=_clean(detection_id,180);outcome=_clean(outcome,60);reason_code=_clean(reason_code,100)
  if not event_id or not detection_id:raise ValueError("event_id and detection_id required")
  if outcome not in OUTCOMES:raise ValueError("invalid revision outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_revision_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   detection=next((x for x in self.detections.snapshot().get("detections",[]) if x.get("detection_id")==detection_id),None);now=self.clock()
   if not detection:result={"status":"revision_not_applied","reason":"detection_missing","revision_id":""}
   elif not detection.get("eligible_for_revision") and outcome!="retain":result={"status":"revision_not_applied","reason":"detection_not_eligible","revision_id":""}
   else:
    with metadata_mutation_lock(self.claims.path,timeout_seconds=5):
     cs=self.claims._load();claim=next((x for x in cs["claims"] if x.get("claim_id")==detection.get("claim_id")),None)
     if not claim:result={"status":"revision_not_applied","reason":"claim_missing","revision_id":""}
     else:
      cd=max(-float(s["controls"]["max_confidence_delta"]),min(float(s["controls"]["max_confidence_delta"]),float(confidence_delta)));ud=max(-float(s["controls"]["max_uncertainty_delta"]),min(float(s["controls"]["max_uncertainty_delta"]),float(uncertainty_delta)))
      if outcome=="retain":claim["state"]="active";claim["active_influence"]=True;claim["eligible"]=True
      elif outcome=="revise":claim["state"]="uncertain";claim["active_influence"]=True;claim["eligible"]=True
      elif outcome=="suspend":claim["state"]="suspended";claim["active_influence"]=False;claim["eligible"]=False
      elif outcome=="retract":claim["state"]="retracted";claim["active_influence"]=False;claim["eligible"]=False;cd=-1.0;ud=1.0
      else:claim["state"]="uncertain";claim["active_influence"]=True
      claim["confidence"]=round(max(0,min(1,float(claim.get("confidence") or 0)+cd)),4);claim["uncertainty"]=round(max(0,min(1,float(claim.get("uncertainty") or 0)+ud)),4);claim["revision"]=int(claim.get("revision") or 0)+1;claim["updated_at"]=now;claim["update_history"]=(list(claim.get("update_history") or [])+[{"event_digest":_digest(event_id),"occurred_at":now,"change":outcome,"detection_digest":_digest(detection_id),"content_free":True}])[-64:];cs["revision"]+=1;cs["updated_at"]=now;write_json_atomic(self.claims.path,cs,expected_type=dict,sort_keys=True)
      key=_digest(detection_id,outcome,reason_code);rid=f"self-model-revision-{key[:24]}";row={"revision_id":rid,"detection_id":detection_id,"claim_id":claim["claim_id"],"outcome":outcome,"reason_digest":_digest(reason_code),"confidence_delta":round(cd,4),"uncertainty_delta":round(ud,4),"claim_state":claim["state"],"active_influence":claim["active_influence"],"created_at":now,"historical_claim_preserved":True,"content_free":True,"proposal_id":"","authorization_id":"","action_id":"","authority_granted":False};s["revisions"].append(row);result={"status":"self_model_revised","revision_id":rid,"claim_id":claim["claim_id"],"outcome":outcome,"claim_state":claim["state"]}
   s["revisions"]=s["revisions"][-int(s["controls"]["max_revisions"]):];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result)}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["revisions"]:counts[x.get("outcome","unresolved")]=counts.get(x.get("outcome","unresolved"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"revision_count":len(s["revisions"]),"outcome_counts":counts,"recent_revisions":deepcopy(s["revisions"][-24:]),"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False}
def build_self_model_revision_inspection(runtime_root=None):return SelfModelRevisionStore(runtime_root).inspection_summary()
