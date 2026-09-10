from __future__ import annotations
"""v1125.7 reflection reliability, unsupported-conclusion restraint, and visible status."""
from copy import deepcopy
from reflective_outcome_lineage import ReflectiveOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION="v1125.7"
class ReflectiveReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ReflectiveOutcomeLineageStore(runtime_root)
 def review(self,*,subject_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get("outcomes",[]) if x.get("subject_id")==subject_id]; outcomes=[x.get("outcome") for x in rows]; unsupported=sum(1 for x in rows if x.get("outcome")=="conclusion" and not x.get("evidence_refs")); high_uncertainty=sum(1 for x in rows if float(x.get("uncertainty",1))>.7); failures=outcomes.count("provider_failure"); reversals=sum(1 for a,b in zip(outcomes,outcomes[1:]) if a!=b); silence=outcomes.count("deliberate_silence")
  suppressed=len(rows)<minimum_evidence
  if suppressed: status="insufficient_evidence"
  elif unsupported: status="unsupported_conclusion_pattern"
  elif failures>=2: status="provider_reliability_concern"
  elif reversals>=3: status="reflection_instability"
  elif high_uncertainty>=3: status="confidence_calibration_concern"
  else: status="stable_or_indeterminate"
  proposal=None
  if status not in {"insufficient_evidence","stable_or_indeterminate"} and operator_review_required: proposal={"proposal_id":f"reflection-policy-{subject_id[:24]}-{len(rows)}","proposal_type":"operator_reviewed_reflection_policy","state":"proposed","approved":False,"authorized":False,"applied":False}
  quality=0.0 if not rows else round(max(0.0,1.0-((unsupported+failures+high_uncertainty*.25+reversals*.1)/max(1,len(rows)))),4)
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"subject_id":subject_id,"sample_size":len(rows),"outcomes":outcomes,"unsupported_conclusion_count":unsupported,"high_uncertainty_count":high_uncertainty,"provider_failure_count":failures,"reversal_count":reversals,"deliberate_silence_count":silence,"false_pattern_suppressed":suppressed,"status":status,"reflection_reliability":quality,"operator_review_proposal":proposal,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"message_sent":False,"initiative_created":False,"external_action_executed":False,"hidden_reasoning_exposed":False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary();ids=sorted({x.get("subject_id") for x in base.get("recent_outcomes",[]) if x.get("subject_id")});reviews=[self.review(subject_id=x) for x in ids[-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"subject_count":len(ids),"reviews":reviews,"visible_status":{"active_reviews":len(reviews),"raw_conclusions_exposed":False,"hidden_reasoning_exposed":False},"authority_boundary":deepcopy(base.get("authority_boundary",{})),"belief_updated":False,"goal_updated":False,"self_model_updated":False,"message_sent":False,"initiative_created":False,"external_action_executed":False}
def build_reflective_reliability_review_inspection(runtime_root=None): return ReflectiveReliabilityReviewer(runtime_root).inspection_summary()
