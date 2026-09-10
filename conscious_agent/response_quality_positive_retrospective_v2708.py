from __future__ import annotations
"""v2708 explicit positive retrospective quality evidence bound to prior response."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2708.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_positive_retrospective_quality(prior_grounding_observability:Mapping[str,Any],followup_signal:Mapping[str,Any],*,evidence_operation_id:str)->dict[str,Any]:
    prior=prior_grounding_observability.get('grounding') if isinstance(prior_grounding_observability.get('grounding'),Mapping) else {}
    target=str(prior.get('operation_ref_digest') or '')[:64];positive=bool(followup_signal.get('positive_resolution') and followup_signal.get('explicit'))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'target_operation_ref_digest':target,'evidence_operation_ref_digest':hashlib.sha256(str(evidence_operation_id or '').encode()).hexdigest() if str(evidence_operation_id or '') else '',
         'state':'supported_success' if target and positive else 'no_retrospective_evidence','evidence_recorded':bool(target and positive),'positive_evidence':bool(target and positive),
         'signal_digest':str(followup_signal.get('signal_digest') or '')[:64],'raw_message_stored':False,'raw_prior_response_stored':False,'automatic_policy_change':False,'authority_granted':False};out['retrospective_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_positive_retrospective_quality']
