import json,tempfile
from pathlib import Path
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
from conscious_agent.cognitive_load_arbitration import CognitiveLoadArbitrator
from conscious_agent.cognitive_work_scheduling import CognitiveWorkScheduler
from conscious_agent.cognitive_work_interruption import CognitiveWorkInterruptionManager
p=t=0
def c(n,x):
 global p,t;t+=1
 if not x:raise AssertionError(n)
 p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td);d=CognitiveDemandStore(r);did=d.register('d',origin_type='active_inquiry',origin_id='q')['result']['demand_id'];aid=CognitiveLoadArbitrator(r).allocate('a',demand_ids=[did])['result']['allocation_id'];s=CognitiveWorkScheduler(r);wid=s.schedule('s',demand_id=did,allocation_id=aid)['result']['work_id'];m=CognitiveWorkInterruptionManager(r);c('interrupt',m.interrupt('i',work_id=wid,resume_token='tok')['status']=='work_transitioned');c('resumable',s.snapshot()['work_items'][0]['state']=='resumable');c('bad_token',m.resume('r0',work_id=wid,resume_token='bad')['status']=='resume_rejected');c('resume',m.resume('r1',work_id=wid,resume_token='tok')['status']=='work_transitioned');c('count',s.snapshot()['work_items'][0]['resume_count']==1);c('not_stale',m.retire_stale('z0',work_id=wid,stale=False)['status']=='retirement_not_required');c('retire',m.retire_stale('z1',work_id=wid,stale=True)['status']=='work_transitioned');c('authority',not m.inspection_summary()['interruption_grants_authority'])
print(json.dumps({'passed':p,'total':t,'suite':'v1115.4'}))
