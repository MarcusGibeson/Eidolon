from __future__ import annotations
"""v2531 content-minimized audit receipt for live internal-voice provider decisions."""
import hashlib,json
from typing import Any,Mapping
CONTRACT_VERSION='v2531.3'
def _d(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def build_internal_voice_provider_receipt(result:Mapping[str,Any],*,episode_digest:str)->dict[str,Any]:
 status=str(result.get('status') or '')[:80]
 row={'ok':True,'contract_version':CONTRACT_VERSION,'episode_digest':str(episode_digest or '')[:64],'status':status,'provider_contacted':bool(result.get('provider_contacted')),'provider_candidate_used':bool(result.get('provider_candidate_used')),'voice_count':len(list(result.get('voice_events') or [])),'fallback_preserved':bool(result.get('fallback_preserved')),'raw_prompt_stored':False,'raw_provider_output_stored':False,'voice_text_stored':False,'hidden_reasoning_exposed':False,'tool_executed':False,'message_sent':False,'authority_broadened':False}
 row['receipt_digest']=_d(row);return row
__all__=['CONTRACT_VERSION','build_internal_voice_provider_receipt']
