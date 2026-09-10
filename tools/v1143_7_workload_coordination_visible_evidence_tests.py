from pathlib import Path
from tempfile import TemporaryDirectory
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_live_arbitration import WorkloadLiveArbitrationStore
from conscious_agent.workload_coordination_reliability_review import WorkloadCoordinationReliabilityReviewStore
from conscious_agent.workload_coordination_visible_evidence import WorkloadCoordinationVisibleEvidenceStore
p=0
def ok(v):
 global p;p+=int(bool(v))
with TemporaryDirectory() as td:
 r=Path(td);e=WorkloadBudgetEligibilityStore(r).register("e",workload_id="w",workload_kind="conversation",owner_id="o",cpu_budget_ms=10,memory_budget_mb=10,latency_budget_ms=10,token_budget=10);c=WorkloadCoordinationCandidateStore(r).register("c",eligibility_id=e["eligibility_id"],coordination_action="defer",coordination_group_id="g",fairness_class_id="f");a=WorkloadLiveArbitrationStore(r).arbitrate("a",candidate_id=c["candidate_id"],available_cpu_ms=5,available_memory_mb=5,available_latency_ms=5,available_tokens=5);rv=WorkloadCoordinationReliabilityReviewStore(r).register("r",arbitration_id=a["arbitration_id"],waiting_cycles=6);s=WorkloadCoordinationVisibleEvidenceStore(r);q=s.register("q",review_id=rv["review_id"]);ok(q["status"]=="evidence_recorded");q2=s.register("q",review_id=rv["review_id"]);ok(q2["idempotent"]);i=s.inspection_summary();ok(i["evidence_count"]==1);ok(i["recent_evidence"][0]["outcome"]=="starvation_risk");ok(i["recent_evidence"][0]["advisory_only"]);ok(not i["raw_content_exposed"])
print({"passed":p,"total":6,"suite":"v1143.7"});raise SystemExit(0 if p==6 else 1)
