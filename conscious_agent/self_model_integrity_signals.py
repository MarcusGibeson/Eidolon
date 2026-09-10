from __future__ import annotations
"""Content-free v1120.0 self-model integrity signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1120.0"; SCHEMA_VERSION="1"
SIGNAL_TYPES={"support_gap","structural_contradiction","temporal_scope_mismatch","persistence_mismatch","confidence_mismatch","unsupported_identity_claim","state_trait_conflation","lineage_gap"}
CLAIM_TYPES={"identity_claim","self_model_claim","temporary_state","persistent_trait","role_claim","capability_claim","limitation_claim"}
STATES={"active","corrected","retracted","merged","superseded","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_mutate_identity":False,"can_mutate_self_model":False,"can_promote_temporary_state":False,"can_select_attention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class SelfModelIntegritySignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"self_model_integrity_signals.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,signal_type:str,claim_type:str,claim_id:str,related_claim_type:str="",related_claim_id:str="",support_ids:list[str]|None=None,temporal_scope:str="unspecified",persistence_class:str="unknown",confidence:float=.5,uncertainty:float=.5,severity:float=.5,sensitivity:str="normal",structural_digest:str=""):
  event_id=_clean(event_id,180); signal_type=_clean(signal_type,80); claim_type=_clean(claim_type,60); claim_id=_clean(claim_id,220); related_claim_type=_clean(related_claim_type,60); related_claim_id=_clean(related_claim_id,220)
  if not event_id or signal_type not in SIGNAL_TYPES or claim_type not in CLAIM_TYPES or not claim_id: raise ValueError("valid event, signal type, and claim lineage required")
  if related_claim_type and related_claim_type not in CLAIM_TYPES: raise ValueError("invalid related claim type")
  supports=sorted(set(_clean(x,220) for x in (support_ids or []) if _clean(x,220))); clamp=lambda x:round(max(0.0,min(float(x),1.0)),4)
  semantic=_digest(signal_type,claim_type,claim_id,related_claim_type,related_claim_id,*supports,temporal_scope,persistence_class,structural_digest)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   dup=next((x for x in s["signals"] if x.get("semantic_key")==semantic and x.get("state")=="active"),None)
   if dup: result={"status":"duplicate_signal_ignored","signal_id":dup["signal_id"]}
   else:
    now=self.clock(); sid=f"self-model-integrity-signal-{semantic[:24]}"; row={"signal_id":sid,"semantic_key":semantic,"signal_type":signal_type,"claim_type":claim_type,"claim_id":claim_id,"related_claim_type":related_claim_type,"related_claim_id":related_claim_id,"support_ids":supports,"temporal_scope":_clean(temporal_scope,64),"persistence_class":_clean(persistence_class,64),"confidence":clamp(confidence),"uncertainty":clamp(uncertainty),"severity":clamp(severity),"sensitivity":_clean(sensitivity,32),"structural_digest":_clean(structural_digest,128),"state":"active","created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True}],"identity_revision_id":"","self_model_revision_id":"","attention_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["signals"].append(row); result={"status":"self_model_integrity_signal_registered","signal_id":sid}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def revise(self,event_id:str,signal_id:str,*,new_state:str,replacement_id:str=""):
  if new_state not in STATES-{"active"}: raise ValueError("invalid state")
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   row=next((x for x in s["signals"] if x.get("signal_id")==signal_id),None)
   if not row: raise ValueError("unknown signal")
   now=self.clock(); row["state"]=new_state; row["replacement_id"]=_clean(replacement_id,220); row["updated_at"]=now; row["history"].append({"change":new_state,"occurred_at":now,"content_free":True}); result={"status":"self_model_integrity_signal_revised","signal_id":signal_id,"state":new_state}; s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["signals"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("signal_id","signal_type","claim_type","claim_id","related_claim_type","related_claim_id","support_ids","temporal_scope","persistence_class","confidence","uncertainty","severity","sensitivity","structural_digest","state","replacement_id","identity_revision_id","self_model_revision_id","attention_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(s["signals"]),"state_counts":counts,"recent_signals":[{k:x.get(k) for k in keys} for x in s["signals"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"claim_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_self_model_integrity_signal_inspection(runtime_root=None): return SelfModelIntegritySignalStore(runtime_root).inspection_summary()
