from pathlib import Path
import tempfile
from conscious_agent.belief_revision_lineage import BeliefRevisionLineageStore
from conscious_agent.epistemic_stability_review import EpistemicStabilityReviewer
p=f=0
def req(x):
 global p,f;p+=bool(x);f+=not bool(x)
with tempfile.TemporaryDirectory() as td:
 root=Path(td);s=BeliefRevisionLineageStore(root);r=EpistemicStabilityReviewer(root);x=r.review(belief_id='b1');req(x['status']=='insufficient_evidence');req(x['false_instability_suppressed']);
 for i,o in enumerate(['weaken','strengthen','weaken','strengthen']):s.record(f'e{i}',belief_id='b1',session_id=f's{i}',outcome=o)
 x=r.review(belief_id='b1',operator_review_required=True);req(x['oscillation_detected']);req(x['reversal_count']>=2);req(x['operator_review_proposal']['approved'] is False);req(x['operator_review_proposal']['applied'] is False);req(not x['belief_mutated']);req(not x['external_action_executed']);i=r.inspection_summary();req(i['contract_version']=='v1118.7');req(not i['proposal_applied'])
print(f'v1118.7 epistemic stability review: {p}/10 passed');raise SystemExit(0 if f==0 and p==10 else 1)
