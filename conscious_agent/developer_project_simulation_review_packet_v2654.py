from __future__ import annotations
"""v2654 operator review packet combining live preflight and synthetic rehearsal evidence."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2654.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_simulation_informed_operator_packet(readiness:Mapping[str,Any],evidence:Mapping[str,Any])->dict[str,Any]:
 eligible=bool(readiness.get('eligible_for_operator_start_trial_review'))
 out={'ok':bool(readiness.get('ok')),'contract_version':CONTRACT_VERSION,'project_id':str(readiness.get('project_id') or '')[:120],'project_digest':str(readiness.get('project_digest') or '')[:64],'eligible_for_operator_start_trial_review':eligible,'simulation_confidence':str(evidence.get('simulation_confidence') or 'insufficient'),'failure_modes':[str(x)[:120] for x in evidence.get('failure_modes') or []][:8],'next_operator_boundary':'project_start_trial_selection' if eligible else 'simulation_or_preflight_remediation','synthetic_evidence_disclosed':True,'review_only':True,'start_authorization_issued':False,'project_started':False,'campaign_started':False,'authority_granted':False};out['packet_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_simulation_informed_operator_packet']
