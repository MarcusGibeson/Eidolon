from __future__ import annotations
"""v2704 review-only response-quality packet."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2704.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_quality_review(quality:Mapping[str,Any],trend:Mapping[str,Any])->dict[str,Any]:
    state=str(quality.get('state') or 'unknown');direction=str(trend.get('direction') or 'insufficient_history')
    review=state in {'quality_concern','mixed_evidence'} or direction=='worsening'
    reasons=[]
    if state=='quality_concern':reasons.append('current_response_quality_concern')
    if state=='mixed_evidence':reasons.append('current_response_mixed_evidence')
    if direction=='worsening':reasons.append('response_quality_trend_worsening')
    out={'ok':True,'contract_version':CONTRACT_VERSION,'review_required':review,'reasons':reasons,'review_state':'operator_review_required' if review else 'no_review_required','automatic_policy_change':False,'automatic_response_repair':False,'provider_contacted':False,'raw_conversation_text_stored':False,'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_response_quality_review']
