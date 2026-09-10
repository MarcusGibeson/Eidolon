from __future__ import annotations
"""v1126.1 durable reflection-quality evaluation candidates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflection_quality_signals import ReflectionQualitySignalStore
CONTRACT_VERSION="v1126.1"; SCHEMA_VERSION="1"
STATES={"active","suppressed","deferred","requires_operator_review","merged","superseded","stale","retracted","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*v:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in v).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"candidates":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_revise_internal_records":False,"can_contact_provider":False,"can_send_message":False,"can_execute":False}}
class ReflectionQualityEvaluationCandidateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflection_quality_evaluation_candidates.json"; self.clock=clock or _now; self.signals=ReflectionQualitySignalStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def create(self,event_id:str,*,signal_id:str,cognitive_load:float=.0,recovery_compatible:bool=True,operator_review_required:bool=False):
  signal=next((x for x in self.signals.snapshot().get("signals",[]) if x.get("signal_id")==signal_id),None)
  if not signal: raise ValueError("existing quality signal required")
  state="active"; reason="quality_review_eligible"
  if signal.get("category")=="well_supported" and float(signal.get("severity",0))<.25: state="suppressed";reason="no_material_quality_concern"
  elif signal.get("recovery_recommended") or cognitive_load>.8 or not recovery_compatible: state="deferred";reason="recovery_or_load_constraint"
  elif operator_review_required: state="requires_operator_review";reason="operator_review_required"
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   structural=_digest(signal_id,state,round(float(cognitive_load),3),recovery_compatible,operator_review_required);existing=next((x for x in s["candidates"] if x.get("structural_digest")==structural),None)
   if existing:result={"status":"duplicate_quality_candidate_suppressed","candidate_id":existing["candidate_id"]}
   else:
    now=self.clock();cid=f"reflection-quality-candidate-{structural[:24]}";s["candidates"].append({"candidate_id":cid,"signal_id":signal_id,"outcome_id":signal.get("outcome_id"),"subject_id":signal.get("subject_id"),"category":signal.get("category"),"severity":signal.get("severity"),"uncertainty":signal.get("uncertainty"),"cognitive_load":max(0,min(1,float(cognitive_load))),"recovery_compatible":bool(recovery_compatible),"operator_review_required":bool(operator_review_required),"state":state,"reason":reason,"structural_digest":structural,"created_at":now,"history":[{"change":"candidate_created","state":state,"occurred_at":now,"content_free":True}]});result={"status":"reflection_quality_candidate_recorded","candidate_id":cid,"state":state,"reason":reason}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["candidates"]:counts[x.get("state")]=counts.get(x.get("state"),0)+1
  recent=[{k:x.get(k) for k in ("candidate_id","signal_id","outcome_id","subject_id","category","severity","uncertainty","cognitive_load","recovery_compatible","operator_review_required","state","reason","structural_digest","created_at")} for x in s["candidates"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"candidate_count":len(s["candidates"]),"state_counts":counts,"recognized_states":sorted(STATES),"recent_candidates":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False}
def build_reflection_quality_evaluation_candidate_inspection(runtime_root=None):return ReflectionQualityEvaluationCandidateStore(runtime_root).inspection_summary()
