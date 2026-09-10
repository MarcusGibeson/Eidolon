from __future__ import annotations
"""v1125.6 durable reflection-outcome lineage without downstream authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from model_backed_reflective_session import ModelBackedReflectiveSessionStore
CONTRACT_VERSION="v1125.6"; SCHEMA_VERSION="1"
OUTCOMES={"conclusion","remain_uncertain","deliberate_silence","provider_failure"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*v:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_update_belief":False,"can_update_goal":False,"can_update_self_model":False,"can_send_message":False,"can_create_initiative":False,"can_execute":False}}
class ReflectiveOutcomeLineageStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflective_outcome_lineage.json"; self.clock=clock or _now; self.sessions=ModelBackedReflectiveSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,session_id:str,predecessor_outcome_id:str="",continuity_state:str="continuous"):
  session=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not session: raise ValueError("existing reflective session required")
  outcome=session.get("outcome");
  if outcome not in OUTCOMES: raise ValueError("recognized reflection outcome required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   structural=_digest(session_id,outcome,session.get("conclusion_digest"),predecessor_outcome_id,continuity_state); existing=next((x for x in s["outcomes"] if x.get("structural_digest")==structural),None)
   if existing: result={"status":"duplicate_reflective_outcome_suppressed","outcome_id":existing["outcome_id"]}
   else:
    now=self.clock();oid=f"reflective-outcome-{structural[:24]}";row={"outcome_id":oid,"session_id":session_id,"subject_id":session.get("subject_id"),"subject_lineage_digest":session.get("subject_lineage_digest"),"outcome":outcome,"conclusion_digest":session.get("conclusion_digest"),"uncertainty":session.get("uncertainty",1.0),"evidence_refs":list(session.get("evidence_refs",[])),"communication_recommendation":session.get("communication_recommendation","silence"),"predecessor_outcome_id":_clean(predecessor_outcome_id,220),"continuity_state":_clean(continuity_state,80),"structural_digest":structural,"state":"recorded","created_at":now,"history":[{"change":"recorded","occurred_at":now,"content_free":True}],"belief_id":"","goal_id":"","self_model_id":"","message_id":"","action_id":""};s["outcomes"].append(row);result={"status":"reflective_outcome_lineage_recorded","outcome_id":oid}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["outcomes"]:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  recent=[{k:x.get(k) for k in ("outcome_id","session_id","subject_id","subject_lineage_digest","outcome","conclusion_digest","uncertainty","evidence_refs","communication_recommendation","predecessor_outcome_id","continuity_state","structural_digest","state","created_at")} for x in s["outcomes"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"outcome_count":len(s["outcomes"]),"outcome_counts":counts,"recent_outcomes":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"message_sent":False,"initiative_created":False,"external_action_executed":False}
def build_reflective_outcome_lineage_inspection(runtime_root=None): return ReflectiveOutcomeLineageStore(runtime_root).inspection_summary()
