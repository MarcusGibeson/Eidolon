from __future__ import annotations
"""v2644 inert project lifecycle simulation contract over exact preflight evidence."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2644.0';STAGES=('queued','preflight_review','simulated_execution','simulated_verification','simulated_outcome_review')
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_lifecycle_simulation(preflight:Mapping[str,Any])->dict[str,Any]:
 eligible=bool(preflight.get('eligible_for_operator_start_review'))
 stages=[{'stage':s,'simulated':True,'executed':False} for s in STAGES] if eligible else []
 out={'ok':eligible,'contract_version':CONTRACT_VERSION,'project_id':str(preflight.get('project_id') or '')[:120] if eligible else '','project_digest':str(preflight.get('project_digest') or '')[:64] if eligible else '','preflight_digest':str(preflight.get('preflight_digest') or '')[:64],'stages':stages,'simulation_only':True,'provider_contacted':False,'tool_execution_authorized':False,'source_mutated':False,'project_started':False,'campaign_started':False,'authority_granted':False};out['simulation_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_lifecycle_simulation']
