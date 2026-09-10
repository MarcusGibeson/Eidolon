from __future__ import annotations
"""v2649 deterministic scenario matrix for inert project lifecycle rehearsal."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2649.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_simulation_scenarios(preflight:Mapping[str,Any])->dict[str,Any]:
 rows=[{'scenario':'nominal','reason':'baseline_success_path'}]
 checks=preflight.get('checks') or {}
 if not checks.get('verification_not_degraded',True) or str(preflight.get('verification_state') or '') in {'attention','degraded'}:rows.append({'scenario':'verification_failure','reason':'verification_health_risk'})
 if not checks.get('no_blockers',True):rows.append({'scenario':'blocked_dependency','reason':'current_blocker_present'})
 # Always rehearse one bounded failure mode even when nominal, so success-path optimism is not the only evidence.
 if len(rows)==1:rows.append({'scenario':'verification_failure','reason':'bounded_adversarial_rehearsal'})
 out={'ok':bool(preflight.get('ok')),'contract_version':CONTRACT_VERSION,'scenarios':rows[:4],'scenario_count':min(4,len(rows)),'includes_nominal':True,'includes_adversarial':len(rows)>1,'simulation_only':True,'automatic_execution_permitted':False,'authority_granted':False};out['scenario_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_simulation_scenarios']
