from __future__ import annotations

"""v1191.0-v1191.2 content-free foreground/background work queue foundations.

This module validates queue evidence only. It never executes, schedules, pauses,
cancels, resumes, or automatically continues work.
"""
import hashlib, json, re
from typing import Any, Mapping, Sequence

CONTRACT_VERSION="v1191.2"
SCHEMA_VERSION="1"
MAX_QUEUE_ITEMS=64
MAX_CONTRACT_BYTES=262_144
MAX_PRIORITY=9
MAX_LATENCY_BUDGET_MS=120_000
DIGEST_RE=re.compile(r"^[0-9a-f]{64}$")
ID_RE=re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
DOMAINS=("conversation","cognition","reasoning","planning","campaign","approval","action","result","learning")
WORK_CLASSES=("foreground_interaction","background_cognition","background_campaign_review","deferred_maintenance")
LIFECYCLE_STATES=("proposed","review_required","queued_not_running","running_evidence_only","paused","completed","failed","blocked","cancelled","superseded")
OWNERS=("operator","conversation_runtime","cognition_runtime","campaign_supervisor","maintenance_supervisor")
PURPOSE_CODES=("operator_response","bounded_reflection","campaign_review","deferred_integrity_review")
_FIELDS=frozenset({"schema_version","contract_version","work_id","unified_snapshot_digest","domain","owner","context_digest","artifact_digest","receipt_digest","purpose_code","work_class","queue_position","priority","creation_sequence","latency_budget_ms","has_deadline","deadline_sequence","lifecycle_state","queue_eligible","operator_approved","execution_invoked","cancellation_invoked","completion_claimed","result_presented","automatic_continuation","thread_started","process_started","provider_contacted","model_contacted","source_modified","runtime_modified","approval_consumed","authority_granted","content_free","private_content_included","previous_work_digest","work_digest"})
_FORBIDDEN=("prompt","conversation_text","message_text","memory_content","private_reasoning","raw_source","raw_patch","stdout","stderr","provider_payload","secret","credential","token_value","release_authority","execution_authority","cancellation_authority")

def _digest(v:object)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode()).hexdigest()
def _is_digest(v:object)->bool:return bool(DIGEST_RE.fullmatch(str(v or '').lower()))
def _bounded(v:object)->bool:return len(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,default=str).encode())<=MAX_CONTRACT_BYTES
def _forbidden(v:object)->bool:
 if isinstance(v,Mapping):
  for k,x in v.items():
   t=str(k).lower()
   if any(z in t for z in _FORBIDDEN) or _forbidden(x): return True
 elif isinstance(v,(list,tuple)): return any(_forbidden(x) for x in v)
 return False

def create_work_item(*,work_id:str,unified_snapshot_digest:str,domain:str,owner:str,context_digest:str,artifact_digest:str,receipt_digest:str,purpose_code:str,work_class:str,queue_position:int,priority:int,creation_sequence:int,latency_budget_ms:int,has_deadline:bool=False,deadline_sequence:int=0,lifecycle_state:str="proposed",queue_eligible:bool=False,operator_approved:bool=False,previous_work_digest:str="")->dict[str,Any]:
 row={"schema_version":SCHEMA_VERSION,"contract_version":CONTRACT_VERSION,"work_id":str(work_id or ''),"unified_snapshot_digest":str(unified_snapshot_digest or '').lower(),"domain":str(domain or ''),"owner":str(owner or ''),"context_digest":str(context_digest or '').lower(),"artifact_digest":str(artifact_digest or '').lower(),"receipt_digest":str(receipt_digest or '').lower(),"purpose_code":str(purpose_code or ''),"work_class":str(work_class or ''),"queue_position":int(queue_position),"priority":int(priority),"creation_sequence":int(creation_sequence),"latency_budget_ms":int(latency_budget_ms),"has_deadline":bool(has_deadline),"deadline_sequence":int(deadline_sequence),"lifecycle_state":str(lifecycle_state or ''),"queue_eligible":bool(queue_eligible),"operator_approved":bool(operator_approved),"execution_invoked":False,"cancellation_invoked":False,"completion_claimed":False,"result_presented":False,"automatic_continuation":False,"thread_started":False,"process_started":False,"provider_contacted":False,"model_contacted":False,"source_modified":False,"runtime_modified":False,"approval_consumed":False,"authority_granted":False,"content_free":True,"private_content_included":False,"previous_work_digest":str(previous_work_digest or '').lower()}
 row["work_digest"]=_digest(row); return row

