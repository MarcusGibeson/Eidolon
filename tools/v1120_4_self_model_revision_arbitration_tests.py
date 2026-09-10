from pathlib import Path
import json, tempfile
from conscious_agent.self_model_integrity_signals import SelfModelIntegritySignalStore
from conscious_agent.self_model_integrity_candidates import SelfModelIntegrityCandidateStore
from conscious_agent.self_model_revision_deliberation import SelfModelRevisionDeliberationStore
from conscious_agent.self_model_revision_arbitration import SelfModelRevisionArbitrator
passed=0
def req(x):
 global passed; assert x; passed+=1
def session(root,tag,operator=False):
 s=SelfModelIntegritySignalStore(root); rr=s.register('s'+tag,signal_type='state_trait_conflation',claim_type='identity_claim',claim_id='i'+tag,temporal_scope='temporary',persistence_class='persistent_trait'); c=SelfModelIntegrityCandidateStore(root); cr=c.register('c'+tag,signal_ids=[rr['result']['signal_id']],operator_review_required=operator); return SelfModelRevisionDeliberationStore(root).open('o'+tag,candidate_id=cr['result']['candidate_id'])['result']['session_id']
with tempfile.TemporaryDirectory() as td:
 root=Path(td); a=SelfModelRevisionArbitrator(root)
 x=a.arbitrate('a1',session_id=session(root,'1'),temporal_scope_mismatch=.9,persistence_mismatch=.9,temporary_state_supported=True,evidence_quality=.8,uncertainty=.1); req(x['arbitration']['outcome']=='reclassify_temporary_state'); req(not x['arbitration']['identity_revised']); y=a.arbitrate('a2',session_id=session(root,'2'),force_unresolved=True); req(y['arbitration']['outcome']=='unresolved'); z=a.arbitrate('a3',session_id=session(root,'3'),support_strength=.8,contradiction_strength=.1,evidence_quality=.8,uncertainty=.1); req(z['arbitration']['outcome']=='retain'); q=a.arbitrate('a4',session_id=session(root,'4',True)); req(q['arbitration']['outcome']=='requires_operator_review'); w=a.arbitrate('a5',session_id=session(root,'5'),contradiction_strength=.9,replacement_supported=True,evidence_quality=.8,uncertainty=.1); req(w['arbitration']['outcome']=='replace_candidate'); inspect=a.inspection_summary(); req(inspect['contract_version']=='v1120.4'); req(not inspect['self_model_revised']); req(not inspect['proposal_created']); req(not inspect['external_action_executed'])
print(json.dumps({'passed':passed,'total':10,'suite':'v1120.4'}))
