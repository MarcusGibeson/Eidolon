from __future__ import annotations
"""v2602 advisory-only strategy learning candidates."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2602.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_strategy_learning_candidates(reliability:Mapping[str,Any],calibration:Mapping[str,Any])->dict[str,Any]:
    cal={str(x.get('strategy_code')):x for x in calibration.get('profiles') or [] if isinstance(x,Mapping)};rows=[]
    for p in reliability.get('profiles') or []:
        if not isinstance(p,Mapping):continue
        code=str(p.get('strategy_code') or 'unspecified');rel=str(p.get('reliability') or 'insufficient_history');cl=str((cal.get(code) or {}).get('calibration') or 'insufficient_history')
        if rel=='underperforming':rec='review_strategy_before_reuse'
        elif cl=='systematic_overprediction':rec='reduce_expected_value_confidence'
        elif rel=='reliable' and cl=='roughly_calibrated':rec='retain_strategy_as_supported_option'
        else:rec='collect_more_project_outcome_evidence'
        rows.append({'strategy_code':code,'reliability':rel,'calibration':cl,'recommendation':rec,'policy_change_applied':False})
    out={'ok':True,'contract_version':CONTRACT_VERSION,'candidates':rows[:16],'candidate_count':len(rows[:16]),'automatic_strategy_change_permitted':False,'priority_model_mutated':False,'development_policy_mutated':False,'operator_review_required':bool(rows),'authority_granted':False};out['learning_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_strategy_learning_candidates']
