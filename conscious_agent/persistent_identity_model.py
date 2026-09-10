from __future__ import annotations
"""Durable evidence-backed identity claims built on established self-model state."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable, Iterable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from persistent_motivation import MotivationStore
CONTRACT_VERSION="v1110.0"
CLAIM_KINDS={"identity_trait","preference","capability","limitation","value_tendency","behavioral_tendency"}
ACTIVE_STATES={"active","uncertain","suspended"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=500): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"claims":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_claims":256,"max_active":64,"max_evidence_refs":32},"state_separation":{"self_model_is_identity_claim":False,"identity_claim_is_preference":False,"identity_claim_is_intention":False,"identity_claim_is_proposal":False,"proposal_is_authorization":False,"authorization_is_execution":False},"authority_boundary":{"can_browse":False,"can_send":False,"can_execute":False,"can_modify_files":False,"can_manage_models":False,"can_authorize":False,"can_approve":False,"can_promote":False,"can_certify":False}}
class PersistentIdentityModelStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root();self.path=self.runtime_root/"persistent_identity_model.json";self.clock=clock or _now;self.motivations=MotivationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register_claim(self,event_id,*,claim_kind,claim_summary,evidence_refs:Iterable[str],confidence=.5,uncertainty=.5,stability="provisional",scope="global",eligible=True,origin="established_self_model"):
  event_id=_clean(event_id,180); kind=_clean(claim_kind,80); summary=_clean(claim_summary,500); refs=tuple(_clean(x,220) for x in evidence_refs if _clean(x,220))
  if not event_id or not summary: raise ValueError("event_id and claim_summary required")
  if kind not in CLAIM_KINDS: raise ValueError("unsupported claim_kind")
  if not refs: raise ValueError("identity claims require evidence")
  if _clean(origin,100) in {"generated_dialogue","post_hoc_dialogue"}: raise ValueError("dialogue cannot retroactively justify identity")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   key=_digest(kind,summary,scope); existing=next((x for x in s["claims"] if x.get("claim_key")==key and x.get("active_influence") is True),None)
   if existing: result={"status":"duplicate_claim_ignored","claim_id":existing["claim_id"]}
   elif sum(x.get("active_influence") is True for x in s["claims"])>=s["controls"]["max_active"]: result={"status":"claim_not_registered","reason":"active_claim_limit","claim_id":""}
   else:
    now=self.clock();cid=f"identity-{key[:24]}"; row={"claim_id":cid,"claim_key":key,"claim_kind":kind,"claim_digest":_digest(summary),"scope_digest":_digest(scope),"origin":_clean(origin,100),"evidence_ref_digests":[_digest(x) for x in refs[:s["controls"]["max_evidence_refs"]]],"evidence_count":len(refs[:s["controls"]["max_evidence_refs"]]),"support_count":len(refs),"contradiction_count":0,"confidence":round(max(0,min(1,float(confidence))),4),"uncertainty":round(max(0,min(1,float(uncertainty))),4),"stability":_clean(stability,80),"state":"active","eligible":bool(eligible),"active_influence":True,"created_at":now,"updated_at":now,"revision":1,"provider_bound":False,"project_bound":False,"proposal_id":"","authorization_id":"","action_id":"","authority_granted":False,"update_history":[{"event_digest":_digest(event_id),"occurred_at":now,"change":"registered","content_free":True}]};s["claims"]=(s["claims"]+[row])[-s["controls"]["max_claims"]:];result={"status":"claim_registered","claim_id":cid}
   now=self.clock();s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:];s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();rows=s["claims"];return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"claim_count":len(rows),"active_claim_count":sum(x.get("active_influence") is True for x in rows),"uncertain_claim_count":sum(x.get("state")=="uncertain" for x in rows),"suspended_claim_count":sum(x.get("state")=="suspended" for x in rows),"recent_claims":[{k:x.get(k) for k in ("claim_id","claim_kind","claim_digest","scope_digest","evidence_count","support_count","contradiction_count","confidence","uncertainty","stability","state","eligible","active_influence","provider_bound","project_bound","proposal_id","authorization_id","action_id")} for x in rows[-24:]],"controls":deepcopy(s["controls"]),"state_separation":deepcopy(s["state_separation"]),"authority_boundary":deepcopy(s["authority_boundary"]),"provider_contacted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"private_content_exposed":False,"runtime_mutated":False}
def build_persistent_identity_model_inspection(runtime_root=None): return PersistentIdentityModelStore(runtime_root).inspection_summary()
