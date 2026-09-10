from pathlib import Path
import tempfile,json
from conscious_agent.epistemic_coherence_signals import EpistemicCoherenceSignalStore
from conscious_agent.epistemic_coherence_candidates import EpistemicCoherenceCandidateStore
passed=0
def req(v):
 global passed; assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); s=EpistemicCoherenceSignalStore(root); a=s.register('s1',signal_type='confidence_mismatch',left_record_type='belief',left_record_id='b1',right_record_type='knowledge',right_record_id='k1')['result']['signal_id']; c=EpistemicCoherenceCandidateStore(root,signals=s); r=c.register('c1',signal_ids=[a],coherence_risk=.8); req(r['status']=='epistemic_coherence_candidate_registered'); req(c.register('c1',signal_ids=[a])['idempotent']); req(c.register('c2',signal_ids=[a],coherence_risk=.8)['status']=='duplicate_candidate_ignored'); snap=c.snapshot(); req(len(snap['candidates'])==1); req(snap['candidates'][0]['record_types']==['belief','knowledge']); req(not any(snap['authority_boundary'].values())); ins=c.inspection_summary(); req(ins['candidate_count']==1); req(not ins['hidden_reasoning_exposed'] and not ins['knowledge_text_exposed']); req(ins['runtime_mutated'] is False); req(ins['contract_version']=='v1119.1')
print(json.dumps({'passed':passed,'total':10,'suite':'v1119.1'}))
