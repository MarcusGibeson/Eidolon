from __future__ import annotations
"""v1142.7 restrained operator-visible evidence for correction influence outcomes."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from operator_correction_reliability_review import OperatorCorrectionReliabilityReviewStore
CONTRACT_VERSION="v1142.7"; SCHEMA_VERSION="1"
STATES={"supported","review_required","deferred","suppressed","retracted","superseded","retired"}
AUTHORITY_KEYS=("can_generate_reasoning_text","can_rewrite_history","can_mutate_belief","can_mutate_goal","can_mutate_motivation","can_mutate_self_model","can_execute","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"evidence_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class OperatorCorrectionVisibleBehaviorEvidenceStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"operator_correction_visible_behavior_evidence.json"; self.clock=clock or _now; self.reviews=OperatorCorrectionReliabilityReviewStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,review_id:str,behavior_surface_id:str,observation_category:str="reasoning_influence",operator_review_required:bool=False,retraction_ids:list[str]|None=None,supersession_ids:list[str]|None=None,retirement_ids:list[str]|None=None):
  event_id=_clean(event_id,180); review_id=_clean(review_id); surface=_clean(behavior_surface_id); category=_clean(observation_category,80)
  if not event_id or not review_id or not surface: raise ValueError("event, review, and behavior surface required")
  review=next((r for r in self.reviews.snapshot().get("review_records",[]) if r.get("review_id")==review_id),None)
  if not review: raise ValueError("exact v1142.6 review required")
  retractions=sorted({_clean(x) for x in retraction_ids or [] if _clean(x)}); supersessions=sorted({_clean(x) for x in supersession_ids or [] if _clean(x)}); retirements=sorted({_clean(x) for x in retirement_ids or [] if _clean(x)})
  if retirements: state="retired"
  elif retractions: state="retracted"
  elif supersessions: state="superseded"
  elif operator_review_required or review.get("state") in {"missed_correction","over_applied","conflict_detected","guidance_drift","inconclusive"}: state="review_required"
  elif review.get("state")=="effective": state="supported"
  else: state="deferred"
  structural=_digest(review_id,surface,category,state,*retractions,*supersessions,*retirements)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["evidence_records"] if x.get("structural_digest")==structural and x.get("state") not in {"retracted","superseded","retired"}),None)
   if duplicate: result={"status":"duplicate_suppressed","evidence_id":duplicate["evidence_id"],"state":"suppressed"}
   else:
    now=self.clock(); eid=f"operator-guidance-evidence-{structural[:24]}"; row={"evidence_id":eid,"review_id":review_id,"application_id":review.get("application_id"),"continuity_id":review.get("continuity_id"),"review_structural_digest":review.get("structural_digest"),"behavior_surface_id":surface,"observation_category":category,"review_state":review.get("state"),"state":state,"historical_record_preserved":True,"operator_visible":True,"content_free":True,"reasoning_text_exposed":False,"state_mutated":False,"retraction_ids":retractions,"supersession_ids":supersessions,"retirement_ids":retirements,"structural_digest":structural,"created_at":now,"history":[{"change":"visible_evidence_recorded","state":state,"occurred_at":now,"content_free":True}]};s["evidence_records"].append(row);result={"status":"evidence_recorded","evidence_id":eid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s["evidence_records"]: counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("evidence_id","review_id","application_id","continuity_id","review_structural_digest","behavior_surface_id","observation_category","review_state","state","historical_record_preserved","operator_visible","content_free","reasoning_text_exposed","state_mutated","retraction_ids","supersession_ids","retirement_ids","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["evidence_records"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["evidence_records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"operator_text_exposed":False,"reasoning_text_exposed":False,"history_rewritten":False,"state_mutated":False}
def build_operator_correction_visible_behavior_evidence_inspection(runtime_root=None): return OperatorCorrectionVisibleBehaviorEvidenceStore(runtime_root).inspection_summary()
