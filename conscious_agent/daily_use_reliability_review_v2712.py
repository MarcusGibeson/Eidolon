from __future__ import annotations
"""v2712 operator-review packet for daily-use reliability concerns."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2712.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_daily_use_reliability_review(reliability:Mapping[str,Any],trend:Mapping[str,Any])->dict[str,Any]:
    state=str(reliability.get('state') or 'insufficient_data');direction=str(trend.get('direction') or 'insufficient_history');review=state=='degraded' or direction=='worsening'
    reasons=[]
    if state=='degraded':reasons.append('daily_use_reliability_degraded')
    if direction=='worsening':reasons.append('daily_use_reliability_trend_worsening')
    out={'ok':True,'contract_version':CONTRACT_VERSION,'review_required':review,'reasons':reasons,'recommended_boundary':'operator_daily_use_reliability_review' if review else 'continue_observation','automatic_repair':False,'automatic_policy_change':False,'automatic_trial_start':False,'raw_conversation_text_stored':False,'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_daily_use_reliability_review']
