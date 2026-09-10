import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from bounded_parallelism import *
from v1374_test_support import *
P=0;r=build_bounded_parallel_plan(campaign_record_digest=C,tasks=TASKS,max_parallel=2,cpu_budget=2,memory_budget_mb=128);req(r['ok'],'ok');P+=1
p=r['parallel_plan'];req(p['lane_count']==2 and p['lanes'][0]['task_count']==2,'parallel reads');P+=1
req(p['lanes'][1]['contains_mutation'] and p['lanes'][1]['task_count']==1,'serialize mutation');P+=1
req(p['all_mutations_serialized'] and p['content_free'],'safe');P+=1
req(not p['execution_authority_created'] and not p['project_mutation_authorized'],'authority');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1374-foundations'})
