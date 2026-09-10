from __future__ import annotations
from response_grounding_output_audit_v2683 import audit_response_grounding_output
def build_checkpoint()->dict:
 p={'personal_memory_reference_permitted':False};c={'must_not_claim_execution_without_receipt':True}
 bad=audit_response_grounding_output('I remember you said that. I installed the update.',p,c)
 good=audit_response_grounding_output('I do not have grounded memory for that, so I am uncertain.',p,c)
 checks={'bad_detected':not bad['ok'],'memory_shape':bad['memory_claim_shape_count']>0,'execution_shape':bad['execution_claim_shape_count']>0,'good_passes':good['ok'],'audit_only':bad['audit_only'] and not bad['response_rewritten'],'no_text_stored':not bad['raw_response_stored'],'no_provider':not bad['provider_contacted'],'no_authority':not bad['authority_granted']}
 return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
__all__=['build_checkpoint']
