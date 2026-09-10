from pathlib import Path
import json,tempfile
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
from conscious_agent.cognitive_load_arbitration import CognitiveLoadArbitrator
from conscious_agent.cognitive_work_scheduling import CognitiveWorkScheduler
from conscious_agent.cognitive_work_outcomes import CognitiveWorkOutcomeLedger
from conscious_agent.cognitive_scheduling_effectiveness import build_cognitive_scheduling_effectiveness
p=t=0
def c(n,x):
 global p,t;t+=1;p+=bool(x)
with tempfile.TemporaryDirectory() as td:
 r=Path(td); d=CognitiveDemandStore(r); a=CognitiveLoadArbitrator(r); s=CognitiveWorkScheduler(r); o=CognitiveWorkOutcomeLedger(r)
 for i,out in enumerate(('completed_useful','completed_partial','completed_no_gain')):
  did=d.register(f'd{i}',origin_type='objective',origin_id=f'o{i}')['result']['demand_id']; aid=a.allocate(f'a{i}',demand_ids=[did])['result']['allocation_id']; wid=s.schedule(f's{i}',demand_id=did,allocation_id=aid)['result']['work_id'];s.transition(f't{i}',work_id=wid,state='completed');o.record(f'e{i}',work_id=wid,outcome=out,evidence_digest=f'x{i}')
 q=build_cognitive_scheduling_effectiveness(r);c('ok',q['ok']);c('contract',q['contract_version']=='v1115.7');c('bounded',0<=q['summary']['bounded_score']<=1);c('evidence',q['summary']['evidence_count']==3);c('nonadaptive',not q['authority_boundary']['can_adapt']);c('no execute',not q['authority_boundary']['can_execute']);c('privacy',not q['raw_content_exposed']);c('checks',all(x['status']=='pass' for x in q['checks']))
print(json.dumps({'passed':p,'total':t,'suite':'v1115.7'}));raise SystemExit(0 if p==t else 1)
