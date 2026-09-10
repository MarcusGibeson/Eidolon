from __future__ import annotations
"""v1120.6 durable, content-free identity and self-model revision lineage; never mutates claims."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1120.6"; SCHEMA_VERSION="1"
OUTCOMES={"retain","weaken","suspend","reclassify_temporary_state","replace_candidate","unresolved","deliberate_no_revision","requires_operator_review"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"revisions":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_revise_identity":False,"can_revise_self_model":False,"can_delete_history":False,"can_promote_trait":False,"can_reclassify_claim":False,"can_replace_claim":False,"can_select_attention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class IdentityRevisionLineageStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"identity_revision_lineage.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,claim_id:str,session_id:str,outcome:str,claim_type:str="self_model_claim",predecessor_revision_id:str="",replacement_claim_id:str="",temporal_scope:str="unspecified",persistence_class:str="unspecified",confidence:float=.5,uncertainty:float=.5):
  event_id=_clean(event_id,180); claim_id=_clean(claim_id,220); session_id=_clean(session_id,220); outcome=_clean(outcome,80); claim_type=_clean(claim_type,80)
  if not event_id or not claim_id or not session_id or outcome not in OUTCOMES: raise ValueError("valid structural lineage required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   structural=_digest(claim_id,session_id,outcome,claim_type,predecessor_revision_id,replacement_claim_id,temporal_scope,persistence_class)
   existing=next((x for x in s["revisions"] if x.get("structural_digest")==structural),None)
   if existing: result={"status":"duplicate_revision_suppressed","revision_id":existing["revision_id"]}
   else:
    now=self.clock(); rid=f"identity-revision-{structural[:24]}"; row={"revision_id":rid,"claim_id":claim_id,"claim_type":claim_type,"session_id":session_id,"outcome":outcome,"predecessor_revision_id":_clean(predecessor_revision_id,220),"replacement_claim_id":_clean(replacement_claim_id,220),"temporal_scope":_clean(temporal_scope,80),"persistence_class":_clean(persistence_class,80),"confidence":max(0,min(float(confidence),1)),"uncertainty":max(0,min(float(uncertainty),1)),"structural_digest":structural,"state":"recorded","created_at":now,"superseded_by_revision_id":"","history":[{"change":"recorded","occurred_at":now,"content_free":True}],"identity_revised":False,"self_model_revised":False,"temporary_state_promoted":False,"history_deleted":False}; s["revisions"].append(row); result={"status":"identity_revision_lineage_recorded","revision_id":rid,"identity_revised":False,"self_model_revised":False}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def supersede(self,event_id:str,*,revision_id:str,successor_revision_id:str):
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["revisions"] if x.get("revision_id")==revision_id),None); successor=next((x for x in s["revisions"] if x.get("revision_id")==successor_revision_id),None)
   if not row or not successor: raise ValueError("known revisions required")
   now=self.clock(); row["state"]="superseded";row["superseded_by_revision_id"]=successor_revision_id;row["history"].append({"change":"superseded","successor_revision_id":successor_revision_id,"occurred_at":now,"content_free":True});result={"status":"identity_revision_superseded","revision_id":revision_id,"history_preserved":True,"identity_revised":False,"self_model_revised":False};s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["revisions"]: counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
  keys=("revision_id","claim_id","claim_type","session_id","outcome","predecessor_revision_id","replacement_claim_id","temporal_scope","persistence_class","confidence","uncertainty","state","superseded_by_revision_id","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision_count":len(s["revisions"]),"outcome_counts":counts,"recent_revisions":[{k:x.get(k) for k in keys} for x in s["revisions"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"history_preserved":True,"identity_revised":False,"self_model_revised":False,"temporary_state_promoted":False,"raw_messages_exposed":False,"claim_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_identity_revision_lineage_inspection(runtime_root=None): return IdentityRevisionLineageStore(runtime_root).inspection_summary()
