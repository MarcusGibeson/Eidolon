from __future__ import annotations
"""v1122.7 deterministic motivational continuity, decay, recurrence, and reversal review."""
from copy import deepcopy
from motivational_outcome_lineage import MotivationalOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION="v1122.7"
class MotivationalStabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=MotivationalOutcomeLineageStore(runtime_root)
 def review(self,*,drive_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get("outcomes",[]) if x.get("drive_id")==drive_id]; outcomes=[x.get("outcome") for x in rows]
  pairs={("retain_drive","decay_transient_urgency"),("decay_transient_urgency","retain_drive"),("prioritize_for_bounded_review","defer_drive"),("defer_drive","prioritize_for_bounded_review")}; reversals=sum(1 for a,b in zip(outcomes,outcomes[1:]) if (a,b) in pairs)
  if len(rows)<minimum_evidence: status="insufficient_evidence"; recurring=False; unstable=False; suppressed=True
  else: recurring=max((outcomes.count(x) for x in set(outcomes)),default=0)>=3; unstable=reversals>=2; status="motivational_instability_detected" if unstable else ("motivational_recurrence_detected" if recurring else "stable_or_indeterminate"); suppressed=False
  proposal=None
  if (unstable or recurring) and operator_review_required: proposal={"proposal_id":f"motivational-policy-{drive_id[:24]}-{len(rows)}","proposal_type":"operator_reviewed_motivational_policy","state":"proposed","approved":False,"authorized":False,"applied":False,"can_select_attention":False,"can_create_initiative":False,"can_send_message":False,"can_create_notification":False,"can_contact_provider":False,"can_browse":False,"can_change_policy":False}
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"drive_id":drive_id,"sample_size":len(rows),"outcomes":outcomes,"reversal_count":reversals,"recurrence_detected":recurring,"motivational_instability_detected":unstable,"false_pattern_suppressed":suppressed,"status":status,"drive_reliability":0.0 if not rows else round(max(0.0,1.0-(reversals/max(1,len(rows)-1))),4),"operator_review_proposal":proposal,"attention_selected":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"policy_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get("drive_id") for x in base.get("recent_outcomes",[]) if x.get("drive_id")}); reviews=[self.review(drive_id=x) for x in ids[-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"drive_count":len(ids),"reviews":reviews,"authority_boundary":deepcopy(base.get("authority_boundary",{})),"attention_selected":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"policy_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_motivational_stability_review(runtime_root=None): return MotivationalStabilityReviewer(runtime_root).inspection_summary()
