from pathlib import Path
import tempfile
from conscious_agent.isolated_sandbox_execution_deliberation_sessions import IsolatedSandboxExecutionDeliberationSessionStore
from conscious_agent.isolated_sandbox_execution_arbitration import IsolatedSandboxExecutionArbitrationStore,OUTCOMES
from conscious_agent.json_storage import write_json_atomic
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition'; d=IsolatedSandboxExecutionDeliberationSessionStore(r); r.mkdir(parents=True,exist_ok=True); s=d._load(); s['sessions'].append({'session_id':'ss-1','candidate_id':'ix-1','eligibility_ids':['ie-1'],'deficiency_candidate_ids':['df-1'],'execution_modes':['source_repair'],'component_ids':['component:a'],'project_digests':['pd'],'scope_digests':['sd'],'workspace_manifest_digests':['m'*64],'command_profile_ids':['cmd'],'resource_budget_ids':['budget'],'pause_reason':'','state':'open'}); write_json_atomic(d.path,s,expected_type=dict,sort_keys=True)
 st=IsolatedSandboxExecutionArbitrationStore(r); x=st.arbitrate('a1',session_id='ss-1',evidence_support=.9,scope_support=.9,containment_support=.9,reversibility_support=.9,isolation_support=.9); check('supported',x['outcome']=='isolated_sandbox_execution_supported'); row=st.snapshot()['outcomes'][0]; check('structural',not row['patch_text_digest'] and not row['sandbox_id']); check('outcomes',len(OUTCOMES)>=16); y=st.arbitrate('a2',session_id='ss-1',deliberate_no_isolated_sandbox_execution=True); check('deliberate no change',y['outcome']=='deliberate_no_isolated_sandbox_execution'); check('authority inert',not any(st.inspection_summary()['authority_boundary'].values()))
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
