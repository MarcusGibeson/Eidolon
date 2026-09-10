from __future__ import annotations
"""v2672 response-grounding policy joining intent with memory/turn evidence sufficiency."""
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2672.0';MAX_PROMPT=900
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_response_grounding_policy(response_intent:Mapping[str,Any],retrieval_sufficiency:Mapping[str,Any],immediate_grounding:Mapping[str,Any]|None=None)->dict[str,Any]:
 ig=immediate_grounding if isinstance(immediate_grounding,Mapping) else {};state=str(retrieval_sufficiency.get('state') or 'no_useful_memory');preserve=bool(retrieval_sufficiency.get('should_preserve_uncertainty')) or bool(ig.get('historical_uncertainty_required'));correction=state=='grounded_correction' or bool(ig.get('current_message_correction'));attributable=state in {'grounded_correction','grounded_relevant_memory'} or bool(ig.get('attributable_memory_available') or ig.get('active_fact_grounded'))
 assertiveness='grounded' if attributable and not preserve else ('cautious' if preserve else 'current_turn_only')
 out={'ok':True,'contract_version':CONTRACT_VERSION,'selected_intent':str(response_intent.get('selected_intent') or 'direct_answer')[:40],'memory_state':state,'assertiveness':assertiveness,'preserve_uncertainty':preserve,'correction_precedence':correction,'personal_memory_reference_permitted':attributable,'unsupported_memory_claims_forbidden':True,'execution_claims_forbidden':bool((response_intent.get('construction_directives') or {}).get('execution_claims_forbidden')),'current_message_precedence':True,'authority_granted':False};out['policy_digest']=_digest(out);return out
def response_grounding_prompt_section(policy:Mapping[str,Any])->str:
 payload={'assertiveness':str(policy.get('assertiveness') or 'cautious'),'preserve_uncertainty':bool(policy.get('preserve_uncertainty')),'correction_precedence':bool(policy.get('correction_precedence')),'personal_memory_reference_permitted':bool(policy.get('personal_memory_reference_permitted')),'unsupported_memory_claims_forbidden':True,'current_message_precedence':True,'authority':'none'};text='<response_grounding data_only="true" authority="none">\n'+json.dumps(payload,sort_keys=True,separators=(',',':'))+'\nUse this only to calibrate grounding; do not infer missing memories or action authority.\n</response_grounding>';return text[:MAX_PROMPT]
__all__=['CONTRACT_VERSION','build_response_grounding_policy','response_grounding_prompt_section']
