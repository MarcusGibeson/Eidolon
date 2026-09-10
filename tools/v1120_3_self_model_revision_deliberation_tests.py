from pathlib import Path
import json, tempfile
from conscious_agent.self_model_integrity_signals import SelfModelIntegritySignalStore
from conscious_agent.self_model_integrity_candidates import SelfModelIntegrityCandidateStore
from conscious_agent.self_model_revision_deliberation import SelfModelRevisionDeliberationStore
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); sig=SelfModelIntegritySignalStore(root); r=sig.register('s1',signal_type='state_trait_conflation',claim_type='identity_claim',claim_id='i1',temporal_scope='temporary',persistence_class='persistent_trait'); sid=r['result']['signal_id']; cand=SelfModelIntegrityCandidateStore(root); c=cand.register('c1',signal_ids=[sid],integrity_risk=.8); cid=c['result']['candidate_id']; store=SelfModelRevisionDeliberationStore(root)
 o=store.open('o1',candidate_id=cid); req(o['status']=='self_model_revision_deliberation_opened'); session=o['result']['session_id']; req(store.open('o1',candidate_id=cid)['idempotent']); req(store.open('o2',candidate_id=cid)['status']=='active_session_reused'); out=store.record_outcome('r1',session_id=session,outcome='deliberate_no_revision'); req(out['result']['identity_revised'] is False); snap=store.snapshot(); req(snap['sessions'][0]['selected_outcome']=='deliberate_no_revision'); req(snap['sessions'][0]['identity_revision_id']==''); req(not any(snap['authority_boundary'].values())); inspect=store.inspection_summary(); req(inspect['contract_version']=='v1120.3'); req(not inspect['hidden_reasoning_exposed']); req(inspect['self_model_revised'] is False)
print(json.dumps({'passed':passed,'total':10,'suite':'v1120.3'}))
