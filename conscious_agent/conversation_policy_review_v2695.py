from __future__ import annotations
from typing import Any,Mapping
import hashlib,json
CONTRACT_VERSION='v2695.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_conversation_policy_review_packet(health:Mapping[str,Any])->dict[str,Any]:
 needs=str(health.get('state')) in {'attention','degraded'} and int(health.get('concern_count') or 0)>0
 actions=[]
 for c in health.get('concerns') or []:
  if c=='response_grounding_review_due':actions.append('review_response_grounding_thresholds')
  elif c=='repeated_output_grounding_concerns':actions.append('review_post_generation_grounding_guard')
  elif c=='conversation_target_coherence_review_due':actions.append('review_target_and_repetition_policy')
  elif c=='context_budget_pressure':actions.append('review_context_lane_budgeting')
  elif c=='weak_memory_without_uncertainty_restraint':actions.append('review_memory_uncertainty_boundary')
 out={'ok':True,'contract_version':CONTRACT_VERSION,'review_required':needs,'state':'operator_review_required' if needs else 'no_review_required','action_codes':actions,'health_digest':str(health.get('health_digest') or '')[:64],'automatic_policy_change':False,'automatic_prompt_change':False,'automatic_response_rewrite':False,'provider_contacted':False,'authority_granted':False};out['review_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_conversation_policy_review_packet']
