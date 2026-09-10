from __future__ import annotations
"""Bounded, non-adaptive homeostasis drift and recovery-effectiveness reconciliation."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_overload_patterns import CognitiveOverloadPatternStore
from sustainable_cognitive_windows import SustainableCognitiveWindowStore
CONTRACT_VERSION="v1116.7"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"reviews":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_reviews":384,"minimum_supported_patterns":1,"high_drift_threshold":0.6},"authority_boundary":{"can_change_schedule":False,"can_pause_work":False,"can_resume_work":False,"can_adapt_behavior":False,"can_select_attention":False,"can_authorize":False,"can_execute":False}}
class HomeostasisDriftReviewStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"homeostasis_drift_reviews.json"; self.clock=clock or _now; self.patterns=CognitiveOverloadPatternStore(self.runtime_root,clock=self.clock); self.windows=SustainableCognitiveWindowStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def evaluate(self,event_id:str,*,pattern_ids:list[str]|None=None):
  event_id=_clean(event_id,180); wanted={_clean(x,220) for x in (pattern_ids or []) if _clean(x,220)}
  if not event_id: raise ValueError("event_id required")
  patterns=[x for x in self.patterns.snapshot()["patterns"] if x.get("active") and (not wanted or x.get("pattern_id") in wanted)]
  outcomes=[x for x in self.windows.snapshot()["outcomes"] if x.get("outcome") not in {"corrected","retracted"}]
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   effective=sum(x.get("outcome") in {"effective","partially_effective"} for x in outcomes); ineffective=sum(x.get("outcome")=="ineffective" for x in outcomes); known=effective+ineffective; ratio=ineffective/max(1,known)
   c=s["controls"]
   if len(patterns)<int(c["minimum_supported_patterns"]): status,reason="insufficient_evidence","no_supported_overload_pattern"
   elif known==0: status,reason="unresolved","missing_recovery_effectiveness"
   elif ratio>=float(c["high_drift_threshold"]): status,reason="drift_supported","repeated_overload_with_low_recovery_effectiveness"
   elif ratio>0: status,reason="mixed","partial_homeostasis_drift"
   else: status,reason="stable","recovery_effectiveness_supported"
   semantic=_digest(*(x.get("pattern_id") for x in patterns),effective,ineffective,status); dup=next((x for x in s["reviews"] if x.get("semantic_key")==semantic),None)
   if dup: result={"status":"duplicate_drift_review_ignored","review_id":dup["review_id"],"reason":"semantic_duplicate"}
   else:
    now=self.clock(); rid=f"homeostasis-drift-{semantic[:24]}"; row={"review_id":rid,"semantic_key":semantic,"pattern_ids":[x.get("pattern_id") for x in patterns],"supported_pattern_count":len(patterns),"effective_outcome_count":effective,"ineffective_outcome_count":ineffective,"drift_ratio":round(ratio,4),"status":status,"reason":reason,"created_at":now,"content_free":True,"schedule_changed":False,"work_paused":False,"work_resumed":False,"adaptation_applied":False,"attention_selected":False,"authorization_id":"","action_id":""}; s["reviews"]=(s["reviews"]+[row])[-int(c["max_reviews"]):]; result={"status":"homeostasis_drift_reviewed","review_id":rid,"review_status":status,"reason":reason}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:]; s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["reviews"]: counts[x.get("status")]=counts.get(x.get("status"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"review_count":len(s["reviews"]),"status_counts":counts,"recent_reviews":deepcopy(s["reviews"][-24:]),"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"missing_feedback_is_success":False,"raw_messages_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_homeostasis_drift_review_inspection(runtime_root=None): return HomeostasisDriftReviewStore(runtime_root).inspection_summary()
