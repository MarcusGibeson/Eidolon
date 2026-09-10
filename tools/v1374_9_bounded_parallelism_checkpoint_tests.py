import sys,time;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from bounded_parallelism import *
from v1374_test_support import *
P=0;r=build_bounded_parallel_plan(campaign_record_digest=C,tasks=TASKS,max_parallel=2,cpu_budget=2,memory_budget_mb=128);p=r['parallel_plan'];req(r['ok'],'checkpoint');P+=1
req(p['lanes'][0]['parallel'] and p['lanes'][1]['contains_mutation'],'lanes');P+=1
x=run_bounded_parallel(campaign_record_digest=C,tasks=TASKS,runner=lambda t:t,max_parallel=2,cpu_budget=2,memory_budget_mb=128);req(x['ok'] and x['parallel_execution']['all_tasks_completed'],'execute');P+=1
req(x['parallel_execution']['result_content_free'],'privacy');P+=1
req(not x['execution_authority_created'] and not x['release_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1374-checkpoint'})
