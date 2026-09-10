from pathlib import Path
import tempfile
from conscious_agent.operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore
from conscious_agent.operator_correction_acceptance_guidance import OperatorCorrectionAcceptanceGuidanceStore
from conscious_agent.operator_correction_reasoning_application import OperatorCorrectionReasoningApplicationStore
from conscious_agent.operator_correction_reasoning_continuity import OperatorCorrectionReasoningContinuityStore
from conscious_agent.operator_correction_reasoning_integration_checkpoint import build_operator_correction_reasoning_integration_checkpoint

def req(v,m):
 if not v: raise AssertionError(m)
def main():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td);e=OperatorCorrectionAcceptanceEligibilityStore(p);g=OperatorCorrectionAcceptanceGuidanceStore(p);a=OperatorCorrectionReasoningApplicationStore(p);c=OperatorCorrectionReasoningContinuityStore(p)
  eid=e.register('e',operator_decision_id='op',decision_kind='correction',target_kind='belief',target_id='b',source_record_id='r',source_revision_id='v')['eligibility_id'];g.register('g',eligibility_id=eid,influence_mode='prefer_corrected_lineage',reasoning_scope_ids=['reflection']);aid=a.select('a',reasoning_scope_id='reflection')['application_id'];c.register('c',application_id=aid,continuity_key='k',restart_epoch=1)
  report=build_operator_correction_reasoning_integration_checkpoint(p,source_root=Path(__file__).resolve().parents[1]);req(report['ok'],'checkpoint');req(report['passed']==20,'20 checks');req(not report['runtime_mutated'] and not report['source_modified'],'read only');req(not report['reasoning_executed'] and not report['history_rewritten'],'separation');req(not report['consciousness_proven'],'claim')
 print('v1142.5: 5/5 passed')
if __name__=='__main__': main()
