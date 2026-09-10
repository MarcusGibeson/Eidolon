from __future__ import annotations
"""v1144.4 restart-safe continuity soak recovery and structural receipts."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from continuity_soak_live_execution import ContinuitySoakLiveExecutionStore
CONTRACT_VERSION="v1144.4"; SCHEMA_VERSION="1"
STATES={"observed","recovered","recovery_failed","stale_released","cancelled","timed_out","completed","retired"}
AUTHORITY_KEYS=("can_contact_provider","can_restart_process","can_interrupt_work","can_resume_work","can_modify_source","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class ContinuitySoakRecoveryReceiptStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"continuity_soak_recovery_receipts.json"; self.clock=clock or _now; self.executions=ContinuitySoakLiveExecutionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,execution_id:str,scenario_id:str,restart_epoch:int=0,worker_claim_id:str="",claim_stale:bool=False,recovery_attempted:bool=False,recovery_succeeded:bool=False,cancelled:bool=False,timed_out:bool=False,completed:bool=False,latency_ms:int=0,resource_budget_exceeded:bool=False):
  if not _clean(event_id,180) or not execution_id or not scenario_id: raise ValueError("event, execution, and scenario required")
  e=next((r for r in self.executions.snapshot().get("records",[]) if r.get("execution_id")==execution_id),None)
  if not e: raise ValueError("exact v1144.3 execution required")
  state="observed"
  if claim_stale: state="stale_released"
  elif cancelled: state="cancelled"
  elif timed_out or resource_budget_exceeded: state="timed_out"
  elif completed: state="completed"
  elif recovery_attempted and recovery_succeeded: state="recovered"
  elif recovery_attempted: state="recovery_failed"
  structural=_digest(execution_id,scenario_id,restart_epoch,worker_claim_id,claim_stale,recovery_attempted,recovery_succeeded,cancelled,timed_out,completed,latency_ms,resource_budget_exceeded,state)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   now=self.clock();rid=f"continuity-soak-receipt-{structural[:24]}";row={"receipt_id":rid,"execution_id":execution_id,"campaign_id":e.get("campaign_id"),"scenario_id":_clean(scenario_id,80),"restart_epoch":max(0,int(restart_epoch)),"worker_claim_id":"" if claim_stale else _clean(worker_claim_id),"stale_claim_released":bool(claim_stale),"recovery_attempted":bool(recovery_attempted),"recovery_succeeded":bool(recovery_succeeded),"latency_ms":max(0,int(latency_ms)),"resource_budget_exceeded":bool(resource_budget_exceeded),"state":state,"structural_digest":structural,"raw_log_recorded":False,"provider_payload_recorded":False,"created_at":now,"history":[{"change":"receipt_recorded","state":state,"occurred_at":now,"content_free":True}]};s["records"].append(row);result={"status":"receipt_recorded","receipt_id":rid,"state":state};s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();keys=("receipt_id","execution_id","campaign_id","scenario_id","restart_epoch","worker_claim_id","stale_claim_released","recovery_attempted","recovery_succeeded","latency_ms","resource_budget_exceeded","state","structural_digest","raw_log_recorded","provider_payload_recorded")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-64:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"source_modified":False}
def build_continuity_soak_recovery_receipt_inspection(runtime_root=None): return ContinuitySoakRecoveryReceiptStore(runtime_root).inspection_summary()
