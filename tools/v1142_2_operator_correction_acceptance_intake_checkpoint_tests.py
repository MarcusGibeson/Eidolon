from pathlib import Path
import tempfile
from conscious_agent.operator_correction_acceptance_eligibility import OperatorCorrectionAcceptanceEligibilityStore
from conscious_agent.operator_correction_acceptance_guidance import OperatorCorrectionAcceptanceGuidanceStore
from conscious_agent.operator_correction_acceptance_intake_checkpoint import build_operator_correction_acceptance_intake_checkpoint

def req(v,m):
 if not v: raise AssertionError(m)
def main():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td); e=OperatorCorrectionAcceptanceEligibilityStore(p); eid=e.register('e1',operator_decision_id='op-1',decision_kind='correction',target_kind='belief',target_id='belief-1',source_record_id='record-1',source_revision_id='rev-1')['eligibility_id']; OperatorCorrectionAcceptanceGuidanceStore(p).register('g1',eligibility_id=eid,influence_mode='prefer_corrected_lineage',reasoning_scope_ids=['reflection'])
  report=build_operator_correction_acceptance_intake_checkpoint(p,source_root=Path(__file__).resolve().parents[1]); req(report['ok'],'checkpoint'); req(report['passed']==18,'18 checks'); req(not report['runtime_mutated'] and not report['source_modified'],'read only'); req(not report['history_rewritten'] and not report['future_reasoning_executed'],'separation'); req(not report['consciousness_proven'],'claim')
 print('v1142.2: 5/5 passed')
if __name__=='__main__': main()
