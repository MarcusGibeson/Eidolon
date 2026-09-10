from __future__ import annotations
"""v2569 precision arbitration above retained v1166 memory retrieval.

The retained relevance/staleness gate remains authoritative. This layer only
narrows already-selected records to reduce prompt stuffing and duplicate weak
context. It never resurrects a suppressed record or mutates memory.
"""
from typing import Any, Mapping
import hashlib,json
from memory_retrieval_policy_execution_v2730_9_2 import load_memory_retrieval_policy
CONTRACT_VERSION='v2569.0'; MAX_PRECISE_SELECTED=8; MAX_FALLBACK_SELECTED=4
AUTHORITY={'memory_mutation_authorized':False,'memory_deletion_authorized':False,'provider_contact_authorized':False,'action_execution_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _content_key(row:Mapping[str,Any])->str:
    text=' '.join(str(row.get(k) or '') for k in ('content','summary','title','name','description','value')).strip().lower()[:1200]
    return hashlib.sha256(text.encode()).hexdigest() if text else _digest({'id':row.get('id'),'type':row.get('type'),'fact_key':row.get('fact_key')})
def refine_memory_retrieval(base:Mapping[str,Any])->dict[str,Any]:
    records=list(base.get('selected_memory_records') or [])
    decisions=[d for d in list(base.get('decisions') or []) if isinstance(d,Mapping) and d.get('selected')]
    # selected decisions retain original candidate indexes; selected records preserve rank order.
    reasons=[str(d.get('reason') or '') for d in decisions]
    has_precise=any(r in {'explicit_correction','literal_relevance','supported_relevance'} for r in reasons)
    policy=load_memory_retrieval_policy()
    limit=int(policy.get("precise_selected_limit") or MAX_PRECISE_SELECTED) if has_precise else int(policy.get("fallback_selected_limit") or MAX_FALLBACK_SELECTED)
    kept=[];seen=set();dropped_duplicate=dropped_weak=0
    for i,row in enumerate(records):
        if not isinstance(row,Mapping): continue
        reason=reasons[i] if i < len(reasons) else 'bounded_context'
        if has_precise and reason not in {'explicit_correction','literal_relevance','supported_relevance'}:
            dropped_weak+=1;continue
        key=_content_key(row)
        if key in seen:
            dropped_duplicate+=1;continue
        if len(kept)>=limit:
            dropped_weak+=1;continue
        seen.add(key);kept.append(dict(row))
    diagnostics={'contract_version':CONTRACT_VERSION,'base_selected_count':len(records),'selected_count':len(kept),'precise_evidence_present':has_precise,'selection_limit':limit,'policy_revision':int(policy.get('revision') or 0),'duplicate_suppressed_count':dropped_duplicate,'weak_context_suppressed_count':dropped_weak,'memory_mutated':False,'provider_contacted':False,'raw_memory_text_stored':False,**AUTHORITY}
    diagnostics['diagnostics_digest']=_digest(diagnostics)
    out=dict(base);out['selected_memory_records']=kept;out['precision_diagnostics']=diagnostics;out['precision_contract_version']=CONTRACT_VERSION;return out
__all__=['CONTRACT_VERSION','refine_memory_retrieval']
