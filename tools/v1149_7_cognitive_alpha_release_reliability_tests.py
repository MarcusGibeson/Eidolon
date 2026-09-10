import tempfile
from conscious_agent.cognitive_alpha_release_continuity import CognitiveAlphaReleaseContinuityStore
from conscious_agent.cognitive_alpha_release_reliability import *
with tempfile.TemporaryDirectory() as d:
 CognitiveAlphaReleaseContinuityStore(d).record_cycle("cycle-a");r=build_cognitive_alpha_release_reliability(d);checks=[r["contract_version"]=="v1149.7",r["continuity_record_count"]==1,r["readiness_path_count"]==5,r["stable_recovery_count"]==5,r["drift_count"]==0,r["failure_count"]==0,r["rollback_pointer_change_count"]==0,r["runtime_packaging_violation_count"]==0,r["reliability_score"]==100,r["uncertainty"]==0,r["classification"]=="reliable",r["operator_visible_state"]=="ready",r["read_only"],not r["operation_performed"],not r["provider_contacted"],not r["consciousness_proven"]]
print(f"v1149.7: {sum(checks)}/{len(checks)}");raise SystemExit(0 if all(checks) else 1)
