from __future__ import annotations
"""Durable, content-free deliberative option records with no external authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1114.0"
ORIGIN_TYPES={"intention","objective","active_inquiry","unresolved_conflict"}
STATES={"candidate","preferred","viable_alternative","deferred","blocked","dominated","incomparable","requires_more_evidence","requires_operator_review","deliberate_no_choice","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_records":256,"max_risk":0.80,"max_resource_cost":0.75,"max_semantic_duplicates":1},"state_separation":{"option_is_decision":False,"decision_is_intention":False,"intention_is_proposal":False,"proposal_is_approval":False,"approval_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_contact_provider":False,"can_ask_user":False,"can_send_message":False,"can_execute":False,"can_authorize":False,"can_modify_files":False,"can_create_external_action":False}}
class DeliberativeOptionStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"deliberative_options.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_type:str,origin_id:str,intended_outcome_digest:str,precondition_digests:list[str]|None=None,dependency_digests:list[str]|None=None,benefit_score:float=.5,risk_score:float=.5,uncertainty:float=.5,resource_cost:float=.5,reversibility:float=.5,time_horizon:str="bounded",operator_constraint_digests:list[str]|None=None)->dict[str,Any]:
  event_id=_clean(event_id,180); origin_type=_clean(origin_type,40); origin_id=_clean(origin_id,220); outcome=_clean(intended_outcome_digest,128)
  if not event_id or origin_type not in ORIGIN_TYPES or not origin_id or not outcome: raise ValueError("valid event_id, origin_type, origin_id, and intended_outcome_digest required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   semantic=_digest(origin_type,origin_id,outcome,*(sorted(precondition_digests or [])),*(sorted(dependency_digests or [])))
   dup=next((x for x in s["records"] if x.get("semantic_key")==semantic and x.get("state")!="retired"),None)
   if dup: result={"status":"duplicate_option_ignored","reason":"semantic_duplicate","option_id":dup["option_id"]}
   else:
    now=self.clock(); oid=f"deliberative-option-{semantic[:24]}"
    clamp=lambda x: round(max(0.0,min(float(x),1.0)),4)
    row={"option_id":oid,"semantic_key":semantic,"origin_type":origin_type,"origin_id":origin_id,"intended_outcome_digest":outcome,"precondition_digests":sorted(set(_clean(x,128) for x in (precondition_digests or []) if _clean(x,128))),"dependency_digests":sorted(set(_clean(x,128) for x in (dependency_digests or []) if _clean(x,128))),"benefit_score":clamp(benefit_score),"risk_score":clamp(risk_score),"uncertainty":clamp(uncertainty),"resource_cost":clamp(resource_cost),"reversibility":clamp(reversibility),"time_horizon":_clean(time_horizon,64),"operator_constraint_digests":sorted(set(_clean(x,128) for x in (operator_constraint_digests or []) if _clean(x,128))),"state":"candidate","comparison_id":"","decision_id":"","intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"change":"registered_candidate","occurred_at":now,"content_free":True}]}
    s["records"]=(s["records"]+[row])[-int(s["controls"]["max_records"]):]; result={"status":"option_registered","reason":"structural_option_registered","option_id":oid}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def apply_comparison(self,option_id:str,*,comparison_id:str,outcome:str):
  if outcome not in STATES-{"candidate"}: raise ValueError("invalid comparison outcome")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); row=next((x for x in s["records"] if x.get("option_id")==option_id),None)
   if not row:return False
   now=self.clock(); row["state"]=outcome; row["comparison_id"]=_clean(comparison_id,220); row["updated_at"]=now; row["history"].append({"change":outcome,"comparison_id":row["comparison_id"],"occurred_at":now,"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return True
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["records"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("option_id","origin_type","origin_id","intended_outcome_digest","precondition_digests","dependency_digests","benefit_score","risk_score","uncertainty","resource_cost","reversibility","time_horizon","operator_constraint_digests","state","comparison_id","decision_id","intention_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"record_count":len(s["records"]),"candidate_count":counts.get("candidate",0),"state_counts":counts,"recent_records":[{k:x.get(k) for k in keys} for x in s["records"][-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_deliberative_option_inspection(runtime_root=None): return DeliberativeOptionStore(runtime_root).inspection_summary()
