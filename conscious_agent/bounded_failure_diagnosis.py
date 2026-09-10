from __future__ import annotations

"""v1495 deterministic failure diagnosis and bounded repair proposals.

This layer classifies verification/execution receipts and may propose one bounded
repair action.  It never performs the repair, retries a provider, edits active
source, installs, or grants authority.
"""

import hashlib, json
from typing import Any, Iterable, Mapping

from development_authority import validate_operator_authorization

CONTRACT_VERSION='v1495.9'
MAX_FAILURES=32


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()


def _classify(row:Mapping[str,Any])->str:
 text=' '.join(str(row.get(k) or '') for k in ('status','reason','failure_code','stderr_class','stage')).casefold()
 if any(t in text for t in ('syntax','parse','compile')):return 'syntax_or_compile_failure'
 if any(t in text for t in ('timeout','timed_out')):return 'timeout_failure'
 if any(t in text for t in ('provider','model','ollama')):return 'provider_failure'
 if any(t in text for t in ('authority','approval','authorization','permission')):return 'authority_boundary_failure'
 if any(t in text for t in ('scope','path','private','traversal')):return 'scope_or_privacy_failure'
 if any(t in text for t in ('assert','test','verification')):return 'behavioral_test_failure'
 if any(t in text for t in ('concurrent','stale','digest','changed')):return 'stale_or_concurrent_source_failure'
 return 'unknown_failure'


def diagnose_candidate_failure(receipts:Iterable[Mapping[str,Any]],*,attempt:int=1)->dict[str,Any]:
 rows=[dict(x or {}) for x in receipts][:MAX_FAILURES]
 failures=[row for row in rows if row.get('passed') is False or str(row.get('status') or '').casefold() in {'failed','blocked','timed_out','cancelled'}]
 classes=[_classify(row) for row in failures]
 primary=classes[0] if classes else 'no_failure'
 retry_safe=primary in {'syntax_or_compile_failure','behavioral_test_failure'} and int(attempt)<2
 repair_kind={
  'syntax_or_compile_failure':'repair_syntax_in_changed_files',
  'behavioral_test_failure':'repair_only_failed_behavior',
  'timeout_failure':'reduce_scope_or_review_timeout',
  'provider_failure':'wait_for_provider_or_operator_decision',
  'authority_boundary_failure':'stop_for_operator_authority',
  'scope_or_privacy_failure':'shrink_scope_and_revalidate',
  'stale_or_concurrent_source_failure':'discard_workspace_and_rebase_after_operator_review',
  'unknown_failure':'stop_for_manual_review','no_failure':'none',
 }[primary]
 result={'contract_version':CONTRACT_VERSION,'failure_count':len(failures),'failure_classes':classes,'primary_failure_class':primary,'repair_kind':repair_kind,'bounded_repair_proposed':bool(failures),'automatic_retry_allowed':False,'repair_attempt_may_be_prepared':retry_safe,'max_additional_attempts':1 if retry_safe else 0,'provider_contacted':False,'source_modified':False,'workspace_modified':False,'installation_authorized':False,'promotion_authorized':False,'operator_review_required':bool(failures),'content_free':True}
 result['diagnosis_digest']=_digest(result);return result


def admit_bounded_repair(diagnosis:Mapping[str,Any],*,candidate_id:str,operator_authorization_receipt:Mapping[str,Any]|None)->dict[str,Any]:
 authorization=validate_operator_authorization(operator_authorization_receipt,stage='bounded_repair',subject_id=str(candidate_id or ''),subject_digest=str(diagnosis.get('diagnosis_digest') or ''))
 allowed=bool(authorization['ok'] and diagnosis.get('repair_attempt_may_be_prepared') and int(diagnosis.get('max_additional_attempts') or 0)>0)
 return {'contract_version':CONTRACT_VERSION,'repair_workspace_authorized':allowed,'authorization_id':authorization['authorization_id'] if allowed else '','authorization_receipt_digest':authorization['receipt_digest'] if allowed else '','automatic_execution':False,'automatic_retry':False,'reason':'operator_authorized_bounded_repair' if allowed else 'repair_not_authorized','diagnosis_digest':str(diagnosis.get('diagnosis_digest') or ''),'active_source_modified':False,'content_free':True}

__all__=['CONTRACT_VERSION','diagnose_candidate_failure','admit_bounded_repair']
