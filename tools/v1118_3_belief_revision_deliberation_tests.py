from pathlib import Path
import tempfile,json
from conscious_agent.evidence_change_signals import EvidenceChangeSignalStore
from conscious_agent.belief_reconsideration_candidates import BeliefReconsiderationCandidateStore
from conscious_agent.belief_revision_deliberation import BeliefRevisionDeliberationStore
passed=0
def req(v):
 global passed; assert v; passed+=1
with tempfile.TemporaryDirectory() as td:
 r=Path(td); sig=EvidenceChangeSignalStore(r); a=sig.register('s1',belief_id='b1',evidence_id='e1',change_type='contradiction_detected',structural_digest='d'); sid=a['result']['signal_id']; c=BeliefReconsiderationCandidateStore(r,signals=sig); cr=c.register('c1',belief_id='b1',signal_ids=[sid]); cid=cr['result']['candidate_id']; store=BeliefRevisionDeliberationStore(r); o=store.open('o1',candidate_id=cid); req(o['ok']); req(o['status']=='belief_revision_deliberation_opened'); req(store.open('o1',candidate_id=cid)['idempotent']); req(store.open('o2',candidate_id=cid)['status']=='active_session_reused'); sess=o['result']['session_id']; out=store.record_outcome('r1',session_id=sess,outcome='retain'); req(out['result']['belief_revised'] is False); snap=store.snapshot(); req(snap['sessions'][0]['selected_outcome']=='retain'); req(not any(snap['authority_boundary'].values())); ins=store.inspection_summary(); req(ins['contract_version']=='v1118.3'); req(not ins['hidden_reasoning_exposed']); req(not ins['belief_revised'])
print(json.dumps({'passed':passed,'total':10,'suite':'v1118.3'}))
