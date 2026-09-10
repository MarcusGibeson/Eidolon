from __future__ import annotations
"""Content-free provider reliability classification and recovery guidance.

This module never installs, pulls, removes, selects, or switches a model. It only
validates the operator's existing configuration and classifies bounded outcomes.
"""
from dataclasses import dataclass,asdict
import hashlib,json
from typing import Any,Mapping
from local_model import (
    LocalModelConfig,LocalModelError,ERROR_UNAVAILABLE,ERROR_MISSING_MODEL,ERROR_TIMEOUT,
    ERROR_CANCELLED,ERROR_MALFORMED,ERROR_EMPTY,ERROR_INTERRUPTED_STREAM,ERROR_HTTP,
    ERROR_INVALID_CONFIG,ERROR_CLOSED,ERROR_CONTEXT_LIMIT,ERROR_UNSUPPORTED_STREAMING,
)

KNOWN_FAILURES=frozenset({
    ERROR_UNAVAILABLE,ERROR_MISSING_MODEL,ERROR_TIMEOUT,ERROR_CANCELLED,ERROR_MALFORMED,
    ERROR_EMPTY,ERROR_INTERRUPTED_STREAM,ERROR_HTTP,ERROR_INVALID_CONFIG,ERROR_CLOSED,
    ERROR_CONTEXT_LIMIT,ERROR_UNSUPPORTED_STREAMING,
})

def _digest(value:str)->str:
    return hashlib.sha256(str(value or '').encode('utf-8')).hexdigest()[:24]

@dataclass(frozen=True)
class ProviderConfigurationProjection:
    valid:bool; provider_class:str; endpoint_identity_digest:str; model_identity_digest:str
    endpoint_configured:bool; model_configured:bool; configuration_mutated:bool=False
    model_management_attempted:bool=False; content_free:bool=True; schema_version:str='1'
    def public_summary(self)->dict[str,Any]:
        row=asdict(self); row['projection_digest']=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest(); return row

def validate_configured_provider(settings:Mapping[str,Any])->ProviderConfigurationProjection:
    """Validate only; never write settings or contact/install provider resources."""
    provider=str(settings.get('local_model_provider') or 'ollama').strip().lower()
    endpoint=str(settings.get('local_model_endpoint') or '').strip()
    model=str(settings.get('local_model') or '').strip()
    valid=True
    try: LocalModelConfig.from_settings(dict(settings)).validated()
    except Exception: valid=False
    return ProviderConfigurationProjection(
        valid=valid,provider_class=provider[:40],endpoint_identity_digest=_digest(endpoint),model_identity_digest=_digest(model),
        endpoint_configured=bool(endpoint),model_configured=bool(model),
    )

def classify_provider_failure(error:BaseException)->str:
    if isinstance(error,LocalModelError):
        return error.code if error.code in KNOWN_FAILURES else 'provider_failure'
    if isinstance(error,TimeoutError): return ERROR_TIMEOUT
    return 'provider_failure'

_GUIDANCE={
 ERROR_UNAVAILABLE:'The configured provider endpoint is unreachable. Keep the current provider/model selection and retry only after the service is available.',
 ERROR_MISSING_MODEL:'The configured model is unavailable. Model installation or selection remains an explicit operator action.',
 ERROR_TIMEOUT:'The provider request timed out. Preserve the draft and operation evidence; do not silently replay an uncertain request.',
 ERROR_CANCELLED:'The request was cancelled. Do not resume generation automatically; a new send must be explicit.',
 ERROR_MALFORMED:'The provider returned malformed data. Preserve operation evidence and do not expose or replay the raw payload.',
 ERROR_EMPTY:'The provider completed without usable text. Keep the draft/recovery state and require an explicit next send.',
 ERROR_INTERRUPTED_STREAM:'The stream ended before authoritative completion. Reconcile the accepted operation before any explicit retry.',
 ERROR_HTTP:'The provider HTTP request failed. Preserve operation evidence and retry only through the existing bounded policy.',
 ERROR_INVALID_CONFIG:'The configured provider settings are invalid. Correcting settings remains an explicit operator action.',
 ERROR_CLOSED:'The local-model client closed before completion. Reconcile the operation; do not assume it completed.',
 ERROR_CONTEXT_LIMIT:'The request exceeded the configured context boundary. Do not truncate protected instructions or silently switch models.',
 ERROR_UNSUPPORTED_STREAMING:'The endpoint does not support this streaming operation. Do not switch providers automatically.',
 'provider_failure':'The provider operation failed safely. Preserve operation evidence and do not infer completion.',
}

def provider_recovery_guidance(error:BaseException)->dict[str,Any]:
    category=classify_provider_failure(error)
    return {
        'failure_category':category,'guidance':_GUIDANCE.get(category,_GUIDANCE['provider_failure']),
        'automatic_provider_switch_allowed':False,'automatic_model_switch_allowed':False,
        'automatic_generation_replay_allowed':False,'preserve_draft':True,'reconcile_before_retry':category in {ERROR_INTERRUPTED_STREAM,ERROR_TIMEOUT,ERROR_CLOSED},
        'content_free':True,
    }

def public_provider_failure(error:BaseException)->dict[str,Any]:
    safe=error.to_safe_dict() if isinstance(error,LocalModelError) else {'code':classify_provider_failure(error),'message':'The provider operation failed safely.','redacted':True}
    recovery=provider_recovery_guidance(error)
    return {
        'failure_category':recovery['failure_category'],'safe_error':safe,'recovery':recovery,
        'contains_prompt':False,'contains_response':False,'contains_provider_payload':False,'content_free':True,
    }

def provider_recovery_operation_projection(marker:Mapping[str,Any],error:BaseException)->dict[str,Any]:
    """Bind provider loss to persisted operation identity without authorizing replay."""
    from operation_identity_contract import public_operation_identity
    projection=public_operation_identity(marker,surface='runtime').public_summary()
    recovery=provider_recovery_guidance(error)
    return {
        'operation_id':projection.get('operation_id',''),'session_id':projection.get('session_id',''),
        'acceptance_identity_digest':projection.get('acceptance_identity_digest',''),
        'operation_recovery_mode':projection.get('recovery_mode','reconcile_only'),
        'provider_failure_category':recovery['failure_category'],
        'automatic_reexecution_allowed':False,'preserve_draft':True,'content_free':True,
    }
