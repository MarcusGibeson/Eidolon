from __future__ import annotations
"""v2647 comparative review over inert project lifecycle scenarios."""
from typing import Any,Mapping,Sequence
import hashlib,json
CONTRACT_VERSION='v2647.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_project_simulation_review(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
 valid=[r for r in rows[:8] if isinstance(r,Mapping) and r.get('synthetic_evidence_only')]
 states=[str(r.get('simulated_status') or '') for r in valid];failure_modes=[]
 if 'verification_failure' in states:failure_modes.append('verification_failure_requires_repair_or_review')
 if 'blocked' in states:failure_modes.append('dependency_block_requires_resolution')
 out={'ok':bool(valid),'contract_version':CONTRACT_VERSION,'scenario_count':len(valid),'simulated_states':states,'failure_modes':failure_modes,'nominal_path_observed':'success' in states,'operator_review_required':True,'simulation_only':True,'recommended_real_start_action':'review_failure_modes_before_authorization' if failure_modes else 'eligible_for_operator_start_review','automatic_project_start_permitted':False,'source_mutation_authorized':False,'authority_granted':False};out['simulation_review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_project_simulation_review']
