from __future__ import annotations
"""Deterministic bounded review arbitration for long-horizon objectives."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from long_horizon_objective import LongHorizonObjectiveStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1109.1"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"receipts":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"mode":"running","quiet":False,"sleeping":False,"paused":False,"max_receipts":256,"max_resource_cost":.75,"repeat_penalty":.09,"stagnation_bonus":.08},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class ObjectiveReviewArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"objective_review_arbitration.json";self.clock=clock or _now;self.objectives=LongHorizonObjectiveStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def select(self,event_id,*,worker_id="objective-review-arbitrator"):
  event_id=_clean(event_id,180);worker_id=_clean(worker_id,120)
  if not event_id:raise ValueError("event_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_review_selection_ignored","receipt":deepcopy(prior["receipt"]),"idempotent":True}
   controls=s["controls"];selected=None;reason=""
   if controls.get("paused") or controls.get("sleeping") or controls.get("quiet") or controls.get("mode")!="running":reason="control_boundary"
   else:
    rows=[x for x in self.objectives.snapshot().get("objectives",[]) if x.get("active_influence") and x.get("eligible") and x.get("state") in {"active","blocked"} and float(x.get("resource_cost") or 0)<=float(controls["max_resource_cost"])]
    def score(x): return round(.24*float(x.get("salience") or 0)+.22*float(x.get("urgency") or 0)+.15*float(x.get("uncertainty") or 0)+.13*(1-float(x.get("confidence") or 0))+.08*(1 if x.get("state")=="blocked" else 0)+float(controls["stagnation_bonus"])*min(3,int(x.get("deferral_count") or 0))-float(controls["repeat_penalty"])*min(5,int(x.get("review_count") or 0))-.16*float(x.get("resource_cost") or 0),6)
    rows.sort(key=lambda x:(-score(x),int(x.get("review_count") or 0),str(x.get("created_at") or ""),str(x.get("objective_id") or "")))
    if rows and score(rows[0])>0:selected=rows[0]
    else:reason="no_eligible_objective"
   now=self.clock();rid=f"objective-review-{_digest(event_id,selected.get('objective_id') if selected else reason)[:24]}";receipt={"receipt_id":rid,"event_digest":_digest(event_id),"worker_digest":_digest(worker_id),"occurred_at":now,"decision":"selected_for_bounded_review" if selected else "deliberate_no_selection","objective_id":selected.get("objective_id") if selected else "","intention_id":selected.get("intention_id") if selected else "","subject_digest":selected.get("subject_digest") if selected else "","reason_code":reason,"reflection_handoff_eligible":bool(selected),"proposal_id":"","authorization_id":"","action_id":"","provider_contacted":False,"action_authority_granted":False,"content_free":True}
   s["receipts"]=(s["receipts"]+[receipt])[-int(controls["max_receipts"]):];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"receipt":deepcopy(receipt)}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":"objective_selected_for_review" if selected else "deliberate_no_selection","receipt":receipt,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["receipts"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"selection_count":sum(x.get("decision")=="selected_for_bounded_review" for x in rows),"deliberate_no_selection_count":sum(x.get("decision")=="deliberate_no_selection" for x in rows),"recent_receipts":deepcopy(rows[-24:]),"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_objective_review_arbitration_inspection(runtime_root=None): return ObjectiveReviewArbitrator(runtime_root).inspection_summary()
