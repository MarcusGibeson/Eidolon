from __future__ import annotations
"""v2526 provider admission for minimized internal-voice verbalization only."""
import hashlib, json
from typing import Any, Mapping
CONTRACT_VERSION='v2526.3'

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def admit_internal_voice_provider_request(request:Mapping[str,Any],*,runtime_enabled:bool=False,provider_allowed:bool=False)->dict[str,Any]:
 if not isinstance(request,Mapping) or len(str(request.get('request_digest') or ''))!=64:raise ValueError('valid verbalization request required')
 if request.get('purpose')!='state_grounded_internal_voice_verbalization':raise ValueError('wrong provider purpose')
 if request.get('raw_prompt_included') or request.get('raw_reasoning_included') or request.get('tool_arguments_included'):raise ValueError('unsafe request content')
 admitted=bool(request.get('enabled')) and bool(runtime_enabled) and bool(provider_allowed)
 row={'ok':True,'contract_version':CONTRACT_VERSION,'request_digest':str(request['request_digest']),'admitted':admitted,'provider_contact_authorized':admitted,'prompt_transmission_authorized':admitted,'purpose_limited':True,'general_provider_authority_granted':False,'tool_execution_authorized':False,'network_browse_authorized':False,'raw_prompt_authorized':False,'raw_reasoning_authorized':False,'reason_code':'admitted' if admitted else 'provider_verbalization_not_enabled'}
 row['admission_digest']=_digest(row);return row
__all__=['CONTRACT_VERSION','admit_internal_voice_provider_request']
