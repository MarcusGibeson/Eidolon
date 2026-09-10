from __future__ import annotations
"""v1143.4 restart-safe workload coordination continuity and control records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from workload_live_arbitration import WorkloadLiveArbitrationStore
CONTRACT_VERSION="v1143.4"; SCHEMA_VERSION="1"
STATES={"pending","claimed","running","yielded","preempted","cancelled","timed_out","budget_exhausted","resumable","stale_released","completed","retired"}
AUTHORITY_KEYS=("can_execute_underlying_work","can_contact_provider","can_send_message","can_modify_source","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class WorkloadCoordinationContinuityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"workload_coordination_continuity.json"; self.clock=clock or _now; self.arbitrations=WorkloadLiveArbitrationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,arbitration_id:str,continuity_key:str,worker_claim_id:str="",restart_epoch:int=0,claim_stale:bool=False,action:str="claim",cpu_used_ms:int=0,memory_peak_mb:int=0,latency_used_ms:int=0,tokens_used:int=0):
  event_id=_clean(event_id,180); continuity_key=_clean(continuity_key); action=_clean(action,80)
  if not event_id or not arbitration_id or not continuity_key: raise ValueError("event, arbitration, and continuity key required")
  a=next((r for r in self.arbitrations.snapshot().get("arbitrations",[]) if r.get("arbitration_id")==arbitration_id),None)
  if not a: raise ValueError("exact v1143.3 arbitration required")
  over=cpu_used_ms>int(a.get("cpu_budget_ms") or 0) or memory_peak_mb>int(a.get("memory_budget_mb") or 0) or latency_used_ms>int(a.get("latency_budget_ms") or 0) or tokens_used>int(a.get("token_budget") or 0)
  state="pending"
  if claim_stale: state="stale_released"
  elif action=="cancel": state="cancelled"
  elif action=="preempt": state="preempted"
  elif action=="yield": state="yielded"
  elif action=="timeout": state="timed_out"
  elif over: state="budget_exhausted"
  elif action=="complete": state="completed"
  elif action=="run": state="running"
  elif worker_claim_id: state="claimed"
  elif int(restart_epoch)>0: state="resumable"
  structural=_digest(arbitration_id,continuity_key,worker_claim_id,restart_epoch,claim_stale,action,cpu_used_ms,memory_peak_mb,latency_used_ms,tokens_used,state)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["records"] if x.get("continuity_key")==continuity_key and x.get("state") in {"claimed","running","resumable"}),None)
   if duplicate: result={"status":"duplicate_suppressed","continuity_id":duplicate["continuity_id"],"state":"retired"}
   else:
    now=self.clock();cid=f"workload-continuity-{structural[:24]}";row={"continuity_id":cid,"arbitration_id":arbitration_id,"continuity_key":continuity_key,"worker_claim_id":"" if claim_stale else _clean(worker_claim_id),"restart_epoch":max(0,int(restart_epoch)),"state":state,"action":action,"cpu_used_ms":max(0,int(cpu_used_ms)),"memory_peak_mb":max(0,int(memory_peak_mb)),"latency_used_ms":max(0,int(latency_used_ms)),"tokens_used":max(0,int(tokens_used)),"cpu_budget_ms":a.get("cpu_budget_ms"),"memory_budget_mb":a.get("memory_budget_mb"),"latency_budget_ms":a.get("latency_budget_ms"),"token_budget":a.get("token_budget"),"stale_claim_released":bool(claim_stale),"underlying_work_authority_granted":False,"structural_digest":structural,"created_at":now,"history":[{"change":"continuity_recorded","state":state,"occurred_at":now,"content_free":True}]};s["records"].append(row);result={"status":"continuity_recorded","continuity_id":cid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for r in s["records"]:counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("continuity_id","arbitration_id","continuity_key","worker_claim_id","restart_epoch","state","action","cpu_used_ms","memory_peak_mb","latency_used_ms","tokens_used","cpu_budget_ms","memory_budget_mb","latency_budget_ms","token_budget","stale_claim_released","underlying_work_authority_granted","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"workload_payload_exposed":False,"underlying_work_executed":False}
def build_workload_coordination_continuity_inspection(runtime_root=None): return WorkloadCoordinationContinuityStore(runtime_root).inspection_summary()
