from __future__ import annotations
"""v1191.6-v1191.8 content-free responsiveness and queue reliability evidence."""
import hashlib,json,re
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1191.8';SCHEMA_VERSION='1';MAX_ITEMS=128;MAX_BYTES=262144
DIGEST_RE=re.compile(r'^[0-9a-f]{64}$')
EVENTS={'interruption','restart','stale_work','provider_outage','starvation','fairness','privacy','latency'}
_FORBIDDEN=('prompt','conversation_text','message_text','memory_content','private_reasoning','raw_source','raw_patch','stdout','stderr','provider_payload','secret','credential','token_value','release_authority')
def _d(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _okd(v:object)->bool:return bool(DIGEST_RE.fullmatch(str(v or '').lower()))
def _private(v:object)->bool:
 if isinstance(v,Mapping):return any(any(x in str(k).lower() for x in _FORBIDDEN) or _private(z) for k,z in v.items())
 if isinstance(v,(list,tuple)):return any(_private(x) for x in v)
 return False
def create_reliability_observation(*,observation_id:str,queue_digest:str,unified_snapshot_digest:str,context_digest:str,event_class:str,foreground_sequence:int,background_sequences:Sequence[int],latency_budget_ms:int,observed_foreground_latency_ms:int,interruption_code:str='none',provider_available:bool=True,restart_generation:int=0)->dict[str,Any]:
 row={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'observation_id':str(observation_id or ''),'queue_digest':str(queue_digest or '').lower(),'unified_snapshot_digest':str(unified_snapshot_digest or '').lower(),'context_digest':str(context_digest or '').lower(),'event_class':str(event_class or ''),'foreground_sequence':int(foreground_sequence),'background_sequences':[int(x) for x in background_sequences],'latency_budget_ms':int(latency_budget_ms),'observed_foreground_latency_ms':int(observed_foreground_latency_ms),'interruption_code':str(interruption_code or ''),'provider_available':bool(provider_available),'restart_generation':int(restart_generation),'content_free':True,'execution_requested':False,'automatic_retry':False,'automatic_continuation':False,'cancellation_requested':False,'authority_requested':False}
 row['observation_digest']=_d(row);return row
def review_reliability_observation(*,observation:Mapping[str,Any],current_snapshot_digest:str,current_context_digest:str,current_queue_digest:str)->dict[str,Any]:
 o=dict(observation);errors=[]
 if len(json.dumps(o,sort_keys=True,separators=(',',':'),default=str).encode())>MAX_BYTES:errors.append('oversized_contract')
 if _private(o):errors.append('private_or_authority_content_present')
 claimed=str(o.pop('observation_digest','')).lower()
 if not _okd(claimed) or claimed!=_d(o):errors.append('tampered_observation')
 if o.get('contract_version')!=CONTRACT_VERSION:errors.append('contract_mismatch')
 if o.get('event_class') not in EVENTS:errors.append('unsupported_event_class')
 for f in ('queue_digest','unified_snapshot_digest','context_digest'):
  if not _okd(o.get(f)):errors.append('invalid_'+f)
 if o.get('unified_snapshot_digest')!=str(current_snapshot_digest or '').lower():errors.append('stale_unified_snapshot')
 if o.get('context_digest')!=str(current_context_digest or '').lower():errors.append('stale_context')
 if o.get('queue_digest')!=str(current_queue_digest or '').lower():errors.append('stale_queue')
 seq=list(o.get('background_sequences') or [])
 if len(seq)>MAX_ITEMS:errors.append('oversized_queue')
 if any(x<0 for x in seq) or len(seq)!=len(set(seq)):errors.append('invalid_background_sequences')
 if int(o.get('foreground_sequence',-1))<0:errors.append('invalid_foreground_sequence')
 budget=int(o.get('latency_budget_ms',0));observed=int(o.get('observed_foreground_latency_ms',-1))
 if budget<1 or budget>60000 or observed<0:errors.append('malformed_latency_budget')
 if int(o.get('restart_generation',-1))<0:errors.append('invalid_restart_generation')
 if o.get('event_class')=='provider_outage' and o.get('provider_available') is not False:errors.append('provider_outage_truth_mismatch')
 if o.get('event_class')!='provider_outage' and o.get('provider_available') is not True:errors.append('provider_availability_truth_mismatch')
 for f in ('execution_requested','automatic_retry','automatic_continuation','cancellation_requested','authority_requested'):
  if o.get(f) is not False:errors.append('hidden_execution_or_authority_claim')
 if o.get('content_free') is not True:errors.append('privacy_contract_violation')
 fg=int(o.get('foreground_sequence',0));foreground_first=all(fg<x for x in seq) if seq else True
 latency_ok=observed<=budget if budget>0 and observed>=0 else False
 starvation_free=(not seq) or (max(seq)-min(seq)<MAX_ITEMS)
 fair_order=seq==sorted(seq)
 errors=sorted(set(errors));ok=not errors
 out={'schema_version':SCHEMA_VERSION,'contract_version':CONTRACT_VERSION,'status':'reliability_evidence_ready' if ok else 'blocked','errors':errors,'error_count':len(errors),'event_class':o.get('event_class',''),'foreground_first':foreground_first,'foreground_latency_within_budget':latency_ok,'starvation_free_evidence':starvation_free,'fair_order_evidence':fair_order,'restart_reconciled':bool(ok and o.get('event_class')=='restart'),'interruption_classified':bool(ok and o.get('event_class')=='interruption'),'provider_outage_deferred':bool(ok and o.get('event_class')=='provider_outage'),'content_free':True,'execution_invoked':False,'automatic_retry':False,'automatic_continuation':False,'real_work_cancelled':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'source_modified':False,'runtime_modified':False,'authority_granted':False}
 out['reliability_digest']=_d(out);return out
def public_reliability_summary(r:Mapping[str,Any])->dict[str,Any]:
 return {k:r.get(k) for k in ('contract_version','status','event_class','foreground_first','foreground_latency_within_budget','starvation_free_evidence','fair_order_evidence','restart_reconciled','interruption_classified','provider_outage_deferred','content_free','authority_granted')}
