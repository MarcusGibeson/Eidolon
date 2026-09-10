from pathlib import Path
import json,tempfile
from conscious_agent.objective_coherence_signals import ObjectiveCoherenceSignalStore
from conscious_agent.objective_coherence_candidates import ObjectiveCoherenceCandidateStore
from conscious_agent.objective_coherence_deliberation import ObjectiveCoherenceDeliberationStore
p=0
def req(x):
 global p; assert x; p+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td); s=ObjectiveCoherenceSignalStore(r); a=s.register('s',signal_type='priority_mismatch',source_type='objective',source_id='o1',related_type='objective',related_id='o2'); c=ObjectiveCoherenceCandidateStore(r).register('c',signal_ids=[a['result']['signal_id']]); st=ObjectiveCoherenceDeliberationStore(r); o=st.open('o',candidate_id=c['result']['candidate_id']); req(o['status']=='objective_coherence_deliberation_opened'); sid=o['result']['session_id']; req(st.open('o',candidate_id=c['result']['candidate_id'])['idempotent']); req(st.open('o2',candidate_id=c['result']['candidate_id'])['status']=='active_session_reused'); z=st.record_outcome('r',session_id=sid,outcome='deliberate_no_repair'); req(z['result']['objectives_reprioritized'] is False); snap=st.snapshot(); req(snap['sessions'][0]['selected_outcome']=='deliberate_no_repair'); req(snap['sessions'][0]['priority_change_id']==''); req(not any(snap['authority_boundary'].values())); i=st.inspection_summary(); req(i['contract_version']=='v1121.3'); req(not i['hidden_reasoning_exposed']); req(i['milestone_modified'] is False)
print(json.dumps({'passed':p,'total':10,'suite':'v1121.3'}))
