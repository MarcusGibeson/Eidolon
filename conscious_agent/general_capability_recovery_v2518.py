from __future__ import annotations

"""v2518 cancellation and rollback request contracts for general capabilities.

Requests are digest-bound proposals only. They never call an adapter or perform
rollback/cancellation themselves.
"""
import hashlib,json,re
from typing import Any,Mapping
from general_capability_manifest_v2509 import validate_capability_manifest

CONTRACT_VERSION='v2518.0'; HEX64=re.compile(r'^[0-9a-f]{64}$')
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()

def prepare_control_request(*, manifest:Mapping[str,Any], envelope:Mapping[str,Any], result_receipt:Mapping[str,Any], control:str, operator_selection_digest:str) -> dict[str,Any]:
    if not validate_capability_manifest(manifest).get('ok'): raise ValueError('valid_manifest_required')
    if not HEX64.fullmatch(str(envelope.get('envelope_digest') or '')): raise ValueError('valid_envelope_required')
    if not HEX64.fullmatch(str(result_receipt.get('receipt_digest') or '')): raise ValueError('valid_result_receipt_required')
    if str(result_receipt.get('envelope_digest') or '') != str(envelope.get('envelope_digest') or ''): raise ValueError('result_envelope_binding_mismatch')
    token=str(control or '').strip().lower()
    if token not in {'cancel','rollback'}: raise ValueError('unsupported_control')
    if token=='cancel' and not manifest.get('cancellation_supported'): raise ValueError('cancellation_not_supported')
    if token=='rollback' and (not manifest.get('reversible') or not manifest.get('rollback_supported')): raise ValueError('rollback_not_supported')
    sel=str(operator_selection_digest or '').lower()
    if not HEX64.fullmatch(sel): raise ValueError('operator_selection_digest_required')
    if token=='rollback' and result_receipt.get('side_effect_performed') is not True: raise ValueError('rollback_requires_side_effect_receipt')
    if token=='cancel' and result_receipt.get('status') not in {'not_invoked','cancelled','failed'}: raise ValueError('completed_success_cannot_be_cancelled')
    row={'contract_version':CONTRACT_VERSION,'control':token,'capability_id':manifest.get('capability_id'),'manifest_digest':manifest.get('manifest_digest'),'envelope_digest':envelope.get('envelope_digest'),'result_receipt_digest':result_receipt.get('receipt_digest'),'operator_selection_digest':sel,'request_ready':True,'operator_authorization_still_required':True,'control_performed':False,'adapter_invoked':False,'side_effect_performed':False,'raw_arguments_stored':False,'raw_output_stored':False,'authority_inferred':False}
    row['control_request_digest']=_digest(row);return row

__all__=['CONTRACT_VERSION','prepare_control_request']
