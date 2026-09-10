from pathlib import Path
import json, tempfile
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
from conscious_agent.cognitive_load_arbitration import CognitiveLoadArbitrator
from conscious_agent.cognitive_work_scheduling import CognitiveWorkScheduler
from conscious_agent.cognitive_work_outcomes import CognitiveWorkOutcomeLedger
p=t=0
def c(n,x):
 global p,t;t+=1;p+=bool(x)
with tempfile.TemporaryDirectory() as td:
 r=Path(td); d=CognitiveDemandStore(r); did=d.register('d',origin_type='intention',origin_id='i')['result']['demand_id']; aid=CognitiveLoadArbitrator(r).allocate('a',demand_ids=[did])['result']['allocation_id']; s=CognitiveWorkScheduler(r); wid=s.schedule('s',demand_id=did,allocation_id=aid)['result']['work_id']; l=CognitiveWorkOutcomeLedger(r)
 c('reject premature',l.record('o0',work_id=wid,outcome='completed_useful')['status']=='outcome_rejected');s.transition('done',work_id=wid,state='completed');q=l.record('o1',work_id=wid,outcome='completed_useful',evidence_digest='abc',confidence=.9);c('record',q['status']=='outcome_recorded');c('idempotent',l.record('o1',work_id=wid,outcome='completed_useful')['idempotent']);c('semantic duplicate',l.record('o2',work_id=wid,outcome='completed_useful',evidence_digest='abc',confidence=.9)['status']=='duplicate_outcome_ignored');oid=q['result']['outcome_id'];z=l.record('o3',work_id=wid,outcome='completed_partial',corrects_outcome_id=oid);snap=l.snapshot();c('correction',z['status']=='outcome_recorded' and not next(x for x in snap['outcomes'] if x['outcome_id']==oid)['active_influence']);c('privacy',all(x['content_free'] for x in snap['outcomes']));c('authority',not any(l.inspection_summary()['authority_boundary'].values()));c('contract',l.inspection_summary()['contract_version']=='v1115.6')
print(json.dumps({'passed':p,'total':t,'suite':'v1115.6'}));raise SystemExit(0 if p==t else 1)
