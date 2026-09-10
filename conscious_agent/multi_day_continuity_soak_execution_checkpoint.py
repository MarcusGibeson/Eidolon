from __future__ import annotations
"""Strictly read-only v1144.5 Multi-Day Continuity Soak Execution checkpoint."""
import hashlib, os
from pathlib import Path
from multi_day_continuity_soak_intake_checkpoint import build_multi_day_continuity_soak_intake_checkpoint
from continuity_soak_live_execution import build_continuity_soak_live_execution_inspection, STATES as EXECUTION_STATES
from continuity_soak_recovery_receipts import build_continuity_soak_recovery_receipt_inspection, STATES as RECEIPT_STATES
CONTRACT_VERSION="v1144.5"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root:Path):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file() and x.suffix not in {".pyc",".pyo"} and "__pycache__" not in x.parts):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_multi_day_continuity_soak_execution_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root(); source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1]; rb=_sig(runtime);sb=_sig(source)
 intake=build_multi_day_continuity_soak_intake_checkpoint(runtime,source_root=source);e=build_continuity_soak_live_execution_inspection(runtime);r=build_continuity_soak_recovery_receipt_inspection(runtime);er=e.get("recent_records",[]);rr=r.get("recent_records",[])
 checks=[("intake_contract",intake.get("contract_version")=="v1144.2"),("execution_contract",e.get("contract_version")=="v1144.3"),("receipt_contract",r.get("contract_version")=="v1144.4"),("exact_campaign_lineage",all(x.get("campaign_id") and x.get("eligibility_id") for x in er)),("operator_confirmation_binding",all(x.get("state") not in {"launched","observing","completed"} or (x.get("operator_confirmation_id") and x.get("launch_token_id")) for x in er)),("bounded_observation",all(int(x.get("observation_index") or 0)>=0 and int(x.get("elapsed_minutes") or 0)>=0 for x in er)),("scenario_receipts",all(x.get("execution_id") and x.get("scenario_id") for x in rr)),("restart_continuity",all(int(x.get("restart_epoch") or 0)>=0 for x in rr)),("stale_claim_release",all(not x.get("stale_claim_released") or not x.get("worker_claim_id") for x in rr)),("recovery_truth",all(not x.get("recovery_succeeded") or x.get("recovery_attempted") for x in rr)),("budget_timeout",all(not x.get("resource_budget_exceeded") or x.get("state")=="timed_out" for x in rr)),("recognized_execution_states",{"awaiting_confirmation","launched","observing","cancelled","timed_out","completed"}<=EXECUTION_STATES),("recognized_receipt_states",{"observed","recovered","recovery_failed","stale_released","cancelled","timed_out","completed"}<=RECEIPT_STATES),("privacy",not e.get("raw_content_exposed") and not r.get("raw_content_exposed") and not e.get("provider_payload_exposed") and not r.get("provider_payload_exposed")),("authority_separation",not any(e.get("authority_boundary",{}).values()) and not any(r.get("authority_boundary",{}).values())),("source_unchanged",not e.get("source_modified") and not r.get("source_modified")),("read_only",rb==_sig(runtime) and sb==_sig(source)),("desktop_verification_pending",True)]
 passed=sum(bool(v) for _,v in checks)
 return {"ok":passed==len(checks),"status":"ready_for_desktop_verification" if passed==len(checks) else "review_required","contract_version":CONTRACT_VERSION,"passed":passed,"total":len(checks),"checks":[{"id":k,"status":"pass" if v else "fail"} for k,v in checks],"intake":intake,"executions":e,"receipts":r,"runtime_mutated":rb!=_sig(runtime),"source_modified":sb!=_sig(source),"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"approval_created":False,"authorization_created":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"consciousness_proven":False,"desktop_verification":"pending"}
