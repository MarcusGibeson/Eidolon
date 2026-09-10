from __future__ import annotations
"""Durable v1121.1 objective-coherence review candidates; candidacy never reprioritizes objectives."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from objective_coherence_signals import ObjectiveCoherenceSignalStore
CONTRACT_VERSION="v1121.1"; SCHEMA_VERSION="1"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=300): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,2000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"candidates":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_reprioritize":False,"can_abandon_objective":False,"can_modify_milestone":False,"can_select_attention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class ObjectiveCoherenceCandidateStore:
 def __init__(self,runtime_root=None,*,signals=None,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"objective_coherence_candidates.json"; self.signals=signals or ObjectiveCoherenceSignalStore(self.runtime_root); self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,signal_ids:list[str],importance:float=.5,urgency:float=.5,coherence_risk:float=.5,sensitivity:str="normal",operator_review_required:bool=False,structural_digest:str=""):
  ids=sorted(set(_clean(x,220) for x in signal_ids if _clean(x,220))); event_id=_clean(event_id,180)
  if not event_id or not ids: raise ValueError("event and signal lineage required")
  known={x["signal_id"]:x for x in self.signals.snapshot().get("signals",[]) if x.get("state")=="active"}
  if any(i not in known for i in ids): raise ValueError("unknown or inactive signal")
  clamp=lambda x:round(max(0.0,min(float(x),1.0)),4); semantic=_digest(*ids,structural_digest)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   dup=next((x for x in s["candidates"] if x.get("semantic_key")==semantic and x.get("state")=="active"),None); overlap=next((x for x in s["candidates"] if x.get("state")=="active" and set(x.get("signal_ids",[]))&set(ids)),None)
   if dup: result={"status":"duplicate_candidate_ignored","candidate_id":dup["candidate_id"]}
   elif overlap: result={"status":"semantic_overlap_detected","candidate_id":overlap["candidate_id"],"overlap_signal_ids":sorted(set(overlap.get("signal_ids",[]))&set(ids))}
   else:
    now=self.clock(); cid=f"objective-coherence-candidate-{semantic[:24]}"; source_types=sorted(set(known[i].get("source_type","") for i in ids)|set(known[i].get("related_type","") for i in ids if known[i].get("related_type"))); row={"candidate_id":cid,"semantic_key":semantic,"signal_ids":ids,"source_types":source_types,"importance":clamp(importance),"urgency":clamp(urgency),"coherence_risk":clamp(coherence_risk),"sensitivity":_clean(sensitivity,32),"operator_review_required":bool(operator_review_required),"structural_digest":_clean(structural_digest,128),"state":"active","created_at":now,"updated_at":now,"history":[{"change":"registered","occurred_at":now,"content_free":True}],"priority_change_id":"","objective_revision_id":"","milestone_revision_id":"","decision_id":"","proposal_id":"","approval_id":"","authorization_id":"","action_id":""}; s["candidates"].append(row); result={"status":"objective_coherence_candidate_registered","candidate_id":cid}
   now=self.clock(); s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["candidates"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  keys=("candidate_id","signal_ids","source_types","importance","urgency","coherence_risk","sensitivity","operator_review_required","structural_digest","state","priority_change_id","objective_revision_id","milestone_revision_id","decision_id","proposal_id","approval_id","authorization_id","action_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"candidate_count":len(s["candidates"]),"state_counts":counts,"recent_candidates":[{k:x.get(k) for k in keys} for x in s["candidates"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_messages_exposed":False,"prompts_exposed":False,"provider_payloads_exposed":False,"objective_text_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_objective_coherence_candidate_inspection(runtime_root=None): return ObjectiveCoherenceCandidateStore(runtime_root).inspection_summary()
