from pathlib import Path
import json,tempfile
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_live_arbitration import WorkloadLiveArbitrationStore
from conscious_agent.workload_coordination_continuity import WorkloadCoordinationContinuityStore
p=0
def ok(v):
 global p;p+=bool(v)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);e=WorkloadBudgetEligibilityStore(r).register("e",workload_id="w",workload_kind="cognition",owner_id="o",cpu_budget_ms=10,memory_budget_mb=10,latency_budget_ms=10,token_budget=10);c=WorkloadCoordinationCandidateStore(r).register("c",eligibility_id=e["eligibility_id"],coordination_action="admit",coordination_group_id="g");a=WorkloadLiveArbitrationStore(r).arbitrate("a",candidate_id=c["candidate_id"],available_cpu_ms=10,available_memory_mb=10,available_latency_ms=10,available_tokens=10);s=WorkloadCoordinationContinuityStore(r);x=s.register("x",arbitration_id=a["arbitration_id"],continuity_key="k",worker_claim_id="worker",action="run");ok(x["state"]=="running");y=s.register("y",arbitration_id=a["arbitration_id"],continuity_key="k2",action="run",tokens_used=11);ok(y["state"]=="budget_exhausted");z=s.register("z",arbitration_id=a["arbitration_id"],continuity_key="k3",worker_claim_id="old",claim_stale=True);ok(z["state"]=="stale_released");q=s.inspection_summary();ok(not q["underlying_work_executed"]);ok(not q["raw_content_exposed"]);ok(not any(q["authority_boundary"].values()))
print(json.dumps({"passed":p,"total":6,"suite":"v1143.4"}));raise SystemExit(0 if p==6 else 1)
