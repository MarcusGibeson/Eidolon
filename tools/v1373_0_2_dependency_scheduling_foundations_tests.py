import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from dependency_scheduling import *
from v1373_test_support import *
P=0;r=build_dependency_schedule(campaign_record_digest=C,tasks=TASKS);req(r['ok'],'ok');P+=1
s=r['dependency_schedule'];req(s['ready_count']==2 and s['held_count']==1,'counts');P+=1
req(s['selected_ready_tasks'][0]['critical_path_units']>=s['selected_ready_tasks'][1]['critical_path_units'],'critical');P+=1
req(s['content_free'] and s['read_only'] and not s['task_execution_authorized'],'safe');P+=1
req(all('task_id' not in x for x in s['ready_tasks']),'content');P+=1
print({'ok':P==5,'passed':P,'total':5,'suite':'v1373-foundations'})
