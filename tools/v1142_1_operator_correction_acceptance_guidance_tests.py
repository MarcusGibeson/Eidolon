from pathlib import Path
import tempfile
from conscious_agent.operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore
from conscious_agent.operator_correction_acceptance_guidance import OperatorCorrectionAcceptanceGuidanceStore

def req(v,m):
 if not v: raise AssertionError(m)
def main():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); e=OperatorCorrectionAcceptanceEligibilityStore(p,clock=lambda:'2026-07-29T19:00:00.000Z'); eid=e.register('e1',operator_decision_id='op-1',decision_kind='acceptance',target_kind='project_assumption',target_id='assumption-1',source_record_id='record-1',source_revision_id='rev-1')['eligibility_id']
  g=OperatorCorrectionAcceptanceGuidanceStore(p,clock=lambda:'2026-07-29T19:01:00.000Z'); r=g.register('g1',eligibility_id=eid,influence_mode='retain_accepted_lineage',reasoning_scope_ids=['planning','reflection'],priority=80)
  req(r['state']=='active','active'); req(g.register('g1',eligibility_id=eid,influence_mode='retain_accepted_lineage',reasoning_scope_ids=['planning','reflection'],priority=80)['idempotent'],'idempotent')
  snap=g.inspection_summary(); row=snap['recent_records'][0]; req(row['advisory_only'] and not row['reasoning_mutated_at_record_time'],'advisory'); req(row['historical_record_preserved'],'history'); req(not any(snap['authority_boundary'].values()),'authority'); req(not snap['operator_text_exposed'],'privacy')
 print('v1142.1: 6/6 passed')
if __name__=='__main__': main()
