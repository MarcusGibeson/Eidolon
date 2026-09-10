from __future__ import annotations
"""v1191.3-v1191.5 operator-reviewed queue state transition evidence.

This contract records content-free operator decisions and accountable presentation
only. It never pauses, cancels, supersedes, completes, or executes real work.
"""
import hashlib,json,re
from typing import Any,Mapping
CONTRACT_VERSION="v1191.5";SCHEMA_VERSION="1";MAX_CONTRACT_BYTES=262_144
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$");ID_RE=re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
ACTIONS=("queue","pause","cancel","supersede","complete","present_result")
DECISIONS=("approve","reject","defer")
ALLOWED={
 "queue":({"proposed","review_required"},"queued_not_running"),
 "pause":({"queued_not_running","running_evidence_only"},"paused"),
 "cancel":({"proposed","review_required","queued_not_running","paused","blocked"},"cancelled"),
 "supersede":({"proposed","review_required","queued_not_running","paused","blocked"},"superseded"),
 "complete":({"running_evidence_only"},"completed"),
 "present_result":({"completed","failed","blocked","cancelled","superseded"},None),
}
_FORBIDDEN=("prompt","conversation_text","message_text","memory_content","private_reasoning","raw_source","raw_patch","stdout","stderr","provider_payload","secret","credential","token_value","release_authority")
def _digest(v:object)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _is_digest(v:object)->bool:return bool(DIGEST_RE.fullmatch(str(v or '').lower()))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_CONTRACT_BYTES
def _forbidden(v:object)->bool:
 if isinstance(v,Mapping):
  return any(any(z in str(k).lower() for z in _FORBIDDEN) or _forbidden(x) for k,x in v.items())
 if isinstance(v,(list,tuple)):return any(_forbidden(x) for x in v)
 return False
def _verify(row:Mapping[str,Any],field:str)->bool:
 u=dict(row);claimed=str(u.pop(field,'')).lower();return _is_digest(claimed) and claimed==_digest(u)
def create_queue_action_request(*,request_id:str,queue_id:str,work_id:str,work_digest:str,unified_snapshot_digest:str,context_digest:str,current_lifecycle_state:str,action:str,target_work_digest:str='',result_receipt_digest:str='',operator_visible_reason_code:str='operator_review')->dict[str,Any]:
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"request_id":str(request_id or ''),"queue_id":str(queue_id or ''),"work_id":str(work_id or ''),"work_digest":str(work_digest or '').lower(),"unified_snapshot_digest":str(unified_snapshot_digest or '').lower(),"context_digest":str(context_digest or '').lower(),"current_lifecycle_state":str(current_lifecycle_state or ''),"action":str(action or ''),"target_work_digest":str(target_work_digest or '').lower(),"result_receipt_digest":str(result_receipt_digest or '').lower(),"operator_visible_reason_code":str(operator_visible_reason_code or ''),"content_free":True,"execution_requested":False,"real_pause_requested":False,"real_cancellation_requested":False,"automatic_continuation":False,"authority_requested":False}
 row['request_digest']=_digest(row);return row
def create_queue_action_review(*,request_digest:str,decision:str,review_id:str,operator_review_digest:str)->dict[str,Any]:
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"request_digest":str(request_digest or '').lower(),"decision":str(decision or ''),"review_id":str(review_id or ''),"operator_review_digest":str(operator_review_digest or '').lower(),"content_free":True,"approval_created":False,"approval_consumed":False,"execution_authority_granted":False,"cancellation_authority_granted":False}
 row['review_digest']=_digest(row);return row
