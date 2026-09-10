from __future__ import annotations
"""v1149.7 content-free Cognitive Alpha release reliability review."""
import hashlib,json
from cognitive_alpha_release_continuity import build_cognitive_alpha_release_continuity_inspection
from cognitive_alpha_release_readiness_execution import build_cognitive_alpha_release_readiness_execution
from cognitive_alpha_recovery_continuity import build_cognitive_alpha_recovery_continuity
CONTRACT_VERSION="v1149.7"
def _digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def build_cognitive_alpha_release_reliability(runtime_root=None):
 continuity=build_cognitive_alpha_release_continuity_inspection(runtime_root);execution=build_cognitive_alpha_release_readiness_execution();recovery=build_cognitive_alpha_recovery_continuity(execution=execution);cr=continuity.get("recent_records",[])
 drift=sum(bool(x.get("drift_detected")) for x in cr);failures=sum(int(x.get("failed_count") or 0) for x in cr);pointer=sum(int(x.get("rollback_pointer_change_count") or 0) for x in cr);packaging=sum(int(x.get("runtime_packaging_violation_count") or 0) for x in cr);unstable=max(0,len(recovery.get("records") or [])-int(recovery.get("stable_count") or 0));issues=drift+failures+pointer+packaging+unstable
 score=max(0,100-issues*12);uncertainty=min(100,(10 if not cr else 0)+issues*8);classification="reliable" if score>=90 and uncertainty<=10 else "review_required"
 report={"contract_version":CONTRACT_VERSION,"review_id":f"cognitive-alpha-release-reliability:{len(cr)}","continuity_record_count":len(cr),"readiness_path_count":len(execution.get("executions") or []),"stable_recovery_count":recovery.get("stable_count",0),"drift_count":drift,"failure_count":failures+unstable,"rollback_pointer_change_count":pointer,"runtime_packaging_violation_count":packaging,"reliability_score":score,"uncertainty":uncertainty,"classification":classification,"operator_visible_state":"ready" if classification=="reliable" else "attention","read_only":True,"raw_content_exposed":False,"hidden_reasoning_exposed":False,"provider_contacted":False,"operation_performed":False,"source_modified":False,"runtime_mutated":False,"desktop_verification_pending":True,"consciousness_proven":False};report["structural_digest"]=_digest(report);return report
