import sys;from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'conscious_agent'),str(R/'tools')]
from dependency_scheduling import *
from v1373_test_support import *
P=0
req(not build_dependency_schedule(campaign_record_digest='bad',tasks=TASKS)['ok'],'lineage');P+=1
x=[dict(t) for t in TASKS];x[1]['depends_on']=['missing'];req(not build_dependency_schedule(campaign_record_digest=C,tasks=x)['ok'],'unknown');P+=1
x=[dict(t) for t in TASKS];x[0]['status']='pending';x[0]['depends_on']=['d'];req(build_dependency_schedule(campaign_record_digest=C,tasks=x)['status']=='dependency_cycle_detected','cycle');P+=1
x=[dict(t) for t in TASKS]+[dict(TASKS[0])];req(not build_dependency_schedule(campaign_record_digest=C,tasks=x)['ok'],'duplicate');P+=1
x=[dict(t) for t in TASKS];x[1]['status']='paused';r=build_dependency_schedule(campaign_record_digest=C,tasks=x);req(r['dependency_schedule']['held_count']>=2,'paused');P+=1
x=[{**t,'status':'completed'} for t in TASKS];r=build_dependency_schedule(campaign_record_digest=C,tasks=x);req(r['dependency_schedule']['schedule_exhausted'],'done');P+=1
req(not build_dependency_schedule(campaign_record_digest=C,tasks=[])['ok'],'empty');P+=1
print({'ok':P==7,'passed':P,'total':7,'suite':'v1373-reliability'})
