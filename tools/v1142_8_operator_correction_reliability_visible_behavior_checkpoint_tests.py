from pathlib import Path
import tempfile
from tools.v1142_6_operator_correction_reliability_review_tests import seed
from conscious_agent.operator_correction_reliability_review import OperatorCorrectionReliabilityReviewStore
from conscious_agent.operator_correction_visible_behavior_evidence import OperatorCorrectionVisibleBehaviorEvidenceStore
from conscious_agent.operator_correction_reliability_visible_behavior_checkpoint import build_operator_correction_reliability_visible_behavior_checkpoint

def req(v,m):
 if not v: raise AssertionError(m)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);aid,cid=seed(p);r=OperatorCorrectionReliabilityReviewStore(p);e=OperatorCorrectionVisibleBehaviorEvidenceStore(p);rid=r.register('r',application_id=aid,continuity_id=cid,expected_influence=True,observed_influence=True)['review_id'];e.register('e',review_id=rid,behavior_surface_id='reflection')
 report=build_operator_correction_reliability_visible_behavior_checkpoint(p,source_root=Path(__file__).resolve().parents[1]);req(report['ok'],'checkpoint');req(report['passed']==22,'22 checks');req(not report['runtime_mutated'] and not report['source_modified'],'read only');req(not report['history_rewritten'],'history');req(not report['consciousness_proven'],'claim')
print('v1142.8: 5/5 passed')
