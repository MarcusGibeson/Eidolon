from __future__ import annotations
"""Deterministic temporal reliability, drift, recurrence, and non-authorizing rescheduling proposals for v1117.7."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from prospective_outcome_evidence import ProspectiveOutcomeEvidenceStore
CONTRACT_VERSION="v1117.7"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"reviews":[],"proposals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{"can_reschedule":False,"can_change_obligation":False,"can_notify":False,"can_send_message":False,"can_select_attention":False,"can_form_intention":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class TemporalReliabilityAnalyzer:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"temporal_reliability_patterns.json"; self.clock=clock or _now; self.outcomes=ProspectiveOutcomeEvidenceStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def analyze(self,event_id:str,*,obligation_category:str="general",minimum_evidence:int=3,operator_review_required:bool=True):
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior: return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   records=self.outcomes.snapshot()["records"]; relevant=[x for x in records if _clean(obligation_category,80) in ("","general") or x.get("obligation_category")==obligation_category]
   counts={}
   for x in relevant: counts[x.get("outcome")]=counts.get(x.get("outcome"),0)+1
   total=len(relevant); fulfilled=counts.get("fulfilled",0); partial=counts.get("partially_fulfilled",0); adverse=counts.get("not_fulfilled",0)+counts.get("expired_without_evidence",0)
   sufficient=total>=max(1,int(minimum_evidence)); reliability=round((fulfilled+0.5*partial)/total,4) if total else None
   drift="insufficient_evidence" if not sufficient else ("adverse_drift" if adverse>fulfilled else "stable_or_positive")
   recurrence="none" if not sufficient else ("repeated_nonfulfillment" if adverse>=2 else "no_reliable_recurrence")
   review_id=f"temporal-reliability-{_digest(event_id,obligation_category,total,counts)[:24]}"
   proposal=None
   if sufficient and drift=="adverse_drift":
    proposal={"proposal_id":f"rescheduling-proposal-{_digest(review_id,'operator_review')[:24]}","review_id":review_id,"proposal_type":"operator_reviewed_rescheduling","reason":"adverse_temporal_drift","operator_review_required":True,"approved":False,"authorized":False,"applied":False,"schedule_changed":False,"content_free":True}
   result={"status":"reliability_review_recorded","review_id":review_id,"obligation_category":_clean(obligation_category,80),"evidence_count":total,"minimum_evidence":max(1,int(minimum_evidence)),"sufficient_evidence":sufficient,"outcome_counts":counts,"reliability_score":reliability,"drift_status":drift,"recurrence_status":recurrence,"false_pattern_suppressed":not sufficient,"proposal_id":proposal.get("proposal_id","") if proposal else "","operator_review_required":bool(proposal) or bool(operator_review_required),"schedule_changed":False,"obligation_changed":False,"approval_id":"","authorization_id":"","action_id":""}
   now=self.clock(); s["reviews"]=(s["reviews"]+[{**result,"occurred_at":now,"content_free":True}])[-1024:]
   if proposal: s["proposals"]=(s["proposals"]+[{**proposal,"occurred_at":now}])[-512:]
   s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-2048:]; s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {"ok":True,"status":"reliability_review_recorded","result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); keys=("review_id","obligation_category","evidence_count","minimum_evidence","sufficient_evidence","outcome_counts","reliability_score","drift_status","recurrence_status","false_pattern_suppressed","proposal_id","operator_review_required","schedule_changed","obligation_changed","approval_id","authorization_id","action_id")
  pkeys=("proposal_id","review_id","proposal_type","reason","operator_review_required","approved","authorized","applied","schedule_changed")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"review_count":len(s["reviews"]),"proposal_count":len(s["proposals"]),"recent_reviews":[{k:x.get(k) for k in keys} for x in s["reviews"][-24:]],"recent_proposals":[{k:x.get(k) for k in pkeys} for x in s["proposals"][-24:]],"authority_boundary":deepcopy(s["authority_boundary"]),"private_content_exposed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_temporal_reliability_inspection(runtime_root=None): return TemporalReliabilityAnalyzer(runtime_root).inspection_summary()
