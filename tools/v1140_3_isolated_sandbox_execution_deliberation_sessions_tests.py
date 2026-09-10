from pathlib import Path
import tempfile
from conscious_agent.isolated_sandbox_execution_candidates import IsolatedSandboxExecutionCandidateStore
from conscious_agent.isolated_sandbox_execution_deliberation_sessions import IsolatedSandboxExecutionDeliberationSessionStore
from conscious_agent.json_storage import write_json_atomic
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition'; c=IsolatedSandboxExecutionCandidateStore(r); r.mkdir(parents=True,exist_ok=True); s=c._load(); s['candidates'].append({'candidate_id':'ix-1','eligibility_ids':['ie-1'],'sandbox_change_arbitration_ids':['sa-1'],'deficiency_candidate_ids':['df-1'],'execution_modes':['source_repair'],'component_ids':['component:a'],'project_digests':['pd'],'scope_digests':['sd'],'workspace_manifest_digests':['m'*64],'command_profile_ids':['cmd'],'resource_budget_ids':['budget'],'estimated_cost':.4,'minimum_reversibility':.9,'minimum_containment_confidence':.9,'workspace_manifest_digests':['m'*64],'isolation_profile_ids':['iso'],'command_profile_ids':['cmd'],'prerequisite_ids':[],'operator_review_required':False,'state':'active'}); write_json_atomic(c.path,s,expected_type=dict,sort_keys=True)
 st=IsolatedSandboxExecutionDeliberationSessionStore(r); x=st.open('d1',candidate_id='ix-1',deliberation_budget=3); check('opened',x['state']=='open'); row=st.snapshot()['sessions'][0]; check('bounded',row['deliberation_budget']==3); check('lineage',row['candidate_id']=='ix-1' and row['workspace_manifest_digests']); check('no sandbox',not row['sandbox_id'] and not row['isolated_sandbox_execution_id']);
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
