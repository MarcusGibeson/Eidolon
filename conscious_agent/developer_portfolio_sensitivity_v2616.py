from __future__ import annotations
"""v2616 ranking-margin/sensitivity evidence for advisory portfolios."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2616.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def inspect_portfolio_ranking_sensitivity(ranking:Mapping[str,Any])->dict[str,Any]:
 rows=[x for x in ranking.get('ranked_candidates') or [] if isinstance(x,Mapping)];margin=1.0
 if len(rows)>=2:margin=max(0,float(rows[0].get('advisory_score') or 0)-float(rows[1].get('advisory_score') or 0))
 state='no_candidates' if not rows else ('fragile' if len(rows)>1 and margin<.05 else ('close' if len(rows)>1 and margin<.12 else 'clear'))
 out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'leader_margin':round(margin,4),'leading_project_id':rows[0].get('project_id') if rows else '','operator_should_review_close_ranking':state in {'fragile','close'},'ranking_changed':False,'project_selected':False,'campaign_started':False,'authority_granted':False};out['sensitivity_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','inspect_portfolio_ranking_sensitivity']
