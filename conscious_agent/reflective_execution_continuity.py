from __future__ import annotations
"""v1125.3 bounded reflective execution and pause/resume continuity."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from model_backed_reflective_session import ModelBackedReflectiveSessionStore
CONTRACT_VERSION="v1125.3"; SCHEMA_VERSION="1"
STATES={"active","paused","resumable","completed","failed","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=220): return " ".join(str(v or "").split())[:n]
def _digest(*v:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"executions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_send_message":False,"can_create_initiative":False,"can_update_belief":False,"can_execute":False}}
class ReflectiveExecutionContinuityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/"reflective_execution_continuity.json";self.clock=clock or _now;self.sessions=ModelBackedReflectiveSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def begin(self,event_id:str,*,session_id:str,cycle_budget:int=1,token_budget:int=500):
  event_id=_clean(event_id,180);session_id=_clean(session_id);cycle_budget=max(1,min(int(cycle_budget),3));token_budget=max(64,min(int(token_budget),1200))
  session=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not session: raise ValueError("existing reflective session required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   existing=next((x for x in s["executions"] if x.get("session_id")==session_id and x.get("state") in {"active","paused","resumable"}),None)
   if existing: result={"status":"reflective_execution_reused","execution_id":existing["execution_id"],"state":existing["state"]}
   else:
    now=self.clock();dig=_digest(session_id,cycle_budget,token_budget,session.get("subject_lineage_digest"));eid=f"reflective-execution-{dig[:24]}";state="failed" if session.get("outcome")=="provider_failure" else "completed"
    row={"execution_id":eid,"session_id":session_id,"subject_lineage_digest":session.get("subject_lineage_digest"),"cycle_budget":cycle_budget,"token_budget":token_budget,"cycles_completed":min(int(session.get("cycles_completed",0)),cycle_budget),"state":state,"pause_reason":"","resume_token_digest":"","provider_failure":session.get("outcome")=="provider_failure","created_at":now,"updated_at":now,"history":[{"change":"execution_recorded","occurred_at":now}],"message_id":"","initiative_id":"","belief_id":"","action_id":""};s["executions"].append(row);result={"status":"reflective_execution_recorded","execution_id":eid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def transition(self,event_id:str,*,execution_id:str,state:str,reason:str=""):
  if state not in {"paused","resumable","completed","stale","retired"}:raise ValueError("recognized execution transition required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["executions"] if x.get("execution_id")==execution_id),None)
   if not row:raise ValueError("execution required")
   now=self.clock();row["state"]=state;row["pause_reason"]=_clean(reason,120) if state=="paused" else row.get("pause_reason","");row["resume_token_digest"]=_digest(execution_id,row.get("subject_lineage_digest")) if state in {"paused","resumable"} else "";row["updated_at"]=now;row["history"].append({"change":state,"occurred_at":now});result={"status":"reflective_execution_transitioned","execution_id":execution_id,"state":state};s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["executions"]:counts[x.get("state")]=counts.get(x.get("state"),0)+1
  recent=[{k:x.get(k) for k in ("execution_id","session_id","subject_lineage_digest","cycle_budget","token_budget","cycles_completed","state","pause_reason","resume_token_digest","provider_failure","created_at","updated_at")} for x in s["executions"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"execution_count":len(s["executions"]),"state_counts":counts,"recent_executions":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"message_sent":False,"initiative_created":False,"belief_updated":False,"external_action_executed":False}
def build_reflective_execution_continuity_inspection(runtime_root=None):return ReflectiveExecutionContinuityStore(runtime_root).inspection_summary()
