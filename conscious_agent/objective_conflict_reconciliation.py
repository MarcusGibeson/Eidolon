from __future__ import annotations
"""Deterministic, authority-free reconciliation of long-horizon objective conflicts."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from long_horizon_objective import LongHorizonObjectiveStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1109.6"
ALLOWED_OUTCOMES={"coexist","priority_adjusted","deferred","suspended","replaced","consolidated","unresolved","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"decisions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_decisions":512},"state_separation":{"objective_is_task":False,"objective_is_proposal":False,"priority_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class ObjectiveConflictStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"objective_conflict_reconciliation.json";self.clock=clock or _now;self.objectives=LongHorizonObjectiveStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def reconcile(self,event_id,*,objective_ids,outcome="unresolved",reason_code="resource_conflict",priority_order=(),replacement_objective_id=""):
  event_id=_clean(event_id,180);ids=tuple(sorted({_clean(x,180) for x in objective_ids if _clean(x,180)}));outcome=_clean(outcome,60);reason_code=_clean(reason_code,100);replacement_objective_id=_clean(replacement_objective_id,180)
  if not event_id or len(ids)<2: raise ValueError("event_id and at least two objective_ids required")
  if outcome not in ALLOWED_OUTCOMES: raise ValueError("invalid conflict outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_conflict_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   known={x.get("objective_id") for x in self.objectives.snapshot().get("objectives",[])};missing=[x for x in ids if x not in known]
   now=self.clock()
   if missing:result={"status":"conflict_not_recorded","reason":"objective_missing","decision_id":""}
   elif replacement_objective_id and replacement_objective_id not in known:result={"status":"conflict_not_recorded","reason":"replacement_objective_missing","decision_id":""}
   else:
    key=_digest(*ids,outcome,reason_code,replacement_objective_id,*priority_order);existing=next((x for x in s["decisions"] if x.get("decision_key")==key),None)
    if existing:result={"status":"duplicate_conflict_ignored","decision_id":existing["decision_id"]}
    else:
     did=f"objective-conflict-{key[:24]}";row={"decision_id":did,"decision_key":key,"objective_ids":list(ids),"objective_count":len(ids),"outcome":outcome,"reason_digest":_digest(reason_code),"priority_order_digests":[_digest(x) for x in priority_order if _clean(x,180)],"replacement_objective_id":replacement_objective_id,"active_influence_removed_from":list(ids) if outcome in {"replaced","retired","consolidated"} else [],"created_at":now,"historical_records_preserved":True,"proposal_id":"","authorization_id":"","action_id":"","authority_granted":False,"content_free":True};s["decisions"].append(row);result={"status":"conflict_recorded","decision_id":did}
   s["decisions"]=s["decisions"][-int(s["controls"]["max_decisions"]):];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result)}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["decisions"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"decision_count":len(rows),"unresolved_count":sum(x.get("outcome")=="unresolved" for x in rows),"replacement_count":sum(x.get("outcome") in {"replaced","consolidated"} for x in rows),"recent_decisions":deepcopy(rows[-24:]),"allowed_outcomes":sorted(ALLOWED_OUTCOMES),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False}
def build_objective_conflict_inspection(runtime_root=None):return ObjectiveConflictStore(runtime_root).inspection_summary()
