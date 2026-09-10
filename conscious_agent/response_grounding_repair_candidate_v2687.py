from __future__ import annotations
"""v2687 structural repair candidates for response-grounding audit concerns."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2687.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_grounding_repair_candidate(audit:Mapping[str,Any],policy:Mapping[str,Any],calibration:Mapping[str,Any])->dict[str,Any]:
 concerns=[str(x) for x in audit.get('concerns') or []]
 actions=[]
 if 'unsupported_personal_memory_claim_shape' in concerns: actions.append('regenerate_without_unsupported_personal_memory_claim_or_state_uncertainty')
 if 'execution_claim_without_authoritative_evidence_shape' in concerns: actions.append('remove_execution_completion_claim_or_bind_authoritative_receipt')
 state='repair_candidate_ready' if actions else 'no_repair_needed'
 out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'action_codes':actions,'concern_count':len(concerns),'audit_digest':str(audit.get('audit_digest') or '')[:64],'policy_digest':str(policy.get('policy_digest') or '')[:64],'calibration_digest':str(calibration.get('calibration_digest') or '')[:64],'candidate_only':True,'response_rewritten':False,'provider_contacted':False,'automatic_regeneration':False,'authority_granted':False};out['candidate_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_response_grounding_repair_candidate']
