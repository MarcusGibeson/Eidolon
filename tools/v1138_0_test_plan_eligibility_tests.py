import json,tempfile
from pathlib import Path
from conscious_agent.test_plan_eligibility import TestPlanEligibilityStore,TEST_PLAN_CATEGORIES
p=t=f=0
def check(n,v):
 global p,t,f;t+=1;p+=bool(v);f+=not bool(v);print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir(parents=True);(r/'specification_arbitration.json').write_text(json.dumps({'outcomes':[{'arbitration_id':'a1','session_id':'s1','candidate_id':'sc1','eligibility_ids':['se1'],'proposal_candidate_ids':['pc1'],'deficiency_candidate_ids':['d1'],'specification_categories':['reliability_specification'],'component_ids':['component.alpha'],'project_digests':['p'],'scope_digests':['q'],'evidence_ids':['e'],'outcome':'specification_supported'}]}))
 store=TestPlanEligibilityStore(r);out=store.register('e1',arbitration_id='a1',test_plan_category='regression_test_plan',scope_component_ids=['component.alpha'],coverage_target_ids=['coverage.alpha'],environment_ids=['env.local'],dependency_ids=['dep.python'],operator_review_required=False)
 check('eligible',out['state']=='eligible');check('idempotent',store.register('e1',arbitration_id='a1',test_plan_category='regression_test_plan',scope_component_ids=['component.alpha'])['idempotent']);row=store.inspection_summary()['recent_records'][0];check('exact specification lineage',row['specification_candidate_id']=='sc1' and row['specification_eligibility_ids']==['se1']);check('category coverage',len(TEST_PLAN_CATEGORIES)>=9);check('content free',not store.inspection_summary()['test_plan_text_exposed'] and not store.inspection_summary()['test_code_exposed']);check('authority inert',not any(store.inspection_summary()['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1138.0'}));raise SystemExit(0 if not f else 1)
