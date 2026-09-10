from __future__ import annotations
"""v1194.6-v1194.8 unified experience reliability and integration hardening."""
import hashlib,json
from typing import Any,Mapping
CONTRACT_VERSION='v1194.8'
EVENTS={'interruption','restart','stale_snapshot','stale_context','stale_focus','provider_outage','latency_budget','integration_drift'}
PRIVATE=('prompt','message','memory','secret','source_text','patch_text','stdout','stderr','provider_payload','private_reasoning')
def _d(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _hex(v:object)->bool:s=str(v or '');return len(s)==64 and all(c in '0123456789abcdef' for c in s)
def _private(v:object)->bool:
 if isinstance(v,Mapping):return any(any(t in str(k).lower() for t in PRIVATE) or _private(x) for k,x in v.items())
 if isinstance(v,(list,tuple)):return any(_private(x) for x in v)
 return False
def create_reliability_event(*,event_id:str,event_class:str,snapshot_digest:str,context_digest:str,focus_digest:str,artifact_digest:str,receipt_digest:str,latency_budget_ms:int,observed_latency_ms:int,sequence:int,previous_event_digest:str='')->dict[str,Any]:
 r={'contract_version':CONTRACT_VERSION,'event_id':event_id,'event_class':event_class,'snapshot_digest':snapshot_digest,'context_digest':context_digest,'focus_digest':focus_digest,'artifact_digest':artifact_digest,'receipt_digest':receipt_digest,'latency_budget_ms':latency_budget_ms,'observed_latency_ms':observed_latency_ms,'sequence':sequence,'previous_event_digest':previous_event_digest,'content_free':True,'recovery_executed':False,'automatic_continuation':False,'provider_contacted':False,'runtime_mutated':False,'authority_granted':False};r['event_digest']=_d(r);return r
def assess_unified_reliability(*,coordination:Mapping[str,Any],event:Mapping[str,Any],current_snapshot_digest:str,current_context_digest:str,current_focus_digest:str)->dict[str,Any]:
 e=dict(event);c=dict(coordination);errors=[]
 claimed=e.get('event_digest');u=dict(e);u.pop('event_digest',None)
 if claimed!=_d(u):errors.append('event_tamper')
 if _private([c,e]):errors.append('private_field')
 for f in ('snapshot_digest','context_digest','focus_digest','artifact_digest','receipt_digest'):
  if not _hex(e.get(f)):errors.append('malformed_'+f)
 if e.get('snapshot_digest')!=current_snapshot_digest:errors.append('stale_snapshot')
 if e.get('context_digest')!=current_context_digest:errors.append('stale_context')
 if e.get('focus_digest')!=current_focus_digest:errors.append('stale_focus')
 if e.get('event_class') not in EVENTS:errors.append('unsupported_event')
 if not isinstance(e.get('sequence'),int) or e.get('sequence')<0:errors.append('invalid_sequence')
 if not isinstance(e.get('latency_budget_ms'),int) or not 1<=e.get('latency_budget_ms')<=5000:errors.append('malformed_latency_budget')
 if not isinstance(e.get('observed_latency_ms'),int) or e.get('observed_latency_ms')<0:errors.append('malformed_observed_latency')
 if isinstance(e.get('observed_latency_ms'),int) and isinstance(e.get('latency_budget_ms'),int) and e['observed_latency_ms']>e['latency_budget_ms']:errors.append('latency_budget_exceeded')
 if c.get('foreground_path_available') is not True:errors.append('foreground_blocked')
 if c.get('original_evidence_preserved') is not True:errors.append('evidence_loss')
 if c.get('inherited_debt_visible') is not True:errors.append('debt_hidden')
 if c.get('execution_invoked') is not False or c.get('runtime_mutated') is not False or c.get('authority_granted') is not False:errors.append('integration_boundary_loss')
 for f in ('recovery_executed','automatic_continuation','provider_contacted','runtime_mutated','authority_granted'):
  if e.get(f) is not False:errors.append('forbidden_claim')
 errors=sorted(set(errors));status='reliability_ready' if not errors else 'blocked'
 r={'contract_version':CONTRACT_VERSION,'status':status,'event_class':e.get('event_class',''),'errors':errors,'error_count':len(errors),'content_free':True,'foreground_path_available':True,'original_evidence_preserved':True,'inherited_debt_visible':True,'latency_within_budget':'latency_budget_exceeded' not in errors,'recovery_review_required':e.get('event_class') in {'interruption','restart','provider_outage','integration_drift'},'recovery_executed':False,'automatic_continuation':False,'execution_invoked':False,'runtime_mutated':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'approval_consumed':False,'authority_granted':False};r['reliability_digest']=_d(r);return r
def public_reliability_summary(r:Mapping[str,Any])->dict[str,Any]:return {k:r.get(k) for k in ('contract_version','status','event_class','error_count','content_free','foreground_path_available','original_evidence_preserved','inherited_debt_visible','latency_within_budget','recovery_review_required','recovery_executed','execution_invoked','runtime_mutated','authority_granted','reliability_digest')}
