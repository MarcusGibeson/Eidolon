from __future__ import annotations
"""v2669 operator review over synthetic rehearsal risk across portfolio candidates."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2669.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_portfolio_rehearsal_review(annotations:Mapping[str,Any])->dict[str,Any]:
 rows=list(annotations.get('projects') or []);elevated=[str(r.get('project_id') or '') for r in rows if isinstance(r,Mapping) and r.get('rehearsal_risk')=='elevated'];unknown=[str(r.get('project_id') or '') for r in rows if isinstance(r,Mapping) and r.get('rehearsal_risk')=='unknown']
 out={'ok':bool(annotations.get('ok')),'contract_version':CONTRACT_VERSION,'elevated_risk_project_ids':elevated[:16],'unknown_risk_project_ids':unknown[:16],'operator_review_required':bool(elevated or unknown),'recommendation':'review_rehearsal_risk_before_selection' if elevated else ('rehearse_unassessed_candidates' if unknown else 'no_rehearsal_risk_objection'),'synthetic_evidence_only':True,'portfolio_ranking_mutated':False,'operator_priority_overridden':False,'automatic_project_selection_permitted':False,'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_portfolio_rehearsal_review']
