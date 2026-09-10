from __future__ import annotations
"""v2717 bounded daily-use failure-mode review candidates."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2717.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_daily_use_failure_mode_review(reliability:Mapping[str,Any],readiness:Mapping[str,Any])->dict[str,Any]:
    modes=[]
    mapping={'conversation_health_degraded':'conversation_quality_regression','response_quality_concern':'unsupported_or_missed_response','weak_memory_without_uncertainty_restraint':'memory_overclaim_risk','context_budget_pressure':'context_crowding','cognitive_pressure_without_recovery_margin':'cognitive_overload_without_recovery'}
    for concern in reliability.get('concerns') or []:
        code=mapping.get(str(concern))
        if code and code not in modes:modes.append(code)
    for blocker in readiness.get('blockers') or []:
        if str(blocker).startswith('no_') and str(blocker) not in modes:modes.append(str(blocker))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'failure_mode_count':len(modes),'failure_modes':modes[:10],'review_required':bool(modes),'automatic_repair':False,'automatic_trial_start':False,'provider_contacted':False,'raw_conversation_text_stored':False,'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_daily_use_failure_mode_review']
