from pathlib import Path
import tempfile
from conscious_agent.operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore

def req(v,m):
 if not v: raise AssertionError(m)
def main():
 with tempfile.TemporaryDirectory() as td:
  s=OperatorCorrectionAcceptanceEligibilityStore(Path(td),clock=lambda:'2026-07-29T19:00:00.000Z')
  r=s.register('e1',operator_decision_id='op-1',decision_kind='correction',target_kind='belief',target_id='belief-1',source_record_id='record-1',source_revision_id='rev-1',project_digest='a'*64,scope_digest='b'*64)
  req(r['state']=='eligible','eligible'); req(s.register('e1',operator_decision_id='op-1',decision_kind='correction',target_kind='belief',target_id='belief-1',source_record_id='record-1',source_revision_id='rev-1')['idempotent'],'idempotent')
  snap=s.inspection_summary(); row=snap['recent_records'][0]; req(row['historical_record_preserved'] and not row['original_state_mutated'],'history'); req(not any(snap['authority_boundary'].values()),'authority'); req(not snap['raw_content_exposed'],'privacy')
  x=s.register('e2',operator_decision_id='op-2',decision_kind='acceptance',target_kind='goal',target_id='',source_record_id='r',source_revision_id='v'); req(x['state']=='awaiting_target','fail closed')
 print('v1142.0: 7/7 passed')
if __name__=='__main__': main()
