from __future__ import annotations
"""v2670 sensitivity note for portfolio choices under uncertain synthetic rehearsal evidence."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2670.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_rehearsal_selection_sensitivity(annotations:Mapping[str,Any],review:Mapping[str,Any])->dict[str,Any]:
 rows=list(annotations.get('projects') or []);unknown=sum(1 for r in rows if isinstance(r,Mapping) and r.get('rehearsal_risk')=='unknown');elevated=len(review.get('elevated_risk_project_ids') or []);state='fragile' if elevated else ('incomplete' if unknown else 'bounded')
 out={'ok':bool(annotations.get('ok')) and bool(review.get('ok')),'contract_version':CONTRACT_VERSION,'state':state,'unknown_count':unknown,'elevated_count':elevated,'selection_confidence':'low' if state=='fragile' else ('moderate' if state=='incomplete' else 'bounded'),'operator_selection_still_required':True,'synthetic_evidence_only':True,'automatic_project_selection_permitted':False,'portfolio_order_changed':False,'authority_granted':False};out['sensitivity_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_rehearsal_selection_sensitivity']
