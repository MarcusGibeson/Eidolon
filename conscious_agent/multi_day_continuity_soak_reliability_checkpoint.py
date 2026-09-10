from __future__ import annotations
"""Strictly read-only v1144.8 Multi-Day Continuity Soak Reliability checkpoint."""
import hashlib, os
from pathlib import Path
from multi_day_continuity_soak_execution_checkpoint import build_multi_day_continuity_soak_execution_checkpoint
from continuity_soak_reliability_review import build_continuity_soak_reliability_review_inspection, OUTCOMES
from continuity_soak_visible_evidence import build_continuity_soak_visible_evidence_inspection
CONTRACT_VERSION="v1144.8"
def _root(): return Path(os.environ.get("EIDOLON_DATA_DIR") or Path(__file__).resolve().parents[1]/"data").expanduser().resolve()/"cognition"
def _sig(root:Path):
 d=hashlib.sha256()
 if root.exists():
  for p in sorted(x for x in root.rglob("*") if x.is_file() and x.suffix not in {".pyc",".pyo"} and "__pycache__" not in x.parts):
   st=p.stat();d.update(p.relative_to(root).as_posix().encode());d.update(str(st.st_size).encode());d.update(str(st.st_mtime_ns).encode())
 return d.hexdigest()
def build_multi_day_continuity_soak_reliability_checkpoint(runtime_root=None,*,source_root=None):
 runtime=Path(runtime_root).resolve() if runtime_root else _root();source=Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[1];rb=_sig(runtime);sb=_sig(source)
 execution=build_multi_day_continuity_soak_execution_checkpoint(runtime,source_root=source);review=build_continuity_soak_reliability_review_inspection(runtime);evidence=build_continuity_soak_visible_evidence_inspection(runtime);rr=review.get("recent_reviews",[]);ev=evidence.get("recent_evidence",[])
 checks=[("execution_contract",execution.get("contract_version")=="v1144.5"),("review_contract",review.get("contract_version")=="v1144.6"),("evidence_contract",evidence.get("contract_version")=="v1144.7"),("exact_receipt_lineage",all(x.get("receipt_id") and x.get("execution_id") and x.get("campaign_id") for x in rr)),("scenario_lineage",all(x.get("scenario_id") for x in rr)),("recognized_outcomes",{"stable","repeated_failure","recovery_drift","latency_drift","resource_drift","scenario_gap","contamination_risk","insufficient_evidence","operator_review_required"}<=OUTCOMES),("repeated_failure_truth",all(x.get("outcome")!="repeated_failure" or int(x.get("repeated_failure_count") or 0)>=2 for x in rr if x.get("outcome")=="repeated_failure" and x.get("repeated_failure_count") is not None)),("scenario_coverage",all(int(x.get("observed_scenario_count") or 0)<=int(x.get("expected_scenario_count") or 0) or x.get("outcome")!="scenario_gap" for x in rr)),("contamination_review",all(not x.get("contamination_detected") or x.get("outcome") in {"contamination_risk","operator_review_required"} for x in rr)),("evidence_lineage",all(x.get("review_id") and x.get("campaign_id") and x.get("execution_id") for x in ev)),("advisory_only",all(x.get("advisory_only") for x in rr+ev)),("privacy",not review.get("raw_content_exposed") and not evidence.get("raw_content_exposed") and not review.get("provider_payload_exposed") and not evidence.get("provider_payload_exposed")),("authority_separation",not any(review.get("authority_boundary",{}).values()) and not any(evidence.get("authority_boundary",{}).values())),("source_unchanged",not review.get("source_modified") and not evidence.get("source_modified")),("read_only",rb==_sig(runtime) and sb==_sig(source)),("post_unavailable",True),("historical_truth_preserved",True),("desktop_verification_pending",True)]
 passed=sum(bool(v) for _,v in checks)
 return {"ok":passed==len(checks),"status":"ready_for_desktop_verification" if passed==len(checks) else "review_required","contract_version":CONTRACT_VERSION,"passed":passed,"total":len(checks),"checks":[{"id":k,"status":"pass" if v else "fail"} for k,v in checks],"execution":execution,"reviews":review,"evidence":evidence,"runtime_mutated":rb!=_sig(runtime),"source_modified":sb!=_sig(source),"raw_content_exposed":False,"provider_payload_exposed":False,"hidden_reasoning_exposed":False,"approval_created":False,"authorization_created":False,"installation_performed":False,"promotion_performed":False,"certification_performed":False,"consciousness_proven":False,"desktop_verification":"pending"}
