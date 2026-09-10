from __future__ import annotations
"""Content-free acknowledgement, deferral, missed-window reconciliation, and temporal conflict detection."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from prospective_review_sessions import ProspectiveReviewSessionStore
CONTRACT_VERSION="v1117.4"
OUTCOMES={"acknowledged","bounded_deferral","missed_window_unresolved","missed_window_acknowledged","conflict_detected","no_conflict","requires_operator_review","superseded","unresolved"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240):return " ".join(str(v or "").split())[:n]
def _digest(*parts):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _parse(v):
 try:return datetime.fromisoformat(str(v).replace("Z","+00:00"))
 except Exception:return None
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_reschedule":False,"can_change_obligation":False,"can_perform_review":False,"can_notify":False,"can_send_message":False,"can_select_attention":False,"can_form_intention":False,"can_propose":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class ProspectiveReviewReconciler:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"prospective_review_reconciliation.json";self.clock=clock or _now;self.sessions=ProspectiveReviewSessionStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def reconcile(self,event_id:str,*,session_id:str,acknowledged:bool=False,deferred_until:str="",conflicting_session_ids:list[str]|None=None,operator_review_required:bool=False):
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   session=next((x for x in self.sessions.snapshot()["sessions"] if x.get("session_id")==session_id),None)
   if not session:raise ValueError("unknown session")
   conflicts=sorted(set(_clean(x,220) for x in (conflicting_session_ids or []) if _clean(x,220) and _clean(x,220)!=session_id))
   missed=session.get("eligibility_outcome")=="missed_window"
   if operator_review_required or session.get("operator_review_required"):outcome,reason="requires_operator_review","sensitivity_boundary"
   elif conflicts:outcome,reason="conflict_detected","overlapping_temporal_claims"
   elif acknowledged and missed:outcome,reason="missed_window_acknowledged","acknowledged_without_outcome_assumption"
   elif acknowledged:outcome,reason="acknowledged","structural_acknowledgement"
   elif deferred_until and _parse(deferred_until):outcome,reason="bounded_deferral","explicit_future_review_boundary"
   elif missed:outcome,reason="missed_window_unresolved","window_closed_without_success_or_failure_assumption"
   else:outcome,reason="no_conflict","no_reconciliation_change_requested"
   rid=f"prospective-reconciliation-{_digest(event_id,session_id,outcome)[:24]}";result={"status":"reconciliation_recorded","reconciliation_id":rid,"session_id":session_id,"obligation_id":session.get("obligation_id"),"outcome":outcome,"reason":reason,"acknowledged":bool(acknowledged),"deferred_until":_clean(deferred_until,64),"conflicting_session_ids":conflicts,"missed_window":missed,"success_inferred":False,"failure_inferred":False,"review_performed":False,"underlying_state_changed":False,"schedule_changed":False,"notification_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""};now=self.clock();s["records"]=(s["records"]+[{**result,"occurred_at":now,"content_free":True}])[-1024:];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-2048:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":"reconciliation_recorded","result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["records"]:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  keys=("reconciliation_id","session_id","obligation_id","outcome","reason","acknowledged","deferred_until","conflicting_session_ids","missed_window","success_inferred","failure_inferred","review_performed","underlying_state_changed","schedule_changed","notification_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"record_count":len(s["records"]),"outcome_counts":counts,"recent_records":[{k:x.get(k) for k in keys} for x in s["records"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"private_content_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_prospective_review_reconciliation_inspection(runtime_root=None):return ProspectiveReviewReconciler(runtime_root).inspection_summary()
