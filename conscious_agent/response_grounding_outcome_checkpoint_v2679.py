from __future__ import annotations
from response_grounding_outcome_feedback_v2677 import build_response_grounding_outcome_feedback
from response_grounding_learning_profile_v2678 import build_response_grounding_learning_profile, build_response_grounding_policy_review

def build_checkpoint()->dict:
 prior={"present":True,"grounding":{"assertiveness":"grounded","memory_state":"grounded_relevant_memory"}}
 corr={"candidate":{"candidate_type":"correction"}}
 feedback=build_response_grounding_outcome_feedback(prior,corr)
 profile=build_response_grounding_learning_profile([feedback,feedback,feedback])
 review=build_response_grounding_policy_review(profile)
 checks={
  "correction_bound":feedback["evidence_recorded"],"adverse_grounded":feedback["adverse_calibration_evidence"],
  "silence_not_validation":not feedback["silence_treated_as_validation"],"profile_review_due":profile["state"]=="overassertion_review_due",
  "review_operator_bound":review["review_due"] and review["recommended_action"]=="operator_review_response_grounding_policy",
  "no_auto_policy":not review["automatic_policy_change"],"no_mutation":not feedback["response_policy_mutated"],"no_authority":not review["authority_granted"],
 }
 return {"ok":all(checks.values()),"checks":checks,"passed":sum(checks.values()),"total":len(checks)}
__all__=["build_checkpoint"]
