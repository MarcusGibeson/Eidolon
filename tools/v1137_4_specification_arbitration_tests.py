import json,tempfile
from pathlib import Path
from conscious_agent.specification_arbitration import SpecificationArbitrationStore,OUTCOMES
p=t=f=0
def check(n,v):
 global p,t,f;t+=1;p+=bool(v);f+=not bool(v);print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir(parents=True); (r/'specification_deliberation_sessions.json').write_text(json.dumps({'sessions':[{'session_id':'s1','candidate_id':'c1','eligibility_ids':['e1'],'deficiency_candidate_ids':['d1'],'specification_categories':['reliability_repair'],'component_ids':['component:x'],'project_digests':['p'],'scope_digests':['s'],'evidence_ids':['ev'],'pause_reason':''}]}))
 store=SpecificationArbitrationStore(r); out=store.arbitrate('a',session_id='s1',evidence_support=.9,scope_support=.9,risk_acceptability=.9,reversibility_support=.9); check('supported',out['outcome']=='specification_supported'); check('idempotent',store.arbitrate('a',session_id='s1')['idempotent']); no=store.arbitrate('n',session_id='s1',deliberate_no_specification=True); check('no proposal',no['outcome']=='deliberate_no_specification'); check('outcomes',len(OUTCOMES)>=16); check('authority inert',not any(store.inspection_summary()['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1137.4'}));raise SystemExit(0 if not f else 1)
