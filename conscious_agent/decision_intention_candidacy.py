from __future__ import annotations
"""Durable, non-forming decision-to-intention candidacy records."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from decision_commitment_lifecycle import DecisionCommitmentStore
CONTRACT_VERSION="v1114.6"
OUTCOMES={"eligible","deferred","suspended","rejected","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"candidates":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_candidates":256,"minimum_support":0.60,"maximum_conflict":0.45,"maximum_risk":0.65},"authority_boundary":{"can_form_intention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_contact_provider":False,"can_modify_files":False}}
class DecisionIntentionCandidacyStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"decision_intention_candidates.json"; self.clock=clock or _now; self.commitments=DecisionCommitmentStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,commitment_id:str,evidence_support:float=.5,conflict_score:float=0.0,risk_score:float=.5,requires_operator_review:bool=False):
  event_id=_clean(event_id,180); commitment_id=_clean(commitment_id,220)
  if not event_id or not commitment_id: raise ValueError("event_id and commitment_id required")
  support=max(0.0,min(float(evidence_support),1.0)); conflict=max(0.0,min(float(conflict_score),1.0)); risk=max(0.0,min(float(risk_score),1.0))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   commitment=next((x for x in self.commitments.snapshot()["commitments"] if x.get("commitment_id")==commitment_id),None)
   if not commitment or commitment.get("lifecycle")!="active": outcome="rejected"; reason="active_commitment_required"
   elif conflict>=s["controls"]["maximum_conflict"]: outcome="suspended"; reason="material_conflict"
   elif risk>s["controls"]["maximum_risk"] or requires_operator_review: outcome="deferred"; reason="operator_review_required"
   elif support<s["controls"]["minimum_support"]: outcome="deferred"; reason="insufficient_support"
   else: outcome="eligible"; reason="bounded_candidacy_only"
   sem=_digest(commitment_id,outcome,round(support,3),round(conflict,3),round(risk,3)); dup=next((x for x in s["candidates"] if x.get("semantic_key")==sem and x.get("state") not in {"retired","rejected"}),None)
   if dup: result={"status":"duplicate_candidate_ignored","candidate_id":dup["candidate_id"],"outcome":dup["state"]}
   else:
    now=self.clock(); cid=f"intention-candidate-{sem[:24]}"; row={"candidate_id":cid,"semantic_key":sem,"commitment_id":commitment_id,"option_id":commitment.get("option_id","") if commitment else "","comparison_id":commitment.get("comparison_id","") if commitment else "","state":outcome,"reason_code":reason,"evidence_support":support,"conflict_score":conflict,"risk_score":risk,"intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"outcome":outcome,"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}]}; s["candidates"]=(s["candidates"]+[row])[-int(s["controls"]["max_candidates"]):]; result={"status":"candidate_recorded","candidate_id":cid,"outcome":outcome,"reason":reason}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={k:sum(x.get("state")==k for x in s["candidates"]) for k in OUTCOMES}; keys=("candidate_id","commitment_id","option_id","comparison_id","state","reason_code","evidence_support","conflict_score","risk_score","intention_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"candidate_count":len(s["candidates"]),"state_counts":counts,"recent_candidates":[{k:x.get(k) for k in keys} for x in s["candidates"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"intention_formed":False,"runtime_mutated":False,"hidden_reasoning_exposed":False,"private_content_exposed":False}
def build_decision_intention_candidacy_inspection(runtime_root=None): return DecisionIntentionCandidacyStore(runtime_root).inspection_summary()
