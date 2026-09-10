from __future__ import annotations
"""v1125.4 silence/communication recommendation and provider-recovery governance."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from model_backed_reflective_session import ModelBackedReflectiveSessionStore
CONTRACT_VERSION="v1125.4"; SCHEMA_VERSION="1"
DECISIONS={"remain_silent","communication_candidate","defer_for_recovery","requires_operator_review","unresolved"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=220):return " ".join(str(v or "").split())[:n]
def _digest(*v:Any):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in v).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"recommendations":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_send_message":False,"can_create_notification":False,"can_create_initiative":False,"can_contact_provider":False,"can_execute":False}}
class ReflectiveCommunicationRecommendationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/"reflective_communication_recommendations.json";self.clock=clock or _now;self.sessions=ModelBackedReflectiveSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def record(self,event_id:str,*,session_id:str,recovery_ready:bool=True,operator_review_required:bool=False):
  session=next((x for x in self.sessions.snapshot().get("sessions",[]) if x.get("session_id")==session_id),None)
  if not session:raise ValueError("existing reflective session required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   if session.get("outcome")=="provider_failure" or not recovery_ready:decision="defer_for_recovery"
   elif operator_review_required:decision="requires_operator_review"
   elif session.get("communication_recommendation")=="communicate" and float(session.get("uncertainty",1))<=0.45:decision="communication_candidate"
   elif session.get("communication_recommendation")=="silence" or session.get("outcome")=="deliberate_silence":decision="remain_silent"
   else:decision="unresolved"
   dig=_digest(session_id,decision,recovery_ready,operator_review_required);rid=f"reflection-recommendation-{dig[:24]}";now=self.clock();row={"recommendation_id":rid,"session_id":session_id,"session_digest":session.get("conclusion_digest"),"decision":decision,"uncertainty":session.get("uncertainty",1.0),"recovery_ready":bool(recovery_ready),"operator_review_required":bool(operator_review_required),"state":"active","structural_digest":dig,"created_at":now,"updated_at":now,"history":[{"change":"recommendation_recorded","occurred_at":now}],"message_id":"","notification_id":"","initiative_id":"","action_id":""};s["recommendations"].append(row);result={"status":"reflective_recommendation_recorded","recommendation_id":rid,"decision":decision,"message_sent":False};s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["recommendations"]:counts[x.get("decision")]=counts.get(x.get("decision"),0)+1
  recent=[{k:x.get(k) for k in ("recommendation_id","session_id","session_digest","decision","uncertainty","recovery_ready","operator_review_required","state","structural_digest","created_at","updated_at")} for x in s["recommendations"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"recommendation_count":len(s["recommendations"]),"decision_counts":counts,"recent_recommendations":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"messages_exposed":False,"provider_payloads_exposed":False,"hidden_reasoning_exposed":False,"message_sent":False,"notification_created":False,"initiative_created":False,"external_action_executed":False}
def build_reflective_communication_recommendation_inspection(runtime_root=None):return ReflectiveCommunicationRecommendationStore(runtime_root).inspection_summary()
