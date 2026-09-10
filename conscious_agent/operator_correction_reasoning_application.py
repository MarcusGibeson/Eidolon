from __future__ import annotations
"""v1142.3 bounded application of operator correction guidance to future reasoning."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from operator_correction_acceptance_guidance import OperatorCorrectionAcceptanceGuidanceStore

CONTRACT_VERSION="v1142.3"; SCHEMA_VERSION="1"
STATES={"selected","no_applicable_guidance","conflict_deferred","operator_review_required","suppressed","retracted","superseded","expired"}
AUTHORITY_KEYS=("can_generate_reasoning_text","can_rewrite_history","can_mutate_belief","can_mutate_goal","can_mutate_motivation","can_mutate_self_model","can_execute","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"application_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class OperatorCorrectionReasoningApplicationStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"operator_correction_reasoning_application.json"; self.clock=clock or _now; self.guidance=OperatorCorrectionAcceptanceGuidanceStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def select(self,event_id:str,*,reasoning_scope_id:str,project_digest:str="",scope_digest:str="",target_kind:str="",target_id:str="",observed_guidance_revision:int|None=None,expired_guidance_ids:list[str]|None=None):
  event_id=_clean(event_id,180); scope=_clean(reasoning_scope_id); target_kind=_clean(target_kind,80); target_id=_clean(target_id); expired=set(_clean(x) for x in expired_guidance_ids or [] if _clean(x))
  if not event_id or not scope: raise ValueError("event and reasoning scope required")
  gs=self.guidance.snapshot(); current_revision=int(gs.get("revision") or 0)
  candidates=[]
  for g in gs.get("guidance_records",[]):
   if scope not in (g.get("reasoning_scope_ids") or []): continue
   if target_kind and g.get("target_kind")!=target_kind: continue
   if target_id and g.get("target_id")!=target_id: continue
   if g.get("state")!="active" or g.get("guidance_id") in expired: continue
   candidates.append(g)
  state="no_applicable_guidance"; reason="no_exact_active_guidance"; selected=[]; suppressed=[]
  stale=observed_guidance_revision is not None and int(observed_guidance_revision)!=current_revision
  if stale: state,reason="operator_review_required","guidance_revision_changed"
  elif candidates:
   ordered=sorted(candidates,key=lambda g:(-int(g.get("priority") or 0),g.get("structural_digest") or "",g.get("guidance_id") or ""))
   top_priority=int(ordered[0].get("priority") or 0); top=[g for g in ordered if int(g.get("priority") or 0)==top_priority]
   modes={g.get("influence_mode") for g in top}
   if "require_operator_review" in modes: state,reason="operator_review_required","operator_review_mode_present"
   elif len(modes)>1 and ({"prefer_corrected_lineage","retain_accepted_lineage"}<=modes or "no_future_influence" in modes): state,reason="conflict_deferred","equal_priority_influence_conflict"
   else:
    winner=top[0]; selected=[winner.get("guidance_id")]; suppressed=[g.get("guidance_id") for g in ordered[1:]]; state,reason="selected","deterministic_priority_and_digest_arbitration"
  structural=_digest(scope,project_digest,scope_digest,target_kind,target_id,current_revision,state,reason,*selected,*suppressed)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   now=self.clock(); aid=f"operator-guidance-application-{structural[:24]}"; row={"application_id":aid,"reasoning_scope_id":scope,"project_digest":_clean(project_digest,128),"scope_digest":_clean(scope_digest,128),"target_kind":target_kind,"target_id":target_id,"guidance_store_revision":current_revision,"observed_guidance_revision":observed_guidance_revision,"selected_guidance_ids":selected,"suppressed_guidance_ids":suppressed,"candidate_count":len(candidates),"state":state,"state_reason":reason,"historical_record_preserved":True,"reasoning_text_generated":False,"reasoning_state_mutated":False,"advisory_application_only":True,"structural_digest":structural,"created_at":now,"history":[{"change":"selection_recorded","state":state,"occurred_at":now,"content_free":True}]}; s["application_records"].append(row); result={"status":"application_recorded","application_id":aid,"state":state,"selected_guidance_ids":selected}; s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s["application_records"]: counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("application_id","reasoning_scope_id","project_digest","scope_digest","target_kind","target_id","guidance_store_revision","observed_guidance_revision","selected_guidance_ids","suppressed_guidance_ids","candidate_count","state","state_reason","historical_record_preserved","reasoning_text_generated","reasoning_state_mutated","advisory_application_only","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["application_records"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["application_records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"operator_text_exposed":False,"reasoning_text_exposed":False,"history_rewritten":False,"reasoning_executed":False}
def build_operator_correction_reasoning_application_inspection(runtime_root=None): return OperatorCorrectionReasoningApplicationStore(runtime_root).inspection_summary()
