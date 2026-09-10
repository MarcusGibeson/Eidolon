import json,tempfile
from pathlib import Path
from conscious_agent.specification_eligibility import SpecificationEligibilityStore
from conscious_agent.specification_candidates import SpecificationCandidateStore
p=t=f=0
def check(n,v):
 global p,t,f;t+=1;p+=bool(v);f+=not bool(v);print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';r.mkdir(parents=True);(r/'development_proposal_arbitration.json').write_text(json.dumps({'outcomes':[{'arbitration_id':'a1','session_id':'s1','candidate_id':'pc1','eligibility_ids':['pe1'],'deficiency_candidate_ids':['d1'],'proposal_categories':['usability_repair'],'component_ids':['ui.panel'],'project_digests':['p'],'scope_digests':['q'],'evidence_ids':['e'],'outcome':'proposal_supported'}]}))
 eid=SpecificationEligibilityStore(r).register('e',arbitration_id='a1',specification_category='usability_specification',scope_component_ids=['ui.panel'],operator_review_required=True)['eligibility_id'];store=SpecificationCandidateStore(r);out=store.register('c',eligibility_ids=[eid]);check('candidate',out['state']=='requires_operator_review');check('overlap',store.register('c2',eligibility_ids=[eid])['status']=='specification_candidate_overlap_merged');row=store.inspection_summary()['recent_candidates'][0];check('lineage',row['eligibility_ids']==[eid] and row['proposal_candidate_ids']==['pc1']);check('no specification text',not row['specification_text_digest']);check('authority inert',not any(store.inspection_summary()['authority_boundary'].values()))
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1137.1'}));raise SystemExit(0 if not f else 1)
