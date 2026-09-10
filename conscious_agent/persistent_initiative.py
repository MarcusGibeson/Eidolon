from __future__ import annotations
"""Durable, provider-neutral communicative initiative candidates.

Initiative is an internal candidacy state only. It cannot send a message, browse,
execute, authorize, modify files, manage models, approve, promote, or certify.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from bounded_intention_formation import BoundedIntentionStore
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1108.0"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"candidates":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_candidates":256,"max_active":32,"default_cooldown_seconds":3600},"state_separation":{"initiative_candidacy_is_selection":False,"selection_is_message":False,"message_is_action":False},"authority_boundary":{"can_send":False,"can_browse":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class PersistentInitiativeStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"persistent_initiative.json";self.clock=clock or _now;self.intentions=BoundedIntentionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id,*,intention_id,initiative_kind="raise_subject",salience=.5,urgency=.5,uncertainty=.5,continuity_value=.5,resource_cost=.2,eligible=True):
  event_id=_clean(event_id,180);intention_id=_clean(intention_id,180);kind=_clean(initiative_kind,100)
  if not event_id or not intention_id: raise ValueError("event_id and intention_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   intention=next((x for x in self.intentions.snapshot().get("intentions",[]) if x.get("intention_id")==intention_id),None)
   if not intention or intention.get("active") is not True: result={"status":"initiative_not_registered","reason":"intention_missing_or_inactive","candidate_id":""}
   elif sum(x.get("active_influence") is True for x in s["candidates"])>=int(s["controls"]["max_active"]): result={"status":"initiative_not_registered","reason":"active_candidate_limit","candidate_id":""}
   else:
    key=_digest(intention_id,kind);existing=next((x for x in s["candidates"] if x.get("candidate_key")==key),None)
    if existing: result={"status":"duplicate_candidate_ignored","candidate_id":existing["candidate_id"]}
    else:
     now=self.clock();cid=f"initiative-{key[:24]}";row={"candidate_id":cid,"candidate_key":key,"intention_id":intention_id,"agenda_id":intention.get("agenda_id"),"subject_digest":intention.get("subject_digest"),"kind":kind,"salience":round(max(0,min(1,float(salience))),4),"urgency":round(max(0,min(1,float(urgency))),4),"uncertainty":round(max(0,min(1,float(uncertainty))),4),"continuity_value":round(max(0,min(1,float(continuity_value))),4),"resource_cost":round(max(0,min(1,float(resource_cost))),4),"eligible":bool(eligible),"active_influence":True,"created_at":now,"updated_at":now,"selection_count":0,"last_selected_at":"","deferral_count":0,"message_id":"","action_id":"","authority_granted":False,"provider_contacted":False}
     s["candidates"]=(s["candidates"]+[row])[-int(s["controls"]["max_candidates"]):];result={"status":"initiative_candidate_registered","candidate_id":cid}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["candidates"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"candidate_count":len(rows),"active_candidate_count":sum(x.get("active_influence") is True for x in rows),"eligible_candidate_count":sum(x.get("active_influence") is True and x.get("eligible") is True for x in rows),"recent_candidates":[{k:x.get(k) for k in ("candidate_id","intention_id","agenda_id","subject_digest","kind","salience","urgency","uncertainty","continuity_value","resource_cost","eligible","active_influence","selection_count","message_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"message_sent":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_subjects_exposed":False,"runtime_mutated":False}
def build_persistent_initiative_inspection(runtime_root=None): return PersistentInitiativeStore(runtime_root).inspection_summary()
