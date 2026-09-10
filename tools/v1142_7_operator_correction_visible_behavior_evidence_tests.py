from pathlib import Path
import tempfile
from tools.v1142_6_operator_correction_reliability_review_tests import seed
from conscious_agent.operator_correction_reliability_review import OperatorCorrectionReliabilityReviewStore
from conscious_agent.operator_correction_visible_behavior_evidence import OperatorCorrectionVisibleBehaviorEvidenceStore

def req(v,m):
 if not v: raise AssertionError(m)
with tempfile.TemporaryDirectory() as td:
 p=Path(td);aid,cid=seed(p);r=OperatorCorrectionReliabilityReviewStore(p);e=OperatorCorrectionVisibleBehaviorEvidenceStore(p)
 rid=r.register('r',application_id=aid,continuity_id=cid,expected_influence=True,observed_influence=True)['review_id'];x=e.register('e',review_id=rid,behavior_surface_id='reflection');req(x['state']=='supported','supported')
 req(e.register('e',review_id=rid,behavior_surface_id='reflection')['idempotent'],'idempotent')
 rid2=r.register('r2',application_id=aid,continuity_id=cid,expected_influence=True,observed_influence=False)['review_id'];req(e.register('e2',review_id=rid2,behavior_surface_id='reflection')['state']=='review_required','review')
 s=e.inspection_summary();req(not s['reasoning_text_exposed'],'privacy');req(not any(s['authority_boundary'].values()),'authority');req(s['recent_records'][0]['content_free'],'content free')
print('v1142.7: 6/6 passed')
