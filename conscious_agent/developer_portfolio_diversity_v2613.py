from __future__ import annotations
"""v2613 advisory diversity/risk inspection for project portfolios."""
from typing import Any, Mapping
import hashlib,json,collections
CONTRACT_VERSION='v2613.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def inspect_portfolio_diversity(portfolio:Mapping[str,Any])->dict[str,Any]:
 rows=[x for x in portfolio.get('candidates') or [] if isinstance(x,Mapping)];counts=collections.Counter(str(x.get('strategy_code') or 'unspecified') for x in rows);high=sum(float(x.get('risk') or 0)>=.7 for x in rows);n=len(rows);concentration=max(counts.values())/n if n and counts else 0
 state='empty' if not n else ('concentrated' if concentration>.7 else 'balanced')
 out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'strategy_count':len(counts),'largest_strategy_share':round(concentration,3),'high_risk_candidate_count':high,'diversification_advisory':'broaden_candidate_mix' if state=='concentrated' else 'no_diversity_warning','candidate_set_modified':False,'project_removed':False,'priority_changed':False,'authority_granted':False};out['diversity_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','inspect_portfolio_diversity']
