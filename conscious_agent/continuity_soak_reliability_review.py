from __future__ import annotations
"""v1144.6 content-free multi-day continuity soak reliability review."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from continuity_soak_recovery_receipts import ContinuitySoakRecoveryReceiptStore
CONTRACT_VERSION="v1144.6"; SCHEMA_VERSION="1"
OUTCOMES={"stable","repeated_failure","recovery_drift","latency_drift","resource_drift","scenario_gap","contamination_risk","insufficient_evidence","operator_review_required"}
AUTHORITY_KEYS=("can_contact_provider","can_restart_process","can_interrupt_work","can_resume_work","can_modify_source","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"reviews":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class ContinuitySoakReliabilityReviewStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"continuity_soak_reliability_reviews.json"; self.clock=clock or _now; self.receipts=ContinuitySoakRecoveryReceiptStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,receipt_id:str,repeated_failure_count:int=0,expected_scenario_count:int=6,observed_scenario_count:int=0,baseline_latency_ms:int=0,observed_latency_ms:int=0,contamination_detected:bool=False,operator_review_required:bool=False):
  event_id=_clean(event_id,180); r=next((x for x in self.receipts.snapshot().get("records",[]) if x.get("receipt_id")==receipt_id),None)
  if not event_id or not r: raise ValueError("event and exact v1144.4 receipt required")
  if operator_review_required: outcome="operator_review_required"
  elif contamination_detected: outcome="contamination_risk"
  elif repeated_failure_count>=2 or r.get("state")=="recovery_failed": outcome="repeated_failure"
  elif r.get("resource_budget_exceeded"): outcome="resource_drift"
  elif observed_latency_ms>max(1,baseline_latency_ms*2) and baseline_latency_ms>0: outcome="latency_drift"
  elif r.get("recovery_attempted") and not r.get("recovery_succeeded"): outcome="recovery_drift"
  elif observed_scenario_count<expected_scenario_count: outcome="scenario_gap"
  elif r.get("state") in {"recovered","completed","observed"}: outcome="stable"
  else: outcome="insufficient_evidence"
  structural=_digest(receipt_id,repeated_failure_count,expected_scenario_count,observed_scenario_count,baseline_latency_ms,observed_latency_ms,contamination_detected,outcome)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   now=self.clock(); rid=f"continuity-soak-reliability-{structural[:24]}"; row={"review_id":rid,"receipt_id":receipt_id,"execution_id":r.get("execution_id"),"campaign_id":r.get("campaign_id"),"scenario_id":r.get("scenario_id"),"restart_epoch":r.get("restart_epoch"),"outcome":outcome,"repeated_failure_count":max(0,int(repeated_failure_count)),"expected_scenario_count":max(1,int(expected_scenario_count)),"observed_scenario_count":max(0,int(observed_scenario_count)),"baseline_latency_ms":max(0,int(baseline_latency_ms)),"observed_latency_ms":max(0,int(observed_latency_ms)),"contamination_detected":bool(contamination_detected),"operator_review_required":bool(operator_review_required),"advisory_only":True,"structural_digest":structural,"created_at":now}; s["reviews"].append(row); result={"status":"review_recorded","review_id":rid,"outcome":outcome}; s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s["reviews"]: counts[r.get("outcome")]=counts.get(r.get("outcome"),0)+1
  keys=("review_id","receipt_id","execution_id","campaign_id","scenario_id","restart_epoch","outcome","repeated_failure_count","expected_scenario_count","observed_scenario_count","baseline_latency_ms","observed_latency_ms","contamination_detected","operator_review_required","advisory_only","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"review_count":len(s["reviews"]),"outcome_counts":counts,"recent_reviews":[{k:r.get(k) for k in keys} for r in s["reviews"][-64:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"source_modified":False}
def build_continuity_soak_reliability_review_inspection(runtime_root=None): return ContinuitySoakReliabilityReviewStore(runtime_root).inspection_summary()
