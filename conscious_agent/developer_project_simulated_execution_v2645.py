from __future__ import annotations
"""v2645 deterministic inert execution receipt for lifecycle rehearsal."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2645.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_simulated_execution_receipt(simulation:Mapping[str,Any],*,scenario:str='nominal')->dict[str,Any]:
 allowed={'nominal','verification_failure','blocked_dependency'};scenario=scenario if scenario in allowed else 'blocked_dependency';ok=bool(simulation.get('ok'))
 status='simulated_completed' if ok and scenario=='nominal' else ('simulated_verification_failed' if ok and scenario=='verification_failure' else 'simulated_blocked')
 out={'ok':ok,'contract_version':CONTRACT_VERSION,'project_id':str(simulation.get('project_id') or '')[:120],'project_digest':str(simulation.get('project_digest') or '')[:64],'simulation_digest':str(simulation.get('simulation_digest') or '')[:64],'scenario':scenario,'status':status,'simulated_files_changed':0,'simulated_commands_run':0,'simulated_network_calls':0,'real_execution_performed':False,'provider_contacted':False,'source_mutated':False,'project_started':False,'authority_granted':False};out['execution_receipt_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_simulated_execution_receipt']
