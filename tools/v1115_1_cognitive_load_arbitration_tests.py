from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
passed=0
def check(name,cond):
 global passed
 if not cond: raise AssertionError(name)
 passed+=1
from conscious_agent.cognitive_demand_records import CognitiveDemandStore
from conscious_agent.cognitive_load_arbitration import CognitiveLoadArbitrator
with tempfile.TemporaryDirectory() as td:
 root=Path(td);s=CognitiveDemandStore(root)
 ids=[]
 for i,(typ,urg,imp,cost,sens,overlap) in enumerate([('objective',.8,.9,.3,0,'a'),('reflection',.7,.6,.6,0,'b'),('active_inquiry',.9,.5,.4,.8,'c'),('milestone',.4,.5,.2,0,'a')]):ids.append(s.register(f'e{i}',origin_type=typ,origin_id=f'o{i}',urgency=urg,importance=imp,cognitive_cost=cost,sensitivity=sens,overlap_key=overlap)['result']['demand_id'])
 a=CognitiveLoadArbitrator(root);r=a.allocate('a1',demand_ids=ids,capacity=.8);out=r['result']['outcomes'];check('completed',r['status']=='allocation_completed');check('sensitivity',out[ids[2]]=='blocked_sensitivity');check('overlap',out[ids[3]] in {'merged','queued','deferred'});check('bounded_budget',sum(r['result']['budgets'].values())<=.8);check('idle_reserved',r['result']['idle_capacity']>=.1);check('idempotent',a.allocate('a1',demand_ids=ids)['idempotent']);idle=a.allocate('a2',demand_ids=[],force_idle=True);check('deliberate_idle',idle['result']['reason']=='deliberate_idle_capacity');check('no_authority',all(not idle['result'][k] for k in ('attention_id','intention_id','decision_id','proposal_id','approval_id','authorization_id','action_id')))
print(json.dumps({'passed':passed,'total':8,'suite':'v1115.1'}))
