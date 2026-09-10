from __future__ import annotations
"""v2666 synthetic rehearsal drift review."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2666.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_rehearsal_drift_review(comparison:Mapping[str,Any])->dict[str,Any]:
 trend=str(comparison.get('trend') or 'insufficient');review=trend in {'worsening','unstable'}
 out={'ok':bool(comparison.get('ok')),'contract_version':CONTRACT_VERSION,'project_id':str(comparison.get('project_id') or '')[:120],'trend':trend,'operator_review_required':review,'recommended_action':'review_project_risk_or_preflight' if review else ('continue_rehearsal_observation' if trend=='insufficient' else 'no_rehearsal_drift_action'),'synthetic_evidence_only':True,'queue_mutated':False,'project_started':False,'real_strategy_weights_mutated':False,'authority_granted':False};out['drift_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_rehearsal_drift_review']
