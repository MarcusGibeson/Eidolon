from __future__ import annotations
"""v2527 injected-provider runtime for admitted internal-voice verbalization requests."""
import hashlib, json
from typing import Any, Callable, Mapping
from internal_voice_verbalization_contract_v2525 import validate_verbalization_candidate
CONTRACT_VERSION='v2527.4';MAX_PROVIDER_INPUT_CHARS=1800

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def _prompt(request:Mapping[str,Any])->str:
 payload={'purpose':'state-grounded internal voice','facts':list(request.get('facts') or [])[:8],'constraints':dict(request.get('style_constraints') or {})}
 return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True)[:MAX_PROVIDER_INPUT_CHARS]
def run_internal_voice_verbalization(request:Mapping[str,Any],admission:Mapping[str,Any],*,provider_generate:Callable[[str],str]|None=None)->dict[str,Any]:
 if str(admission.get('request_digest') or '')!=str(request.get('request_digest') or ''):raise ValueError('admission/request mismatch')
 if not admission.get('admitted') or not admission.get('provider_contact_authorized'):return {'ok':True,'status':'verbalization_not_admitted','provider_contacted':False,'candidate_created':False,'authority_broadened':False}
 if provider_generate is None:raise ValueError('provider callable required for admitted request')
 prompt=_prompt(request); raw=provider_generate(prompt); candidate=validate_verbalization_candidate(request,raw)
 row={'ok':True,'status':'verbalization_candidate_created','contract_version':CONTRACT_VERSION,'source_request_digest':str(request['request_digest']),'admission_digest':str(admission.get('admission_digest') or ''),'candidate':candidate,'provider_contacted':True,'provider_input_digest':hashlib.sha256(prompt.encode()).hexdigest(),'provider_output_digest':hashlib.sha256(str(raw).encode()).hexdigest(),'raw_provider_output_stored':False,'raw_prompt_stored':False,'candidate_only':True,'provider_result_admitted':False,'tool_executed':False,'message_sent':False,'authority_broadened':False}
 row['runtime_digest']=_digest(row);return row
__all__=['CONTRACT_VERSION','run_internal_voice_verbalization']
