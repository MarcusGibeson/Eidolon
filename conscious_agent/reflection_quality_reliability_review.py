from __future__ import annotations
"""v1126.7 reflection-quality integration reliability and false-pattern suppression."""
from copy import deepcopy
from reflection_quality_outcome_lineage import ReflectionQualityOutcomeLineageStore, CONTRACT_VERSION as LINEAGE_VERSION
CONTRACT_VERSION="v1126.7"
class ReflectionQualityReliabilityReviewer:
 def __init__(self,runtime_root=None): self.lineage=ReflectionQualityOutcomeLineageStore(runtime_root)
 def review(self,*,reflection_outcome_id:str,minimum_evidence:int=3,operator_review_required:bool=False):
  rows=[x for x in self.lineage.snapshot().get("outcomes",[]) if x.get("reflection_outcome_id")==reflection_outcome_id]; outcomes=[x.get("outcome") for x in rows]
  unsupported=outcomes.count("mark_unsupported"); contradictions=outcomes.count("reconcile_contradiction"); recalibrations=outcomes.count("recalibrate_confidence"); recovery=outcomes.count("defer_for_provider_recovery"); unresolved=outcomes.count("unresolved"); reversals=sum(1 for a,b in zip(outcomes,outcomes[1:]) if a!=b); suppressed=len(rows)<minimum_evidence
  if suppressed: status="insufficient_evidence"
  elif unsupported>=2: status="repeated_unsupported_conclusion"
  elif recovery>=2: status="provider_recovery_reliability_concern"
  elif reversals>=3: status="quality_evaluation_instability"
  elif unresolved>=2: status="persistent_quality_uncertainty"
  else: status="stable_or_indeterminate"
  proposal=None
  if status not in {"insufficient_evidence","stable_or_indeterminate"} and operator_review_required: proposal={"proposal_id":f"reflection-quality-policy-{reflection_outcome_id[:20]}-{len(rows)}","proposal_type":"operator_reviewed_reflection_quality_policy","state":"proposed","approved":False,"authorized":False,"applied":False}
  reliability=0.0 if not rows else round(max(0.0,1.0-((unsupported+recovery+unresolved*.5+reversals*.15)/max(1,len(rows)))),4)
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"reflection_outcome_id":reflection_outcome_id,"sample_size":len(rows),"outcomes":outcomes,"unsupported_count":unsupported,"contradiction_reconciliation_count":contradictions,"confidence_recalibration_count":recalibrations,"provider_recovery_deferral_count":recovery,"unresolved_count":unresolved,"reversal_count":reversals,"false_pattern_suppressed":suppressed,"status":status,"quality_reliability":reliability,"operator_review_proposal":proposal,"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False,"hidden_reasoning_exposed":False}
 def inspection_summary(self):
  base=self.lineage.inspection_summary(); ids=sorted({x.get("reflection_outcome_id") for x in base.get("recent_outcomes",[]) if x.get("reflection_outcome_id")}); reviews=[self.review(reflection_outcome_id=x) for x in ids[-24:]]
  return {"ok":True,"contract_version":CONTRACT_VERSION,"lineage_contract_version":LINEAGE_VERSION,"review_count":len(reviews),"reviews":reviews,"visible_status":{"active_reviews":len(reviews),"raw_conclusions_exposed":False,"evidence_text_exposed":False,"hidden_reasoning_exposed":False},"authority_boundary":deepcopy(base.get("authority_boundary",{})),"belief_updated":False,"goal_updated":False,"self_model_updated":False,"provider_contacted":False,"message_sent":False,"external_action_executed":False}
def build_reflection_quality_reliability_review_inspection(runtime_root=None): return ReflectionQualityReliabilityReviewer(runtime_root).inspection_summary()
