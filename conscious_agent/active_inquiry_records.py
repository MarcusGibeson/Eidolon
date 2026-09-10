from __future__ import annotations
"""Durable provider-neutral active-inquiry records with no external authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Any
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from curiosity_inquiry_promotion import CuriosityInquiryPromotionStore
CONTRACT_VERSION = "v1113.0"
STATES = {"pending_activation","active_internal","deferred","internal_only","awaiting_operator_review","awaiting_natural_evidence","merged","suspended","abandoned","deliberate_non_inquiry","expired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_records":256,"max_active":32,"default_resource_budget":0.35,"max_resource_budget":0.70,"default_reconsideration_seconds":86400},"state_separation":{"candidate_is_active_inquiry":False,"active_inquiry_is_research_proposal":False,"research_proposal_is_approval":False,"approval_is_authorization":False,"authorization_is_browsing":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_contact_provider":False,"can_ask_user":False,"can_send_message":False,"can_execute":False,"can_authorize":False,"can_modify_files":False,"can_activate_research":False}}
class ActiveInquiryStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):
  self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"active_inquiries.json"; self.clock=clock or _now; self.promotions=CuriosityInquiryPromotionStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,inquiry_candidate_id:str,scope_digest:str="",expected_information_value:float=.5,known_uncertainty:float=.5,sensitivity:float=.0,intrusion:float=.0,resource_budget:float=.35,allowed_source_classes:list[str]|None=None,expires_at:str="",reconsider_after:str="") -> dict[str,Any]:
  event_id=_clean(event_id,180); cid=_clean(inquiry_candidate_id,220)
  if not event_id or not cid: raise ValueError("event_id and inquiry_candidate_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   candidate=next((x for x in self.promotions.snapshot()["promotions"] if x.get("inquiry_candidate_id")==cid and x.get("state")=="candidate"),None)
   semantic=_digest(cid,scope_digest or candidate.get("semantic_key") if candidate else "")
   duplicate=next((x for x in s["records"] if x.get("semantic_key")==semantic and x.get("state") not in {"abandoned","expired","merged"}),None)
   if not candidate: result={"status":"registration_rejected","reason":"eligible_candidate_required","active_inquiry_id":""}
   elif duplicate: result={"status":"duplicate_inquiry_ignored","reason":"semantic_duplicate","active_inquiry_id":duplicate["active_inquiry_id"]}
   else:
    now=self.clock(); iid=f"active-inquiry-{semantic[:24]}"; budget=max(0.0,min(float(resource_budget),float(s["controls"]["max_resource_budget"])))
    row={"active_inquiry_id":iid,"semantic_key":semantic,"inquiry_candidate_id":cid,"question_id":candidate.get("question_id", ""),"decision_id":candidate.get("decision_id", ""),"project_digest":candidate.get("project_digest", ""),"scope_digest":_clean(scope_digest,64),"expected_information_value":round(max(0,min(float(expected_information_value),1)),4),"known_uncertainty":round(max(0,min(float(known_uncertainty),1)),4),"sensitivity":round(max(0,min(float(sensitivity),1)),4),"intrusion":round(max(0,min(float(intrusion),1)),4),"resource_budget":round(budget,4),"allowed_source_classes":sorted(set(_clean(x,40) for x in (allowed_source_classes or ["existing_structural_records"]) if _clean(x,40))),"expires_at":_clean(expires_at,40),"reconsider_after":_clean(reconsider_after,40),"state":"pending_activation","arbitration_id":"","merge_target_id":"","research_proposal_id":"","approval_id":"","authorization_id":"","browse_receipt_id":"","provider_receipt_id":"","user_prompt_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"change":"registered_pending_activation","occurred_at":now,"content_free":True}]}
    s["records"]=(s["records"]+[row])[-int(s["controls"]["max_records"]):]; result={"status":"inquiry_registered","reason":"structural_candidate_registered","active_inquiry_id":iid}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def apply_arbitration(self,active_inquiry_id:str,*,arbitration_id:str,outcome:str,merge_target_id:str=""):
  if outcome not in STATES-{"pending_activation","expired"}: raise ValueError("invalid inquiry outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); row=next((x for x in s["records"] if x.get("active_inquiry_id")==active_inquiry_id),None)
   if not row:return False
   now=self.clock(); row["state"]=outcome;row["arbitration_id"]=_clean(arbitration_id,220);row["merge_target_id"]=_clean(merge_target_id,220);row["updated_at"]=now;row["history"].append({"change":outcome,"arbitration_id":row["arbitration_id"],"occurred_at":now,"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return True
 def inspection_summary(self):
  s=self._load(); rows=s["records"]; counts={}
  for row in rows: counts[row.get("state")]=counts.get(row.get("state"),0)+1
  safe_keys=("active_inquiry_id","inquiry_candidate_id","question_id","decision_id","project_digest","scope_digest","expected_information_value","known_uncertainty","sensitivity","intrusion","resource_budget","allowed_source_classes","expires_at","reconsider_after","state","arbitration_id","merge_target_id","research_proposal_id","approval_id","authorization_id","browse_receipt_id","provider_receipt_id","user_prompt_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"record_count":len(rows),"active_count":counts.get("active_internal",0),"pending_count":counts.get("pending_activation",0),"state_counts":counts,"recent_records":[{k:x.get(k) for k in safe_keys} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_active_inquiry_inspection(runtime_root=None): return ActiveInquiryStore(runtime_root).inspection_summary()
