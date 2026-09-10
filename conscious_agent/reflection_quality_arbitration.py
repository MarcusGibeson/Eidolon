from __future__ import annotations
"""v1126.4 deterministic reflection-quality arbitration and provider-recovery continuity."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflection_quality_evaluation_sessions import ReflectionQualityEvaluationSessionStore
CONTRACT_VERSION="v1126.4"; SCHEMA_VERSION="1"
OUTCOMES={"retain_supported_conclusion","mark_unsupported","reconcile_contradiction","recalibrate_confidence","defer_for_provider_recovery","defer_for_operator_review","unresolved"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=200): return " ".join(str(v or "").split())[:n]
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_revise_internal_records":False,"can_contact_provider":False,"can_send_message":False,"can_execute":False}}
class ReflectionQualityArbitrationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflection_quality_arbitration.json"; self.clock=clock or _now; self.sessions=ReflectionQualityEvaluationSessionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,session_id:str,contradiction_supported:bool=False,confidence_calibration_supported:bool=False,provider_recovered:bool=False,operator_review_required:bool=False):
  ss=self.sessions.snapshot(); row=next((x for x in ss.get("sessions",[]) if x.get("session_id")==session_id),None)
  if not row: raise ValueError("quality evaluation session required")
  category=row.get("category"); outcome="unresolved"; reason="insufficient_structural_support"
  if operator_review_required or row.get("pause_reason")=="operator_review_required": outcome="defer_for_operator_review";reason="operator_review_required"
  elif row.get("state")=="paused" and not provider_recovered: outcome="defer_for_provider_recovery";reason="provider_or_recovery_constraint"
  elif category=="unsupported_conclusion": outcome="mark_unsupported";reason="missing_structural_evidence"
  elif category=="contradiction" and contradiction_supported: outcome="reconcile_contradiction";reason="contradiction_structurally_confirmed"
  elif category=="confidence_mismatch" and confidence_calibration_supported: outcome="recalibrate_confidence";reason="confidence_mismatch_confirmed"
  elif category=="provider_failure": outcome="retain_supported_conclusion" if provider_recovered else "defer_for_provider_recovery";reason="provider_recovered" if provider_recovered else "provider_recovery_pending"
  elif category in {"well_supported","provider_recovery"}: outcome="retain_supported_conclusion";reason="structural_support_sufficient"
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   existing=next((x for x in s["outcomes"] if x.get("session_id")==session_id),None)
   if existing: result={"status":"quality_arbitration_outcome_reused","arbitration_id":existing["arbitration_id"],"outcome":existing["outcome"]}
   else:
    now=self.clock(); aid=f"reflection-quality-arbitration-{session_id.rsplit('-',1)[-1]}"; s["outcomes"].append({"arbitration_id":aid,"session_id":session_id,"candidate_id":row.get("candidate_id"),"signal_id":row.get("signal_id"),"outcome_id":row.get("outcome_id"),"category":category,"outcome":outcome,"reason_code":reason,"provider_recovered":bool(provider_recovered),"state":"recorded","created_at":now,"history":[{"change":"arbitrated","occurred_at":now,"content_free":True}]}); result={"status":"reflection_quality_arbitration_recorded","arbitration_id":aid,"outcome":outcome,"reason_code":reason}
   now=self.clock();s["processed_events"].append({"event_id":_clean(event_id,180),"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["outcomes"]:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"outcome_count":len(s["outcomes"]),"outcome_counts":counts,"recognized_outcomes":sorted(OUTCOMES),"recent_outcomes":deepcopy(s["outcomes"][-24:]),"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False}
def build_reflection_quality_arbitration_inspection(runtime_root=None):return ReflectionQualityArbitrationStore(runtime_root).inspection_summary()
