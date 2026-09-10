import json,tempfile
from pathlib import Path
from conscious_agent.specification_eligibility import SpecificationEligibilityStore,SPECIFICATION_CATEGORIES
p=t=f=0
def check(n,v):
 global p,t,f;t+=1;p+=bool(v);f+=not bool(v);print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir(parents=True);(r/'development_proposal_arbitration.json').write_text(json.dumps({'outcomes':[{'arbitration_id':'a1','session_id':'s1','candidate_id':'pc1','eligibility_ids':['pe1'],'deficiency_candidate_ids':['d1'],'proposal_categories':['reliability_repair'],'component_ids':['component.alpha'],'project_digests':['p'],'scope_digests':['q'],'evidence_ids':['e'],'outcome':'proposal_supported'}]}))
 store=SpecificationEligibilityStore(r);out=store.register('e1',arbitration_id='a1',specification_category='reliability_specification',scope_component_ids=['component.alpha'],operator_review_required=False)
 check('eligible',out['state']=='eligible');check('idempotent',store.register('e1',arbitration_id='a1',specification_category='reliability_specification',scope_component_ids=['component.alpha'])['idempotent']);row=store.inspection_summary()['recent_records'][0];check('exact proposal lineage',row['proposal_candidate_id']=='pc1' and row['proposal_eligibility_ids']==['pe1']);check('category coverage',len(SPECIFICATION_CATEGORIES)>=8);check('content free',not store.inspection_summary()['specification_text_exposed']);check('authority inert',not any(store.inspection_summary()['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1137.0'}));raise SystemExit(0 if not f else 1)
