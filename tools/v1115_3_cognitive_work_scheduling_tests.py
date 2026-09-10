import json,tempfile
from pathlib import Path
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
from conscious_agent.cognitive_load_arbitration import CognitiveLoadArbitrator
from conscious_agent.cognitive_work_scheduling import CognitiveWorkScheduler
p=t=0
def c(n,x):
 global p,t;t+=1
 if not x:raise AssertionError(n)
 p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td); ds=CognitiveDemandStore(r); did=ds.register('d1',origin_type='objective',origin_id='o1',cognitive_cost=.2)['result']['demand_id']; aid=CognitiveLoadArbitrator(r).allocate('a1',demand_ids=[did])['result']['allocation_id']; s=CognitiveWorkScheduler(r); x=s.schedule('s1',demand_id=did,allocation_id=aid,slice_budget=.2); wid=x['result']['work_id']; c('created',x['status']=='work_scheduled');c('duplicate_event',s.schedule('s1',demand_id=did,allocation_id=aid)['idempotent']);c('semantic_duplicate',s.schedule('s2',demand_id=did,allocation_id=aid)['status']=='duplicate_work_ignored');c('lineage',s.snapshot()['work_items'][0]['demand_id']==did);c('bounded',s.snapshot()['work_items'][0]['slice_budget']<=.5);c('authority',not any(s.inspection_summary()['authority_boundary'].values()));c('content_free',not s.inspection_summary()['raw_content_exposed']);c('transition',s.transition('t1',work_id=wid,state='running')['status']=='work_transitioned')
print(json.dumps({'passed':p,'total':t,'suite':'v1115.3'}))
