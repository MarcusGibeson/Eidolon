from __future__ import annotations
"""v2528 semantic guard and cadence admission for provider-generated voice candidates."""
import re, hashlib, json
from typing import Any, Mapping
from internal_voice_cadence_v2523 import InternalVoiceCadence
CONTRACT_VERSION='v2528.4'
_FORBIDDEN=(r'chain[- ]of[- ]thought',r'hidden reasoning',r'I executed',r'I sent ',r'I browsed ',r'I changed your files')
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def admit_provider_voice_candidate(runtime_result:Mapping[str,Any],*,runtime_root,event_id:str)->dict[str,Any]:
 if runtime_result.get('status')!='verbalization_candidate_created':return {'ok':True,'status':'no_candidate','emit':False,'provider_candidate_admitted':False}
 c=dict(runtime_result.get('candidate') or {}); text=' '.join(str(c.get('voice_text') or '').split())[:320]
 low=text.lower(); unsafe=any(re.search(p,low) for p in _FORBIDDEN) or not text
 if unsafe:return {'ok':True,'status':'provider_voice_rejected','emit':False,'provider_candidate_admitted':False,'reason_code':'unsafe_or_empty_voice','hidden_reasoning_exposed':False,'authority_broadened':False}
 cad=InternalVoiceCadence(runtime_root).admit(event_id,voice_text=text,source_digest=str(c.get('source_request_digest') or ''))
 row={'ok':True,'status':'provider_voice_admitted' if cad.get('emit') else 'provider_voice_suppressed','emit':bool(cad.get('emit')),'provider_candidate_admitted':bool(cad.get('emit')),'voice_text':text if cad.get('emit') else '','voice_digest':str(c.get('candidate_digest') or ''),'cadence_status':cad.get('status'),'claims_literal_thought_transcript':False,'hidden_reasoning_exposed':False,'authority_broadened':False}
 row['guard_digest']=_digest(row);return row
__all__=['CONTRACT_VERSION','admit_provider_voice_candidate']
