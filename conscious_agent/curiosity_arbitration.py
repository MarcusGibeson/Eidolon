from __future__ import annotations
"""Bounded deterministic curiosity arbitration with deliberate non-inquiry."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from endogenous_curiosity import EndogenousCuriosityStore
CONTRACT_VERSION="v1111.1"
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=400):return " ".join(str(v or "").split())[:n]
def _digest(*p):return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":"1","contract_version":CONTRACT_VERSION,"receipts":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"minimum_score":.42,"max_receipts":512,"repeat_penalty":.18,"resource_limit":.7},"authority_boundary":{"can_create_inquiry":False,"can_browse":False,"can_contact_provider":False,"can_message_user":False,"can_execute":False,"can_authorize":False}}
class CuriosityArbitrator:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"curiosity_arbitration.json";self.clock=clock or _now;self.store=EndogenousCuriosityStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def select(self,event_id,*,quiet=False,sleep=False,paused=False,topic_allowed=True,resource_available=1.0):
  event_id=_clean(event_id,180)
  if not event_id:raise ValueError("event_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   candidates=[x for x in self.store.snapshot()["candidates"] if x.get("eligible") and x.get("state") in {"candidate","deferred"}]
   reason="";selected=None;score=0.0
   if quiet or sleep or paused:reason="control_boundary"
   elif not topic_allowed:reason="topic_boundary"
   elif float(resource_available)<.1:reason="resource_boundary"
   else:
    ranked=[]
    for x in candidates:
     base=.32*float(x.get("uncertainty") or 0)+.24*float(x.get("novelty") or 0)+.2*float(x.get("answerability") or 0)+.24*float(x.get("relevance") or 0)-.22*float(x.get("resource_cost") or 0)-s["controls"]["repeat_penalty"]*min(2,int(x.get("selection_count") or 0))
     ranked.append((round(base,6),x.get("candidate_id"),x))
    ranked.sort(key=lambda z:(-z[0],z[1] or ""))
    if ranked and ranked[0][0]>=s["controls"]["minimum_score"] and float(ranked[0][2].get("resource_cost") or 0)<=min(float(resource_available),s["controls"]["resource_limit"]):score,_,selected=ranked[0]
    else:reason="deliberate_non_inquiry"
   now=self.clock();rid=f"curiosity-selection-{_digest(event_id)[:24]}";result={"status":"curiosity_selected" if selected else "no_curiosity_selected","receipt_id":rid,"candidate_id":selected.get("candidate_id") if selected else "","score":score,"reason":reason,"inquiry_id":"","provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"authority_granted":False}
   s["receipts"]=(s["receipts"]+[{**result,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}])[-s["controls"]["max_receipts"]:];s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["receipts"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"receipt_count":len(rows),"selection_count":sum(bool(x.get("candidate_id")) for x in rows),"no_selection_count":sum(not x.get("candidate_id") for x in rows),"recent_receipts":[{k:x.get(k) for k in ("receipt_id","candidate_id","score","reason","inquiry_id","provider_contacted","external_browsing_performed","message_sent","authority_granted")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"authority_boundary":deepcopy(s["authority_boundary"]),"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_curiosity_arbitration_inspection(runtime_root=None):return CuriosityArbitrator(runtime_root).inspection_summary()
