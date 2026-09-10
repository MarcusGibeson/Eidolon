from __future__ import annotations
"""v1194.3-v1194.5 operator coordination and accountable navigation."""
import hashlib,json
from typing import Any,Mapping,Sequence
CONTRACT_VERSION='v1194.5'
DECISIONS={'approve','reject','defer'}
DOMAINS=('conversation','cognition','reasoning','planning','campaign','approval','action','result','learning')
PURPOSES={'operator_navigation','review_required','blocked_attention','result_available','return_to_conversation'}
PRIVATE=('prompt','message','memory','secret','source_text','patch_text','stdout','stderr','provider_payload','private_reasoning')
def _d(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _hex(v:object)->bool:s=str(v or '');return len(s)==64 and all(c in '0123456789abcdef' for c in s)
def _private(v:object)->bool:
 if isinstance(v,Mapping):return any(any(t in str(k).lower() for t in PRIVATE) or _private(x) for k,x in v.items())
 if isinstance(v,(list,tuple)):return any(_private(x) for x in v)
 return False
def create_coordination_request(*,coordination_id:str,snapshot_digest:str,context_digest:str,from_domain:str,to_domain:str,purpose_code:str,artifact_digest:str,receipt_digest:str)->dict[str,Any]:
 r={'contract_version':CONTRACT_VERSION,'coordination_id':coordination_id,'snapshot_digest':snapshot_digest,'context_digest':context_digest,'from_domain':from_domain,'to_domain':to_domain,'purpose_code':purpose_code,'artifact_digest':artifact_digest,'receipt_digest':receipt_digest,'content_free':True,'state_mutation_requested':False,'execution_requested':False,'automatic_continuation_requested':False,'authority_requested':False};r['request_digest']=_d(r);return r
def create_coordination_review(*,request_digest:str,decision:str,review_id:str,operator_review_digest:str)->dict[str,Any]:
 r={'contract_version':CONTRACT_VERSION,'request_digest':request_digest,'decision':decision,'review_id':review_id,'operator_review_digest':operator_review_digest,'content_free':True,'approval_consumed':False,'execution_authorized':False,'authority_granted':False};r['review_digest']=_d(r);return r
def coordinate_operator_navigation(*,view:Mapping[str,Any],request:Mapping[str,Any],review:Mapping[str,Any],current_snapshot_digest:str,current_context_digest:str)->dict[str,Any]:
 errors=[];q=dict(request);rv=dict(review);v=dict(view)
 for row,field in ((q,'request_digest'),(rv,'review_digest')):
  claimed=row.get(field);unsigned=dict(row);unsigned.pop(field,None)
  if claimed!=_d(unsigned):errors.append('tampered_'+field.split('_')[0])
 if _private([v,q,rv]):errors.append('private_field')
 for f in ('snapshot_digest','context_digest','artifact_digest','receipt_digest'):
  if not _hex(q.get(f)):errors.append('malformed_'+f)
 if not _hex(rv.get('operator_review_digest')):errors.append('malformed_operator_review_digest')
 if q.get('snapshot_digest')!=current_snapshot_digest:errors.append('stale_snapshot')
 if q.get('context_digest')!=current_context_digest:errors.append('stale_context')
 if q.get('from_domain') not in DOMAINS or q.get('to_domain') not in DOMAINS:errors.append('unsupported_domain')
 if q.get('from_domain')==q.get('to_domain'):errors.append('no_op_navigation')
 if q.get('purpose_code') not in PURPOSES:errors.append('unsupported_purpose')
 if rv.get('decision') not in DECISIONS:errors.append('unsupported_decision')
 if rv.get('request_digest')!=q.get('request_digest'):errors.append('review_request_mismatch')
 if v.get('summary',{}).get('foreground_path_available') is not True:errors.append('foreground_blocked')
 if v.get('summary',{}).get('original_evidence_preserved') is not True:errors.append('evidence_loss')
 if v.get('summary',{}).get('global_profile_pass_claimed') is True:errors.append('false_global_pass')
 for f in ('state_mutation_requested','execution_requested','automatic_continuation_requested','authority_requested'):
  if q.get(f) is not False:errors.append('forbidden_claim')
 if rv.get('approval_consumed') is not False or rv.get('execution_authorized') is not False or rv.get('authority_granted') is not False:errors.append('forbidden_claim')
 errors=sorted(set(errors));decision=str(rv.get('decision') or '')
 status='navigation_ready' if not errors and decision=='approve' else ('navigation_rejected' if not errors and decision=='reject' else ('navigation_deferred' if not errors and decision=='defer' else 'blocked'))
 changed=status=='navigation_ready'
 result={'contract_version':CONTRACT_VERSION,'status':status,'decision':decision,'errors':errors,'error_count':len(errors),'from_domain':q.get('from_domain',''),'presented_domain':q.get('to_domain','') if changed else q.get('from_domain',''),'focus_changed':changed,'accountable_transition':changed,'content_free':True,'foreground_path_available':True,'original_evidence_preserved':True,'inherited_debt_visible':True,'subsystem_state_changed':False,'approval_created':False,'approval_consumed':False,'execution_invoked':False,'automatic_continuation':False,'runtime_mutated':False,'provider_contacted':False,'model_contacted':False,'thread_started':False,'process_started':False,'authority_granted':False};result['transition_digest']=_d(result);return result
def public_coordination_summary(r:Mapping[str,Any])->dict[str,Any]:return {k:r.get(k) for k in ('contract_version','status','decision','from_domain','presented_domain','focus_changed','accountable_transition','error_count','transition_digest','content_free','foreground_path_available','original_evidence_preserved','inherited_debt_visible','execution_invoked','runtime_mutated','authority_granted')}
