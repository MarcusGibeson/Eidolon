from __future__ import annotations
"""Promote quality-approved curiosity questions into bounded, non-executing inquiry candidates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from curiosity_quality_arbitration import CuriosityQualityArbitrator
CONTRACT_VERSION="v1111.6"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"promotions":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_candidates":256,"max_active":48},"state_separation":{"question_is_inquiry_candidate":False,"inquiry_candidate_is_active_inquiry":False,"inquiry_is_browse":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_activate_inquiry":False,"can_ask_user":False,"can_browse":False,"can_contact_provider":False,"can_message_user":False,"can_execute":False,"can_authorize":False}}
class CuriosityInquiryPromotionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"curiosity_inquiry_promotions.json"; self.clock=clock or _now; self.quality=CuriosityQualityArbitrator(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def promote(self,event_id,*,decision_id,project_id="",stop_condition_digest=""):
  event_id=_clean(event_id,180); did=_clean(decision_id,220)
  if not event_id or not did: raise ValueError("event_id and decision_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   d=next((x for x in self.quality.snapshot()["decisions"] if x.get("decision_id")==did),None)
   if not d or d.get("outcome")!="eligible_for_inquiry": result={"status":"promotion_rejected","reason":"quality_decision_not_eligible","inquiry_candidate_id":""}
   elif sum(x.get("state")=="candidate" for x in s["promotions"])>=s["controls"]["max_active"]: result={"status":"promotion_rejected","reason":"active_limit","inquiry_candidate_id":""}
   else:
    key=_digest(d.get("question_id"),_clean(project_id,120)); existing=next((x for x in s["promotions"] if x.get("semantic_key")==key and x.get("state")=="candidate"),None)
    if existing: result={"status":"duplicate_promotion_ignored","inquiry_candidate_id":existing["inquiry_candidate_id"]}
    else:
     now=self.clock(); iid=f"curiosity-inquiry-{key[:24]}"; row={"inquiry_candidate_id":iid,"semantic_key":key,"decision_id":did,"question_id":d.get("question_id"),"project_digest":_digest(project_id) if project_id else "","stop_condition_digest":_clean(stop_condition_digest,64),"state":"candidate","active_inquiry_id":"","browse_receipt_id":"","user_prompt_id":"","proposal_id":"","authorization_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"change":"promoted_to_inquiry_candidate","occurred_at":now,"content_free":True}]}; s["promotions"]=(s["promotions"]+[row])[-s["controls"]["max_candidates"]:]; result={"status":"inquiry_candidate_created","inquiry_candidate_id":iid}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); rows=s["promotions"]; return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"promotion_count":len(rows),"active_candidate_count":sum(x.get("state")=="candidate" for x in rows),"recent_promotions":[{k:x.get(k) for k in ("inquiry_candidate_id","decision_id","question_id","project_digest","stop_condition_digest","state","active_inquiry_id","browse_receipt_id","user_prompt_id","proposal_id","authorization_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_curiosity_inquiry_promotion_inspection(runtime_root=None): return CuriosityInquiryPromotionStore(runtime_root).inspection_summary()