def review_queue_action(*,request:Mapping[str,Any],review:Mapping[str,Any],current_snapshot_digest:str,current_context_digest:str,current_work_digest:str)->dict[str,Any]:
 req,rev=dict(request),dict(review);errors=[]
 if not _bounded([req,rev]):errors.append('oversized_contract')
 if _forbidden([req,rev]):errors.append('private_or_authority_content_present')
 if not _verify(req,'request_digest'):errors.append('tampered_request')
 if not _verify(rev,'review_digest'):errors.append('tampered_review')
 if req.get('contract_version')!=CONTRACT_VERSION or rev.get('contract_version')!=CONTRACT_VERSION:errors.append('contract_mismatch')
 for f in ('request_id','queue_id','work_id'):
  if not ID_RE.fullmatch(str(req.get(f) or '')):errors.append('invalid_'+f)
 if not ID_RE.fullmatch(str(rev.get('review_id') or '')):errors.append('invalid_review_id')
 for f in ('work_digest','unified_snapshot_digest','context_digest'):
  if not _is_digest(req.get(f)):errors.append('invalid_'+f)
 if not _is_digest(rev.get('operator_review_digest')):errors.append('invalid_operator_review_digest')
 if rev.get('decision') not in DECISIONS:errors.append('unsupported_decision')
 action=str(req.get('action') or '')
 if action not in ACTIONS:errors.append('unsupported_action')
 if rev.get('request_digest')!=req.get('request_digest'):errors.append('review_request_mismatch')
 if req.get('unified_snapshot_digest')!=str(current_snapshot_digest or '').lower():errors.append('stale_unified_snapshot')
 if req.get('context_digest')!=str(current_context_digest or '').lower():errors.append('stale_context')
 if req.get('work_digest')!=str(current_work_digest or '').lower():errors.append('stale_work')
 if req.get('operator_visible_reason_code') not in {'operator_review','operator_cancellation','operator_pause','operator_supersession','operator_completion','operator_presentation'}:errors.append('unsupported_reason_code')
 if action in ALLOWED:
  allowed,target=ALLOWED[action]
  if req.get('current_lifecycle_state') not in allowed:errors.append('invalid_lifecycle_transition')
  if action=='supersede' and not _is_digest(req.get('target_work_digest')):errors.append('missing_superseding_work_digest')
  if action!='supersede' and req.get('target_work_digest'):errors.append('unexpected_target_work_digest')
  if action in {'complete','present_result'} and not _is_digest(req.get('result_receipt_digest')):errors.append('missing_result_receipt_digest')
  if action not in {'complete','present_result'} and req.get('result_receipt_digest'):errors.append('unexpected_result_receipt_digest')
 for f in ('execution_requested','real_pause_requested','real_cancellation_requested','automatic_continuation','authority_requested'):
  if req.get(f) is not False:errors.append('hidden_execution_or_authority_claim')
 for f in ('approval_created','approval_consumed','execution_authority_granted','cancellation_authority_granted'):
  if rev.get(f) is not False:errors.append('hidden_execution_or_authority_claim')
 if req.get('content_free') is not True or rev.get('content_free') is not True:errors.append('privacy_contract_violation')
 errors=sorted(set(errors));decision=str(rev.get('decision') or '')
 accepted=not errors and decision=='approve';target=ALLOWED.get(action,(set(),None))[1]
 next_state=(target if accepted and target else req.get('current_lifecycle_state',''))
 result_presented=bool(accepted and action=='present_result')
 status='transition_ready' if accepted else ('transition_rejected' if not errors and decision=='reject' else ('transition_deferred' if not errors and decision=='defer' else 'blocked'))
 out={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"request_id":req.get('request_id',''),"queue_id":req.get('queue_id',''),"work_id":req.get('work_id',''),"action":action,"decision":decision,"status":status,"errors":errors,"error_count":len(errors),"previous_lifecycle_state":req.get('current_lifecycle_state',''),"presented_lifecycle_state":next_state,"transition_recorded":accepted,"result_presented":result_presented,"content_free":True,"private_content_included":False,"real_work_paused":False,"real_work_cancelled":False,"real_work_superseded":False,"real_work_completed":False,"execution_invoked":False,"automatic_continuation":False,"approval_created":False,"approval_consumed":False,"provider_contacted":False,"model_contacted":False,"thread_started":False,"process_started":False,"source_modified":False,"runtime_modified":False,"authority_granted":False}
 out['transition_digest']=_digest(out);return out
def public_queue_action_summary(result:Mapping[str,Any])->dict[str,Any]:
 return {k:result.get(k) for k in ('contract_version','status','action','decision','previous_lifecycle_state','presented_lifecycle_state','transition_recorded','result_presented','content_free','execution_invoked','automatic_continuation','authority_granted')}
