from __future__ import annotations
"""v2718 operator-review-only sustained daily-use trial readiness packet."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2718.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_daily_use_trial_readiness_packet(readiness:Mapping[str,Any],failure_review:Mapping[str,Any])->dict[str,Any]:
    eligible=bool(readiness.get('engineering_ready')) and not bool(failure_review.get('review_required'))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'eligible_for_operator_trial_review':eligible,'review_state':'operator_trial_review_ready' if eligible else 'resolve_engineering_readiness_first','readiness_digest':str(readiness.get('readiness_digest') or '')[:64],'failure_review_digest':str(failure_review.get('review_digest') or '')[:64],
         'real_daily_use_proven':False,'trial_started':False,'automatic_trial_start':False,'operator_selection_required':True,'raw_conversation_text_stored':False,'authority_granted':False};out['packet_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_daily_use_trial_readiness_packet']
