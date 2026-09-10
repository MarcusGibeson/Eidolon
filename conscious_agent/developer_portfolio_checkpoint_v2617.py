from __future__ import annotations
"""v2617 consolidated outcome-aware developer portfolio review."""
from typing import Any, Mapping, Sequence
import hashlib,json
from developer_portfolio_contract_v2611 import build_developer_portfolio_candidates
from developer_portfolio_scoring_v2612 import score_developer_portfolio
from developer_portfolio_diversity_v2613 import inspect_portfolio_diversity
from developer_portfolio_review_v2614 import build_portfolio_review_packet
from developer_portfolio_conflicts_v2615 import inspect_portfolio_conflicts
from developer_portfolio_sensitivity_v2616 import inspect_portfolio_ranking_sensitivity
CONTRACT_VERSION='v2617.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_developer_portfolio_review(rows:Sequence[Mapping[str,Any]],annotations:Mapping[str,Any]|None=None)->dict[str,Any]:
 p=build_developer_portfolio_candidates(rows);r=score_developer_portfolio(p,annotations);d=inspect_portfolio_diversity(p);c=inspect_portfolio_conflicts(rows);s=inspect_portfolio_ranking_sensitivity(r);review=build_portfolio_review_packet(p,r,d)
 out={'ok':True,'contract_version':CONTRACT_VERSION,'portfolio':p,'ranking':r,'diversity':d,'conflicts':c,'sensitivity':s,'review':review,'operator_selection_required':bool(p.get('candidate_count')),'automatic_project_selection_permitted':False,'campaign_start_authorized':False,'source_mutation_authorized':False,'authority_granted':False};out['checkpoint_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_developer_portfolio_review']
