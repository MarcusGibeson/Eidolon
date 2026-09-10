from __future__ import annotations
"""v1125.1 structural subject intake for bounded reflective cognition."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock

CONTRACT_VERSION="v1125.1"; SCHEMA_VERSION="1"
SUBJECT_KINDS={"selected_attention","motivation","goal","memory","concern","event"}
STATES={"active","deferred","requires_operator_review","superseded","stale","retracted","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=220): return " ".join(str(v or "").split())[:n]
def _digest(*v:Any): return hashlib.sha256("\x1f".join(_clean(x,2000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"subjects":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_start_reflection":False,"can_contact_provider":False,"can_create_belief":False,"can_create_goal":False,"can_send_message":False,"can_execute":False}}
class ReflectiveSubjectIntakeStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflective_subject_intake.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,subject_kind:str,source_id:str,source_contract:str,importance:float=0.5,uncertainty:float=0.5,sensitivity:str="normal",operator_review_required:bool=False,state:str="active"):
  event_id=_clean(event_id,180); source_id=_clean(source_id); source_contract=_clean(source_contract,80); subject_kind=_clean(subject_kind,60); sensitivity=_clean(sensitivity,40)
  if subject_kind not in SUBJECT_KINDS: raise ValueError("recognized reflective subject kind required")
  if state not in STATES: raise ValueError("recognized subject lifecycle state required")
  if not event_id or not source_id or not source_contract: raise ValueError("event and exact source lineage required")
  importance=max(0.0,min(float(importance),1.0)); uncertainty=max(0.0,min(float(uncertainty),1.0))
  structural=_digest(subject_kind,source_contract,source_id,round(importance,4),round(uncertainty,4),sensitivity,operator_review_required)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   existing=next((x for x in s["subjects"] if x.get("structural_digest")==structural and x.get("state") in {"active","deferred","requires_operator_review"}),None)
   if existing: result={"status":"reflective_subject_reused","subject_id":existing["subject_id"]}
   else:
    now=self.clock(); sid=f"reflective-subject-{structural[:24]}"; row={"subject_id":sid,"subject_kind":subject_kind,"source_id":source_id,"source_contract":source_contract,"importance":importance,"uncertainty":uncertainty,"sensitivity":sensitivity,"operator_review_required":bool(operator_review_required),"state":"requires_operator_review" if operator_review_required else state,"structural_digest":structural,"created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True}],"raw_text":"","prompt":"","provider_payload":"","evidence_text":"","hidden_reasoning":"","reflection_id":"","belief_id":"","goal_id":"","message_id":"","action_id":""};s["subjects"].append(row);result={"status":"reflective_subject_registered","subject_id":sid}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["subjects"]: counts[x.get("subject_kind")]=counts.get(x.get("subject_kind"),0)+1
  recent=[{k:x.get(k) for k in ("subject_id","subject_kind","source_id","source_contract","importance","uncertainty","sensitivity","operator_review_required","state","structural_digest","created_at","updated_at")} for x in s["subjects"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"subject_count":len(s["subjects"]),"kind_counts":counts,"recent_subjects":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"reflection_created":False,"belief_created":False,"goal_created":False,"message_sent":False,"provider_contacted":False,"external_action_executed":False}
def build_reflective_subject_intake_inspection(runtime_root=None): return ReflectiveSubjectIntakeStore(runtime_root).inspection_summary()