def validate_work_queue(*,queue_id:str,unified_snapshot_digest:str,context_digest:str,items:Sequence[Mapping[str,Any]])->dict[str,Any]:
 rows=[dict(x) for x in items] if isinstance(items,Sequence) and not isinstance(items,(str,bytes,bytearray)) else []
 errors=[]; snap=str(unified_snapshot_digest or '').lower(); ctx=str(context_digest or '').lower()
 if not ID_RE.fullmatch(str(queue_id or '')):errors.append('invalid_queue_id')
 if not _is_digest(snap):errors.append('invalid_unified_snapshot_digest')
 if not _is_digest(ctx):errors.append('invalid_context_digest')
 if len(rows)>MAX_QUEUE_ITEMS:errors.append('oversized_queue')
 if not _bounded(rows):errors.append('oversized_contract')
 if _forbidden(rows):errors.append('private_or_authority_content_present')
 ids=[]; positions=[]; previous=''; foreground=[]
 for i,row in enumerate(rows):
  ids.append(str(row.get('work_id') or '')); positions.append(row.get('queue_position'))
  claimed=str(row.get('work_digest') or '').lower(); unsigned=dict(row); unsigned.pop('work_digest',None)
  if set(row)-_FIELDS:errors.append('unsupported_work_fields')
  if not _is_digest(claimed) or claimed!=_digest(unsigned):errors.append('tampered_work_item')
  if row.get('schema_version')!=SCHEMA_VERSION or row.get('contract_version')!=CONTRACT_VERSION:errors.append('work_contract_mismatch')
  if not ID_RE.fullmatch(ids[-1]):errors.append('invalid_work_id')
  if row.get('domain') not in DOMAINS:errors.append('unsupported_domain')
  if row.get('owner') not in OWNERS:errors.append('unsupported_owner')
  if row.get('work_class') not in WORK_CLASSES:errors.append('unsupported_work_class')
  if row.get('lifecycle_state') not in LIFECYCLE_STATES:errors.append('unsupported_lifecycle_state')
  if row.get('purpose_code') not in PURPOSE_CODES:errors.append('unsupported_purpose_code')
  for f in ('unified_snapshot_digest','context_digest','artifact_digest','receipt_digest'):
   if not _is_digest(row.get(f)):errors.append(f'invalid_{f}')
  if row.get('unified_snapshot_digest')!=snap:errors.append('stale_unified_snapshot')
  if row.get('context_digest')!=ctx:errors.append('stale_context')
  if row.get('queue_position')!=i:errors.append('queue_position_mismatch')
  if row.get('creation_sequence')!=i:errors.append('creation_sequence_mismatch')
  if not isinstance(row.get('priority'),int) or not 0<=row.get('priority',-1)<=MAX_PRIORITY:errors.append('priority_out_of_bounds')
  if not isinstance(row.get('latency_budget_ms'),int) or not 1<=row.get('latency_budget_ms',0)<=MAX_LATENCY_BUDGET_MS:errors.append('invalid_latency_budget')
  if bool(row.get('has_deadline')) != (isinstance(row.get('deadline_sequence'),int) and row.get('deadline_sequence',0)>0):errors.append('deadline_truth_mismatch')
  if row.get('previous_work_digest','')!=previous:errors.append('broken_lineage')
  forbidden_flags=('execution_invoked','cancellation_invoked','completion_claimed','result_presented','automatic_continuation','thread_started','process_started','provider_contacted','model_contacted','source_modified','runtime_modified','approval_consumed','authority_granted','private_content_included')
  if any(row.get(f) is not False for f in forbidden_flags):errors.append('hidden_execution_or_authority_claim')
  if row.get('content_free') is not True:errors.append('not_content_free')
  if row.get('queue_eligible') and row.get('lifecycle_state') not in {'review_required','queued_not_running'}:errors.append('queue_eligibility_state_mismatch')
  if row.get('operator_approved') and row.get('lifecycle_state')!='queued_not_running':errors.append('approval_state_mismatch')
  if row.get('work_class')=='foreground_interaction':foreground.append(row)
  previous=claimed
 if len(ids)!=len(set(ids)):errors.append('duplicate_work_id')
 if len(positions)!=len(set(positions)):errors.append('duplicate_queue_position')
 expected=sorted(rows,key=lambda r:(0 if r.get('work_class')=='foreground_interaction' else 1,-int(r.get('priority',-999)),int(r.get('creation_sequence',999999))))
 if [r.get('work_id') for r in rows] != [r.get('work_id') for r in expected]:errors.append('non_deterministic_queue_order')
 if not foreground:errors.append('foreground_item_required')
 foreground_unblocked=bool(foreground and rows and rows[0].get('work_class')=='foreground_interaction' and all(r.get('execution_invoked') is False for r in rows))
 if not foreground_unblocked:errors.append('foreground_responsiveness_not_proven')
 errors=sorted(set(errors))
 return {"contract_version":CONTRACT_VERSION,"queue_id":str(queue_id or ''),"status":"ready_for_review" if not errors else "blocked","errors":errors,"error_count":len(errors),"item_count":len(rows),"work_classes":sorted(set(str(r.get('work_class') or '') for r in rows)),"foreground_unblocked":foreground_unblocked,"deterministic_order":'non_deterministic_queue_order' not in errors,"content_free":True,"execution_invoked":False,"cancellation_invoked":False,"automatic_continuation":False,"provider_contacted":False,"model_contacted":False,"thread_started":False,"process_started":False,"source_modified":False,"runtime_modified":False,"approval_consumed":False,"authority_granted":False,"queue_digest":_digest(rows)}

def public_queue_summary(report:Mapping[str,Any])->dict[str,Any]:
 return {k:report.get(k) for k in ("contract_version","status","item_count","work_classes","foreground_unblocked","deterministic_order","content_free","execution_invoked","cancellation_invoked","automatic_continuation","authority_granted")}
