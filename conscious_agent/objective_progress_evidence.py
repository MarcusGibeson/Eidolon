from __future__ import annotations
"""Evidence-disciplined progress accounting for objectives and milestones."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from long_horizon_objective import LongHorizonObjectiveStore
from objective_milestone_decomposition import ObjectiveMilestoneStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1109.4"
ALLOWED_EVIDENCE={"bounded_reflection","resolved_inquiry","explicit_user_update","verified_structural_change","authorized_action_receipt","milestone_lifecycle"}
ALLOWED_STATES={"unknown","blocked","partial","regressed","completed","invalidated"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"evidence":[],"claims":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_evidence":1024,"max_claims":512},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class ObjectiveProgressLedger:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"objective_progress_evidence.json";self.clock=clock or _now;self.objectives=LongHorizonObjectiveStore(self.runtime_root);self.milestones=ObjectiveMilestoneStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def record(self,event_id,*,objective_id,milestone_id="",evidence_type,evidence_id,claimed_state="partial",criteria_satisfied=()):
  event_id=_clean(event_id,180);objective_id=_clean(objective_id,180);milestone_id=_clean(milestone_id,180);evidence_type=_clean(evidence_type,80);evidence_id=_clean(evidence_id,180);claimed_state=_clean(claimed_state,40)
  if not event_id or not objective_id or not evidence_id:raise ValueError("event_id, objective_id, and evidence_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_progress_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   objective=next((x for x in self.objectives.snapshot().get("objectives",[]) if x.get("objective_id")==objective_id),None);milestone=next((x for x in self.milestones.snapshot().get("milestones",[]) if x.get("milestone_id")==milestone_id),None) if milestone_id else None
   ekey=_digest(objective_id,milestone_id,evidence_type,evidence_id);duplicate=next((x for x in s["evidence"] if x.get("evidence_key")==ekey),None)
   criteria=[_digest(x) for x in criteria_satisfied if _clean(x,300)]
   reason=""
   if not objective:reason="objective_missing"
   elif milestone_id and (not milestone or milestone.get("objective_id")!=objective_id):reason="milestone_missing_or_mismatched"
   elif evidence_type not in ALLOWED_EVIDENCE:reason="unrecognized_evidence_type"
   elif claimed_state not in ALLOWED_STATES:reason="invalid_progress_state"
   elif duplicate:reason="duplicate_evidence"
   elif claimed_state=="completed" and not criteria:reason="completion_evidence_insufficient"
   now=self.clock()
   if reason:result={"status":"progress_rejected" if reason!="duplicate_evidence" else "duplicate_evidence_ignored","reason":reason,"claim_id":""}
   else:
    eid=f"progress-evidence-{ekey[:24]}";cid=f"progress-claim-{_digest(ekey,claimed_state,*criteria)[:24]}";s["evidence"].append({"evidence_id":eid,"evidence_key":ekey,"source_type":evidence_type,"source_digest":_digest(evidence_id),"objective_id":objective_id,"milestone_id":milestone_id,"occurred_at":now,"content_free":True});s["claims"].append({"claim_id":cid,"objective_id":objective_id,"milestone_id":milestone_id,"progress_state":claimed_state,"criteria_digests":criteria,"criteria_count":len(criteria),"evidence_ids":[eid],"supported":True,"invalidated":claimed_state=="invalidated","created_at":now,"proposal_id":"","authorization_id":"","action_id":"","content_free":True});result={"status":"progress_recorded","claim_id":cid,"evidence_id":eid}
   s["evidence"]=s["evidence"][-int(s["controls"]["max_evidence"]):];s["claims"]=s["claims"][-int(s["controls"]["max_claims"]):];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"result":deepcopy(result),"occurred_at":now}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();claims=s["claims"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"evidence_count":len(s["evidence"]),"claim_count":len(claims),"completed_claim_count":sum(x.get("progress_state")=="completed" and x.get("supported") for x in claims),"invalidated_claim_count":sum(x.get("progress_state")=="invalidated" or x.get("invalidated") for x in claims),"recent_claims":deepcopy(claims[-24:]),"accepted_evidence_types":sorted(ALLOWED_EVIDENCE),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_objective_progress_inspection(runtime_root=None):return ObjectiveProgressLedger(runtime_root).inspection_summary()
