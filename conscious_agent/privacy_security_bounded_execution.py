from __future__ import annotations
"""v1148.3 operator-confirmed bounded structural security-test execution."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from privacy_security_test_catalog import build_privacy_security_test_catalog

CONTRACT_VERSION="v1148.3"; SCHEMA_VERSION="1"
STATES={"awaiting_confirmation","passed","contained","review_required","timed_out","cancelled","suppressed"}
AUTHORITY_KEYS=("browses","contacts_provider","executes_commands","mutates_cognition","mutates_memory","modifies_source","sends_messages","creates_notifications","creates_goals","creates_plans","creates_development_proposals","creates_approval","creates_authorization","installs","promotes","certifies")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=200): return " ".join(str(v or "").split())[:n]
def _digest(v:object): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class PrivacySecurityBoundedExecutionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"privacy_security_bounded_execution.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def execute(self,event_id:str,*,scenario_id:str,operator_confirmation_id:str="",observed_outcome:str="",steps_used:int=0,attempts_used:int=0,runtime_ms:int=0,cancelled:bool=False,timed_out:bool=False):
  event_id=_clean(event_id);scenario_id=_clean(scenario_id);observed_outcome=_clean(observed_outcome,40)
  if not event_id or not scenario_id: raise ValueError("event_id and scenario_id required")
  scenario=next((r for r in build_privacy_security_test_catalog().get("scenarios",[]) if r.get("scenario_id")==scenario_id),None)
  if not scenario: raise ValueError("exact v1148.1 scenario required")
  confirmed=bool(_clean(operator_confirmation_id))
  bounded=0<=int(steps_used)<=int(scenario["max_steps"]) and 0<=int(attempts_used)<=int(scenario["max_attempts"]) and 0<=int(runtime_ms)<=int(scenario["max_runtime_ms"])
  if cancelled: state,reason="cancelled","operator_cancelled"
  elif timed_out or int(runtime_ms)>int(scenario["max_runtime_ms"]): state,reason="timed_out","bounded_timeout"
  elif not confirmed: state,reason="awaiting_confirmation","operator_confirmation_required"
  elif not bounded: state,reason="review_required","budget_violation"
  elif observed_outcome==scenario["expected_outcome"]: state,reason="passed","expected_protection_observed"
  elif observed_outcome in {"deny","quarantine","review","constrain","stop"}: state,reason="contained","alternate_bounded_protection_observed"
  else: state,reason="review_required","unexpected_or_missing_outcome"
  base={"scenario_id":scenario_id,"scenario_digest":scenario["structural_digest"],"threat_id":scenario["threat_id"],"category":scenario["category"],"attack_surface":scenario["attack_surface"],"operator_confirmation_id":_clean(operator_confirmation_id),"expected_outcome":scenario["expected_outcome"],"observed_outcome":observed_outcome,"steps_used":max(0,int(steps_used)),"attempts_used":max(0,int(attempts_used)),"runtime_ms":max(0,int(runtime_ms)),"provider_tokens_used":0,"state":state,"state_reason":reason}
  structural=_digest(base)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["records"] if x.get("scenario_id")==scenario_id and x.get("structural_digest")==structural),None)
   if duplicate: result={"status":"duplicate_suppressed","execution_id":duplicate["execution_id"],"state":"suppressed"}
   else:
    now=self.clock();eid=f"privacy-security-execution-{structural[:24]}";row={"execution_id":eid,**base,"structural_digest":structural,"fixture_content_included":False,"raw_payload_recorded":False,"provider_payload_recorded":False,"source_modified":False,"created_at":now};s["records"].append(row);result={"status":"execution_recorded","execution_id":eid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();keys=("execution_id","scenario_id","scenario_digest","threat_id","category","attack_surface","operator_confirmation_id","expected_outcome","observed_outcome","steps_used","attempts_used","runtime_ms","provider_tokens_used","state","state_reason","structural_digest","fixture_content_included","raw_payload_recorded","provider_payload_recorded","source_modified")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"source_modified":False}
def build_privacy_security_bounded_execution_inspection(runtime_root=None): return PrivacySecurityBoundedExecutionStore(runtime_root).inspection_summary()
