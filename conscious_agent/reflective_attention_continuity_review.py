from __future__ import annotations
"""v1123.7 interruption, resumption, distraction, fixation, and reliability review."""
from copy import deepcopy
from reflective_attention_outcome_lineage import ReflectiveAttentionOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION="v1123.7"
class ReflectiveAttentionContinuityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ReflectiveAttentionOutcomeLineageStore(runtime_root)
 def review(self,*,candidate_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get("outcomes",[]) if x.get("candidate_id")==candidate_id]; outcomes=[x.get("outcome") for x in rows]; interruptions=sum(1 for x in rows if x.get("interruption_state") in {"interrupted","resumed"}); resumes=sum(1 for x in rows if x.get("interruption_state")=="resumed")
  switches=sum(1 for a,b in zip(outcomes,outcomes[1:]) if a!=b); repeated_deferral=outcomes.count("defer_for_recovery")>=3; fixation=max((outcomes.count(x) for x in set(outcomes)),default=0)>=4 and len(set(outcomes))==1
  if len(rows)<minimum_evidence: status="insufficient_evidence"; distraction=False; suppressed=True
  else: distraction=switches>=3 or interruptions>=3; status="fixation_detected" if fixation else ("repeated_distraction_detected" if distraction else ("recovery_deferral_pattern" if repeated_deferral else "stable_or_indeterminate")); suppressed=False
  proposal=None
  if (distraction or fixation or repeated_deferral) and operator_review_required: proposal={"proposal_id":f"attention-policy-{candidate_id[:24]}-{len(rows)}","proposal_type":"operator_reviewed_attention_policy","state":"proposed","approved":False,"authorized":False,"applied":False,"can_select_attention":False,"can_create_reflection":False,"can_create_intention":False,"can_create_initiative":False,"can_send_message":False,"can_create_notification":False,"can_contact_provider":False,"can_browse":False,"can_change_policy":False}
  reliability=0.0 if not rows else round(max(0.0,1.0-(switches/max(1,len(rows)-1))),4)
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"candidate_id":candidate_id,"sample_size":len(rows),"outcomes":outcomes,"interruption_count":interruptions,"resumption_count":resumes,"switch_count":switches,"repeated_distraction_detected":distraction,"fixation_detected":fixation,"recovery_deferral_pattern":repeated_deferral,"false_pattern_suppressed":suppressed,"status":status,"attention_reliability":reliability,"operator_review_proposal":proposal,"attention_selected":False,"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"policy_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get("candidate_id") for x in base.get("recent_outcomes",[]) if x.get("candidate_id")}); reviews=[self.review(candidate_id=x) for x in ids[-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"candidate_count":len(ids),"reviews":reviews,"authority_boundary":deepcopy(base.get("authority_boundary",{})),"attention_selected":False,"reflection_created":False,"intention_created":False,"initiative_created":False,"message_sent":False,"notification_created":False,"provider_contacted":False,"browsing_performed":False,"policy_applied":False,"approval_granted":False,"authorization_granted":False,"external_action_executed":False,"hidden_reasoning_exposed":False,"runtime_mutated":False}
def build_reflective_attention_continuity_review(runtime_root=None): return ReflectiveAttentionContinuityReviewer(runtime_root).inspection_summary()
