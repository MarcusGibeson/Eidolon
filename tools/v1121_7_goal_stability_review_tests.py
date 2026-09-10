from pathlib import Path
import json,tempfile
from conscious_agent.objective_coherence_outcome_lineage import ObjectiveCoherenceOutcomeLineageStore
from conscious_agent.goal_stability_review import GoalStabilityReviewer
passed=0
def req(x):
 global passed; assert x; passed+=1
with tempfile.TemporaryDirectory() as td:
 root=Path(td); l=ObjectiveCoherenceOutcomeLineageStore(root); r=GoalStabilityReviewer(root); req(r.review(objective_id="none")["status"]=="insufficient_evidence")
 for n,out in enumerate(["retain","reprioritization_candidate","retain"],1): l.record(f"e{n}",objective_id="obj-1",session_id=f"s{n}",outcome=out)
 x=r.review(objective_id="obj-1",operator_review_required=True); req(x["sample_size"]==3); req(x["goal_instability_detected"]); req(x["reversal_count"]==2); req(x["false_instability_suppressed"] is False); req(x["operator_review_proposal"]["applied"] is False); req(not x["objectives_reprioritized"] and not x["objective_abandoned"]); req(not x["dependency_modified"] and not x["milestone_modified"]); req(not x["approval_granted"] and not x["authorization_granted"] and not x["external_action_executed"]); req(r.inspection_summary()["contract_version"]=="v1121.7")
print(json.dumps({"passed":passed,"total":10,"suite":"v1121.7"}))
