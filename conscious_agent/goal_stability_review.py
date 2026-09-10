from __future__ import annotations
"""v1121.7 deterministic long-horizon objective coherence stability review."""
from copy import deepcopy
from objective_coherence_outcome_lineage import ObjectiveCoherenceOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION="v1121.7"
class GoalStabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ObjectiveCoherenceOutcomeLineageStore(runtime_root)
 def review(self,*,objective_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get("outcomes",[]) if x.get("objective_id")==objective_id]
  outcomes=[x.get("outcome") for x in rows]; directional=[x for x in outcomes if x in {"retain","reprioritization_candidate","dependency_repair_candidate","milestone_revision_candidate","clarify_abandonment"}]
  reversal_pairs={("retain","reprioritization_candidate"),("reprioritization_candidate","retain"),("retain","milestone_revision_candidate"),("milestone_revision_candidate","retain"),("retain","clarify_abandonment"),("clarify_abandonment","retain")}
  reversals=sum(1 for a,b in zip(directional,directional[1:]) if (a,b) in reversal_pairs)
  if len(rows)<minimum_evidence: status="insufficient_evidence"; unstable=False; recurring=False; suppressed=True
  else: recurring=max((outcomes.count(x) for x in set(outcomes)),default=0)>=3; unstable=reversals>=2; status="goal_instability_detected" if unstable else ("goal_pattern_recurrence_detected" if recurring else "stable_or_indeterminate"); suppressed=False
  proposal=None
  if (unstable or recurring) and operator_review_required:
   proposal={"proposal_id":f"goal-policy-{objective_id[:24]}-{len(rows)}","proposal_type":"operator_reviewed_goal_policy","state":"proposed","approved":False,"authorized":False,"applied":False,"can_reprioritize":False,"can_abandon_objective":False,"can_modify_dependency":False,"can_modify_milestone":False,"can_change_policy":False}
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"objective_id":objective_id,"sample_size":len(rows),"outcomes":outcomes,"reversal_count":reversals,"recurrence_detected":recurring,"goal_instability_detected":unstable,"false_instability_suppressed":suppressed,"status":status,"goal_reliability":0.0 if not rows else round(max(0.0,1.0-(reversals/max(1,len(rows)-1))),4),"operator_review_proposal":proposal,"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False,"proposal_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get("objective_id") for x in base.get("recent_outcomes",[]) if x.get("objective_id")}); reviews=[self.review(objective_id=x) for x in ids[-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"objective_count":len(ids),"reviews":reviews,"authority_boundary":deepcopy(base.get("authority_boundary",{})),"objectives_reprioritized":False,"objective_abandoned":False,"dependency_modified":False,"milestone_modified":False,"proposal_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_goal_stability_review(runtime_root=None): return GoalStabilityReviewer(runtime_root).inspection_summary()
