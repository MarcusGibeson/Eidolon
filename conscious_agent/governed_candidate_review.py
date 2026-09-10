from __future__ import annotations

"""v1497 governed candidate review and installation admission evidence.

This module may prepare a review packet and installation preview. It does not
perform installation or promotion and cannot mint operator authority.
"""

import hashlib, json
from typing import Any, Mapping

from development_authority import is_hex64, validate_operator_authorization

CONTRACT_VERSION='v1497.9'


def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def build_review_packet(*,plan:Mapping[str,Any],change_receipt:Mapping[str,Any],verification:Mapping[str,Any],source_manifest_digest:str,rollback_digest:str)->dict[str,Any]:
 checks={
  'plan_ready':str(plan.get('status') or '')=='plan_ready_for_operator_review' and is_hex64(plan.get('plan_digest')),
  'workspace_only_change':str(change_receipt.get('status') or '')=='workspace_changed' and bool(change_receipt.get('workspace_only')) and not bool(change_receipt.get('active_source_modified')) and str(change_receipt.get('plan_digest') or '')==str(plan.get('plan_digest') or '') and is_hex64(change_receipt.get('change_digest')),
  'verification_passed':bool(verification.get('verification_passed')) and is_hex64(verification.get('verification_digest')),
  'source_manifest_bound':is_hex64(source_manifest_digest),
  'rollback_bound':is_hex64(rollback_digest),
 }
 row={'contract_version':CONTRACT_VERSION,'candidate_id':str(plan.get('candidate_id') or ''),'plan_digest':str(plan.get('plan_digest') or ''),'change_digest':str(change_receipt.get('change_digest') or ''),'verification_digest':str(verification.get('verification_digest') or ''),'source_manifest_digest':str(source_manifest_digest or ''),'rollback_digest':str(rollback_digest or ''),'checks':checks,'review_ready':all(checks.values()),'operator_review_required':True,'installation_executed':False,'promotion_executed':False,'provider_contacted':False,'content_free':True}
 row['review_digest']=_digest(row);return row

def installation_preview(review:Mapping[str,Any],*,authoritative_source_digest:str,candidate_source_digest:str)->dict[str,Any]:
 ready=bool(review.get('review_ready')) and is_hex64(review.get('review_digest')) and is_hex64(authoritative_source_digest) and is_hex64(candidate_source_digest) and authoritative_source_digest!=candidate_source_digest
 row={'contract_version':CONTRACT_VERSION,'candidate_id':str(review.get('candidate_id') or ''),'review_digest':str(review.get('review_digest') or ''),'authoritative_source_digest':str(authoritative_source_digest),'candidate_source_digest':str(candidate_source_digest),'preview_ready':ready,'would_replace_source':ready,'preserve_private_runtime':True,'rollback_required':True,'installation_executed':False,'promotion_executed':False,'operator_approval_required':True,'content_free':True}
 row['preview_digest']=_digest(row);return row

def admit_operator_installation(preview:Mapping[str,Any],*,operator_authorization_receipt:Mapping[str,Any]|None,expected_preview_digest:str)->dict[str,Any]:
 preview_digest=str(preview.get('preview_digest') or '')
 authorization=validate_operator_authorization(operator_authorization_receipt,stage='installation',subject_id=str(preview.get('candidate_id') or ''),subject_digest=preview_digest)
 exact=bool(preview.get('preview_ready') and preview_digest==str(expected_preview_digest or '') and authorization['ok'])
 return {'contract_version':CONTRACT_VERSION,'admitted_for_external_installer':exact,'installation_executed':False,'promotion_executed':False,'authorization_id':authorization['authorization_id'] if exact else '','authorization_receipt_digest':authorization['receipt_digest'] if exact else '','preview_digest':preview_digest,'reason':'exact_operator_approval_admitted' if exact else 'operator_approval_or_digest_missing','content_free':True}

__all__=['CONTRACT_VERSION','build_review_packet','installation_preview','admit_operator_installation']
