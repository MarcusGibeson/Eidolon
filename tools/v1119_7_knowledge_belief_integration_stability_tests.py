from pathlib import Path
import json, tempfile
from conscious_agent.epistemic_coherence_outcome_lineage import EpistemicCoherenceOutcomeLineageStore
from conscious_agent.knowledge_belief_integration_stability import KnowledgeBeliefIntegrationStabilityReviewer
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); s=EpistemicCoherenceOutcomeLineageStore(root); r=KnowledgeBeliefIntegrationStabilityReviewer(root)
 s.record('e1',candidate_id='c1',session_id='s1',outcome='merge_candidate',signal_ids=['x']); low=r.review(candidate_id='c1'); req(low['status']=='insufficient_evidence'); req(low['false_instability_suppressed'])
 for i,o in enumerate(['retain_separation','merge_candidate','retain_separation'],2): s.record(f'e{i}',candidate_id='c1',session_id=f's{i}',outcome=o,signal_ids=['x'])
 unstable=r.review(candidate_id='c1',operator_review_required=True); req(unstable['integration_instability_detected']); req(unstable['reversal_count']>=2); req(unstable['operator_review_proposal']['applied'] is False); req(not unstable['records_repaired']); req(not unstable['records_merged'])
 for i in range(3): s.record(f'r{i}',candidate_id='c2',session_id=f'rs{i}',outcome='request_more_evidence',signal_ids=['y'])
 recurring=r.review(candidate_id='c2'); req(recurring['repeated_inconsistency_detected'])
 inspect=r.inspection_summary(); req(inspect['contract_version']=='v1119.7'); req(not inspect['proposal_applied'])
print(json.dumps({'passed':passed,'total':10,'suite':'v1119.7'}))
