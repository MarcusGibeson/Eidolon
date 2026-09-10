from __future__ import annotations
"""v1135.1 governed content-free deficiency candidates."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from deficiency_signals import DeficiencySignalStore
CONTRACT_VERSION="v1135.1"; SCHEMA_VERSION="1"
STATES={"active","suppressed","deferred","awaiting_prerequisite","requires_operator_review","merged","superseded","stale","obsolete","retracted","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"candidates":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in ("can_read_raw_files","can_modify_source","can_create_sandbox","can_run_tests","can_create_proposal","can_mutate_goals","can_mutate_plans","can_mutate_initiatives","can_approve","can_authorize","can_execute","can_promote","can_certify")}}
class DeficiencyCandidateStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"deficiency_candidates.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def register(self,event_id:str,*,signal_ids:list[str],predecessor_candidate_ids:list[str]|None=None,contradiction_ids:list[str]|None=None,retraction_ids:list[str]|None=None):
  ids=list(dict.fromkeys(_clean(x,220) for x in signal_ids if _clean(x,220))); pred=list(dict.fromkeys(_clean(x,220) for x in (predecessor_candidate_ids or []) if _clean(x,220))); contradictions=list(dict.fromkeys(_clean(x,220) for x in (contradiction_ids or []) if _clean(x,220))); retractions=list(dict.fromkeys(_clean(x,220) for x in (retraction_ids or []) if _clean(x,220)))
  snapshot=DeficiencySignalStore(self.runtime_root).snapshot(); rows=[r for r in snapshot.get("signals",[]) if r.get("signal_id") in ids]
  if not event_id or len(rows)!=len(ids) or not rows: raise ValueError("exact deficiency signal lineage required")
  cats=sorted({r["deficiency_category"] for r in rows}); comps=sorted({x for r in rows for x in r.get("component_ids",[])}); evidence=sorted({x for r in rows for x in r.get("evidence_ids",[])})
  semantic=_digest(*cats,*comps,*evidence,*sorted(r.get("scope_digest","") for r in rows)); recurrence=max(r.get("recurrence_count",1) for r in rows); confidence=max(r.get("confidence",0) for r in rows); uncertainty=max(r.get("uncertainty",1) for r in rows); weak=all(r.get("state")=="suppressed" for r in rows) or (recurrence<2 and confidence<.65); prereqs=sorted({x for r in rows for x in r.get("prerequisite_ids",[])}); review=any(r.get("operator_review_required") for r in rows); state="retracted" if retractions else ("requires_operator_review" if review else ("awaiting_prerequisite" if prereqs else ("suppressed" if weak else "active")))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   data=self._load(); prior=next((x for x in data["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   overlap=next((x for x in data["candidates"] if x.get("semantic_overlap_key")==semantic and x.get("state") in {"active","deferred","awaiting_prerequisite","requires_operator_review"}),None)
   if overlap: result={"status":"semantic_overlap_merged","candidate_id":overlap["candidate_id"]}
   else:
    now=self.clock(); cid=f"def-candidate-{semantic[:24]}"; row={"candidate_id":cid,"signal_ids":ids,"deficiency_categories":cats,"component_ids":comps,"evidence_ids":evidence,"project_digests":sorted({r.get("project_digest","") for r in rows}),"scope_digests":sorted({r.get("scope_digest","") for r in rows}),"predecessor_candidate_ids":pred,"semantic_overlap_key":semantic,"severity":max(r.get("severity",0) for r in rows),"impact":max(max(r.get("user_impact",0),r.get("operator_impact",0),r.get("cognitive_impact",0),r.get("operational_impact",0)) for r in rows),"recurrence_count":recurrence,"reproducibility":max(r.get("reproducibility",0) for r in rows),"confidence":confidence,"uncertainty":uncertainty,"estimated_investigation_cost":max(r.get("estimated_investigation_cost",0) for r in rows),"recovery_compatible":all(r.get("recovery_relevance",0)<.9 for r in rows),"resource_compatible":max(r.get("estimated_investigation_cost",0) for r in rows)<=.8,"prerequisite_ids":prereqs,"operator_review_required":review,"contradiction_ids":contradictions,"retraction_ids":retractions,"structural_digest":_digest(semantic,state,*contradictions,*retractions),"state":state,"created_at":now,"updated_at":now,"proposal_id":"","patch_id":"","sandbox_id":"","test_run_id":"","goal_id":"","plan_id":"","initiative_id":"","approval_id":"","authorization_id":""}; data["candidates"].append(row); result={"status":"deficiency_candidate_registered","candidate_id":cid,"state":state}
   now=self.clock(); data["processed_events"].append({"event_id":_clean(event_id,180),"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); data["revision"]+=1; data["updated_at"]=now; write_json_atomic(self.path,data,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  data=self._load(); counts={}
  for r in data["candidates"]: counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("candidate_id","signal_ids","deficiency_categories","component_ids","evidence_ids","project_digests","scope_digests","predecessor_candidate_ids","semantic_overlap_key","severity","impact","recurrence_count","reproducibility","confidence","uncertainty","estimated_investigation_cost","recovery_compatible","resource_compatible","prerequisite_ids","operator_review_required","contradiction_ids","retraction_ids","structural_digest","state","proposal_id","patch_id","sandbox_id","test_run_id","goal_id","plan_id","initiative_id","approval_id","authorization_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"candidate_count":len(data["candidates"]),"state_counts":counts,"recent_candidates":[{k:r.get(k) for k in keys} for r in data["candidates"][-24:]],"authority_boundary":deepcopy(data["authority_boundary"]),"raw_content_exposed":False,"proposal_text_exposed":False,"source_content_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"external_action_executed":False}
def build_deficiency_candidate_inspection(runtime_root=None): return DeficiencyCandidateStore(runtime_root).inspection_summary()
