from pathlib import Path
import tempfile
from conscious_agent.operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore
from conscious_agent.operator_correction_acceptance_guidance import OperatorCorrectionAcceptanceGuidanceStore
from conscious_agent.operator_correction_reasoning_application import OperatorCorrectionReasoningApplicationStore
from conscious_agent.operator_correction_reasoning_continuity import OperatorCorrectionReasoningContinuityStore
from conscious_agent.operator_correction_reliability_review import OperatorCorrectionReliabilityReviewStore

def req(v,m):
 if not v: raise AssertionError(m)
def seed(p):
 e=OperatorCorrectionAcceptanceEligibilityStore(p);g=OperatorCorrectionAcceptanceGuidanceStore(p);a=OperatorCorrectionReasoningApplicationStore(p);c=OperatorCorrectionReasoningContinuityStore(p)
 eid=e.register('e',operator_decision_id='op',decision_kind='correction',target_kind='belief',target_id='b',source_record_id='r',source_revision_id='v')['eligibility_id'];g.register('g',eligibility_id=eid,influence_mode='prefer_corrected_lineage',reasoning_scope_ids=['reflection']);aid=a.select('a',reasoning_scope_id='reflection')['application_id'];cid=c.register('c',application_id=aid,continuity_key='k')['continuity_id'];return aid,cid
with tempfile.TemporaryDirectory() as td:
 p=Path(td);aid,cid=seed(p);s=OperatorCorrectionReliabilityReviewStore(p)
 r=s.register('r1',application_id=aid,continuity_id=cid,expected_influence=True,observed_influence=False);req(r['state']=='missed_correction','missed')
 r2=s.register('r2',application_id=aid,continuity_id=cid,expected_influence=False,observed_influence=True);req(r2['state']=='over_applied','over')
 r3=s.register('r3',application_id=aid,continuity_id=cid,expected_influence=True,observed_influence=True);req(r3['state']=='effective','effective')
 req(s.register('r3',application_id=aid,continuity_id=cid,expected_influence=True,observed_influence=True)['idempotent'],'idempotent')
 req(not any(s.inspection_summary()['authority_boundary'].values()),'authority')
 req(not s.inspection_summary()['reasoning_text_exposed'],'privacy')
print('v1142.6: 6/6 passed')
