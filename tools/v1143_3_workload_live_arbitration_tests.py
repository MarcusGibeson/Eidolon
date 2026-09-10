from pathlib import Path
import json,tempfile
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_live_arbitration import WorkloadLiveArbitrationStore
p=0
def ok(v):
 global p;p+=bool(v)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);e=WorkloadBudgetEligibilityStore(r).register("e",workload_id="w",workload_kind="conversation",owner_id="o",priority=80,cpu_budget_ms=10,memory_budget_mb=10,latency_budget_ms=10,token_budget=10);c=WorkloadCoordinationCandidateStore(r).register("c",eligibility_id=e["eligibility_id"],coordination_action="admit",coordination_group_id="g");s=WorkloadLiveArbitrationStore(r);a=s.arbitrate("a",candidate_id=c["candidate_id"],available_cpu_ms=10,available_memory_mb=10,available_latency_ms=10,available_tokens=10);ok(a["state"]=="admitted");ok(s.arbitrate("a",candidate_id=c["candidate_id"],available_cpu_ms=1,available_memory_mb=1,available_latency_ms=1,available_tokens=1)["idempotent"]);d=s.arbitrate("d",candidate_id=c["candidate_id"],available_cpu_ms=1,available_memory_mb=10,available_latency_ms=10,available_tokens=10);ok(d["state"]=="deferred");q=s.inspection_summary();ok(not q["underlying_work_executed"]);ok(not any(q["authority_boundary"].values()));ok(not q["raw_content_exposed"])
print(json.dumps({"passed":p,"total":6,"suite":"v1143.3"}));raise SystemExit(0 if p==6 else 1)
