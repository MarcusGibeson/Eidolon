from pathlib import Path
import tempfile
from conscious_agent.operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore
from conscious_agent.operator_correction_acceptance_guidance import OperatorCorrectionAcceptanceGuidanceStore
from conscious_agent.operator_correction_reasoning_application import OperatorCorrectionReasoningApplicationStore

def req(v,m):
 if not v: raise AssertionError(m)
def main():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); e=OperatorCorrectionAcceptanceEligibilityStore(p); g=OperatorCorrectionAcceptanceGuidanceStore(p); a=OperatorCorrectionReasoningApplicationStore(p)
  eid=e.register('e1',operator_decision_id='op1',decision_kind='correction',target_kind='belief',target_id='b1',source_record_id='r1',source_revision_id='rev1')['eligibility_id']
  gid=g.register('g1',eligibility_id=eid,influence_mode='prefer_corrected_lineage',reasoning_scope_ids=['reflection'],priority=80)['guidance_id']
  r=a.select('a1',reasoning_scope_id='reflection',target_kind='belief',target_id='b1'); req(r['state']=='selected','selected'); req(r['selected_guidance_ids']==[gid],'exact guidance')
  req(a.select('a1',reasoning_scope_id='reflection')['idempotent'],'idempotent')
  req(a.select('a2',reasoning_scope_id='planning')['state']=='no_applicable_guidance','no match')
  rev=g.snapshot()['revision']; req(a.select('a3',reasoning_scope_id='reflection',observed_guidance_revision=rev-1)['state']=='operator_review_required','stale fail closed')
  s=a.inspection_summary(); req(not s['reasoning_executed'] and not any(s['authority_boundary'].values()),'authority'); req(not s['raw_content_exposed'],'privacy')
 print('v1142.3: 6/6 passed')
if __name__=='__main__': main()
