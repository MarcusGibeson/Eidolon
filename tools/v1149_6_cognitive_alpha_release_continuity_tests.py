import tempfile
from conscious_agent.cognitive_alpha_release_continuity import *
with tempfile.TemporaryDirectory() as d:
 s=CognitiveAlphaReleaseContinuityStore(d,clock=lambda:"2026-07-30T00:00:00.000Z");a=s.record_cycle("cycle-a");b=s.record_cycle("cycle-a");r=s.inspection_summary();x=r["recent_records"][0]
 checks=[a["status"]=="continuity_recorded",b["status"]=="duplicate_suppressed",b["idempotent"],r["contract_version"]=="v1149.6",r["record_count"]==1,x["path_count"]==5,x["stable_count"]==5,x["failed_count"]==0,x["rollback_pointer_change_count"]==0,x["runtime_packaging_violation_count"]==0,x["visible_state"]=="steady",not x["raw_content_recorded"],not x["operation_performed"],r["read_only"],not any(r["authority_boundary"].values()),not r["consciousness_proven"]]
print(f"v1149.6: {sum(checks)}/{len(checks)}");raise SystemExit(0 if all(checks) else 1)
