from __future__ import annotations
"""v2652 content-minimized developer evidence from inert lifecycle rehearsal."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2652.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_simulation_developer_evidence(*,simulation_health:Mapping[str,Any],simulation_review:Mapping[str,Any],project_id:str,project_digest:str)->dict[str,Any]:
 state=str(simulation_health.get('state') or 'insufficient');failures=[str(x)[:120] for x in simulation_review.get('failure_modes') or []][:8]
 confidence='moderate' if state=='nominal' else ('low' if state=='attention' else 'insufficient')
 out={'ok':bool(simulation_health.get('ok')) and bool(simulation_review.get('ok')),'contract_version':CONTRACT_VERSION,'project_id':str(project_id or '')[:120],'project_digest':str(project_digest or '')[:64],'simulation_health_state':state,'simulation_confidence':confidence,'failure_modes':failures,'scenario_count':int(simulation_health.get('scenario_count') or 0),'synthetic_evidence_only':True,'real_verification_substituted':False,'real_execution_substituted':False,'operator_review_required':True,'project_started':False,'authority_granted':False};out['evidence_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_simulation_developer_evidence']
