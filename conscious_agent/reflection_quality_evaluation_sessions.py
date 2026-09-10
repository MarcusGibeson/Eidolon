from __future__ import annotations
"""v1126.3 bounded reflection-quality evaluation sessions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflection_quality_evaluation_candidates import ReflectionQualityEvaluationCandidateStore
CONTRACT_VERSION="v1126.3"; SCHEMA_VERSION="1"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"sessions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_revise_internal_records":False,"can_contact_provider":False,"can_send_message":False,"can_execute":False}}
class ReflectionQualityEvaluationSessionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflection_quality_evaluation_sessions.json"; self.clock=clock or _now; self.candidates=ReflectionQualityEvaluationCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,candidate_id:str,evaluation_budget:int=1,provider_available:bool=True,recovery_compatible:bool=True):
  c=next((x for x in self.candidates.snapshot().get("candidates",[]) if x.get("candidate_id")==candidate_id),None)
  if not c or c.get("state") not in {"active","deferred","requires_operator_review"}: raise ValueError("eligible quality candidate required")
  budget=max(1,min(int(evaluation_budget),6))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   existing=next((x for x in s["sessions"] if x.get("candidate_id")==candidate_id and x.get("state") in {"open","paused"}),None)
   if existing: result={"status":"active_quality_evaluation_session_reused","session_id":existing["session_id"]}
   else:
    now=self.clock(); state="open" if provider_available and recovery_compatible and c.get("state")=="active" else "paused"; pause_reason="" if state=="open" else ("operator_review_required" if c.get("state")=="requires_operator_review" else "provider_or_recovery_constraint"); structural=_digest(candidate_id,budget,provider_available,recovery_compatible,state); sid=f"reflection-quality-session-{structural[:24]}"; s["sessions"].append({"session_id":sid,"candidate_id":candidate_id,"signal_id":c.get("signal_id"),"outcome_id":c.get("outcome_id"),"category":c.get("category"),"evaluation_budget":budget,"provider_available":bool(provider_available),"recovery_compatible":bool(recovery_compatible),"state":state,"pause_reason":pause_reason,"selected_outcome":"","reason_code":"","structural_digest":structural,"created_at":now,"updated_at":now,"history":[{"change":"opened" if state=="open" else "paused_at_open","occurred_at":now,"content_free":True}]}); result={"status":"reflection_quality_evaluation_session_opened","session_id":sid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":_clean(event_id,180),"occurred_at":now,"result":deepcopy(result)});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["sessions"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  recent=[{k:x.get(k) for k in ("session_id","candidate_id","signal_id","outcome_id","category","evaluation_budget","provider_available","recovery_compatible","state","pause_reason","selected_outcome","reason_code","structural_digest","created_at","updated_at")} for x in s["sessions"][-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"session_count":len(s["sessions"]),"state_counts":counts,"recent_sessions":recent,"authority_boundary":deepcopy(s["authority_boundary"]),"conclusions_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False}
def build_reflection_quality_evaluation_session_inspection(runtime_root=None): return ReflectionQualityEvaluationSessionStore(runtime_root).inspection_summary()
