from __future__ import annotations
"""v2573 structural sufficiency signal for precision memory retrieval."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2573.0'
AUTHORITY={'memory_mutation_authorized':False,'provider_contact_authorized':False,'response_claim_authorized':False,'action_execution_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def assess_memory_retrieval_sufficiency(projection:Mapping[str,Any])->dict[str,Any]:
    rows=list(projection.get('selected_memory_records') or [])
    precision=projection.get('precision_diagnostics') if isinstance(projection.get('precision_diagnostics'),Mapping) else {}
    corrections=sum(bool(r.get('operator_correction') or r.get('explicit_correction') or r.get('correction_of')) for r in rows if isinstance(r,Mapping))
    if corrections: state='grounded_correction'
    elif rows and precision.get('precise_evidence_present'): state='grounded_relevant_memory'
    elif rows: state='weak_context_only'
    else: state='no_useful_memory'
    out={'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'selected_count':len(rows),'explicit_correction_count':corrections,'should_preserve_uncertainty':state in {'weak_context_only','no_useful_memory'},'should_not_invent_memory':True,'raw_memory_text_stored':False,**AUTHORITY};out['sufficiency_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','assess_memory_retrieval_sufficiency']
