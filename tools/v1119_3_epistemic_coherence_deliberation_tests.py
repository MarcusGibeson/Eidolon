from pathlib import Path
import json, tempfile
from conscious_agent.epistemic_coherence_signals import EpistemicCoherenceSignalStore
from conscious_agent.epistemic_coherence_candidates import EpistemicCoherenceCandidateStore
from conscious_agent.epistemic_coherence_deliberation import EpistemicCoherenceDeliberationStore
passed=0
def req(x):
 global passed
 assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); sig=EpistemicCoherenceSignalStore(root); r=sig.register('s1',signal_type='structural_contradiction',left_record_type='belief',left_record_id='b1',right_record_type='knowledge',right_record_id='k1'); sid=r['result']['signal_id']; cand=EpistemicCoherenceCandidateStore(root); c=cand.register('c1',signal_ids=[sid],coherence_risk=.8); cid=c['result']['candidate_id']; store=EpistemicCoherenceDeliberationStore(root)
 o=store.open('o1',candidate_id=cid); req(o['status']=='epistemic_coherence_deliberation_opened'); session=o['result']['session_id']; req(store.open('o1',candidate_id=cid)['idempotent']); req(store.open('o2',candidate_id=cid)['status']=='active_session_reused'); out=store.record_outcome('r1',session_id=session,outcome='deliberate_no_repair'); req(out['result']['records_repaired'] is False); snap=store.snapshot(); req(snap['sessions'][0]['selected_outcome']=='deliberate_no_repair'); req(snap['sessions'][0]['repair_id']==''); req(not any(snap['authority_boundary'].values())); inspect=store.inspection_summary(); req(inspect['contract_version']=='v1119.3'); req(not inspect['hidden_reasoning_exposed']); req(inspect['records_repaired'] is False)
print(json.dumps({'passed':passed,'total':10,'suite':'v1119.3'}))
