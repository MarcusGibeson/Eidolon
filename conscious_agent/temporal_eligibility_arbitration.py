from __future__ import annotations
"""Deterministic temporal eligibility arbitration that recommends review but performs none."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from prospective_obligation_records import ProspectiveObligationStore
CONTRACT_VERSION="v1117.1"
OUTCOMES={"eligible_for_bounded_review","eligible_reduced_budget","not_yet_eligible","awaiting_prerequisite","deferred_by_cognitive_load","deferred_by_recovery_requirement","requires_operator_review","merged","superseded","stale","obsolete","deliberate_non_review","unresolved","missed_window"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _parse(v):
 try:return datetime.fromisoformat(str(v).replace("Z","+00:00"))
 except Exception:return None
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"eligibility_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_perform_review":False,"can_change_objective":False,"can_change_intention":False,"can_notify":False,"can_send_message":False,"can_change_schedule":False,"can_select_attention":False,"can_propose":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class TemporalEligibilityArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"temporal_eligibility_arbitration.json"; self.clock=clock or _now; self.obligations=ProspectiveObligationStore(self.runtime_root,clock=self.clock)
 def _load(self):
  state=load_json_file(self.path,_default(),expected_type=dict)
  if state.get("schema_version")!="1":state=_default()
  for k,v in _default().items():state.setdefault(k,deepcopy(v))
  return state
 def snapshot(self):return deepcopy(self._load())
 def arbitrate(self,event_id:str,*,obligation_id:str,now_at:str="",satisfied_preconditions:list[str]|None=None,cognitive_load:float=0.0,recovery_required:bool=False,operator_review_required:bool=False,semantic_overlap_id:str="",deliberate_non_review:bool=False):
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   state=self._load(); prior=next((x for x in state["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in self.obligations.snapshot()["obligations"] if x.get("obligation_id")==obligation_id),None)
   if not row: raise ValueError("unknown obligation")
   now_text=_clean(now_at,64) or self.clock(); now=_parse(now_text); sat=set(satisfied_preconditions or []); missing=[x for x in row.get("precondition_ids",[]) if x not in sat]
   if row.get("state")=="superseded": outcome,reason="superseded","obligation_lifecycle"
   elif row.get("state") in {"obsolete","retracted","retired"}: outcome,reason="obsolete","obligation_lifecycle"
   elif missing: outcome,reason="awaiting_prerequisite","unsatisfied_preconditions"
   elif deliberate_non_review: outcome,reason="deliberate_non_review","bounded_non_review_selected"
   elif operator_review_required or row.get("sensitivity")=="operator_review": outcome,reason="requires_operator_review","sensitivity_boundary"
   elif recovery_required: outcome,reason="deferred_by_recovery_requirement","recovery_constraint"
   elif float(cognitive_load)>=.8: outcome,reason="deferred_by_cognitive_load","capacity_constraint"
   elif semantic_overlap_id: outcome,reason="merged","semantic_overlap"
   elif not now: outcome,reason="unresolved","invalid_current_time"
   elif _parse(row.get("expires_at")) and now>_parse(row.get("expires_at")): outcome,reason="stale","expiration_boundary"
   elif _parse(row.get("stale_after")) and now>_parse(row.get("stale_after")): outcome,reason="stale","staleness_boundary"
   elif _parse(row.get("earliest_review_at")) and now<_parse(row.get("earliest_review_at")): outcome,reason="not_yet_eligible","earliest_time_not_arrived"
   elif _parse(row.get("target_window_start")) and now<_parse(row.get("target_window_start")): outcome,reason="not_yet_eligible","window_not_open"
   elif _parse(row.get("target_window_end")) and now>_parse(row.get("target_window_end")): outcome,reason="missed_window","window_closed_without_outcome_assumption"
   elif float(cognitive_load)>=.55: outcome,reason="eligible_reduced_budget","bounded_capacity"
   else: outcome,reason="eligible_for_bounded_review","window_open_and_prerequisites_satisfied"
   rid=f"temporal-eligibility-{_digest(event_id,obligation_id,now_text)[:24]}"; result={"status":"eligibility_recorded","eligibility_id":rid,"obligation_id":obligation_id,"outcome":outcome,"reason":reason,"evaluated_at":now_text,"missed_window":outcome=="missed_window","review_performed":False,"underlying_state_changed":False,"notification_id":"","attention_id":"","intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; occurred=self.clock(); state["eligibility_records"]=(state["eligibility_records"]+[{**result,"event_digest":_digest(event_id),"occurred_at":occurred,"content_free":True}])[-1024:]; state["processed_events"]=(state["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":occurred,"result":deepcopy(result),"content_free":True}])[-2048:]; state["revision"]+=1; state["updated_at"]=occurred; write_json_atomic(self.path,state,expected_type=dict,sort_keys=True); return {"ok":True,"status":"eligibility_recorded","result":result,"idempotent":False}
 def inspection_summary(self):
  state=self._load(); counts={}
  for row in state["eligibility_records"]:counts[row.get("outcome")]=counts.get(row.get("outcome"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":state["revision"],"eligibility_count":len(state["eligibility_records"]),"outcome_counts":counts,"recent_eligibility":[{k:x.get(k) for k in ("eligibility_id","obligation_id","outcome","reason","evaluated_at","missed_window","review_performed","underlying_state_changed","notification_id","attention_id","intention_id","proposal_id","approval_id","authorization_id","action_id")} for x in state["eligibility_records"][-24:]],"authority_boundary":deepcopy(state["authority_boundary"]),"time_passing_is_outcome_evidence":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_temporal_eligibility_inspection(runtime_root=None):return TemporalEligibilityArbitrator(runtime_root).inspection_summary()
