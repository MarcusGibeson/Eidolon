from __future__ import annotations
"""Content-free commitment outcome evidence and bounded reconsideration triggers."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from decision_commitment_lifecycle import DecisionCommitmentStore
CONTRACT_VERSION="v1114.7"
OUTCOME_CLASSES={"supported","stalled","contradicted","superseded","completed","abandoned","unknown"}
TRIGGERS={"reaffirm_review","reconsider","suspend_review","retirement_review","none"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":"1","contract_version":CONTRACT_VERSION,"outcomes":[],"processed_events":[],"revision":0,"updated_at":"","controls":{"max_outcomes":512},"authority_boundary":{"can_reconsider_automatically":False,"can_transition_commitment":False,"can_form_intention":False,"can_create_proposal":False,"can_approve":False,"can_authorize":False,"can_execute":False}}
class CommitmentOutcomeEvidenceStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"commitment_outcome_evidence.json"; self.clock=clock or _now; self.commitments=DecisionCommitmentStore(self.runtime_root,clock=self.clock)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  if s.get("schema_version")!="1": s=_default()
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def record(self,event_id:str,*,commitment_id:str,outcome_class:str,reliability:float=.5,relevance:float=.5,correction_of:str="",retracted:bool=False):
  if outcome_class not in OUTCOME_CLASSES: raise ValueError("invalid outcome_class")
  event_id=_clean(event_id,180); commitment_id=_clean(commitment_id,220); reliability=max(0.0,min(float(reliability),1.0)); relevance=max(0.0,min(float(relevance),1.0))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   commitment=next((x for x in self.commitments.snapshot()["commitments"] if x.get("commitment_id")==commitment_id),None)
   if not commitment: result={"status":"outcome_rejected","reason":"known_commitment_required","outcome_id":""}
   else:
    if retracted: trigger="none"
    elif outcome_class=="supported" and reliability>=.7 and relevance>=.6: trigger="reaffirm_review"
    elif outcome_class in {"contradicted","superseded"} and reliability>=.6: trigger="suspend_review"
    elif outcome_class in {"completed","abandoned"} and reliability>=.7: trigger="retirement_review"
    elif outcome_class=="stalled" and reliability>=.5: trigger="reconsider"
    else: trigger="none"
    sem=_digest(commitment_id,outcome_class,round(reliability,3),round(relevance,3),correction_of,retracted); dup=next((x for x in s["outcomes"] if x.get("semantic_key")==sem and not x.get("retracted")),None)
    if dup: result={"status":"duplicate_outcome_ignored","outcome_id":dup["outcome_id"],"trigger":dup["reconsideration_trigger"]}
    else:
     now=self.clock(); oid=f"commitment-outcome-{sem[:24]}"; row={"outcome_id":oid,"semantic_key":sem,"commitment_id":commitment_id,"option_id":commitment.get("option_id","") ,"comparison_id":commitment.get("comparison_id","") ,"outcome_class":outcome_class,"reliability":reliability,"relevance":relevance,"correction_of":_clean(correction_of,220),"retracted":bool(retracted),"active_influence":not retracted,"reconsideration_trigger":trigger,"trigger_executed":False,"created_at":now,"updated_at":now,"content_free":True}; s["outcomes"]=(s["outcomes"]+[row])[-int(s["controls"]["max_outcomes"]):]; result={"status":"outcome_recorded","outcome_id":oid,"trigger":trigger}
   now=self.clock(); s["processed_events"]=(s["processed_events"]+[{"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}])[-1024:]; s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); classes={k:sum(x.get("outcome_class")==k for x in s["outcomes"]) for k in OUTCOME_CLASSES}; triggers={k:sum(x.get("reconsideration_trigger")==k for x in s["outcomes"]) for k in TRIGGERS}; keys=("outcome_id","commitment_id","option_id","comparison_id","outcome_class","reliability","relevance","correction_of","retracted","active_influence","reconsideration_trigger","trigger_executed")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"revision":s["revision"],"outcome_count":len(s["outcomes"]),"outcome_class_counts":classes,"trigger_counts":triggers,"recent_outcomes":[{k:x.get(k) for k in keys} for x in s["outcomes"][-24:]],"missing_feedback_is_positive":False,"correlation_is_causation":False,"authority_boundary":deepcopy(s["authority_boundary"]),"runtime_mutated":False,"hidden_reasoning_exposed":False,"private_content_exposed":False}
def build_commitment_outcome_evidence_inspection(runtime_root=None): return CommitmentOutcomeEvidenceStore(runtime_root).inspection_summary()
