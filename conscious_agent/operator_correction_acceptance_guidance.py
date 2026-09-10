from __future__ import annotations
"""v1142.1 governed content-free future-reasoning guidance from operator decisions."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore

CONTRACT_VERSION="v1142.1"; SCHEMA_VERSION="1"
INFLUENCE_MODES={"prefer_corrected_lineage","suppress_superseded_lineage","retain_accepted_lineage","require_operator_review","no_future_influence"}
STATES={"active","suppressed","deferred","requires_operator_review","superseded","retracted","retired"}
AUTHORITY_KEYS=("can_rewrite_history","can_delete_history","can_mutate_belief","can_mutate_goal","can_mutate_motivation","can_mutate_self_model","can_generate_reasoning_text","can_execute","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"guidance_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class OperatorCorrectionAcceptanceGuidanceStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"operator_correction_acceptance_guidance.json"; self.clock=clock or _now; self.eligibility=OperatorCorrectionAcceptanceEligibilityStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,eligibility_id:str,influence_mode:str,reasoning_scope_ids:list[str],priority:int=50,contradiction_ids:list[str]|None=None,retraction_ids:list[str]|None=None,supersession_ids:list[str]|None=None,retirement_ids:list[str]|None=None):
  event_id=_clean(event_id,180); eligibility_id=_clean(eligibility_id); influence_mode=_clean(influence_mode,80); scopes=sorted({_clean(x) for x in reasoning_scope_ids if _clean(x)})
  if not event_id or influence_mode not in INFLUENCE_MODES or not scopes: raise ValueError("bounded event, influence mode, and reasoning scopes required")
  eligibility=next((r for r in self.eligibility.snapshot().get("records",[]) if r.get("eligibility_id")==eligibility_id),None)
  if not eligibility: raise ValueError("exact v1142.0 eligibility required")
  contradictions=sorted({_clean(x) for x in contradiction_ids or [] if _clean(x)}); retractions=sorted({_clean(x) for x in retraction_ids or [] if _clean(x)}); supersessions=sorted({_clean(x) for x in supersession_ids or [] if _clean(x)}); retirements=sorted({_clean(x) for x in retirement_ids or [] if _clean(x)})
  state="active"
  if retirements: state="retired"
  elif retractions or eligibility.get("state")=="retracted": state="retracted"
  elif supersessions or eligibility.get("state")=="superseded": state="superseded"
  elif contradictions or eligibility.get("state")=="suppressed": state="suppressed"
  elif eligibility.get("state")!="eligible" or influence_mode=="no_future_influence": state="deferred"
  structural=_digest(eligibility_id,influence_mode,*scopes,priority,*contradictions,*retractions,*supersessions,*retirements)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["guidance_records"] if x.get("structural_digest")==structural and x.get("state") in {"active","deferred","requires_operator_review"}),None)
   if duplicate: result={"status":"duplicate_suppressed","guidance_id":duplicate["guidance_id"],"state":"suppressed"}
   else:
    now=self.clock(); gid=f"operator-guidance-{structural[:24]}"; row={"guidance_id":gid,"eligibility_id":eligibility_id,"operator_decision_id":eligibility.get("operator_decision_id"),"decision_kind":eligibility.get("decision_kind"),"target_kind":eligibility.get("target_kind"),"target_id":eligibility.get("target_id"),"source_record_id":eligibility.get("source_record_id"),"source_revision_id":eligibility.get("source_revision_id"),"influence_mode":influence_mode,"reasoning_scope_ids":scopes,"priority":max(0,min(int(priority),100)),"historical_record_preserved":True,"original_state_mutated":False,"reasoning_mutated_at_record_time":False,"advisory_only":True,"contradiction_ids":contradictions,"retraction_ids":retractions,"supersession_ids":supersessions,"retirement_ids":retirements,"state":state,"structural_digest":structural,"created_at":now,"history":[{"change":"recorded","state":state,"occurred_at":now,"content_free":True}]}; s["guidance_records"].append(row); result={"status":"guidance_recorded","guidance_id":gid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s["guidance_records"]:counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("guidance_id","eligibility_id","operator_decision_id","decision_kind","target_kind","target_id","source_record_id","source_revision_id","influence_mode","reasoning_scope_ids","priority","historical_record_preserved","original_state_mutated","reasoning_mutated_at_record_time","advisory_only","state","structural_digest","contradiction_ids","retraction_ids","supersession_ids","retirement_ids")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["guidance_records"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["guidance_records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"operator_text_exposed":False,"reasoning_text_exposed":False,"history_rewritten":False,"future_reasoning_executed":False}
def build_operator_correction_acceptance_guidance_inspection(runtime_root=None): return OperatorCorrectionAcceptanceGuidanceStore(runtime_root).inspection_summary()
