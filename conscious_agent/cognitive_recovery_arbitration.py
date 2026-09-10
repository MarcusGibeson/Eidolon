from __future__ import annotations
"""Deterministic, non-executing cognitive recovery and pacing arbitration."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_homeostasis_signals import CognitiveHomeostasisSignalStore
CONTRACT_VERSION="v1116.1"
OUTCOMES={"maintain_pace","reduce_budget_recommended","recovery_window_recommended","defer_new_work_recommended","fragmentation_review_required","operator_review_required","deliberate_rest_recommended","insufficient_evidence"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"reviews":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_signal_count":1,"high_pressure":0.72,"high_fragmentation":0.68,"low_recovery_margin":0.28,"high_uncertainty":0.75,"minimum_rest_reserve":0.15},"authority_boundary":{"can_change_schedule":False,"can_pause_work":False,"can_resume_work":False,"can_select_attention":False,"can_form_intention":False,"can_create_decision":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class CognitiveRecoveryArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"cognitive_recovery_arbitration.json";self.clock=clock or _now;self.signals=CognitiveHomeostasisSignalStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def review(self,event_id:str,*,signal_ids:list[str],operator_review:bool=False,force_rest:bool=False):
  event_id=_clean(event_id,180);ids=list(dict.fromkeys(_clean(x,220) for x in signal_ids if _clean(x,220)))
  if not event_id:raise ValueError("event_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   rows=[x for x in self.signals.snapshot()["signals"] if x.get("signal_id") in ids and x.get("state")=="observed"]
   c=s["controls"]
   if len(rows)<int(c["minimum_signal_count"]):outcome="insufficient_evidence";reason="missing_structural_signal"
   elif operator_review:outcome="operator_review_required";reason="operator_constraint"
   elif force_rest:outcome="deliberate_rest_recommended";reason="explicit_bounded_rest"
   else:
    avg=lambda k:sum(float(x.get(k,0)) for x in rows)/len(rows)
    pressure,fragmentation,margin,uncertainty=avg("load_pressure"),avg("fragmentation"),avg("recovery_margin"),avg("uncertainty")
    if uncertainty>=c["high_uncertainty"]:outcome="insufficient_evidence";reason="high_uncertainty"
    elif fragmentation>=c["high_fragmentation"]:outcome="fragmentation_review_required";reason="fragmentation_threshold"
    elif pressure>=c["high_pressure"] and margin<=c["low_recovery_margin"]:outcome="recovery_window_recommended";reason="high_pressure_low_margin"
    elif pressure>=c["high_pressure"]:outcome="reduce_budget_recommended";reason="high_pressure"
    elif margin<=c["low_recovery_margin"]:outcome="defer_new_work_recommended";reason="low_recovery_margin"
    else:outcome="maintain_pace";reason="bounded_load_with_recovery_margin"
   rid=f"recovery-review-{_digest(event_id,*ids)[:24]}";result={"status":"review_completed","review_id":rid,"signal_ids":ids,"outcome":outcome,"reason":reason,"recommended_rest_reserve":c["minimum_rest_reserve"] if outcome in {"recovery_window_recommended","deliberate_rest_recommended"} else 0.0,"schedule_changed":False,"work_paused":False,"work_resumed":False,"attention_id":"","intention_id":"","decision_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""};now=self.clock();s["reviews"]=(s["reviews"]+[{**result,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}])[-512:];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":"review_completed","result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["reviews"]:counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"review_count":len(s["reviews"]),"outcome_counts":counts,"recent_reviews":[{k:x.get(k) for k in ("review_id","signal_ids","outcome","reason","recommended_rest_reserve","schedule_changed","work_paused","work_resumed","attention_id","intention_id","decision_id","proposal_id","approval_id","authorization_id","action_id")} for x in s["reviews"][-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"external_browsing_performed":False,"provider_contacted":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_cognitive_recovery_arbitration_inspection(runtime_root=None):return CognitiveRecoveryArbitrator(runtime_root).inspection_summary()
