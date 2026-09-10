from __future__ import annotations
"""v1140.0 durable content-free isolated sandbox execution eligibility."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from sandbox_change_arbitration import SandboxChangeArbitrationStore
CONTRACT_VERSION="v1140.0"; SCHEMA_VERSION="1"
EXECUTION_MODES={"materialize_isolated_workspace","apply_candidate_change","run_candidate_compile","run_candidate_tests","collect_structural_receipts","deliberate_no_execution_review"}
STATES={"eligible","suppressed","deferred","awaiting_prerequisite","requires_operator_review","superseded","retracted","stale","retired"}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=240): return " ".join(str(v or "").split())[:n]
def _digest(*p): return hashlib.sha256("\x1f".join(_clean(x,3000) for x in p).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"eligibility_records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in ("can_read_raw_source","can_write_patch_text","can_create_sandbox","can_write_sandbox_files","can_execute_commands","can_run_tests","can_modify_source","can_install","can_approve","can_authorize","can_execute","can_promote","can_certify")}}
class IsolatedSandboxExecutionEligibilityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"isolated_sandbox_execution_eligibility.json"; self.clock=clock or _now; self.arbitration=SandboxChangeArbitrationStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def snapshot(self): return deepcopy(self._load())
 def register(self,event_id:str,*,arbitration_id:str,execution_modes:list[str],isolation_profile_id:str,workspace_manifest_digest:str,resource_budget_id:str="",command_profile_id:str="",prerequisite_ids:list[str]|None=None,operator_review_required:bool=True,estimated_cost:float=.5,containment_confidence:float=.5,reversibility:float=.5):
  outcome=next((x for x in self.arbitration._load().get("outcomes",[]) if x.get("arbitration_id")==arbitration_id),None)
  clean=lambda xs:list(dict.fromkeys(_clean(x,220) for x in (xs or []) if _clean(x,220)))
  modes,prereqs=clean(execution_modes),clean(prerequisite_ids)
  if not event_id or not outcome or not isolation_profile_id or not workspace_manifest_digest: raise ValueError("exact supported sandbox-change lineage and isolation manifest required")
  if not modes or any(x not in EXECUTION_MODES for x in modes): raise ValueError("recognized bounded execution modes required")
  clamp=lambda x:round(max(0,min(float(x),1)),4); cost,contain,rev=map(clamp,(estimated_cost,containment_confidence,reversibility))
  supported=outcome.get("outcome") in {"sandbox_change_supported","sandbox_change_probable"}; verified=outcome.get("outcome")=="sandbox_change_supported"; no_exec="deliberate_no_execution_review" in modes
  state,reason="suppressed","unsupported_sandbox_change_outcome"
  if no_exec: state,reason="deferred","deliberate_no_execution"
  elif prereqs: state,reason="awaiting_prerequisite","prerequisite_pending"
  elif operator_review_required: state,reason="requires_operator_review","operator_review_required"
  elif supported and contain>=.65 and rev>=.5: state,reason="eligible","bounded_isolated_execution_eligibility"
  elif supported: state,reason="suppressed","insufficient_containment_or_reversibility"
  semantic=_digest(arbitration_id,*modes,isolation_profile_id,workspace_manifest_digest,resource_budget_id,command_profile_id,*prereqs)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   dup=next((x for x in s["eligibility_records"] if x.get("semantic_key")==semantic and x.get("state") in {"eligible","deferred","awaiting_prerequisite","requires_operator_review"}),None)
   if dup: result={"status":"isolated_sandbox_execution_eligibility_reused","eligibility_id":dup["eligibility_id"],"state":dup["state"]}
   else:
    now=self.clock(); eid=f"isolated-sandbox-execution-eligibility-{semantic[:24]}"; row={"eligibility_id":eid,"sandbox_change_arbitration_id":arbitration_id,"sandbox_change_session_id":outcome.get("session_id"),"sandbox_change_candidate_id":outcome.get("candidate_id"),"sandbox_change_eligibility_ids":outcome.get("eligibility_ids",[]),"deficiency_candidate_ids":outcome.get("deficiency_candidate_ids",[]),"change_categories":outcome.get("change_categories",[]),"component_ids":outcome.get("component_ids",[]),"project_digests":outcome.get("project_digests",[]),"scope_digests":outcome.get("scope_digests",[]),"evidence_ids":outcome.get("evidence_ids",[]),"supported_sandbox_change":verified,"eligible_sandbox_change":supported,"execution_modes":modes,"isolation_profile_id":_clean(isolation_profile_id,220),"workspace_manifest_digest":_clean(workspace_manifest_digest,220),"resource_budget_id":_clean(resource_budget_id,220),"command_profile_id":_clean(command_profile_id,220),"estimated_cost":cost,"containment_confidence":contain,"reversibility":rev,"prerequisite_ids":prereqs,"operator_review_required":bool(operator_review_required),"eligibility_reason":reason,"semantic_key":semantic,"structural_digest":_digest(semantic,state,cost,contain,rev),"state":state,"created_at":now,"updated_at":now,"sandbox_id":"","patch_digest":"","command_receipt_ids":[],"test_receipt_ids":[],"approval_id":"","authorization_id":"","execution_id":"","installation_id":"","promotion_id":"","certification_id":""}; s["eligibility_records"].append(row); result={"status":"isolated_sandbox_execution_eligibility_registered","eligibility_id":eid,"state":state,"reason":reason}
   now=self.clock(); s["processed_events"].append({"event_id":_clean(event_id,180),"occurred_at":now,"result":deepcopy(result),"content_free":True}); s["revision"]+=1; s["updated_at"]=now; write_json_atomic(self.path,s,expected_type=dict,sort_keys=True); return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load(); counts={}
  for x in s["eligibility_records"]: counts[x.get("state")]=counts.get(x.get("state"),0)+1
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["eligibility_records"]),"state_counts":counts,"execution_modes":sorted(EXECUTION_MODES),"recent_records":deepcopy(s["eligibility_records"][-24:]),"authority_boundary":deepcopy(s["authority_boundary"]),"raw_source_exposed":False,"patch_text_exposed":False,"private_path_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"sandbox_created":False,"commands_executed":False,"tests_executed":False,"external_action_executed":False}
def build_isolated_sandbox_execution_eligibility_inspection(runtime_root=None): return IsolatedSandboxExecutionEligibilityStore(runtime_root).inspection_summary()
