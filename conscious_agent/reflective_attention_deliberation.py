from __future__ import annotations
"""v1123.3 bounded reflective-attention review sessions; never selects attention."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from reflective_attention_review_candidates import ReflectiveAttentionReviewCandidateStore
CONTRACT_VERSION="v1123.3"; SCHEMA_VERSION="1"
OUTCOMES={"retain_for_review","prioritize_for_bounded_attention","defer_for_recovery","merge_overlap","deliberate_non_selection","unresolved","requires_operator_review"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"sessions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_select_attention":False,"can_create_reflection":False,"can_create_intention":False,"can_create_initiative":False,"can_initiate_communication":False,"can_create_notification":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_contact_provider":False,"can_mutate_schedule":False,"can_promote":False,"can_certify":False}}
class ReflectiveAttentionDeliberationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflective_attention_deliberation.json"; self.clock=clock or _now; self.candidates=ReflectiveAttentionReviewCandidateStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,candidate_id:str,available_outcomes:list[str]|None=None):
  event_id=_clean(event_id,180); candidate_id=_clean(candidate_id,220); outcomes=list(dict.fromkeys(available_outcomes or ["retain_for_review","prioritize_for_bounded_attention","defer_for_recovery","merge_overlap","deliberate_non_selection","unresolved","requires_operator_review"]))
  if not event_id or not candidate_id or any(x not in OUTCOMES for x in outcomes): raise ValueError("valid event, candidate, and outcomes required")
  known=next((x for x in self.candidates.snapshot().get("candidates",[]) if x.get("candidate_id")==candidate_id and x.get("state") in {"active","deferred","requires_operator_review"}),None)
  if not known: raise ValueError("eligible attention-review candidate required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   existing=next((x for x in s["sessions"] if x.get("candidate_id")==candidate_id and x.get("state") in {"open","deferred"}),None)
   if existing: result={"status":"active_attention_review_session_reused","session_id":existing["session_id"]}
   else:
    now=self.clock(); sid=f"reflective-attention-session-{_digest(candidate_id,*outcomes)[:24]}"; row={"session_id":sid,"candidate_id":candidate_id,"signal_ids":known.get("signal_ids",[]),"source_categories":known.get("source_categories",[]),"relevance":known.get("relevance",0.0),"importance":known.get("importance",0.0),"urgency":known.get("urgency",0.0),"uncertainty":known.get("uncertainty",0.0),"persistence":known.get("persistence",0.0),"cognitive_load":known.get("cognitive_load",0.0),"recovery_compatibility":known.get("recovery_compatibility",0.0),"semantic_overlap":known.get("semantic_overlap",False),"operator_review_required":known.get("operator_review_required",False),"available_outcomes":outcomes,"state":"open","selected_outcome":"","selection_reason_code":"","created_at":now,"updated_at":now,"history":[{"change":"opened","occurred_at":now,"content_free":True}],"selected_attention_id":"","reflection_id":"","intention_id":"","initiative_id":"","message_id":"","notification_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["sessions"].append(row); result={"status":"reflective_attention_deliberation_opened","session_id":sid}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def record_outcome(self,event_id:str,*,session_id:str,outcome:str,reason_code:str="bounded_salience_comparison"):
  if outcome not in OUTCOMES: raise ValueError("invalid outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["sessions"] if x.get("session_id")==session_id),None)
   if not row or row.get("state") not in {"open","deferred"}: raise ValueError("open session required")
   if row.get("operator_review_required") and outcome!="requires_operator_review": outcome="requires_operator_review"
   now=self.clock(); row["selected_outcome"]=outcome; row["selection_reason_code"]=_clean(reason_code,80); row["state"]="deferred" if outcome in {"unresolved","requires_operator_review","defer_for_recovery"} else "closed"; row["updated_at"]=now; row["history"].append({"change":"outcome_recorded","outcome":outcome,"occurred_at":now,"content_free":True}); result={"status":"reflective_attention_deliberation_outcome_recorded","session_id":session_id,"outcome":outcome,"attention_selected":False,"reflection_created":False,"initiative_created":False,"message_sent":False,"notification_created":False}
   s["processed_events"].append({"event_id":_clean(event_id,180),"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["sessions"]: counts[x.get("selected_outcome") or x.get("state")]=counts.get(x.get("selected_outcome") or x.get("state"),0)+1
  keys=("session_id","candidate_id","signal_ids","source_categories","relevance","importance","urgency","uncertainty","persistence","cognitive_load","recovery_compatibility","semantic_overlap","operator_review_required","available_outcomes","state","selected_outcome","selection_reason_code","selected_attention_id","reflection_id","intention_id","initiative_id","message_id","notification_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"session_count":len(s["sessions"]),"outcome_counts":counts,"recent_sessions":[{k:x.get(k) for k in keys} for x in s["sessions"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"raw_content_exposed":False,"hidden_reasoning_exposed":False,"attention_selected":False,"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"runtime_mutated":False}
def build_reflective_attention_deliberation_inspection(runtime_root=None): return ReflectiveAttentionDeliberationStore(runtime_root).inspection_summary()
