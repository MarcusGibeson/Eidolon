from __future__ import annotations
"""v1143.3 bounded live workload arbitration and admission records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from workload_coordination_candidates import WorkloadCoordinationCandidateStore
CONTRACT_VERSION="v1143.3"; SCHEMA_VERSION="1"
STATES={"admitted","reserved","deferred","preemption_requested","operator_review_required","cancelled","completed","suppressed","expired"}
AUTHORITY_KEYS=("can_execute_underlying_work","can_contact_provider","can_send_message","can_modify_source","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"arbitrations":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class WorkloadLiveArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"workload_live_arbitration.json"; self.clock=clock or _now; self.candidates=WorkloadCoordinationCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,candidate_id:str,observed_candidate_revision:int|None=None,available_cpu_ms:int=0,available_memory_mb:int=0,available_latency_ms:int=0,available_tokens:int=0,active_priority:int|None=None,operator_confirmed:bool=False):
  event_id=_clean(event_id,180)
  if not event_id or not candidate_id: raise ValueError("event and exact candidate required")
  cs=self.candidates.snapshot(); candidate=next((r for r in cs.get("candidates",[]) if r.get("candidate_id")==candidate_id),None)
  if not candidate: raise ValueError("exact v1143.1 candidate required")
  current_rev=int(cs.get("revision") or 0); stale=observed_candidate_revision is not None and int(observed_candidate_revision)!=current_rev
  fits=all(a>=int(candidate.get(k) or 0) for a,k in ((available_cpu_ms,"cpu_budget_ms"),(available_memory_mb,"memory_budget_mb"),(available_latency_ms,"latency_budget_ms"),(available_tokens,"token_budget")))
  state="deferred"; reason="candidate_not_admissible"
  if stale: state,reason="operator_review_required","candidate_revision_changed"
  elif candidate.get("state")=="requires_operator_review" and not operator_confirmed: state,reason="operator_review_required","confirmation_required"
  elif candidate.get("state")!="active": state,reason="deferred","candidate_not_active"
  elif not fits: state,reason="deferred","resource_budget_unavailable"
  elif active_priority is not None and int(candidate.get("priority") or 0)>int(active_priority): state,reason="preemption_requested","higher_priority_candidate"
  elif candidate.get("coordination_action")=="reserve": state,reason="reserved","budget_reserved"
  elif candidate.get("coordination_action")=="admit": state,reason="admitted","budget_admitted"
  else: state,reason="deferred","advisory_action_not_executable"
  structural=_digest(candidate_id,current_rev,available_cpu_ms,available_memory_mb,available_latency_ms,available_tokens,active_priority,operator_confirmed,state,reason)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["arbitrations"] if x.get("structural_digest")==structural and x.get("state") in {"admitted","reserved","preemption_requested","operator_review_required"}),None)
   if duplicate: result={"status":"duplicate_suppressed","arbitration_id":duplicate["arbitration_id"],"state":"suppressed"}
   else:
    now=self.clock(); aid=f"workload-arbitration-{structural[:24]}"; row={"arbitration_id":aid,"candidate_id":candidate_id,"eligibility_id":candidate.get("eligibility_id"),"workload_id":candidate.get("workload_id"),"workload_kind":candidate.get("workload_kind"),"coordination_group_id":candidate.get("coordination_group_id"),"priority":candidate.get("priority"),"candidate_store_revision":current_rev,"observed_candidate_revision":observed_candidate_revision,"cpu_budget_ms":candidate.get("cpu_budget_ms"),"memory_budget_mb":candidate.get("memory_budget_mb"),"latency_budget_ms":candidate.get("latency_budget_ms"),"token_budget":candidate.get("token_budget"),"state":state,"state_reason":reason,"operator_confirmed":bool(operator_confirmed),"schedule_recorded":state in {"admitted","reserved","preemption_requested"},"underlying_work_executed":False,"structural_digest":structural,"created_at":now,"history":[{"change":"arbitration_recorded","state":state,"occurred_at":now,"content_free":True}]};s["arbitrations"].append(row);result={"status":"arbitration_recorded","arbitration_id":aid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for r in s["arbitrations"]: counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("arbitration_id","candidate_id","eligibility_id","workload_id","workload_kind","coordination_group_id","priority","candidate_store_revision","observed_candidate_revision","cpu_budget_ms","memory_budget_mb","latency_budget_ms","token_budget","state","state_reason","operator_confirmed","schedule_recorded","underlying_work_executed","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["arbitrations"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["arbitrations"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"workload_payload_exposed":False,"underlying_work_executed":False}
def build_workload_live_arbitration_inspection(runtime_root=None): return WorkloadLiveArbitrationStore(runtime_root).inspection_summary()
