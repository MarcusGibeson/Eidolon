from __future__ import annotations
"""v1143.6 content-free workload coordination fairness and reliability review."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from workload_live_arbitration import WorkloadLiveArbitrationStore
from workload_coordination_continuity import WorkloadCoordinationContinuityStore
CONTRACT_VERSION="v1143.6"; SCHEMA_VERSION="1"
OUTCOMES={"balanced","starvation_risk","latency_risk","resource_drift","contention","preemption_pressure","insufficient_evidence","operator_review_required"}
AUTHORITY_KEYS=("can_execute_underlying_work","can_change_scheduler","can_contact_provider","can_send_message","can_modify_source","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"reviews":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class WorkloadCoordinationReliabilityReviewStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"workload_coordination_reliability_reviews.json"; self.clock=clock or _now; self.arbitrations=WorkloadLiveArbitrationStore(self.runtime_root); self.continuity=WorkloadCoordinationContinuityStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,arbitration_id:str,continuity_id:str="",waiting_cycles:int=0,observed_latency_ms:int=0,observed_cpu_ms:int=0,observed_memory_mb:int=0,observed_tokens:int=0,peer_admissions:int=0,operator_review_required:bool=False):
  event_id=_clean(event_id,180)
  if not event_id or not arbitration_id: raise ValueError("event and arbitration required")
  a=next((r for r in self.arbitrations.snapshot().get("arbitrations",[]) if r.get("arbitration_id")==arbitration_id),None)
  if not a: raise ValueError("exact v1143.3 arbitration required")
  c=next((r for r in self.continuity.snapshot().get("records",[]) if r.get("continuity_id")==continuity_id),None) if continuity_id else None
  if continuity_id and not c: raise ValueError("exact v1143.4 continuity required")
  drift=observed_cpu_ms>int(a.get("cpu_budget_ms") or 0) or observed_memory_mb>int(a.get("memory_budget_mb") or 0) or observed_latency_ms>int(a.get("latency_budget_ms") or 0) or observed_tokens>int(a.get("token_budget") or 0)
  if operator_review_required: outcome="operator_review_required"
  elif drift: outcome="resource_drift"
  elif waiting_cycles>=5: outcome="starvation_risk"
  elif observed_latency_ms>max(1,int(a.get("latency_budget_ms") or 0)*8//10): outcome="latency_risk"
  elif a.get("state")=="preemption_requested": outcome="preemption_pressure"
  elif peer_admissions>=4 and a.get("state") in {"deferred","reserved"}: outcome="contention"
  elif c or a.get("state") in {"admitted","completed"}: outcome="balanced"
  else: outcome="insufficient_evidence"
  structural=_digest(arbitration_id,continuity_id,waiting_cycles,observed_latency_ms,observed_cpu_ms,observed_memory_mb,observed_tokens,peer_admissions,outcome)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   now=self.clock();rid=f"workload-reliability-{structural[:24]}";row={"review_id":rid,"arbitration_id":arbitration_id,"continuity_id":continuity_id,"workload_id":a.get("workload_id"),"workload_kind":a.get("workload_kind"),"fairness_class_id":a.get("fairness_class_id"),"outcome":outcome,"waiting_cycles":max(0,int(waiting_cycles)),"observed_latency_ms":max(0,int(observed_latency_ms)),"observed_cpu_ms":max(0,int(observed_cpu_ms)),"observed_memory_mb":max(0,int(observed_memory_mb)),"observed_tokens":max(0,int(observed_tokens)),"peer_admissions":max(0,int(peer_admissions)),"operator_review_required":bool(operator_review_required),"scheduler_authority_granted":False,"underlying_work_authority_granted":False,"structural_digest":structural,"created_at":now,"history":[{"change":"review_recorded","outcome":outcome,"occurred_at":now,"content_free":True}]};s["reviews"].append(row);result={"status":"review_recorded","review_id":rid,"outcome":outcome};s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s["reviews"]:counts[r.get("outcome")]=counts.get(r.get("outcome"),0)+1
  keys=("review_id","arbitration_id","continuity_id","workload_id","workload_kind","fairness_class_id","outcome","waiting_cycles","observed_latency_ms","observed_cpu_ms","observed_memory_mb","observed_tokens","peer_admissions","operator_review_required","scheduler_authority_granted","underlying_work_authority_granted","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"review_count":len(s["reviews"]),"outcome_counts":counts,"recent_reviews":[{k:r.get(k) for k in keys} for r in s["reviews"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"workload_payload_exposed":False,"scheduler_mutated":False,"underlying_work_executed":False}
def build_workload_coordination_reliability_review_inspection(runtime_root=None): return WorkloadCoordinationReliabilityReviewStore(runtime_root).inspection_summary()
