from __future__ import annotations
"""v1139.0 durable content-free supervised sandbox-change eligibility."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from test_plan_arbitration import TestPlanArbitrationStore
CONTRACT_VERSION="v1139.0"; SCHEMA_VERSION="1"
CHANGE_CATEGORIES={"source_repair","test_repair","documentation_repair","configuration_repair","usability_repair","architecture_repair","privacy_governance_repair","deliberate_no_sandbox_change_review"}
OPERATION_CATEGORIES={"create_candidate_file","modify_candidate_file","delete_candidate_file","create_candidate_test","modify_candidate_test","candidate_configuration_change","candidate_documentation_change"}
STATES={"eligible","suppressed","deferred","awaiting_prerequisite","requires_operator_review","superseded","retracted","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"eligibility_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in ("can_read_raw_source","can_write_patch_text","can_modify_source","can_create_sandbox","can_write_sandbox_files","can_execute_commands","can_run_tests","can_install","can_approve","can_authorize","can_execute","can_promote","can_certify")}}
class SandboxChangeEligibilityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"sandbox_change_eligibility.json"; self.clock=clock or _now; self.arbitration=TestPlanArbitrationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,arbitration_id:str,change_category:str,component_ids:list[str],path_digests:list[str],operation_categories:list[str],isolation_profile_id:str,resource_budget_id:str="",prerequisite_ids:list[str]|None=None,operator_review_required:bool=True,estimated_cost:float=.5,reversibility:float=.5,containment_confidence:float=.5):
  outcome=next((x for x in self.arbitration._load().get("outcomes",[]) if x.get("arbitration_id")==arbitration_id),None)
  clean=lambda xs:list(dict.fromkeys(_clean(x,220) for x in (xs or []) if _clean(x,220)))
  comps,paths,ops,prereqs=map(clean,(component_ids,path_digests,operation_categories,prerequisite_ids))
  if not event_id or not outcome or change_category not in CHANGE_CATEGORIES or not comps or not paths or not isolation_profile_id: raise ValueError("exact supported-test-plan lineage and structural sandbox scope required")
  if any(x not in OPERATION_CATEGORIES for x in ops) or not ops: raise ValueError("recognized bounded operation categories required")
  clamp=lambda x:round(max(0,min(float(x),1)),4); cost,rev,contain=map(clamp,(estimated_cost,reversibility,containment_confidence))
  supported=outcome.get("outcome") in {"test_plan_supported","test_plan_probable"}; verified=outcome.get("outcome")=="test_plan_supported"; no_change=change_category=="deliberate_no_sandbox_change_review"
  state,reason="suppressed","unsupported_test_plan_outcome"
  if no_change: state,reason="deferred","deliberate_no_sandbox_change"
  elif prereqs: state,reason="awaiting_prerequisite","prerequisite_pending"
  elif operator_review_required: state,reason="requires_operator_review","operator_review_required"
  elif supported and contain>=.5: state,reason="eligible","bounded_structural_eligibility"
  elif supported: state,reason="suppressed","insufficient_containment_confidence"
  semantic=_digest(arbitration_id,change_category,*comps,*paths,*ops,isolation_profile_id,resource_budget_id,*prereqs)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   dup=next((x for x in s["eligibility_records"] if x.get("semantic_key")==semantic and x.get("state") in {"eligible","deferred","awaiting_prerequisite","requires_operator_review"}),None)
   if dup: result={"status":"sandbox_change_eligibility_reused","eligibility_id":dup["eligibility_id"],"state":dup["state"]}
   else:
    now=self.clock(); eid=f"sandbox-change-eligibility-{semantic[:24]}"; row={"eligibility_id":eid,"arbitration_id":arbitration_id,"session_id":outcome.get("session_id"),"test_plan_candidate_id":outcome.get("candidate_id"),"test_plan_eligibility_ids":outcome.get("eligibility_ids",[]),"specification_candidate_ids":outcome.get("specification_candidate_ids",[]),"proposal_candidate_ids":outcome.get("proposal_candidate_ids",[]),"deficiency_candidate_ids":outcome.get("deficiency_candidate_ids",[]),"test_plan_categories":outcome.get("test_plan_categories",[]),"change_category":change_category,"component_ids":comps,"path_digests":paths,"operation_categories":ops,"isolation_profile_id":_clean(isolation_profile_id,220),"resource_budget_id":_clean(resource_budget_id,220),"project_digests":outcome.get("project_digests",[]),"scope_digests":outcome.get("scope_digests",[]),"evidence_ids":outcome.get("evidence_ids",[]),"supported_test_plan":verified,"eligible_test_plan":supported,"estimated_cost":cost,"reversibility":rev,"containment_confidence":contain,"prerequisite_ids":prereqs,"operator_review_required":bool(operator_review_required),"eligibility_reason":reason,"semantic_key":semantic,"structural_digest":_digest(semantic,state,cost,rev,contain),"state":state,"created_at":now,"updated_at":now,"patch_text_digest":"","sandbox_id":"","sandbox_change_id":"","test_execution_id":"","approval_id":"","authorization_id":"","execution_id":"","installation_id":"","promotion_id":"","certification_id":""}; s["eligibility_records"].append(row); result={"status":"sandbox_change_eligibility_registered","eligibility_id":eid,"state":state,"reason":reason}
   now=self.clock(); s["processed_events"].append({"event_id":_clean(event_id,180),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["eligibility_records"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["eligibility_records"]),"state_counts":counts,"change_categories":sorted(CHANGE_CATEGORIES),"operation_categories":sorted(OPERATION_CATEGORIES),"recent_records":deepcopy(s["eligibility_records"][-24:]),"authority_boundary":deepcopy(s["authority_boundary"]),"raw_source_exposed":False,"patch_text_exposed":False,"private_path_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"external_action_executed":False}
def build_sandbox_change_eligibility_inspection(runtime_root=None): return SandboxChangeEligibilityStore(runtime_root).inspection_summary()
