from pathlib import Path
import json,tempfile
from conscious_agent.objective_coherence_signals import ObjectiveCoherenceSignalStore
from conscious_agent.objective_coherence_candidates import ObjectiveCoherenceCandidateStore
from conscious_agent.objective_coherence_deliberation import ObjectiveCoherenceDeliberationStore
from conscious_agent.objective_coherence_arbitration import ObjectiveCoherenceArbitrator
p=0
def req(x):
 global p; assert x; p+=1
def ses(root,t,op=False):
 s=ObjectiveCoherenceSignalStore(root); x=s.register('s'+t,signal_type='priority_mismatch',source_type='objective',source_id='o'+t,related_type='objective',related_id='r'+t); c=ObjectiveCoherenceCandidateStore(root).register('c'+t,signal_ids=[x['result']['signal_id']],operator_review_required=op); return ObjectiveCoherenceDeliberationStore(root).open('o'+t,candidate_id=c['result']['candidate_id'])['result']['session_id']
with tempfile.TemporaryDirectory() as td:
 r=Path(td); a=ObjectiveCoherenceArbitrator(r); x=a.arbitrate('1',session_id=ses(r,'1'),priority_mismatch=.9,evidence_quality=.8,uncertainty=.1); req(x['arbitration']['outcome']=='reprioritization_candidate'); req(not x['arbitration']['objectives_reprioritized']); y=a.arbitrate('2',session_id=ses(r,'2'),force_unresolved=True); req(y['arbitration']['outcome']=='unresolved'); z=a.arbitrate('3',session_id=ses(r,'3'),evidence_quality=.8,uncertainty=.1); req(z['arbitration']['outcome']=='retain'); q=a.arbitrate('4',session_id=ses(r,'4',True)); req(q['arbitration']['outcome']=='requires_operator_review'); w=a.arbitrate('5',session_id=ses(r,'5'),dependency_conflict=.9,evidence_quality=.8,uncertainty=.1); req(w['arbitration']['outcome']=='dependency_repair_candidate'); i=a.inspection_summary(); req(i['contract_version']=='v1121.4'); req(not i['milestone_modified']); req(not i['proposal_created']); req(not i['external_action_executed'])
print(json.dumps({'passed':p,'total':10,'suite':'v1121.4'}))
