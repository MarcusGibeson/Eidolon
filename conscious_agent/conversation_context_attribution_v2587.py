from __future__ import annotations
"""v2587 content-free attribution for the already-built conversation prompt."""
from typing import Any, Mapping
import hashlib, json
CONTRACT_VERSION='v2587.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def build_conversation_context_attribution(metrics:Mapping[str,Any], memory_feedback:Mapping[str,Any]|None=None)->dict[str,Any]:
    budget=max(0,int(metrics.get('input_budget_tokens') or 0));used=max(0,int(metrics.get('estimated_prompt_tokens') or 0));headroom=max(0,budget-used)
    included=tuple(str(x)[:64] for x in (metrics.get('context_lanes_included') or metrics.get('prompt_section_categories_included') or ()))
    omitted=tuple(str(x)[:64] for x in (metrics.get('context_lanes_omitted') or metrics.get('prompt_section_categories_omitted') or ()))
    memory=memory_feedback if isinstance(memory_feedback,Mapping) else {}
    pressure=0.0 if budget<=0 else min(1.0,used/max(1,budget))
    out={'ok':True,'contract_version':CONTRACT_VERSION,'input_budget_tokens':budget,'estimated_prompt_tokens':used,'headroom_tokens':headroom,'budget_pressure':round(pressure,4),'memory_candidates':int(metrics.get('memory_candidates') or 0),'memories_included':int(metrics.get('memories_included') or 0),'memories_omitted':int(metrics.get('memories_omitted') or 0),'history_turn_candidates':int(metrics.get('history_turn_candidates') or 0),'history_turns_included':int(metrics.get('history_turns_included') or 0),'history_turns_omitted':int(metrics.get('history_turns_omitted') or 0),'included_lanes':included,'omitted_lanes':omitted,'memory_retrieval_state':str(memory.get('state') or 'unknown')[:48],'memory_uncertainty_preserved':bool(memory.get('should_preserve_uncertainty')),'current_message_protected':True,'protected_instructions_preserved':True,'raw_prompt_stored':False,'raw_context_stored':False,'raw_memory_text_stored':False,'provider_contacted':False,'context_mutated':False,'authority_granted':False}
    out['attribution_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_conversation_context_attribution']
