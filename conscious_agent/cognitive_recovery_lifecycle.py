from __future__ import annotations
"""Durable, operator-reviewed cognitive recovery lifecycle records with no scheduling authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1116.3"
ELIGIBLE_OUTCOMES={"reduce_budget_recommended","recovery_window_recommended","defer_new_work_recommended","fragmentation_review_required","operator_review_required","deliberate_rest_recommended"}
STATES={"proposed","acknowledged","active_observation","completed","suspended","retired","corrected","retracted"}
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_records":384,"max_window_units":64,"max_rest_reserve":0.5},"authority_boundary":{"can_change_schedule":False,"can_pause_work":False,"can_resume_work":False,"can_select_attention":False,"can_form_intention":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class CognitiveRecoveryLifecycleStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"cognitive_recovery_lifecycle.json";self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def propose(self,event_id:str,*,review_id:str,recommendation:str,recommended_rest_reserve:float=0.0,window_units:int=1,structural_digest:str=""):
  event_id=_clean(event_id,180);review_id=_clean(review_id,220);recommendation=_clean(recommendation,80)
  if not event_id or not review_id or recommendation not in ELIGIBLE_OUTCOMES:raise ValueError("valid event_id, review_id, and eligible recommendation required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   semantic=_digest(review_id,recommendation,_clean(structural_digest,128));dup=next((x for x in s["records"] if x.get("semantic_key")==semantic and x.get("state") not in {"retired","retracted"}),None)
   if dup:result={"status":"duplicate_recovery_record_ignored","recovery_id":dup["recovery_id"],"reason":"semantic_duplicate"}
   else:
    now=self.clock();rid=f"recovery-lifecycle-{semantic[:24]}";c=s["controls"];row={"recovery_id":rid,"semantic_key":semantic,"review_id":review_id,"recommendation":recommendation,"recommended_rest_reserve":round(max(0.0,min(float(recommended_rest_reserve),float(c["max_rest_reserve"]))),4),"window_units":max(1,min(int(window_units),int(c["max_window_units"]))),"structural_digest":_clean(structural_digest,128),"state":"proposed","created_at":now,"updated_at":now,"history":[{"change":"proposed","occurred_at":now,"content_free":True}],"schedule_id":"","work_item_id":"","attention_id":"","intention_id":"","decision_id":"","approval_id":"","authorization_id":"","action_id":""};s["records"]=(s["records"]+[row])[-int(c["max_records"]):];result={"status":"recovery_record_proposed","recovery_id":rid,"reason":"bounded_recovery_recommendation"}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def transition(self,event_id:str,*,recovery_id:str,outcome:str,operator_confirmed:bool=False):
  event_id=_clean(event_id,180);recovery_id=_clean(recovery_id,220);outcome=_clean(outcome,64)
  if outcome not in {"acknowledged","active_observation","completed","suspended","retired","corrected","retracted"}:raise ValueError("unsupported lifecycle outcome")
  if not operator_confirmed:return {"ok":False,"status":"confirmation_required","state_changed":False}
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["records"] if x.get("recovery_id")==recovery_id),None)
   if not row:raise ValueError("unknown recovery_id")
   now=self.clock();previous=row["state"];row["state"]=outcome;row["updated_at"]=now;row["history"].append({"change":outcome,"previous_state":previous,"occurred_at":now,"content_free":True,"operator_confirmed":True});result={"status":"recovery_lifecycle_updated","recovery_id":recovery_id,"previous_state":previous,"state":outcome,"schedule_changed":False,"work_paused":False,"work_resumed":False}
   s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1536:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":"recovery_lifecycle_updated","result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();counts={}
  for x in s["records"]:counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("recovery_id","review_id","recommendation","recommended_rest_reserve","window_units","structural_digest","state","schedule_id","work_item_id","attention_id","intention_id","decision_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"record_count":len(s["records"]),"state_counts":counts,"recent_records":[{k:x.get(k) for k in keys} for x in s["records"][-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_cognitive_recovery_lifecycle_inspection(runtime_root=None):return CognitiveRecoveryLifecycleStore(runtime_root).inspection_summary()
