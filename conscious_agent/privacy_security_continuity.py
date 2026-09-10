from __future__ import annotations
"""v1148.6 content-free cross-cycle privacy/security continuity review."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from privacy_security_bounded_execution import build_privacy_security_bounded_execution_inspection
from privacy_security_findings_receipts import build_privacy_security_findings_receipts_inspection

CONTRACT_VERSION="v1148.6"; SCHEMA_VERSION="1"
def _now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _digest(v:object): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default(): return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"revision":0,"updated_at":""}
class PrivacySecurityContinuityStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None): self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root(); self.path=self.runtime_root/"privacy_security_continuity.json"; self.clock=clock or _now
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items(): s.setdefault(k,deepcopy(v))
  return s
 def record_cycle(self,cycle_id:str):
  cycle_id=" ".join(str(cycle_id or "").split())[:160]
  if not cycle_id: raise ValueError("cycle_id required")
  executions=build_privacy_security_bounded_execution_inspection(self.runtime_root).get("recent_records",[])
  findings=build_privacy_security_findings_receipts_inspection(self.runtime_root).get("recent_records",[])
  execution_ids={x.get("execution_id") for x in executions}
  orphan_findings=sum(1 for x in findings if x.get("execution_id") not in execution_ids)
  recurrence={}
  for x in findings:
   code=str(x.get("finding_code") or "none"); recurrence[code]=recurrence.get(code,0)+1
  repeated=sum(1 for count in recurrence.values() if count>1 and count)
  unresolved=sum(1 for x in findings if x.get("state") in {"recovery_failed","review_required"})
  recovered=sum(1 for x in findings if x.get("state")=="recovered")
  stale=sum(1 for x in executions if x.get("state") in {"timed_out","cancelled","suppressed"})
  basis={"execution_count":len(executions),"finding_count":len(findings),"orphan_finding_count":orphan_findings,"repeated_finding_count":repeated,"unresolved_count":unresolved,"recovered_count":recovered,"stale_or_suppressed_count":stale}
  structural=_digest(basis)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load(); prior=s["records"][-1] if s["records"] else None
   duplicate=next((x for x in s["records"] if x.get("cycle_id")==cycle_id),None)
   if duplicate:return {"ok":True,"status":"duplicate_suppressed","continuity_id":duplicate["continuity_id"],"idempotent":True}
   revision=int(s.get("revision") or 0)+1; drift=bool(prior) and prior.get("basis_digest")!=structural
   state="attention" if unresolved or orphan_findings else ("changed" if drift else "steady")
   row={"continuity_id":f"privacy-security-continuity-{revision}","cycle_id":cycle_id,"revision":revision,"prior_revision":prior.get("revision") if prior else None,"prior_structural_digest":prior.get("structural_digest") if prior else None,"basis_digest":structural,**basis,"drift_detected":drift,"visible_state":state,"raw_content_recorded":False,"provider_payload_recorded":False,"source_modified":False,"created_at":self.clock()};row["structural_digest"]=_digest(row)
   s["records"].append(row);s["revision"]=revision;s["updated_at"]=row["created_at"];write_json_atomic(self.path,s,expected_type=dict,sort_keys=True)
   return {"ok":True,"status":"continuity_recorded","continuity_id":row["continuity_id"],"visible_state":state,"idempotent":False}
 def inspection_summary(self):
  s=self._load();keys=("continuity_id","cycle_id","revision","prior_revision","prior_structural_digest","basis_digest","execution_count","finding_count","orphan_finding_count","repeated_finding_count","unresolved_count","recovered_count","stale_or_suppressed_count","drift_detected","visible_state","structural_digest","raw_content_recorded","provider_payload_recorded","source_modified")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-32:]],"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"read_only":True}
def build_privacy_security_continuity_inspection(runtime_root=None): return PrivacySecurityContinuityStore(runtime_root).inspection_summary()
