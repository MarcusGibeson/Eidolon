from __future__ import annotations
"""v1120.7 deterministic identity revision reliability and self-model stability review."""
from copy import deepcopy
from identity_revision_lineage import IdentityRevisionLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION="v1120.7"
class SelfModelStabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=IdentityRevisionLineageStore(runtime_root)
 def review(self,*,claim_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get("revisions",[]) if x.get("claim_id")==claim_id]
  outcomes=[x.get("outcome") for x in rows]; directional=[x for x in outcomes if x in {"retain","weaken","suspend","reclassify_temporary_state","replace_candidate"}]
  reversal_pairs={("retain","replace_candidate"),("replace_candidate","retain"),("retain","suspend"),("suspend","retain"),("weaken","retain"),("retain","weaken"),("reclassify_temporary_state","retain"),("retain","reclassify_temporary_state")}
  reversals=sum(1 for a,b in zip(directional,directional[1:]) if (a,b) in reversal_pairs)
  if len(rows)<minimum_evidence: status="insufficient_evidence"; unstable=False; recurring=False; suppressed=True
  else: recurring=max((outcomes.count(x) for x in set(outcomes)),default=0)>=3; unstable=reversals>=2; status="identity_oscillation_detected" if unstable else ("revision_recurrence_detected" if recurring else "stable_or_indeterminate"); suppressed=False
  proposal=None
  if (unstable or recurring) and operator_review_required:
   proposal={"proposal_id":f"identity-policy-{claim_id[:24]}-{len(rows)}","proposal_type":"operator_reviewed_identity_policy","state":"proposed","approved":False,"authorized":False,"applied":False,"can_revise_identity":False,"can_revise_self_model":False,"can_change_policy":False,"can_promote_trait":False}
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"claim_id":claim_id,"sample_size":len(rows),"outcomes":outcomes,"reversal_count":reversals,"recurrence_detected":recurring,"identity_oscillation_detected":unstable,"false_instability_suppressed":suppressed,"status":status,"revision_reliability":0.0 if not rows else round(max(0.0,1.0-(reversals/max(1,len(rows)-1))),4),"operator_review_proposal":proposal,"identity_revised":False,"self_model_revised":False,"temporary_state_promoted":False,"proposal_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get("claim_id") for x in base.get("recent_revisions",[]) if x.get("claim_id")}); reviews=[self.review(claim_id=x) for x in ids[-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"claim_count":len(ids),"reviews":reviews,"authority_boundary":deepcopy(base.get("authority_boundary",{})),"identity_revised":False,"self_model_revised":False,"temporary_state_promoted":False,"proposal_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_self_model_stability_review(runtime_root=None): return SelfModelStabilityReviewer(runtime_root).inspection_summary()
