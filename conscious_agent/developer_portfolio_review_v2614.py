from __future__ import annotations
"""v2614 operator-review packet for outcome-aware developer portfolios."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2614.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_portfolio_review_packet(portfolio:Mapping[str,Any],ranking:Mapping[str,Any],diversity:Mapping[str,Any])->dict[str,Any]:
 rows=[]
 for r in ranking.get('ranked_candidates') or []:
  if isinstance(r,Mapping): rows.append({'project_id':r.get('project_id'),'project_digest':r.get('project_digest'),'strategy_code':r.get('strategy_code'),'advisory_score':r.get('advisory_score'),'historical_confidence_factor':r.get('historical_confidence_factor')})
 out={'ok':True,'contract_version':CONTRACT_VERSION,'portfolio_digest':portfolio.get('portfolio_digest'),'ranking_digest':ranking.get('ranking_digest'),'diversity_digest':diversity.get('diversity_digest'),'ranked_candidates':rows[:16],'leading_project_id':ranking.get('leading_project_id') or '','diversity_state':diversity.get('state'),'operator_selection_required':bool(rows),'selected_project_id':'','project_selected':False,'campaign_started':False,'source_mutation_authorized':False,'automatic_priority_change_permitted':False,'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_portfolio_review_packet']
