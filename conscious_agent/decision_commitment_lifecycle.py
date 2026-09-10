from __future__ import annotations
"""Durable, non-authorizing decision commitments derived from preferred deliberative options."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from deliberative_option_records import DeliberativeOptionStore
CONTRACT_VERSION="v1114.3"
LIFECYCLES={"active","suspended","expired","retired","replaced"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"commitments":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_commitments":256,"default_reconsider_after_seconds":86400,"default_expiry_seconds":604800},"authority_boundary":{"can_form_intention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False,"can_browse":False,"can_contact_provider":False,"can_modify_files":False}}
class DecisionCommitmentStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"decision_commitments.json"; self.clock=clock or _now; self.options=DeliberativeOptionStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def commit(self,event_id:str,*,option_id:str,comparison_id:str,reconsider_at:str="",expires_at:str=""):
  event_id=_clean(event_id,180); option_id=_clean(option_id,220); comparison_id=_clean(comparison_id,220)
  if not event_id or not option_id or not comparison_id: raise ValueError("event_id, option_id, and comparison_id required")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   option=next((x for x in self.options.snapshot()["records"] if x.get("option_id")==option_id),None)
   if not option or option.get("state")!="preferred" or option.get("comparison_id")!=comparison_id: result={"status":"commitment_rejected","reason":"preferred_option_and_exact_comparison_required","commitment_id":""}
   else:
    sem=_digest(option_id,comparison_id); dup=next((x for x in s["commitments"] if x.get("semantic_key")==sem and x.get("lifecycle")=="active"),None)
    if dup: result={"status":"duplicate_commitment_ignored","reason":"semantic_duplicate","commitment_id":dup["commitment_id"]}
    else:
     now=self.clock(); cid=f"decision-commitment-{sem[:24]}"; row={"commitment_id":cid,"semantic_key":sem,"option_id":option_id,"comparison_id":comparison_id,"origin_type":option.get("origin_type"),"origin_id":option.get("origin_id"),"lifecycle":"active","active":True,"reconsider_at":_clean(reconsider_at,48),"expires_at":_clean(expires_at,48),"replaced_by_commitment_id":"","intention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":"","created_at":now,"updated_at":now,"history":[{"outcome":"committed","event_digest":_digest(event_id),"occurred_at":now,"content_free":True}]}; s["commitments"]=(s["commitments"]+[row])[-int(s["controls"]["max_commitments"]):]; result={"status":"commitment_created","reason":"preferred_option_committed","commitment_id":cid}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def transition(self,event_id:str,*,commitment_id:str,outcome:str,reason_code:str="bounded_review",replacement_id:str=""):
  if outcome not in LIFECYCLES: raise ValueError("invalid lifecycle outcome")
  event_id=_clean(event_id,180); commitment_id=_clean(commitment_id,220)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["commitments"] if x.get("commitment_id")==commitment_id),None)
   if not row: result={"status":"transition_rejected","reason":"unknown_commitment"}
   else:
    now=self.clock(); row["lifecycle"]=outcome; row["active"]=outcome=="active"; row["updated_at"]=now
    if outcome=="replaced": row["replaced_by_commitment_id"]=_clean(replacement_id,220)
    row["history"].append({"outcome":outcome,"reason_code":_clean(reason_code,80),"event_digest":_digest(event_id),"occurred_at":now,"content_free":True}); result={"status":"commitment_transitioned","outcome":outcome,"commitment_id":commitment_id}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={k:sum(x.get("lifecycle")==k for x in s["commitments"]) for k in LIFECYCLES}; keys=("commitment_id","option_id","comparison_id","origin_type","origin_id","lifecycle","active","reconsider_at","expires_at","replaced_by_commitment_id","intention_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"commitment_count":len(s["commitments"]),"active_commitment_count":counts.get("active",0),"lifecycle_counts":counts,"recent_commitments":[{k:x.get(k) for k in keys} for x in s["commitments"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"hidden_reasoning_exposed":False,"private_content_exposed":False}
def build_decision_commitment_inspection(runtime_root=None): return DecisionCommitmentStore(runtime_root).inspection_summary()
