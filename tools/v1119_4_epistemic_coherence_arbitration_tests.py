from pathlib import Path
import json, tempfile
from conscious_agent.epistemic_coherence_signals import EpistemicCoherenceSignalStore
from conscious_agent.epistemic_coherence_candidates import EpistemicCoherenceCandidateStore
from conscious_agent.epistemic_coherence_deliberation import EpistemicCoherenceDeliberationStore
from conscious_agent.epistemic_coherence_arbitration import EpistemicCoherenceArbitrator
passed=0
def req(x):
 global passed
 assert x; passed+=1
def session(root,tag,operator=False):
 s=EpistemicCoherenceSignalStore(root); rr=s.register('s'+tag,signal_type='semantic_duplication',left_record_type='knowledge',left_record_id='k'+tag,right_record_type='belief',right_record_id='b'+tag); c=EpistemicCoherenceCandidateStore(root); cr=c.register('c'+tag,signal_ids=[rr['result']['signal_id']],operator_review_required=operator); return EpistemicCoherenceDeliberationStore(root).open('o'+tag,candidate_id=cr['result']['candidate_id'])['result']['session_id']
with tempfile.TemporaryDirectory() as td:
 root=Path(td); a=EpistemicCoherenceArbitrator(root)
 x=a.arbitrate('a1',session_id=session(root,'1'),duplication_strength=.9,contradiction_strength=.1,evidence_quality=.8,uncertainty=.1); req(x['arbitration']['outcome']=='merge_candidate'); req(not x['arbitration']['records_repaired']); y=a.arbitrate('a2',session_id=session(root,'2'),force_unresolved=True); req(y['arbitration']['outcome']=='unresolved'); z=a.arbitrate('a3',session_id=session(root,'3'),contradiction_strength=.1,duplication_strength=.1,dependency_staleness=.1,confidence_mismatch=.1); req(z['arbitration']['outcome']=='deliberate_no_repair'); q=a.arbitrate('a4',session_id=session(root,'4',True),duplication_strength=.9); req(q['arbitration']['outcome']=='requires_operator_review'); w=a.arbitrate('a5',session_id=session(root,'5'),dependency_staleness=.9,replacement_supported=True,evidence_quality=.8,uncertainty=.1); req(w['arbitration']['outcome']=='replace_dependency'); inspect=a.inspection_summary(); req(inspect['contract_version']=='v1119.4'); req(not inspect['records_repaired']); req(not inspect['proposal_created']); req(not inspect['external_action_executed'])
print(json.dumps({'passed':passed,'total':10,'suite':'v1119.4'}))
