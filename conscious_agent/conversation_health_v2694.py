from __future__ import annotations
"""v2694 read-only conversation health from structural quality evidence."""
from pathlib import Path
from typing import Any,Mapping
import hashlib,json
try:
 from response_grounding_learning_observability_v2680 import build_response_grounding_learning_observability
 from response_grounding_audit_observability_v2686 import load_response_grounding_output_audit_observability
 from conversation_target_outcome_history_v2691 import build_conversation_target_learning_profile
 from memory_retrieval_observability_v2576 import load_memory_retrieval_observability
 from conversation_context_observability_v2590 import load_conversation_context_observability
except ImportError:
 from response_grounding_learning_observability_v2680 import build_response_grounding_learning_observability
 from response_grounding_audit_observability_v2686 import load_response_grounding_output_audit_observability
 from conversation_target_outcome_history_v2691 import build_conversation_target_learning_profile
 from memory_retrieval_observability_v2576 import load_memory_retrieval_observability
 from conversation_context_observability_v2590 import load_conversation_context_observability
CONTRACT_VERSION='v2694.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_conversation_health(runtime_root:str|Path|None=None)->dict[str,Any]:
 g=build_response_grounding_learning_observability(runtime_root);a=load_response_grounding_output_audit_observability(runtime_root);t=build_conversation_target_learning_profile(runtime_root);m=load_memory_retrieval_observability(runtime_root);c=load_conversation_context_observability(runtime_root)
 mf=m.get('feedback') if isinstance(m.get('feedback'),Mapping) else {}
 concerns=[]
 if g.get('review_due'): concerns.append('response_grounding_review_due')
 if int(a.get('concern_event_count') or 0)>=3: concerns.append('repeated_output_grounding_concerns')
 if str(t.get('state'))=='conversation_coherence_review_due': concerns.append('conversation_target_coherence_review_due')
 if str(mf.get('state')) in {'weak_context_only','no_useful_memory'} and not bool(mf.get('should_preserve_uncertainty')): concerns.append('weak_memory_without_uncertainty_restraint')
 if str(c.get('state'))=='budget_constrained': concerns.append('context_budget_pressure')
 state='degraded' if len(concerns)>=3 else ('attention' if concerns else 'nominal')
 out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'concern_count':len(concerns),'concerns':concerns,'grounding_state':str(g.get('state') or 'no_history'),'target_state':str(t.get('state') or 'no_history'),'memory_state':str(mf.get('state') or 'no_data'),'context_state':str(c.get('state') or 'no_data'),'automatic_policy_change':False,'response_mutated':False,'provider_contacted':False,'raw_conversation_text_stored':False,'authority_granted':False};out['health_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_conversation_health']
