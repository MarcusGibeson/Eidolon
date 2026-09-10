from __future__ import annotations
"""v1124.3 bounded reflective-focus sessions over selected attention."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from selected_attention_records import SelectedAttentionStore
CONTRACT_VERSION="v1124.3"; SCHEMA_VERSION="1"
OUTCOMES={"continue_bounded_focus","suspend_for_recovery","disengage_deliberately","defer_for_operator_review","resolve_overlap","unresolved"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"sessions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_create_reflection":False,"can_create_intention":False,"can_create_initiative":False,"can_send_message":False,"can_create_notification":False,"can_contact_provider":False,"can_browse":False,"can_execute":False}}
class ReflectiveFocusDeliberationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"reflective_focus_deliberation.json"; self.clock=clock or _now; self.attention=SelectedAttentionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def open(self,event_id:str,*,attention_id:str,focus_budget:int=1,interruptible:bool=True,recovery_compatible:bool=True,operator_review_required:bool=False,overlap_attention_ids:list[str]|None=None):
  event_id=_clean(event_id,180); attention_id=_clean(attention_id,220); focus_budget=max(1,min(int(focus_budget),8)); overlaps=sorted({_clean(x,220) for x in (overlap_attention_ids or []) if _clean(x,220) and _clean(x,220)!=attention_id})
  known=next((x for x in self.attention.snapshot().get("records",[]) if x.get("attention_id")==attention_id and x.get("state") in {"active","suspended"}),None)
  if not event_id or not known: raise ValueError("eligible selected attention required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   existing=next((x for x in s["sessions"] if x.get("attention_id")==attention_id and x.get("state") in {"open","suspended"}),None)
   if existing: result={"status":"active_focus_session_reused","session_id":existing["session_id"]}
   else:
    now=self.clock(); structural=_digest(attention_id,focus_budget,interruptible,recovery_compatible,operator_review_required,*overlaps); sid=f"reflective-focus-session-{structural[:24]}"; row={"session_id":sid,"attention_id":attention_id,"focus_budget":focus_budget,"interruptible":bool(interruptible),"recovery_compatible":bool(recovery_compatible),"operator_review_required":bool(operator_review_required),"overlap_attention_ids":overlaps,"state":"open","selected_outcome":"","selection_reason_code":"","structural_digest":structural,"created_at":now,"updated_at":now,"history":[{"change":"opened","occurred_at":now,"content_free":True}],"reflection_id":"","intention_id":"","initiative_id":"","message_id":"","notification_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["sessions"].append(row); result={"status":"reflective_focus_session_opened","session_id":sid}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def record_outcome(self,event_id:str,*,session_id:str,outcome:str,reason_code:str):
  if outcome not in OUTCOMES: raise ValueError("valid focus outcome required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["sessions"] if x.get("session_id")==session_id and x.get("state") in {"open","suspended"}),None)
   if not row: raise ValueError("open focus session required")
   if row.get("operator_review_required") and outcome!="defer_for_operator_review": outcome="defer_for_operator_review"
   now=self.clock(); row["selected_outcome"]=outcome; row["selection_reason_code"]=_clean(reason_code,100); row["state"]="suspended" if outcome in {"suspend_for_recovery","defer_for_operator_review","unresolved"} else "closed"; row["updated_at"]=now; row["history"].append({"change":"outcome_recorded","outcome":outcome,"occurred_at":now,"content_free":True}); result={"status":"reflective_focus_outcome_recorded","session_id":session_id,"outcome":outcome,"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False}
   s["processed_events"].append({"event_id":_clean(event_id,180),"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["sessions"]: counts[x.get("selected_outcome") or x.get("state")]=counts.get(x.get("selected_outcome") or x.get("state"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"session_count":len(s["sessions"]),"outcome_counts":counts,"recent_sessions":deepcopy(s["sessions"][-24:]),"authority_boundary":deepcopy(s["authority_boundary"]),"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_reflective_focus_deliberation_inspection(runtime_root=None): return ReflectiveFocusDeliberationStore(runtime_root).inspection_summary()
