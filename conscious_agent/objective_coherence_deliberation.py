from __future__ import annotations
"""v1121.3 durable bounded goal-coherence deliberation; never mutates objectives."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from objective_coherence_candidates import ObjectiveCoherenceCandidateStore
CONTRACT_VERSION="v1121.3"; SCHEMA_VERSION="1"
OUTCOMES={"retain","reprioritization_candidate","dependency_repair_candidate","milestone_revision_candidate","clarify_abandonment","unresolved","deliberate_no_repair","requires_operator_review"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"sessions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_reprioritize":False,"can_abandon_objective":False,"can_modify_dependency":False,"can_modify_milestone":False,"can_select_attention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class ObjectiveCoherenceDeliberationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"objective_coherence_deliberation.json"; self.clock=clock or _now; self.candidates=ObjectiveCoherenceCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,candidate_id:str,available_outcomes:list[str]|None=None,operator_review_required:bool=False):
  event_id=_clean(event_id,180); candidate_id=_clean(candidate_id,220); outcomes=list(dict.fromkeys(available_outcomes or ["retain","reprioritization_candidate","dependency_repair_candidate","milestone_revision_candidate","clarify_abandonment","unresolved","deliberate_no_repair"]))
  if not event_id or not candidate_id or any(x not in OUTCOMES for x in outcomes): raise ValueError("valid event_id, candidate_id, and outcomes required")
  known=next((x for x in self.candidates.snapshot().get("candidates",[]) if x.get("candidate_id")==candidate_id and x.get("state")=="active"),None)
  if not known: raise ValueError("active objective coherence candidate required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   existing=next((x for x in s["sessions"] if x.get("candidate_id")==candidate_id and x.get("state") in {"open","deferred"}),None)
   if existing: result={"status":"active_session_reused","session_id":existing["session_id"]}
   else:
    now=self.clock(); sid=f"objective-coherence-session-{_digest(candidate_id,*outcomes)[:24]}"; row={"session_id":sid,"candidate_id":candidate_id,"signal_ids":known.get("signal_ids",[]),"source_types":known.get("source_types",[]),"available_outcomes":outcomes,"operator_review_required":bool(operator_review_required or known.get("operator_review_required")),"state":"open","selected_outcome":"","selection_reason_code":"","created_at":now,"updated_at":now,"history":[{"change":"opened","occurred_at":now,"content_free":True}],"priority_change_id":"","dependency_revision_id":"","milestone_revision_id":"","objective_revision_id":"","decision_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["sessions"].append(row); result={"status":"objective_coherence_deliberation_opened","session_id":sid}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def record_outcome(self,event_id:str,*,session_id:str,outcome:str,reason_code:str="bounded_comparison"):
  if outcome not in OUTCOMES: raise ValueError("invalid outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["sessions"] if x.get("session_id")==session_id),None)
   if not row or row.get("state") not in {"open","deferred"}: raise ValueError("open session required")
   if row.get("operator_review_required") and outcome!="requires_operator_review": outcome="requires_operator_review"
   now=self.clock(); row["selected_outcome"]=outcome; row["selection_reason_code"]=_clean(reason_code,80); row["state"]="deferred" if outcome in {"unresolved","requires_operator_review"} else "closed"; row["updated_at"]=now; row["history"].append({"change":"outcome_recorded","outcome":outcome,"occurred_at":now,"content_free":True}); result={"status":"objective_coherence_outcome_recorded","session_id":session_id,"outcome":outcome,"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False}
   s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["sessions"]: counts[x.get("selected_outcome") or x.get("state")]=counts.get(x.get("selected_outcome") or x.get("state"),0)+1
  keys=("session_id","candidate_id","signal_ids","source_types","available_outcomes","operator_review_required","state","selected_outcome","selection_reason_code","priority_change_id","dependency_revision_id","milestone_revision_id","objective_revision_id","decision_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"session_count":len(s["sessions"]),"outcome_counts":counts,"recent_sessions":[{k:x.get(k) for k in keys} for x in s["sessions"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"objective_text_exposed":False,"hidden_reasoning_exposed":False,"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False,"runtime_mutated":False}
def build_objective_coherence_deliberation_inspection(runtime_root=None): return ObjectiveCoherenceDeliberationStore(runtime_root).inspection_summary()
