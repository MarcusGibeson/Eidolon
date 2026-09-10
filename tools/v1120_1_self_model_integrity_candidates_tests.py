from pathlib import Path
import tempfile,json
from conscious_agent.self_model_integrity_signals import SelfModelIntegritySignalStore
from conscious_agent.self_model_integrity_candidates import SelfModelIntegrityCandidateStore
passed=0
def req(v):
 global passed; assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); s=SelfModelIntegritySignalStore(root); a=s.register('s1',signal_type='confidence_mismatch',claim_type='identity_claim',claim_id='i1',related_claim_type='self_model_claim',related_claim_id='m1')['result']['signal_id']; c=SelfModelIntegrityCandidateStore(root,signals=s); r=c.register('c1',signal_ids=[a],integrity_risk=.8); req(r['status']=='self_model_integrity_candidate_registered'); req(c.register('c1',signal_ids=[a])['idempotent']); req(c.register('c2',signal_ids=[a],integrity_risk=.8)['status']=='duplicate_candidate_ignored'); snap=c.snapshot(); req(len(snap['candidates'])==1); req(snap['candidates'][0]['claim_types']==['identity_claim','self_model_claim']); req(not any(snap['authority_boundary'].values())); ins=c.inspection_summary(); req(ins['candidate_count']==1); req(not ins['hidden_reasoning_exposed'] and not ins['claim_text_exposed']); req(ins['runtime_mutated'] is False); req(ins['contract_version']=='v1120.1')
print(json.dumps({'passed':passed,'total':10,'suite':'v1120.1'}))
