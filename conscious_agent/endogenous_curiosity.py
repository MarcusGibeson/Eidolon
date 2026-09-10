from __future__ import annotations
"""Durable, provider-neutral curiosity candidates from established uncertainty."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Iterable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1111.0"
ORIGINS={"knowledge_gap","contradictory_evidence","unresolved_inquiry","objective_blocker","self_model_change","structural_change","residual_question"}
ACTIVE={"candidate","deferred"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"candidates":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_candidates":256,"max_active":64,"max_evidence_refs":24},"state_separation":{"curiosity_is_inquiry":False,"curiosity_is_intention":False,"curiosity_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_contact_provider":False,"can_message_user":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class EndogenousCuriosityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"endogenous_curiosity.json";self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1":s=_default()
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self):return deepcopy(self._load())
 def register_candidate(self,event_id,*,origin_kind,subject_summary,evidence_refs:Iterable[str],uncertainty=.5,novelty=.5,answerability=.5,relevance=.5,resource_cost=.2,eligible=True,project_id="",source_state_id="",origin="established_internal_state"):
  event_id=_clean(event_id,180);kind=_clean(origin_kind,80);summary=_clean(subject_summary,600);refs=tuple(_clean(x,240) for x in evidence_refs if _clean(x,240))
  if not event_id or not summary:raise ValueError("event_id and subject_summary required")
  if kind not in ORIGINS:raise ValueError("unsupported origin_kind")
  if not refs:raise ValueError("curiosity requires evidence")
  if _clean(origin,100) in {"generated_dialogue","post_hoc_dialogue"}:raise ValueError("dialogue cannot retroactively justify curiosity")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   key=_digest(kind,summary,project_id,source_state_id);existing=next((x for x in s["candidates"] if x.get("semantic_key")==key and x.get("state") in ACTIVE),None)
   if existing:result={"status":"duplicate_candidate_ignored","candidate_id":existing["candidate_id"]}
   elif sum(x.get("state") in ACTIVE for x in s["candidates"])>=s["controls"]["max_active"]:result={"status":"candidate_not_registered","reason":"active_limit","candidate_id":""}
   else:
    now=self.clock();cid=f"curiosity-{key[:24]}";b=lambda v:round(max(0,min(1,float(v))),4)
    row={"candidate_id":cid,"semantic_key":key,"origin_kind":kind,"subject_digest":_digest(summary),"source_state_digest":_digest(source_state_id),"project_digest":_digest(project_id),"evidence_ref_digests":[_digest(x) for x in refs[:s["controls"]["max_evidence_refs"]]],"evidence_count":len(refs[:s["controls"]["max_evidence_refs"]]),"uncertainty":b(uncertainty),"novelty":b(novelty),"answerability":b(answerability),"relevance":b(relevance),"resource_cost":b(resource_cost),"eligible":bool(eligible),"state":"candidate","deferral_count":0,"selection_count":0,"last_selected_at":"","created_at":now,"updated_at":now,"provider_bound":False,"inquiry_id":"","proposal_id":"","authorization_id":"","action_id":"","authority_granted":False,"history":[{"event_digest":_digest(event_id),"occurred_at":now,"change":"registered","content_free":True}]};s["candidates"]=(s["candidates"]+[row])[-s["controls"]["max_candidates"]:];result={"status":"candidate_registered","candidate_id":cid}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["candidates"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"candidate_count":len(rows),"active_candidate_count":sum(x.get("state") in ACTIVE for x in rows),"eligible_candidate_count":sum(x.get("state") in ACTIVE and x.get("eligible") for x in rows),"origin_counts":{k:sum(x.get("origin_kind")==k for x in rows) for k in sorted(ORIGINS)},"recent_candidates":[{k:x.get(k) for k in ("candidate_id","origin_kind","subject_digest","source_state_digest","project_digest","evidence_count","uncertainty","novelty","answerability","relevance","resource_cost","eligible","state","deferral_count","selection_count","provider_bound","inquiry_id","proposal_id","authorization_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_browsing_performed":False,"message_sent":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_endogenous_curiosity_inspection(runtime_root=None):return EndogenousCuriosityStore(runtime_root).inspection_summary()
