from __future__ import annotations
"""v1148.4 content-free security finding, containment, and recovery receipts."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
from typing import Any, Callable
from json_storage import load_json_file, write_json_atomic
from metadata_mutation_coordination import metadata_mutation_lock
from privacy_security_bounded_execution import PrivacySecurityBoundedExecutionStore
CONTRACT_VERSION="v1148.4";SCHEMA_VERSION="1"
STATES={"no_finding","contained","recovered","recovery_failed","review_required","retired"}
AUTHORITY_KEYS=("contacts_provider","executes_commands","mutates_cognition","mutates_memory","modifies_source","sends_messages","creates_notifications","creates_goals","creates_plans","creates_development_proposals","creates_approval","creates_authorization","installs","promotes","certifies")
def _now():return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _clean(v:Any,n=200):return " ".join(str(v or "").split())[:n]
def _digest(v:object):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _root():return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _default():return {"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"records":[],"processed_events":[],"revision":0,"updated_at":"","authority_boundary":{k:False for k in AUTHORITY_KEYS}}
class PrivacySecurityFindingReceiptStore:
 def __init__(self,runtime_root=None,*,clock:Callable[[],str]|None=None):self.runtime_root=Path(runtime_root).resolve() if runtime_root else _root();self.path=self.runtime_root/"privacy_security_findings_receipts.json";self.clock=clock or _now;self.executions=PrivacySecurityBoundedExecutionStore(self.runtime_root)
 def _load(self):
  s=load_json_file(self.path,_default(),expected_type=dict)
  for k,v in _default().items():s.setdefault(k,deepcopy(v))
  return s
 def record(self,event_id:str,*,execution_id:str,finding_code:str="none",severity:int=0,contained:bool=False,recovery_attempted:bool=False,recovery_succeeded:bool=False,operator_review_required:bool=False):
  if not _clean(event_id) or not _clean(execution_id):raise ValueError("event_id and execution_id required")
  execution=next((r for r in self.executions.snapshot().get("records",[]) if r.get("execution_id")==execution_id),None)
  if not execution:raise ValueError("exact v1148.3 execution required")
  sev=max(0,min(5,int(severity)));code=_clean(finding_code,80)
  if code in {"","none"} and sev==0:state="no_finding"
  elif recovery_succeeded and recovery_attempted:state="recovered"
  elif recovery_attempted and not recovery_succeeded:state="recovery_failed"
  elif contained:state="contained"
  else:state="review_required";operator_review_required=True
  base={"execution_id":execution_id,"execution_digest":execution["structural_digest"],"scenario_id":execution["scenario_id"],"category":execution["category"],"finding_code":code or "unspecified","severity":sev,"contained":bool(contained),"recovery_attempted":bool(recovery_attempted),"recovery_succeeded":bool(recovery_succeeded),"operator_review_required":bool(operator_review_required),"state":state}
  structural=_digest(base)
  with metadata_mutation_lock(self.path,timeout_seconds=5):
   s=self._load();prior=next((x for x in s["processed_events"] if x.get("event_id")==event_id),None)
   if prior:return {"ok":True,**deepcopy(prior["result"]),"idempotent":True}
   now=self.clock();rid=f"privacy-security-finding-{structural[:24]}";row={"receipt_id":rid,**base,"structural_digest":structural,"raw_evidence_recorded":False,"provider_payload_recorded":False,"source_modified":False,"created_at":now};s["records"].append(row);result={"status":"receipt_recorded","receipt_id":rid,"state":state};s["processed_events"].append({"event_id":event_id,"occurred_at":now,"result":deepcopy(result),"content_free":True});s["revision"]+=1;s["updated_at"]=now;write_json_atomic(self.path,s,expected_type=dict,sort_keys=True);return {"ok":True,**result,"idempotent":False}
 def inspection_summary(self):
  s=self._load();keys=("receipt_id","execution_id","execution_digest","scenario_id","category","finding_code","severity","contained","recovery_attempted","recovery_succeeded","operator_review_required","state","structural_digest","raw_evidence_recorded","provider_payload_recorded","source_modified")
  return {"ok":True,"contract_version":CONTRACT_VERSION,"record_count":len(s["records"]),"recent_records":[{k:r.get(k) for k in keys} for r in s["records"][-32:]],"authority_boundary":deepcopy(s["authority_boundary"]),"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"source_modified":False}
def build_privacy_security_findings_receipts_inspection(runtime_root=None):return PrivacySecurityFindingReceiptStore(runtime_root).inspection_summary()
