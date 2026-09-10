from __future__ import annotations
"""v1142.6 content-free reliability review for operator-guidance influence."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from operator_correction_reasoning_application import OperatorCorrectionReasoningApplicationStore
from operator_correction_reasoning_continuity import OperatorCorrectionReasoningContinuityStore
CONTRACT_VERSION="v1142.6"; SCHEMA_VERSION="1"
STATES={"effective","missed_correction","over_applied","conflict_detected","guidance_drift","inconclusive","suppressed","retracted","superseded","retired"}
AUTHORITY_KEYS=("can_generate_reasoning_text","can_rewrite_history","can_mutate_belief","can_mutate_goal","can_mutate_motivation","can_mutate_self_model","can_execute","can_approve","can_authorize","can_install","can_promote","can_certify")
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p:Any): return hashlib.sha256("\x1f".join(_clean(x,4000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"review_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class OperatorCorrectionReliabilityReviewStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):
  self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"operator_correction_reliability_review.json"; self.clock=clock or _now; self.applications=OperatorCorrectionReasoningApplicationStore(self.runtime_root); self.continuity=OperatorCorrectionReasoningContinuityStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,application_id:str,continuity_id:str="",expected_influence:bool|None=None,observed_influence:bool|None=None,scope_match:bool=True,guidance_revision_match:bool=True,conflict_present:bool=False,operator_review_required:bool=False,retraction_ids:list[str]|None=None,supersession_ids:list[str]|None=None,retirement_ids:list[str]|None=None):
  event_id=_clean(event_id,180); application_id=_clean(application_id); continuity_id=_clean(continuity_id)
  if not event_id or not application_id: raise ValueError("event and application required")
  app=next((r for r in self.applications.snapshot().get("application_records",[]) if r.get("application_id")==application_id),None)
  if not app: raise ValueError("exact v1142.3 application required")
  cont=None
  if continuity_id:
   cont=next((r for r in self.continuity.snapshot().get("continuity_records",[]) if r.get("continuity_id")==continuity_id),None)
   if not cont or cont.get("application_id")!=application_id: raise ValueError("exact v1142.4 continuity lineage required")
  retractions=sorted({_clean(x) for x in retraction_ids or [] if _clean(x)}); supersessions=sorted({_clean(x) for x in supersession_ids or [] if _clean(x)}); retirements=sorted({_clean(x) for x in retirement_ids or [] if _clean(x)})
  if retirements: state="retired"
  elif retractions: state="retracted"
  elif supersessions: state="superseded"
  elif operator_review_required: state="inconclusive"
  elif conflict_present or app.get("state")=="conflict_deferred": state="conflict_detected"
  elif not guidance_revision_match: state="guidance_drift"
  elif expected_influence is True and observed_influence is False: state="missed_correction"
  elif expected_influence is False and observed_influence is True: state="over_applied"
  elif expected_influence is not None and observed_influence is not None and scope_match: state="effective"
  else: state="inconclusive"
  structural=_digest(application_id,continuity_id,expected_influence,observed_influence,scope_match,guidance_revision_match,conflict_present,state,*retractions,*supersessions,*retirements)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in s["review_records"] if x.get("structural_digest")==structural and x.get("state") not in {"retracted","superseded","retired"}),None)
   if duplicate: result={"status":"duplicate_suppressed","review_id":duplicate["review_id"],"state":"suppressed"}
   else:
    now=self.clock(); rid=f"operator-guidance-review-{structural[:24]}"; row={"review_id":rid,"application_id":application_id,"continuity_id":continuity_id,"selected_guidance_ids":list(app.get("selected_guidance_ids") or []),"application_structural_digest":app.get("structural_digest"),"continuity_structural_digest":cont.get("structural_digest") if cont else "","reasoning_scope_id":app.get("reasoning_scope_id"),"expected_influence":expected_influence,"observed_influence":observed_influence,"scope_match":bool(scope_match),"guidance_revision_match":bool(guidance_revision_match),"conflict_present":bool(conflict_present),"state":state,"historical_record_preserved":True,"advisory_only":True,"reasoning_text_stored":False,"state_mutated":False,"retraction_ids":retractions,"supersession_ids":supersessions,"retirement_ids":retirements,"structural_digest":structural,"created_at":now,"history":[{"change":"reliability_review_recorded","state":state,"occurred_at":now,"content_free":True}]}; s["review_records"].append(row); result={"status":"review_recorded","review_id":rid,"state":state}
   now=self.clock();s["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for r in s["review_records"]: counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("review_id","application_id","continuity_id","selected_guidance_ids","application_structural_digest","continuity_structural_digest","reasoning_scope_id","expected_influence","observed_influence","scope_match","guidance_revision_match","conflict_present","state","historical_record_preserved","advisory_only","reasoning_text_stored","state_mutated","retraction_ids","supersession_ids","retirement_ids","structural_digest")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["review_records"]),"state_counts":counts,"recent_records":[{k:r.get(k) for k in keys} for r in s["review_records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"operator_text_exposed":False,"reasoning_text_exposed":False,"history_rewritten":False,"state_mutated":False}
def build_operator_correction_reliability_review_inspection(runtime_root=None): return OperatorCorrectionReliabilityReviewStore(runtime_root).inspection_summary()
