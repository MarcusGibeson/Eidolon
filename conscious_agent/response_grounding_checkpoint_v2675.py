from __future__ import annotations
from response_grounding_policy_v2672 import build_response_grounding_policy, response_grounding_prompt_section
from response_assertion_calibration_v2673 import build_response_assertion_calibration

def build_checkpoint()->dict:
 sel={'selected_intent':'direct_answer','construction_directives':{'execution_claims_forbidden':True}};p=build_response_grounding_policy(sel,{'state':'weak_context_only','should_preserve_uncertainty':True},{'historical_uncertainty_required':True});c=build_response_assertion_calibration(p);prompt=response_grounding_prompt_section(p);checks={'cautious':p['assertiveness']=='cautious','uncertainty':c['must_label_memory_uncertainty'],'no_memory_invention':c['must_not_invent_memory'],'no_execution_claim':c['must_not_claim_execution_without_receipt'],'prompt_bounded':len(prompt)<=900,'data_only':'data_only="true"' in prompt,'no_content_generated':not c['response_content_generated'],'no_authority':not p['authority_granted']};return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
