from pathlib import Path
import tempfile
from conscious_agent.sandbox_change_deliberation_sessions import SandboxChangeDeliberationSessionStore
from conscious_agent.sandbox_change_arbitration import SandboxChangeArbitrationStore,OUTCOMES
from conscious_agent.json_storage import write_json_atomic
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition'; d=SandboxChangeDeliberationSessionStore(r); r.mkdir(parents=True,exist_ok=True); s=d._load(); s['sessions'].append({'session_id':'ss-1','candidate_id':'sc-1','eligibility_ids':['se-1'],'deficiency_candidate_ids':['df-1'],'change_categories':['source_repair'],'component_ids':['component:a'],'project_digests':['pd'],'scope_digests':['sd'],'evidence_ids':['ev'],'pause_reason':'','state':'open'}); write_json_atomic(d.path,s,expected_type=dict,sort_keys=True)
 st=SandboxChangeArbitrationStore(r); x=st.arbitrate('a1',session_id='ss-1',evidence_support=.9,scope_support=.9,containment_support=.9,reversibility_support=.9,isolation_support=.9); check('supported',x['outcome']=='sandbox_change_supported'); row=st.snapshot()['outcomes'][0]; check('structural',not row['patch_text_digest'] and not row['sandbox_id']); check('outcomes',len(OUTCOMES)>=16); y=st.arbitrate('a2',session_id='ss-1',deliberate_no_sandbox_change=True); check('deliberate no change',y['outcome']=='deliberate_no_sandbox_change'); check('authority inert',not any(st.inspection_summary()['authority_boundary'].values()))
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
