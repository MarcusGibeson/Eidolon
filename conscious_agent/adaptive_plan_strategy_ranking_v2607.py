from __future__ import annotations
"""v2607 advisory adaptive-plan ranking wrapper with historical strategy confidence."""
from typing import Any, Mapping, Sequence
import hashlib,json
try:
 from adaptive_plan_health_v2508 import rank_plan_candidates
except ImportError:
 from adaptive_plan_health_v2508 import rank_plan_candidates
CONTRACT_VERSION='v2607.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def rank_plan_candidates_with_strategy_evidence(rows:Sequence[Mapping[str,Any]],annotations:Mapping[str,Any])->dict[str,Any]:
 factors={str(x.get('strategy_code')):float(x.get('confidence_factor') or 1.0) for x in annotations.get('annotations') or [] if isinstance(x,Mapping)};adjusted=[]
 for row in rows[:24]:
  if not isinstance(row,Mapping):continue
  x=dict(row);code=str(x.get('strategy_code') or 'unspecified');base=max(0,min(1,float(x.get('confidence') or .5)));x['confidence']=round(max(0,min(1,base*factors.get(code,1.0))),4);x['strategy_confidence_factor']=round(factors.get(code,1.0),3);adjusted.append(x)
 ranked=rank_plan_candidates(adjusted);out={'ok':True,'contract_version':CONTRACT_VERSION,'ranked_plans':ranked.get('ranked_plans') or [],'leading_plan_id':ranked.get('leading_plan_id') or '','historical_strategy_evidence_applied':bool(factors),'comparison_is_advisory':True,'plans_reprioritized':False,'operator_priority_overridden':False,'plan_mutation_performed':False,'execution_authorized':False,'authority_granted':False};out['ranking_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','rank_plan_candidates_with_strategy_evidence']
