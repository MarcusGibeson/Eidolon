from pathlib import Path
import json,tempfile
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_coordination_intake_checkpoint import build_workload_coordination_intake_checkpoint
p=0
def ok(v):
 global p;p+=bool(v)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);e=WorkloadBudgetEligibilityStore(r);x=e.register('e1',workload_id='w1',workload_kind='conversation',owner_id='o1',cpu_budget_ms=10,memory_budget_mb=10,latency_budget_ms=10,token_budget=10);WorkloadCoordinationCandidateStore(r).register('c1',eligibility_id=x['eligibility_id'],coordination_action='reserve',coordination_group_id='g1')
 q=build_workload_coordination_intake_checkpoint(r,source_root=Path(__file__).resolve().parents[1]);ok(q['ok']);ok(q['contract_version']=='v1143.2');ok(q['passed']==16);ok(not q['runtime_mutated']);ok(not q['source_modified']);ok(not q['execution_started']);ok(not q['schedule_mutated']);ok(not q['raw_content_exposed']);ok(q['desktop_verification']=='pending')
print(json.dumps({'passed':p,'total':9,'suite':'v1143.2'}));raise SystemExit(0 if p==9 else 1)
