from __future__ import annotations
"""v1149.6 content-free cross-cycle Cognitive Alpha release continuity."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from cognitive_alpha_release_readiness_execution import build_cognitive_alpha_release_readiness_execution
from cognitive_alpha_recovery_continuity import build_cognitive_alpha_recovery_continuity
CONTRACT_VERSION="v1149.6"; SCHEMA_VERSION="1"
AUTHORITY_BOUNDARY={k:False for k in ('executes_commands','modifies_source','mutates_runtime_operations','installs','upgrades','creates_backup','rolls_back','packages','promotes','certifies','contacts_provider','sends_messages','creates_approval','creates_authorization')}
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"revision":0,"updated_at":""}
class CognitiveAlphaReleaseContinuityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/"cognitive_alpha_release_continuity.json";self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def record_cycle(self,cycle_id:str):
  cycle_id=" ".join(str(cycle_id or "").split())[:160]
  if not cycle_id: raise ValueError("cycle_id required")
  execution=build_cognitive_alpha_release_readiness_execution(); recovery=build_cognitive_alpha_recovery_continuity(execution=execution)
  executions=list(execution.get("executions") or []); records=list(recovery.get("records") or [])
  basis={"execution_digest":execution.get("structural_digest"),"recovery_digest":recovery.get("structural_digest"),"path_count":len(executions),"stable_count":recovery.get("stable_count",0),"failed_count":sum(x.get("status")!="stable" for x in records),"rollback_pointer_change_count":sum(bool(x.get("rollback_pointer_changed")) for x in records),"runtime_packaging_violation_count":sum(bool(x.get("runtime_state_packaged")) for x in records)}
  basis_digest=_digest(basis)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=s["records"][-1] if s["records"] else None
   duplicate=next((x for x in s["records"] if x.get("cycle_id")==cycle_id),None)
   if duplicate:return {"ok":True,"status":"duplicate_suppressed","continuity_id":duplicate["continuity_id"],"idempotent":True}
   revision=int(s.get("revision") or 0)+1;drift=bool(prior) and prior.get("basis_digest")!=basis_digest
   attention=bool(basis["failed_count"] or basis["rollback_pointer_change_count"] or basis["runtime_packaging_violation_count"])
   visible="attention" if attention else ("changed" if drift else "steady")
   row={"continuity_id":f"cognitive-alpha-release-continuity-{revision}","cycle_id":cycle_id,"revision":revision,"prior_revision":prior.get("revision") if prior else None,"prior_structural_digest":prior.get("structural_digest") if prior else None,"basis_digest":basis_digest,**basis,"drift_detected":drift,"visible_state":visible,"raw_content_recorded":False,"source_modified":False,"operation_performed":False,"created_at":self.clock()};row["structural_digest"]=_digest(row)
   s["records"].append(row);s["revision"]=revision;s["updated_at"]=row["created_at"];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {"ok":True,"status":"continuity_recorded","continuity_id":row["continuity_id"],"visible_state":visible,"idempotent":False}
 def inspection_summary(self):
  s=self._load();keys=("continuity_id","cycle_id","revision","prior_revision","prior_structural_digest","basis_digest","execution_digest","recovery_digest","path_count","stable_count","failed_count","rollback_pointer_change_count","runtime_packaging_violation_count","drift_detected","visible_state","structural_digest","raw_content_recorded","source_modified","operation_performed")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-32:]],"read_only":True,"raw_content_exposed":False,"hidden_reasoning_exposed":False,"authority_boundary":dict(AUTHORITY_BOUNDARY),"desktop_verification_pending":True,"consciousness_proven":False}
def build_cognitive_alpha_release_continuity_inspection(runtime_root=None): return CognitiveAlphaReleaseContinuityStore(runtime_root).inspection_summary()
