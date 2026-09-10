from pathlib import Path
import json,tempfile
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_live_arbitration import WorkloadLiveArbitrationStore
from conscious_agent.workload_coordination_continuity import WorkloadCoordinationContinuityStore
from conscious_agent.workload_coordination_execution_checkpoint import build_workload_coordination_execution_checkpoint
p=0
def ok(v):
 global p;p+=bool(v)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);e=WorkloadBudgetEligibilityStore(r).register("e",workload_id="w",workload_kind="inquiry",owner_id="o",cpu_budget_ms=10,memory_budget_mb=10,latency_budget_ms=10,token_budget=10);c=WorkloadCoordinationCandidateStore(r).register("c",eligibility_id=e["eligibility_id"],coordination_action="admit",coordination_group_id="g");a=WorkloadLiveArbitrationStore(r).arbitrate("a",candidate_id=c["candidate_id"],available_cpu_ms=10,available_memory_mb=10,available_latency_ms=10,available_tokens=10);WorkloadCoordinationContinuityStore(r).register("x",arbitration_id=a["arbitration_id"],continuity_key="k",action="complete");q=build_workload_coordination_execution_checkpoint(r,source_root=Path(__file__).resolve().parents[1]);ok(q["ok"]);ok(q["contract_version"]=="v1143.5");ok(q["passed"]==17);ok(not q["runtime_mutated"]);ok(not q["source_modified"]);ok(not q["underlying_work_executed"]);ok(q["desktop_verification"]=="pending")
print(json.dumps({"passed":p,"total":7,"suite":"v1143.5"}));raise SystemExit(0 if p==7 else 1)
