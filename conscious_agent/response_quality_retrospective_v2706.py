from __future__ import annotations
"""v2706 retrospective response-quality evidence bound to a prior turn."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2706.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_retrospective_response_quality(prior_grounding_observability:Mapping[str,Any], grounding_outcome_feedback:Mapping[str,Any], *, evidence_operation_id:str)->dict[str,Any]:
    prior=prior_grounding_observability.get('grounding') if isinstance(prior_grounding_observability.get('grounding'),Mapping) else {}
    target=str(prior.get('operation_ref_digest') or '')
    adverse=bool(grounding_outcome_feedback.get('adverse_calibration_evidence'))
    explicit=bool(grounding_outcome_feedback.get('explicit_correction') or grounding_outcome_feedback.get('explicit_retraction'))
    if not target or not explicit:
        state='no_retrospective_evidence'
    elif adverse:
        state='quality_concern'
    else:
        state='mixed_evidence'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'target_operation_ref_digest':target[:64],
         'evidence_operation_ref_digest':hashlib.sha256(str(evidence_operation_id or '').encode()).hexdigest() if str(evidence_operation_id or '') else '',
         'state':state,'evidence_recorded':bool(target and explicit),'adverse_evidence':adverse,
         'disposition':str(grounding_outcome_feedback.get('disposition') or 'none')[:48],
         'raw_prior_response_stored':False,'raw_correction_text_stored':False,'automatic_policy_change':False,'authority_granted':False}
    out['retrospective_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_retrospective_response_quality']
