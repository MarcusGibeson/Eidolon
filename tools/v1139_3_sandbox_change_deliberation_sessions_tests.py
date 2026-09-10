from pathlib import Path
import tempfile
from conscious_agent.sandbox_change_candidates import SandboxChangeCandidateStore
from conscious_agent.sandbox_change_deliberation_sessions import SandboxChangeDeliberationSessionStore
from conscious_agent.json_storage import write_json_atomic
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition'; c=SandboxChangeCandidateStore(r); r.mkdir(parents=True,exist_ok=True); s=c._load(); s['candidates'].append({'candidate_id':'sc-1','eligibility_ids':['se-1'],'arbitration_ids':['ta-1'],'deficiency_candidate_ids':['df-1'],'change_categories':['source_repair'],'component_ids':['component:a'],'project_digests':['pd'],'scope_digests':['sd'],'evidence_ids':['ev'],'estimated_cost':.4,'minimum_reversibility':.9,'minimum_containment_confidence':.9,'path_digests':['a'*64],'isolation_profile_ids':['iso'],'operation_categories':['modify_candidate_file'],'prerequisite_ids':[],'operator_review_required':False,'state':'active'}); write_json_atomic(c.path,s,expected_type=dict,sort_keys=True)
 st=SandboxChangeDeliberationSessionStore(r); x=st.open('d1',candidate_id='sc-1',deliberation_budget=3); check('opened',x['state']=='open'); row=st.snapshot()['sessions'][0]; check('bounded',row['deliberation_budget']==3); check('lineage',row['candidate_id']=='sc-1' and row['path_digests']); check('no sandbox',not row['sandbox_id'] and not row['sandbox_change_id']);
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
