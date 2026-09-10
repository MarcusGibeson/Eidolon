from __future__ import annotations
"""Content-free conversation latency phase accounting and provider warm-state tracking."""
from dataclasses import dataclass,asdict
import hashlib,json,threading,time
from typing import Any,Mapping
_LOCK=threading.Lock(); _WARM=set(); SCHEMA_VERSION='1'

def _key(provider:str,endpoint:str,model:str)->str:
    raw='|'.join((str(provider or '').strip().lower(),str(endpoint or '').strip(),str(model or '').strip()))
    return hashlib.sha256(raw.encode()).hexdigest()

def classify_provider_start(provider:str,endpoint:str,model:str)->str:
    key=_key(provider,endpoint,model)
    with _LOCK: return 'warm' if key in _WARM else 'cold'

def mark_provider_warm(provider:str,endpoint:str,model:str)->None:
    with _LOCK: _WARM.add(_key(provider,endpoint,model))

def clear_provider_warm_registry()->None:
    with _LOCK: _WARM.clear()

def build_conversation_timing_receipt(timings:Mapping[str,Any],*,provider_start_kind:str='not_contacted',prompt_tokens:int=0)->dict[str,Any]:
    def n(k):
        v=timings.get(k)
        return int(v) if isinstance(v,(int,float)) and v>=0 else None
    pre=n('pre_provider'); provider=n('provider'); total=n('total'); context=n('context_build'); first_transport=n('first_transport_chunk'); first_visible=n('first_visible_token'); commit=n('commit')
    if commit is None and total is not None and pre is not None and provider is not None:
        commit=max(0,total-pre-provider)
    provider_wait=(max(0,first_transport-pre) if first_transport is not None and pre is not None else None)
    stream_to_visible=(max(0,first_visible-first_transport) if first_visible is not None and first_transport is not None else None)
    eidolon_overhead=(max(0,total-provider) if total is not None and provider is not None else total)
    row={
      'schema_version':SCHEMA_VERSION,'provider_start_kind':provider_start_kind if provider_start_kind in {'cold','warm','not_contacted'} else 'unknown',
      'estimated_prompt_tokens':max(0,int(prompt_tokens or 0)),'context_assembly_ms':context,'pre_provider_total_ms':pre,
      'provider_wait_to_first_transport_ms':provider_wait,'stream_to_first_visible_ms':stream_to_visible,'provider_total_ms':provider,
      'commit_ms':commit,'first_visible_ms':first_visible,'total_ms':total,'eidolon_overhead_excluding_provider_ms':eidolon_overhead,
      'provider_latency_separated':provider is not None,'content_free':True,'contains_prompt':False,'contains_response':False,
    }
    row['receipt_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return row
