import json,tempfile
from pathlib import Path
from conscious_agent.development_proposal_deliberation_sessions import DevelopmentProposalDeliberationSessionStore
p=t=f=0
def check(n,v):
 global p,t,f;t+=1;p+=bool(v);f+=not bool(v);print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir(parents=True); (r/'development_proposal_candidates.json').write_text(json.dumps({'candidates':[{'candidate_id':'c1','state':'active','eligibility_ids':['e1'],'arbitration_ids':['a1'],'deficiency_candidate_ids':['d1'],'proposal_categories':['reliability_repair'],'component_ids':['component:x'],'project_digests':['p'],'scope_digests':['s'],'evidence_ids':['ev'],'estimated_complexity':.4,'estimated_risk':.3,'minimum_reversibility':.8,'prerequisite_ids':[],'operator_review_required':False}]}))
 store=DevelopmentProposalDeliberationSessionStore(r); out=store.open('open',candidate_id='c1',deliberation_budget=3); check('open',out['state']=='open'); check('idempotent',store.open('open',candidate_id='c1')['idempotent']); check('bounded',store.snapshot()['sessions'][0]['deliberation_budget']==3); check('authority inert',not any(store.inspection_summary()['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1136.3'}));raise SystemExit(0 if not f else 1)
