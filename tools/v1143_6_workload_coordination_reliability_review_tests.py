from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_live_arbitration import WorkloadLiveArbitrationStore
from conscious_agent.workload_coordination_continuity import WorkloadCoordinationContinuityStore
from conscious_agent.workload_coordination_reliability_review import WorkloadCoordinationReliabilityReviewStore
p=0
def ok(v):
 global p;p+=int(bool(v))
with TemporaryDirectory() as td:
 r=Path(td);e=WorkloadBudgetEligibilityStore(r).register("e",workload_id="w",workload_kind="cognition",owner_id="o",cpu_budget_ms=10,memory_budget_mb=10,latency_budget_ms=10,token_budget=10);c=WorkloadCoordinationCandidateStore(r).register("c",eligibility_id=e["eligibility_id"],coordination_action="admit",coordination_group_id="g",fairness_class_id="f");a=WorkloadLiveArbitrationStore(r).arbitrate("a",candidate_id=c["candidate_id"],available_cpu_ms=10,available_memory_mb=10,available_latency_ms=10,available_tokens=10);x=WorkloadCoordinationContinuityStore(r).register("x",arbitration_id=a["arbitration_id"],continuity_key="k",action="complete");s=WorkloadCoordinationReliabilityReviewStore(r);q=s.register("q",arbitration_id=a["arbitration_id"],continuity_id=x["continuity_id"],waiting_cycles=0,observed_latency_ms=5);ok(q["outcome"]=="balanced");z=s.register("z",arbitration_id=a["arbitration_id"],waiting_cycles=6);ok(z["outcome"]=="starvation_risk");d=s.register("d",arbitration_id=a["arbitration_id"],observed_cpu_ms=11);ok(d["outcome"]=="resource_drift");i=s.inspection_summary();ok(i["review_count"]==3);ok(not i["raw_content_exposed"]);ok(not any(i["authority_boundary"].values()))
print({"passed":p,"total":6,"suite":"v1143.6"});raise SystemExit(0 if p==6 else 1)
