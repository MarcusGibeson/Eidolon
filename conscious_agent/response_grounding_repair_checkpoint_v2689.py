from __future__ import annotations
from response_grounding_output_audit_v2683 import audit_response_grounding_output
from response_grounding_repair_candidate_v2687 import build_response_grounding_repair_candidate
from response_grounding_repair_review_v2688 import build_response_grounding_repair_review
def build_checkpoint():
 p={'personal_memory_reference_permitted':False,'policy_digest':'a'*64};c={'must_not_claim_execution_without_receipt':True,'calibration_digest':'b'*64};a=audit_response_grounding_output('I remember you said this.',p,c);cand=build_response_grounding_repair_candidate(a,p,c);r=build_response_grounding_repair_review(cand);checks={'audit_concern':not a['ok'],'candidate_ready':cand['state']=='repair_candidate_ready','review_required':r['review_required'],'candidate_only':cand['candidate_only'],'no_rewrite':not r['automatic_response_rewrite'],'no_regen':not r['automatic_provider_regeneration'],'no_provider':not cand['provider_contacted'],'no_authority':not r['authority_granted']};return {'ok':all(checks.values()),'checks':checks,'passed':sum(checks.values()),'total':len(checks)}
