from __future__ import annotations
"""v2575 content-minimized feedback for memory retrieval use."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2575.0'
AUTHORITY={'memory_mutation_authorized':False,'provider_contact_authorized':False,'response_claim_authorized':False,'action_execution_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_memory_retrieval_feedback(projection:Mapping[str,Any])->dict[str,Any]:
    suff=projection.get('retrieval_sufficiency') if isinstance(projection.get('retrieval_sufficiency'),Mapping) else {}
    precision=projection.get('precision_diagnostics') if isinstance(projection.get('precision_diagnostics'),Mapping) else {}
    budget=projection.get('prompt_budget_diagnostics') if isinstance(projection.get('prompt_budget_diagnostics'),Mapping) else {}
    state=str(suff.get('state') or 'unknown')[:48]
    out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'selected_count':int(suff.get('selected_count') or budget.get('selected_count') or 0),'duplicate_suppressed_count':int(precision.get('duplicate_suppressed_count') or 0),'weak_context_suppressed_count':int(precision.get('weak_context_suppressed_count') or 0),'fact_conflict_suppressed_count':int(budget.get('fact_conflict_suppressed_count') or 0),'budget_suppressed_count':int(budget.get('budget_suppressed_count') or 0),'estimated_prompt_chars':int(budget.get('estimated_prompt_chars') or 0),'should_preserve_uncertainty':bool(suff.get('should_preserve_uncertainty')),'raw_memory_text_stored':False,**AUTHORITY};out['feedback_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','build_memory_retrieval_feedback']
