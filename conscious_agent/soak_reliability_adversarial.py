from __future__ import annotations
"""v1195.6-v1195.8 content-free soak reliability and adversarial hardening."""
import hashlib, json
from typing import Any, Mapping
CONTRACT_VERSION='v1195.8'
EVENTS={'restart_storm','resource_exhaustion','latency_degradation','provider_outage','queue_starvation','cancellation_race','privacy_attack','long_duration_drift'}
PRIVATE=('prompt','message','memory','secret','source_text','patch_text','stdout','stderr','provider_payload','private_reasoning','conversation')
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _hex(v:object)->bool:s=str(v or '');return len(s)==64 and all(c in '0123456789abcdef' for c in s)
def _private(v:object)->bool:
 if isinstance(v,Mapping):return any(any(t in str(k).lower() for t in PRIVATE) or _private(x) for k,x in v.items())
 if isinstance(v,(list,tuple)):return any(_private(x) for x in v)
 return False
def create_soak_reliability_event(*,event_id:str,event_class:str,soak_digest:str,plan_digest:str,terminal_interval_digest:str,snapshot_digest:str,context_digest:str,artifact_digest:str,receipt_digest:str,sequence:int,previous_event_digest:str='',restart_count:int=0,resource_percent:int=0,observed_latency_ms:int=0,latency_budget_ms:int=1000,starvation_cycles:int=0,cancellation_observations:int=0,drift_score:int=0)->dict[str,Any]:
 r={'contract_version':CONTRACT_VERSION,'event_id':event_id,'event_class':event_class,'soak_digest':soak_digest,'plan_digest':plan_digest,'terminal_interval_digest':terminal_interval_digest,'snapshot_digest':snapshot_digest,'context_digest':context_digest,'artifact_digest':artifact_digest,'receipt_digest':receipt_digest,'sequence':sequence,'previous_event_digest':previous_event_digest,'restart_count':restart_count,'resource_percent':resource_percent,'observed_latency_ms':observed_latency_ms,'latency_budget_ms':latency_budget_ms,'starvation_cycles':starvation_cycles,'cancellation_observations':cancellation_observations,'drift_score':drift_score,'content_free':True,'automatic_recovery':False,'automatic_retry':False,'cancellation_executed':False,'provider_contacted':False,'runtime_mutated':False,'authority_granted':False};r['event_digest']=_digest(r);return r
def assess_soak_reliability(*,soak_summary:Mapping[str,Any],progression_summary:Mapping[str,Any],event:Mapping[str,Any],current_snapshot_digest:str,current_context_digest:str,previous_event:Mapping[str,Any]|None=None)->dict[str,Any]:
 s,p,e=dict(soak_summary),dict(progression_summary),dict(event);errors=[]
 claimed=e.get('event_digest');u=dict(e);u.pop('event_digest',None)
 if claimed!=_digest(u):errors.append('event_tamper')
 if _private([s,p,e]):errors.append('private_field')
 for f in ('soak_digest','plan_digest','terminal_interval_digest','snapshot_digest','context_digest','artifact_digest','receipt_digest'):
  if not _hex(e.get(f)):errors.append('malformed_'+f)
 if e.get('soak_digest')!=s.get('soak_digest'):errors.append('stale_soak')
 if e.get('plan_digest')!=s.get('plan_digest'):errors.append('stale_plan')
 if e.get('terminal_interval_digest')!=s.get('terminal_interval_digest'):errors.append('stale_terminal_interval')
 if e.get('snapshot_digest')!=current_snapshot_digest:errors.append('stale_snapshot')
 if e.get('context_digest')!=current_context_digest:errors.append('stale_context')
 if e.get('event_class') not in EVENTS:errors.append('unsupported_event')
 if not isinstance(e.get('sequence'),int) or e.get('sequence')<0:errors.append('invalid_sequence')
 if previous_event is None:
  if e.get('sequence')!=0 or e.get('previous_event_digest'):errors.append('broken_lineage')
 else:
  if e.get('sequence')!=previous_event.get('sequence',-1)+1 or e.get('previous_event_digest')!=previous_event.get('reliability_digest'):errors.append('broken_lineage')
 bounds={'restart_count':(0,32),'resource_percent':(0,100),'observed_latency_ms':(0,60000),'latency_budget_ms':(1,10000),'starvation_cycles':(0,1000),'cancellation_observations':(0,1000),'drift_score':(0,100)}
 for f,(lo,hi) in bounds.items():
  v=e.get(f)
  if not isinstance(v,int) or not lo<=v<=hi:errors.append('malformed_'+f)
 if isinstance(e.get('observed_latency_ms'),int) and isinstance(e.get('latency_budget_ms'),int) and e['observed_latency_ms']>e['latency_budget_ms']:errors.append('latency_budget_exceeded')
 if e.get('event_class')=='restart_storm' and e.get('restart_count',0)<3:errors.append('restart_storm_not_observed')
 if e.get('event_class')=='resource_exhaustion' and e.get('resource_percent',0)<90:errors.append('resource_exhaustion_not_observed')
 if e.get('event_class')=='queue_starvation' and e.get('starvation_cycles',0)<3:errors.append('starvation_not_observed')
 if e.get('event_class')=='cancellation_race' and e.get('cancellation_observations',0)<2:errors.append('cancellation_race_not_observed')
 if e.get('event_class')=='long_duration_drift' and e.get('drift_score',0)<10:errors.append('drift_not_observed')
 if s.get('foreground_path_available') is not True:errors.append('foreground_blocked')
 if s.get('original_evidence_preserved') is not True:errors.append('evidence_loss')
 if p.get('execution_invoked') is not False or p.get('authority_granted') is not False:errors.append('progression_boundary_loss')
 for f in ('automatic_recovery','automatic_retry','cancellation_executed','provider_contacted','runtime_mutated','authority_granted'):
  if e.get(f) is not False:errors.append('forbidden_claim')
 errors=sorted(set(errors));status='reliability_ready' if not errors else 'blocked'
 r={'contract_version':CONTRACT_VERSION,'status':status,'event_class':e.get('event_class',''),'sequence':e.get('sequence',-1),'errors':errors,'error_count':len(errors),'content_free':True,'exact_lineage_verified':'broken_lineage' not in errors,'foreground_path_available':True,'original_evidence_preserved':True,'recovery_review_required':e.get('event_class') in EVENTS,'automatic_recovery':False,'automatic_retry':False,'cancellation_executed':False,'execution_invoked':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'runtime_mutated':False,'approval_consumed':False,'authority_granted':False};r['reliability_digest']=_digest(r);return r
def public_soak_reliability_summary(r:Mapping[str,Any])->dict[str,Any]:return {k:r.get(k) for k in ('contract_version','status','event_class','sequence','error_count','content_free','exact_lineage_verified','foreground_path_available','original_evidence_preserved','recovery_review_required','automatic_recovery','automatic_retry','cancellation_executed','execution_invoked','runtime_mutated','authority_granted','reliability_digest')}
