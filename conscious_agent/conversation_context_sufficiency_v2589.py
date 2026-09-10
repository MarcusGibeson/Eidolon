from __future__ import annotations
"""v2589 structural sufficiency judgement over prompt attribution."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2589.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def assess_context_sufficiency(attribution:Mapping[str,Any], arbitration:Mapping[str,Any])->dict[str,Any]:
    pressure=float(attribution.get('budget_pressure') or 0.0);mstate=str(attribution.get('memory_retrieval_state') or 'unknown')
    history=int(attribution.get('history_turns_included') or 0);mem=int(attribution.get('memories_included') or 0)
    if pressure>=.97: state='budget_constrained'
    elif mstate in {'grounded_correction','grounded_relevant_memory'} or history>0 or mem>0: state='context_supported'
    elif mstate in {'weak_context_only','no_useful_memory'}: state='sparse_preserve_uncertainty'
    else: state='current_turn_only'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'budget_pressure':round(pressure,4),'advisory_count':int(arbitration.get('advisory_count') or 0),'should_preserve_uncertainty':state in {'sparse_preserve_uncertainty','budget_constrained'} or bool(attribution.get('memory_uncertainty_preserved')),'context_rebuild_required':False,'automatic_context_expansion_permitted':False,'automatic_context_truncation_permitted':False,'raw_content_stored':False,'authority_granted':False}
    out['sufficiency_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','assess_context_sufficiency']
