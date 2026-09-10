from __future__ import annotations
"""v2612 outcome-aware advisory portfolio scoring."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2612.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def score_developer_portfolio(portfolio:Mapping[str,Any],annotations:Mapping[str,Any]|None=None)->dict[str,Any]:
 factors={str(x.get('strategy_code')):float(x.get('confidence_factor') or 1) for x in (annotations or {}).get('annotations') or [] if isinstance(x,Mapping)};rows=[]
 for c in portfolio.get('candidates') or []:
  if not isinstance(c,Mapping):continue
  f=max(.4,min(1.1,factors.get(str(c.get('strategy_code')),1.0)));ev=float(c.get('expected_value') or 0);risk=float(c.get('risk') or 0);rev=float(c.get('reversibility') or 0);prio=float(c.get('operator_priority') or 0);ver=float(c.get('verification_confidence') or 0);eff=float(c.get('effort') or 0)
  score=.30*((ev+1)/2)*f+.25*prio+.15*ver+.10*rev+.10*(1-risk)+.10*(1/(1+eff))
  rows.append({'project_id':c.get('project_id'),'project_digest':c.get('project_digest'),'strategy_code':c.get('strategy_code'),'historical_confidence_factor':round(f,3),'advisory_score':round(max(0,min(1,score)),4),'operator_priority':prio,'score_is_advisory':True})
 rows.sort(key=lambda x:(-x['advisory_score'],str(x['project_id'])));out={'ok':True,'contract_version':CONTRACT_VERSION,'ranked_candidates':rows,'leading_project_id':rows[0]['project_id'] if rows else '','automatic_project_selection_permitted':False,'operator_priority_overridden':False,'campaign_started':False,'authority_granted':False};out['ranking_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','score_developer_portfolio']
