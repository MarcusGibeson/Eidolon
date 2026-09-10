from __future__ import annotations
"""v2571 conflict-aware prompt budget over precision-selected memories."""
from typing import Any, Mapping
import hashlib,json
CONTRACT_VERSION='v2571.0'; MAX_MEMORY_PROMPT_CHARS=1800
AUTHORITY={'memory_mutation_authorized':False,'memory_deletion_authorized':False,'provider_contact_authorized':False,'action_execution_authorized':False,'independent_authority_granted':False}
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _text(row:Mapping[str,Any])->str:return ' '.join(str(row.get(k) or '') for k in ('content','summary','title','name','description','value')).strip()[:1200]
def apply_memory_retrieval_budget(projection:Mapping[str,Any], *, max_chars:int=MAX_MEMORY_PROMPT_CHARS)->dict[str,Any]:
    budget=max(256,min(4000,int(max_chars or MAX_MEMORY_PROMPT_CHARS))); rows=[dict(r) for r in projection.get('selected_memory_records') or [] if isinstance(r,Mapping)]
    # Prefer explicit corrections, then current/recent evidence, while retaining stable input order inside equal ranks.
    def priority(item):
        i,row=item; correction=bool(row.get('operator_correction') or row.get('explicit_correction') or row.get('correction_of')); current=bool(row.get('current')) or str(row.get('age_band') or '').lower() in {'current','recent'}
        return (0 if correction else 1,0 if current else 1,i)
    ordered=sorted(enumerate(rows),key=priority)
    kept=[];fact_seen=set();used=0;conflicts=budget_suppressed=0
    for _,row in ordered:
        fact=str(row.get('fact_key') or row.get('subject_key') or row.get('preference_key') or '').strip().lower()[:160]
        correction=bool(row.get('operator_correction') or row.get('explicit_correction') or row.get('correction_of'))
        if fact and fact in fact_seen and not correction:
            conflicts+=1;continue
        size=len(_text(row))
        if kept and used+size>budget:
            budget_suppressed+=1;continue
        if not kept and size>budget:
            # Preserve one most-important row but bounded downstream text remains the caller's responsibility.
            kept.append(row);used=min(size,budget);fact_seen.add(fact) if fact else None;continue
        kept.append(row);used+=size
        if fact: fact_seen.add(fact)
    diag={'contract_version':CONTRACT_VERSION,'input_count':len(rows),'selected_count':len(kept),'prompt_char_budget':budget,'estimated_prompt_chars':used,'fact_conflict_suppressed_count':conflicts,'budget_suppressed_count':budget_suppressed,'memory_mutated':False,'provider_contacted':False,'raw_memory_text_stored':False,**AUTHORITY};diag['diagnostics_digest']=_digest(diag)
    out=dict(projection);out['selected_memory_records']=kept;out['prompt_budget_diagnostics']=diag;out['prompt_budget_contract_version']=CONTRACT_VERSION;return out
__all__=['CONTRACT_VERSION','MAX_MEMORY_PROMPT_CHARS','apply_memory_retrieval_budget']
