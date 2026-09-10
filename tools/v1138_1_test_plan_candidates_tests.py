import json,tempfile
from pathlib import Path
from conscious_agent.test_plan_candidates import TestPlanCandidateStore,STATES
p=t=f=0
def check(n,v):
 global p,t,f;t+=1;p+=bool(v);f+=not bool(v);print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir(parents=True);(r/'test_plan_eligibility.json').write_text(json.dumps({'eligibility_records':[{'eligibility_id':'e1','arbitration_id':'a1','specification_candidate_id':'sc1','specification_eligibility_ids':['se1'],'proposal_candidate_ids':['pc1'],'deficiency_candidate_ids':['d1'],'test_plan_category':'regression_test_plan','component_ids':['component.alpha'],'coverage_target_ids':['coverage.alpha'],'environment_ids':['env.local'],'dependency_ids':['dep.python'],'project_digests':['p'],'scope_digests':['q'],'evidence_ids':['e'],'estimated_cost':.4,'reproducibility':.9,'determinism':.95,'prerequisite_ids':[],'operator_review_required':False,'state':'eligible'}]}))
 store=TestPlanCandidateStore(r);out=store.register('c1',eligibility_ids=['e1']);check('active',out['state']=='active');check('idempotent',store.register('c1',eligibility_ids=['e1'])['idempotent']);row=store.inspection_summary()['recent_candidates'][0];check('lineage coverage',row['specification_candidate_ids']==['sc1'] and row['coverage_target_ids']==['coverage.alpha']);check('recognized states',len(STATES)==11);check('content authority boundaries',not store.inspection_summary()['test_plan_text_exposed'] and not any(store.inspection_summary()['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1138.1'}));raise SystemExit(0 if not f else 1)
