from pathlib import Path
import tempfile
from conscious_agent.operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore
from conscious_agent.operator_correction_acceptance_guidance import OperatorCorrectionAcceptanceGuidanceStore
from conscious_agent.operator_correction_reasoning_application import OperatorCorrectionReasoningApplicationStore
from conscious_agent.operator_correction_reasoning_continuity import OperatorCorrectionReasoningContinuityStore

def req(v,m):
 if not v: raise AssertionError(m)
def main():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); e=OperatorCorrectionAcceptanceEligibilityStore(p); g=OperatorCorrectionAcceptanceGuidanceStore(p); a=OperatorCorrectionReasoningApplicationStore(p); c=OperatorCorrectionReasoningContinuityStore(p)
  eid=e.register('e',operator_decision_id='op',decision_kind='acceptance',target_kind='decision',target_id='d',source_record_id='r',source_revision_id='v')['eligibility_id'];g.register('g',eligibility_id=eid,influence_mode='retain_accepted_lineage',reasoning_scope_ids=['planning']);aid=a.select('a',reasoning_scope_id='planning')['application_id']
  r=c.register('c1',application_id=aid,continuity_key='k1',owner_id='o',worker_claim_id='w');req(r['state']=='claimed','claimed')
  req(c.register('c2',application_id=aid,continuity_key='k1')['status']=='duplicate_suppressed','duplicate')
  r2=c.register('c3',application_id=aid,continuity_key='k2',worker_claim_id='old',restart_epoch=2,claim_stale=True);req(r2['state']=='stale_released','stale')
  row=next(x for x in c.snapshot()['continuity_records'] if x['continuity_id']==r2['continuity_id']);req(not row['worker_claim_id'] and row['stale_claim_released'],'claim cleared')
  s=c.inspection_summary();req(not s['reasoning_started'] and not any(s['authority_boundary'].values()),'authority');req(not s['raw_content_exposed'],'privacy')
 print('v1142.4: 6/6 passed')
if __name__=='__main__': main()
