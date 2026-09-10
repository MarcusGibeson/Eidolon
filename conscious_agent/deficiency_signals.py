from __future__ import annotations
"""v1135.0 durable content-free deficiency eligibility signals."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
CONTRACT_VERSION="v1135.0"; SCHEMA_VERSION="1"
DEFICIENCY_CATEGORIES={"capability_deficiency","reliability_deficiency","usability_deficiency","architectural_deficiency","test_coverage_deficiency","documentation_or_operator_control_deficiency","privacy_or_governance_deficiency","deliberate_no_deficiency_review"}
SOURCE_CATEGORIES={"project_perception","system_perception","failed_checkpoint","degraded_checkpoint","reliability_review","repeated_cognition_failure","repeated_conversation_failure","repeated_inquiry_failure","repeated_goal_failure","repeated_planning_failure","operator_confirmed_problem","stale_work","blocked_work","abandoned_work","deferred_work","resource_budget_failure","continuity_failure","usability_friction","architectural_structure","sandbox_evidence","development_evidence"}
STATES={"active","suppressed","deferred","awaiting_prerequisite","requires_operator_review","superseded","retracted","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*parts): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in parts).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():
 return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"signals":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in ("can_browse","can_contact_provider","can_execute","can_modify_files","can_install","can_pull_model","can_send_message","can_create_notification","can_create_goal","can_create_plan","can_create_initiative","can_create_proposal","can_approve","can_authorize","can_promote","can_certify","can_delete_data","can_change_rollback")}}
class DeficiencySignalStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):
  self.runtime_root=Path(runtime_root).expanduser().resolve() if runtime_root else _root(); self.path=self.runtime_root/"deficiency_signals.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,origin_ids:list[str],source_categories:list[str],deficiency_category:str,component_ids:list[str],project_digest:str,scope_digest:str,evidence_ids:list[str],recurrence_count:int=1,reproducibility:float=.5,severity:float=.5,urgency:float=.5,user_impact:float=.0,operator_impact:float=.0,cognitive_impact:float=.0,operational_impact:float=.0,confidence:float=.5,uncertainty:float=.5,sensitivity:str="bounded",recovery_relevance:float=.0,estimated_investigation_cost:float=.5,prerequisite_ids:list[str]|None=None,operator_review_required:bool=False,architectural_suspicion:bool=False,verified_defect:bool=False):
  event_id=_clean(event_id,180); origins=list(dict.fromkeys(_clean(x,220) for x in origin_ids if _clean(x,220))); sources=sorted(set(source_categories)); comps=list(dict.fromkeys(_clean(x,220) for x in component_ids if _clean(x,220))); evidence=list(dict.fromkeys(_clean(x,220) for x in evidence_ids if _clean(x,220))); prereqs=list(dict.fromkeys(_clean(x,220) for x in (prerequisite_ids or []) if _clean(x,220)))
  if not event_id or not origins or not comps or not evidence or deficiency_category not in DEFICIENCY_CATEGORIES or not set(sources).issubset(SOURCE_CATEGORIES): raise ValueError("complete structural deficiency lineage required")
  clamp=lambda x:round(max(0,min(float(x),1)),4)
  reproducibility,severity,urgency,user_impact,operator_impact,cognitive_impact,operational_impact,confidence,uncertainty,recovery_relevance,estimated_investigation_cost=[clamp(x) for x in (reproducibility,severity,urgency,user_impact,operator_impact,cognitive_impact,operational_impact,confidence,uncertainty,recovery_relevance,estimated_investigation_cost)]
  recurrence=max(1,int(recurrence_count)); single_sample=recurrence<2 and reproducibility<.6; unsupported_severity=severity>.8 and confidence<.5; novelty_only=recurrence<2 and not verified_defect and not operator_review_required
  semantic=_digest(*origins,*sources,deficiency_category,*comps,project_digest,scope_digest,*evidence)
  state="requires_operator_review" if operator_review_required else ("awaiting_prerequisite" if prereqs else ("suppressed" if single_sample or unsupported_severity or novelty_only or uncertainty>.97 else "active"))
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   data=self._load(); prior=next((x for x in data["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,"status":"duplicate_event_ignored","result":deepcopy(prior["result"]),"idempotent":True}
   duplicate=next((x for x in data["signals"] if x.get("semantic_key")==semantic and x.get("state") in {"active","deferred","awaiting_prerequisite","requires_operator_review"}),None)
   if duplicate: result={"status":"duplicate_signal_ignored","signal_id":duplicate["signal_id"]}
   else:
    now=self.clock(); sid=f"def-signal-{semantic[:24]}"; structural=_digest(semantic,recurrence,reproducibility,severity,urgency,confidence,uncertainty,state)
    row={"signal_id":sid,"semantic_key":semantic,"origin_ids":origins,"source_categories":sources,"deficiency_category":deficiency_category,"component_ids":comps,"project_digest":_clean(project_digest,128),"scope_digest":_clean(scope_digest,128),"evidence_ids":evidence,"recurrence_count":recurrence,"reproducibility":reproducibility,"severity":severity,"urgency":urgency,"user_impact":user_impact,"operator_impact":operator_impact,"cognitive_impact":cognitive_impact,"operational_impact":operational_impact,"confidence":confidence,"uncertainty":uncertainty,"sensitivity":_clean(sensitivity,80),"recovery_relevance":recovery_relevance,"estimated_investigation_cost":estimated_investigation_cost,"prerequisite_ids":prereqs,"operator_review_required":bool(operator_review_required),"architectural_suspicion":bool(architectural_suspicion),"verified_defect":bool(verified_defect),"single_sample_suppressed":single_sample,"unsupported_severity_suppressed":unsupported_severity,"novelty_only_suppressed":novelty_only,"observed_impact_only":True,"structural_digest":structural,"state":state,"created_at":now,"updated_at":now,"candidate_id":"","proposal_id":"","specification_id":"","test_plan_id":"","sandbox_change_id":"","approval_id":"","authorization_id":"","execution_id":"","promotion_id":"","certification_id":""}
    data["signals"].append(row); result={"status":"deficiency_signal_registered","signal_id":sid,"state":state}
   now=self.clock(); data["processed_events"].append({"event_id":event_id,"event_digest":_digest(event_id),"occurred_at":now,"result":deepcopy(result),"content_free":True}); data["revision"]+=1; data["updated_at"]=now; write_json_atomic(self.path,data,expected_type=dict,sort_keys=True); return {"ok":True,"status":result["status"],"result":result,"idempotent":False}
 def inspection_summary(self):
  data=self._load(); counts={}
  for r in data["signals"]: counts[r.get("state")]=counts.get(r.get("state"),0)+1
  keys=("signal_id","origin_ids","source_categories","deficiency_category","component_ids","project_digest","scope_digest","evidence_ids","recurrence_count","reproducibility","severity","urgency","user_impact","operator_impact","cognitive_impact","operational_impact","confidence","uncertainty","sensitivity","recovery_relevance","estimated_investigation_cost","prerequisite_ids","operator_review_required","architectural_suspicion","verified_defect","single_sample_suppressed","unsupported_severity_suppressed","novelty_only_suppressed","observed_impact_only","structural_digest","state","candidate_id","proposal_id","specification_id","test_plan_id","sandbox_change_id","approval_id","authorization_id","execution_id","promotion_id","certification_id")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"signal_count":len(data["signals"]),"state_counts":counts,"recent_signals":[{k:r.get(k) for k in keys} for r in data["signals"][-24:]],"authority_boundary":deepcopy(data["authority_boundary"]),"raw_content_exposed":False,"source_content_exposed":False,"failure_log_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"external_action_executed":False}
def build_deficiency_signal_inspection(runtime_root=None): return DeficiencySignalStore(runtime_root).inspection_summary()
