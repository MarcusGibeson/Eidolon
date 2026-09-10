from __future__ import annotations
"""v2680 read-only observability for response-grounding outcome learning."""
from pathlib import Path
from typing import Any
from response_grounding_learning_profile_v2678 import load_response_grounding_feedback_history, build_response_grounding_learning_profile, build_response_grounding_policy_review
CONTRACT_VERSION="v2680.0"
def build_response_grounding_learning_observability(runtime_root:str|Path|None=None)->dict[str,Any]:
    history=load_response_grounding_feedback_history(runtime_root); profile=build_response_grounding_learning_profile(history.get('rows') or []); review=build_response_grounding_policy_review(profile)
    return {
      'ok':True,'contract_version':CONTRACT_VERSION,'state':profile['state'],'evidence_count':profile['evidence_count'],'adverse_count':profile['adverse_count'],
      'cautious_correction_count':profile['cautious_correction_count'],'review_due':review['review_due'],'recommended_action':review['recommended_action'],
      'automatic_policy_change_permitted':False,'raw_prompt_stored':False,'raw_response_stored':False,'raw_correction_text_stored':False,'authority_granted':False,
    }
__all__=['CONTRACT_VERSION','build_response_grounding_learning_observability']
