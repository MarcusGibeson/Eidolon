from __future__ import annotations
"""Strictly read-only v1143.8 Workload Coordination Reliability and Visible Behavior checkpoint."""
import hashlib, os
from pathlib import Path
from workload_coordination_execution_checkpoint import build_workload_coordination_execution_checkpoint
from workload_coordination_reliability_review import build_workload_coordination_reliability_review_inspection, OUTCOMES
from workload_coordination_visible_evidence import build_workload_coordination_visible_evidence_inspection
CONTRACT_VERSION="v1143.8"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root:Path):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file() and x.suffix not in {".pyc",".pyo"} and "__pycache__" not in x.parts):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_workload_coordination_reliability_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb=_sig(runtime);sb=_sig(source)
 execution=build_workload_coordination_execution_checkpoint(runtime,source_root=source);review=build_workload_coordination_reliability_review_inspection(runtime);evidence=build_workload_coordination_visible_evidence_inspection(runtime);rr=review.get("recent_reviews",[]);ee=evidence.get("recent_evidence",[])
 checks=[("execution_contract",execution.get("contract_version")=="v1143.5"),("review_contract",review.get("contract_version")=="v1143.6"),("evidence_contract",evidence.get("contract_version")=="v1143.7"),("exact_review_lineage",all(r.get("arbitration_id") for r in rr)),("exact_evidence_lineage",all(e.get("review_id") for e in ee)),("recognized_outcomes",{"balanced","starvation_risk","latency_risk","resource_drift","contention","preemption_pressure","insufficient_evidence","operator_review_required"}<=OUTCOMES),("starvation_visible",all(r.get("outcome")!="starvation_risk" or int(r.get("waiting_cycles") or 0)>=5 for r in rr)),("resource_drift_visible",all(r.get("outcome")!="resource_drift" or any(int(r.get(k) or 0)>0 for k in ("observed_cpu_ms","observed_memory_mb","observed_latency_ms","observed_tokens")) for r in rr)),("operator_visibility_content_free",not review.get("raw_content_exposed") and not evidence.get("raw_content_exposed") and not review.get("workload_payload_exposed") and not evidence.get("workload_payload_exposed")),("advisory_evidence",all(e.get("advisory_only") for e in ee)),("authority_separation",not any(review.get("authority_boundary",{}).values()) and not any(evidence.get("authority_boundary",{}).values())),("no_scheduler_mutation",not review.get("scheduler_mutated") and not evidence.get("scheduler_mutated")),("no_underlying_execution",not review.get("underlying_work_executed") and not evidence.get("underlying_work_executed")),("read_only",rb==_sig(runtime) and sb==_sig(source)),("desktop_verification_pending",True)]
 passed=sum(bool(v) for _,v in checks)
 return {"ok":passed==len(checks),"status":"ready_for_desktop_verification" if passed==len(checks) else "review_required","contract_version":CONTRACT_VERSION,"passed":passed,"total":len(checks),"checks":[{"id":k,"status":"pass" if v else "fail"} for k,v in checks],"execution":execution,"review":review,"evidence":evidence,"runtime_mutated":rb!=_sig(runtime),"source_modified":sb!=_sig(source),"raw_content_exposed":False,"workload_payload_exposed":False,"scheduler_mutated":False,"underlying_work_executed":False,"approval_created":False,"authorization_created":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"consciousness_proven":False,"desktop_verification":"pending"}
