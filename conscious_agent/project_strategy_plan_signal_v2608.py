from __future__ import annotations
"""v2608 candidate-only plan signals from project strategy history."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2608.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_strategy_plan_signal_candidate(*,plan_id:str,plan_digest:str,strategy_code:str,annotations:Mapping[str,Any])->dict[str,Any]:
 ann=next((x for x in annotations.get('annotations') or [] if isinstance(x,Mapping) and str(x.get('strategy_code'))==str(strategy_code)),None);factor=float((ann or {}).get('confidence_factor') or 1.0);severity=round(max(0,min(1,1-factor)),3);eligible=bool(ann and factor<.8)
 out={'ok':True,'contract_version':CONTRACT_VERSION,'plan_id':str(plan_id)[:120],'plan_digest':str(plan_digest)[:64],'strategy_code':str(strategy_code)[:80],'candidate_present':eligible,'signal_type':'goal_value_changed' if eligible else 'none','signal_code':'historical_strategy_underperformance' if eligible else 'none','severity':severity,'expected_value_delta':round(-severity*.5,3) if eligible else 0.0,'signal_recorded':False,'plan_modified':False,'plan_reprioritized':False,'operator_priority_overridden':False,'authority_granted':False};out['candidate_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_strategy_plan_signal_candidate']
