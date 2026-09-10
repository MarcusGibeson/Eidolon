from __future__ import annotations
"""v1144.3 operator-confirmed bounded continuity-soak execution records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from continuity_soak_campaign_candidates import ContinuitySoakCampaignCandidateStore, SOAK_SCENARIOS
CONTRACT_VERSION="v1144.3"; SCHEMA_VERSION="1"
STATES={"awaiting_confirmation","launched","observing","cancelled","timed_out","completed","suppressed","expired","retired"}
AUTHORITY_KEYS=("can_contact_provider","can_restart_process","can_interrupt_work","can_resume_work","can_modify_source","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class ContinuitySoakLiveExecutionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"continuity_soak_live_execution.json"; self.clock=clock or _now; self.campaigns=ContinuitySoakCampaignCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,campaign_id:str,operator_confirmation_id:str="",launch_token_id:str="",worker_claim_id:str="",action:str="launch",scenario_id:str="",observation_index:int=0,elapsed_minutes:int=0,cancel_requested:bool=False,timeout_reached:bool=False):
  event_id=_clean(event_id,180); action=_clean(action,80); scenario_id=_clean(scenario_id,80)
  if not event_id or not campaign_id: raise ValueError("event and campaign required")
  c=next((r for r in self.campaigns.snapshot().get("candidates",[]) if r.get("campaign_id")==campaign_id),None)
  if not c: raise ValueError("exact v1144.1 campaign required")
  if scenario_id and scenario_id not in SOAK_SCENARIOS: raise ValueError("recognized scenario required")
  confirmed=bool(_clean(operator_confirmation_id) and _clean(launch_token_id))
  state="awaiting_confirmation"; reason="operator_confirmation_required"
  if cancel_requested or action=="cancel": state,reason="cancelled","operator_cancelled"
  elif timeout_reached or action=="timeout": state,reason="timed_out","bounded_timeout"
  elif c.get("state") not in {"requires_operator_review","planned"}: state,reason="suppressed","campaign_not_launchable"
  elif not confirmed: state,reason="awaiting_confirmation","exact_confirmation_and_token_required"
  elif action=="complete": state,reason="completed","bounded_campaign_complete"
  elif action=="observe": state,reason="observing","bounded_observation"
  else: state,reason="launched","operator_confirmed_launch"
  structural=_digest(campaign_id,operator_confirmation_id,launch_token_id,worker_claim_id,action,scenario_id,observation_index,elapsed_minutes,state)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["records"] if x.get("campaign_id")==campaign_id and x.get("state") in {"launched","observing"}),None)
   if duplicate and state in {"launched","observing"}: result={"status":"duplicate_suppressed","execution_id":duplicate["execution_id"],"state":"suppressed"}
   else:
    now=self.clock(); eid=f"continuity-soak-execution-{structural[:24]}"; row={"execution_id":eid,"campaign_id":campaign_id,"eligibility_id":c.get("eligibility_id"),"operator_confirmation_id":_clean(operator_confirmation_id),"launch_token_id":_clean(launch_token_id),"worker_claim_id":_clean(worker_claim_id),"action":action,"scenario_id":scenario_id,"observation_index":max(0,int(observation_index)),"elapsed_minutes":max(0,int(elapsed_minutes)),"duration_days":c.get("duration_days"),"observation_interval_minutes":c.get("observation_interval_minutes"),"state":state,"state_reason":reason,"structural_digest":structural,"provider_payload_recorded":False,"raw_log_recorded":False,"source_modified":False,"created_at":now,"history":[{"change":"execution_recorded","state":state,"occurred_at":now,"content_free":True}]};s["records"].append(row);result={"status":"execution_recorded","execution_id":eid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); keys=("execution_id","campaign_id","eligibility_id","operator_confirmation_id","launch_token_id","worker_claim_id","action","scenario_id","observation_index","elapsed_minutes","duration_days","observation_interval_minutes","state","state_reason","structural_digest","provider_payload_recorded","raw_log_recorded","source_modified")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"source_modified":False}
def build_continuity_soak_live_execution_inspection(runtime_root=None): return ContinuitySoakLiveExecutionStore(runtime_root).inspection_summary()
