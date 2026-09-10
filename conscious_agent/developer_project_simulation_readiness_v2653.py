from __future__ import annotations
"""v2653 advisory start-readiness bridge incorporating simulation evidence."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2653.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_simulation_informed_start_readiness(preflight:Mapping[str,Any],evidence:Mapping[str,Any])->dict[str,Any]:
 binding=str(preflight.get('project_id') or '')==str(evidence.get('project_id') or '') and str(preflight.get('project_digest') or '')==str(evidence.get('project_digest') or '')
 pre=bool(preflight.get('eligible_for_operator_start_review'));sim_ok=str(evidence.get('simulation_health_state') or '')=='nominal';eligible=binding and pre and sim_ok
 reasons=[]
 if not binding:reasons.append('project_binding_mismatch')
 if not pre:reasons.append('preflight_not_ready')
 if not sim_ok:reasons.append('simulation_requires_attention')
 out={'ok':binding and bool(evidence.get('ok')),'contract_version':CONTRACT_VERSION,'project_id':str(preflight.get('project_id') or '')[:120] if binding else '','project_digest':str(preflight.get('project_digest') or '')[:64] if binding else '','eligible_for_operator_start_trial_review':eligible,'reasons':reasons,'simulation_confidence':str(evidence.get('simulation_confidence') or 'insufficient'),'real_verification_still_required':True,'operator_start_authorization_required':True,'automatic_project_start_permitted':False,'campaign_started':False,'authority_granted':False};out['readiness_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_simulation_informed_start_readiness']
