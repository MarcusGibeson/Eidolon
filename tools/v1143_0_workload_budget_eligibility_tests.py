from pathlib import Path
import json,tempfile
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
p=0
def ok(v):
 global p;p+=bool(v)
with tempfile.TemporaryDirectory() as td:
 s=WorkloadBudgetEligibilityStore(Path(td))
 a=s.register('e1',workload_id='w1',workload_kind='cognition',owner_id='o1',cpu_budget_ms=100,memory_budget_mb=64,latency_budget_ms=500,token_budget=1000)
 ok(a['state']=='eligible')
 ok(s.register('e1',workload_id='w1',workload_kind='cognition',owner_id='o1',cpu_budget_ms=100,memory_budget_mb=64,latency_budget_ms=500,token_budget=1000)['idempotent'])
 b=s.register('e2',workload_id='w2',workload_kind='conversation',owner_id='o2',cpu_budget_ms=0,memory_budget_mb=64,latency_budget_ms=100,token_budget=50)
 ok(b['state']=='awaiting_budget')
 c=s.register('e3',workload_id='w3',workload_kind='inquiry',owner_id='o3',cpu_budget_ms=5,memory_budget_mb=5,latency_budget_ms=5,token_budget=5,prerequisite_ids=['p1'])
 ok(c['state']=='awaiting_prerequisite')
 d=s.inspection_summary();ok(d['contract_version']=='v1143.0');ok(not any(d['authority_boundary'].values()));ok(not d['raw_content_exposed'])
print(json.dumps({'passed':p,'total':7,'suite':'v1143.0'}))
raise SystemExit(0 if p==7 else 1)
