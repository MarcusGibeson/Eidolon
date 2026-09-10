from __future__ import annotations
"""Durable non-authorizing intentions derived from bounded reflection outcomes."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any,Callable
from agenda_guided_reflection import AgendaGuidedReflection
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1107.4"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"intentions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_intentions":256,"max_active":32},"state_separation":{"attention_is_intention":False,"intention_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_create_action_proposal":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_modify_files":False,"can_manage_models":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class BoundedIntentionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"bounded_intentions.json";self.clock=clock or _now;self.reflections=AgendaGuidedReflection(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def form(self,event_id,*,intake_id,intention_kind="reflect_further",priority=.5,confidence=.5,expires_at=""):
  event_id=_clean(event_id,180);intake_id=_clean(intake_id,180);kind=_clean(intention_kind,100)
  if not event_id or not intake_id:raise ValueError("event_id and intake_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   intake=next((x for x in self.reflections.snapshot().get("intakes",[]) if x.get("intake_id")==intake_id),None)
   if not intake or intake.get("eligible_for_intention") is not True:result={"status":"intention_not_formed","reason":"reflection_not_eligible","intention_id":""}
   elif sum(x.get("active") is True for x in s["intentions"])>=int(s["controls"]["max_active"]):result={"status":"intention_not_formed","reason":"active_intention_limit","intention_id":""}
   else:
    key=_digest(intake_id,kind);existing=next((x for x in s["intentions"] if x.get("intention_key")==key),None)
    if existing:result={"status":"duplicate_intention_ignored","intention_id":existing["intention_id"]}
    else:
     now=self.clock();iid=f"intention-{key[:24]}";row={"intention_id":iid,"intention_key":key,"intake_id":intake_id,"agenda_id":intake.get("agenda_id"),"subject_digest":intake.get("subject_digest"),"kind":kind,"priority":round(max(0,min(1,float(priority))),4),"confidence":round(max(0,min(1,float(confidence))),4),"created_at":now,"updated_at":now,"expires_at":_clean(expires_at,80),"active":True,"lifecycle":"active","proposal_id":"","authorized_action_id":"","completed_action_id":"","provider_contacted":False,"external_action_requested":False,"action_authority_granted":False,"hidden_reasoning_stored":False};s["intentions"]=(s["intentions"]+[row])[-int(s["controls"]["max_intentions"]):];result={"status":"intention_formed","intention_id":iid,"lifecycle":"active"}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["intentions"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"intention_count":len(rows),"active_intention_count":sum(x.get("active") is True for x in rows),"recent_intentions":[{k:x.get(k) for k in ("intention_id","intake_id","agenda_id","subject_digest","kind","priority","confidence","created_at","lifecycle","proposal_id","authorized_action_id","completed_action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"action_authority_changed":False,"hidden_reasoning_exposed":False,"private_subjects_exposed":False,"runtime_mutated":False}
def build_bounded_intention_inspection(runtime_root=None):return BoundedIntentionStore(runtime_root).inspection_summary()
