from __future__ import annotations
"""v1132.0 durable content-free revisable world-model relationship signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1132.0"; SCHEMA_VERSION="1"
ENTITY_CATEGORIES={"person","project","event","belief","cause","temporal_context"}
RELATION_CATEGORIES={"associated_with","involves","precedes","follows","supports","contradicts","may_cause","corrects","contextualizes"}
STATES={"active","suppressed","deferred","awaiting_prerequisite","requires_operator_review","superseded","retracted","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_mutate_belief":False,"can_mutate_memory":False,"can_browse":False,"can_contact_provider":False,"can_execute":False,"can_modify_files":False,"can_send_message":False,"can_create_notification":False,"can_approve":False,"can_authorize":False,"can_promote":False,"can_certify":False}}
class RevisableWorldModelSignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"revisable_world_model_signals.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_ids:list[str],subject_id:str,subject_category:str,object_id:str,object_category:str,relation_category:str,evidence_ids:list[str],predecessor_signal_ids:list[str]|None=None,project_id:str="",conversation_id:str="",temporal_context_id:str="",confidence:float=.5,uncertainty:float=.5,sensitivity:float=.0,correction:bool=False,prerequisite_ids:list[str]|None=None,operator_review_required:bool=False,structural_digest:str=""):
  event_id=_clean(event_id,180); origins=list(dict.fromkeys(_clean(x,220) for x in origin_ids if _clean(x,220))); evidence=list(dict.fromkeys(_clean(x,220) for x in evidence_ids if _clean(x,220))); predecessors=list(dict.fromkeys(_clean(x,220) for x in (predecessor_signal_ids or []) if _clean(x,220))); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220)))
  if not event_id or not origins or not evidence or not _clean(subject_id) or not _clean(object_id) or subject_category not in ENTITY_CATEGORIES or object_category not in ENTITY_CATEGORIES or relation_category not in RELATION_CATEGORIES: raise ValueError("complete structural world-model lineage required")
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); confidence,uncertainty,sensitivity=[clamp(x) for x in (confidence,uncertainty,sensitivity)]
  semantic=_digest(subject_id,subject_category,object_id,object_category,relation_category,temporal_context_id,structural_digest)
  state="requires_operator_review" if operator_review_required else ("awaiting_prerequisite" if prereqs else ("suppressed" if confidence<.2 or uncertainty>.95 else "active"))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   dup=next((x for x in s["signals"] if x.get("semantic_key")==semantic and x.get("state") in {"active","deferred","awaiting_prerequisite","requires_operator_review"}),None)
   if dup: result={"status":"duplicate_signal_ignored","signal_id":dup["signal_id"]}
   else:
    now=self.clock(); sid=f"world-model-signal-{semantic[:24]}"; row={"signal_id":sid,"semantic_key":semantic,"origin_ids":origins,"subject_id":_clean(subject_id,220),"subject_category":subject_category,"object_id":_clean(object_id,220),"object_category":object_category,"relation_category":relation_category,"evidence_ids":evidence,"predecessor_signal_ids":predecessors,"project_id":_clean(project_id,160),"conversation_id":_clean(conversation_id,160),"temporal_context_id":_clean(temporal_context_id,220),"confidence":confidence,"uncertainty":uncertainty,"sensitivity":sensitivity,"correction":bool(correction),"prerequisite_ids":prereqs,"operator_review_required":bool(operator_review_required),"structural_digest":_clean(structural_digest,128),"state":state,"created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True,"correction":bool(correction)}],"world_model_candidate_id":"","belief_revision_id":"","message_id":"","approval_id":"","authorization_id":"","action_id":""}; s["signals"].append(row); result={"status":"world_model_signal_registered","signal_id":sid,"state":state}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["signals"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("signal_id","origin_ids","subject_id","subject_category","object_id","object_category","relation_category","evidence_ids","predecessor_signal_ids","project_id","conversation_id","temporal_context_id","confidence","uncertainty","sensitivity","correction","prerequisite_ids","operator_review_required","structural_digest","state","world_model_candidate_id","belief_revision_id","message_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(s["signals"]),"state_counts":counts,"recent_signals":[{k:x.get(k) for k in keys} for x in s["signals"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"evidence_text_exposed":False,"belief_text_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"external_action_executed":False}
def build_revisable_world_model_signal_inspection(runtime_root=None): return RevisableWorldModelSignalStore(runtime_root).inspection_summary()
