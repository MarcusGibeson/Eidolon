from pathlib import Path
import json,tempfile
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
p=0
def ok(v):
 global p;p+=bool(v)
with tempfile.TemporaryDirectory() as td:
 r=Path(td);e=WorkloadBudgetEligibilityStore(r);x=e.register('e1',workload_id='w1',workload_kind='development',owner_id='o1',cpu_budget_ms=100,memory_budget_mb=64,latency_budget_ms=500,token_budget=1000)
 s=WorkloadCoordinationCandidateStore(r);a=s.register('c1',eligibility_id=x['eligibility_id'],coordination_action='admit',coordination_group_id='g1',fairness_class_id='interactive')
 ok(a['state']=='active');ok(s.register('c1',eligibility_id=x['eligibility_id'],coordination_action='admit',coordination_group_id='g1')['idempotent'])
 b=s.register('c2',eligibility_id=x['eligibility_id'],coordination_action='defer',coordination_group_id='g1');ok(b['state']=='deferred')
 q=s.inspection_summary();ok(q['contract_version']=='v1143.1');ok(all(r['advisory_only'] and not r['execution_started'] and not r['schedule_mutated'] for r in q['recent_records']));ok(not any(q['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':6,'suite':'v1143.1'}));raise SystemExit(0 if p==6 else 1)
