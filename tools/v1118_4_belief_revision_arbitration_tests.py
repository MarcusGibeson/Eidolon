from pathlib import Path
import tempfile,json
from conscious_agent.evidence_change_signals import EvidenceChangeSignalStore
from conscious_agent.belief_reconsideration_candidates import BeliefReconsiderationCandidateStore
from conscious_agent.belief_revision_deliberation import BeliefRevisionDeliberationStore
from conscious_agent.belief_revision_arbitration import BeliefRevisionArbitrator
passed=0
def req(v):
 global passed; assert v; passed+=1
def setup(root,n,op=False):
 s=EvidenceChangeSignalStore(root); x=s.register('s'+n,belief_id='b'+n,evidence_id='e'+n,change_type='contradiction_detected',structural_digest=n); c=BeliefReconsiderationCandidateStore(root,signals=s); y=c.register('c'+n,belief_id='b'+n,signal_ids=[x['result']['signal_id']],operator_review_required=op); d=BeliefRevisionDeliberationStore(root); return d.open('o'+n,candidate_id=y['result']['candidate_id'],operator_review_required=op)['result']['session_id']
with tempfile.TemporaryDirectory() as td:
 r=Path(td); a=BeliefRevisionArbitrator(r); sid=setup(r,'1'); req(a.arbitrate('a1',session_id=sid,support_strength=.9,contradiction_strength=.2,evidence_quality=.9)['arbitration']['outcome']=='strengthen'); sid=setup(r,'2'); req(a.arbitrate('a2',session_id=sid,support_strength=.2,contradiction_strength=.9,evidence_quality=.8)['arbitration']['outcome']=='suspend'); sid=setup(r,'3'); req(a.arbitrate('a3',session_id=sid,support_strength=.2,contradiction_strength=.9,evidence_quality=.8,replacement_supported=True)['arbitration']['outcome']=='replace'); sid=setup(r,'4'); req(a.arbitrate('a4',session_id=sid,force_unresolved=True)['arbitration']['outcome']=='unresolved'); sid=setup(r,'5'); req(a.arbitrate('a5',session_id=sid,support_strength=.5,contradiction_strength=.5)['arbitration']['outcome']=='deliberate_no_revision'); sid=setup(r,'6',True); req(a.arbitrate('a6',session_id=sid)['arbitration']['outcome']=='requires_operator_review'); ins=a.inspection_summary(); req(ins['contract_version']=='v1118.4'); req(not ins['belief_revised']); req(not ins['proposal_created']); req(not ins['external_action_executed'])
print(json.dumps({'passed':passed,'total':10,'suite':'v1118.4'}))
