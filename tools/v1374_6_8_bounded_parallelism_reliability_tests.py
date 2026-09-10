import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from bounded_parallelism import *
from v1374_test_support import *
P=0
req(not build_bounded_parallel_plan(campaign_record_digest='bad',tasks=TASKS)['ok'],'lineage');P+=1
x=[dict(TASKS[0]),dict(TASKS[0])];req(not build_bounded_parallel_plan(campaign_record_digest=C,tasks=x)['ok'],'duplicate');P+=1
x=[dict(TASKS[0])];x[0]['writes']=['a'];req(not build_bounded_parallel_plan(campaign_record_digest=C,tasks=x)['ok'],'write kind');P+=1
x=[dict(TASKS[0])];x[0]['cpu_units']=5;req(not build_bounded_parallel_plan(campaign_record_digest=C,tasks=x,cpu_budget=2)['ok'],'cpu');P+=1
x=[dict(t) for t in TASKS];x[1]['execution_authorized']=False;req(run_bounded_parallel(campaign_record_digest=C,tasks=x,runner=lambda _:1)['status']=='per_task_execution_authority_required','authority');P+=1
r=run_bounded_parallel(campaign_record_digest=C,tasks=TASKS,runner=lambda t:(_ for _ in ()).throw(RuntimeError()) if t=='test-b' else 1,max_parallel=2,cpu_budget=2,memory_budget_mb=128);req(not r['ok'],'failure');P+=1
req(not build_bounded_parallel_plan(campaign_record_digest=C,tasks=[],max_parallel=2)['ok'],'empty');P+=1
print({'ok':P==7,'passed':P,'total':7,'suite':'v1374-reliability'})
