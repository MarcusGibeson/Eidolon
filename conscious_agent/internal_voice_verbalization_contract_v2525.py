from __future__ import annotations
"""v2525 provider-neutral request contract for richer internal-voice wording.

The contract prepares a content-minimized verbalization request from audited
structural cognition. It does not call a provider and is disabled by default.
"""
import hashlib, json
from typing import Any, Mapping
CONTRACT_VERSION='v2525.5';MAX_FACTS=8;MAX_OUTPUT_CHARS=320

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,default=str).encode()).hexdigest()
def prepare_internal_voice_verbalization_request(episode:Mapping[str,Any],*,enabled:bool=False)->dict[str,Any]:
 if not isinstance(episode,Mapping) or not episode.get('ok') or not episode.get('episode_digest'):raise ValueError('valid cognitive episode required')
 facts=[]
 for change in list(episode.get('meaningful_changes') or [])[:4]:facts.append({'kind':'state_change','code':str(change)[:80]})
 for step in list(episode.get('steps') or [])[:3]:facts.append({'kind':'cognitive_operation','operation':str(step.get('operation') or '')[:60],'outcome_type':str(step.get('outcome_type') or '')[:80],'reason_code':str(step.get('reason_code') or '')[:120]})
 for outcome in list(episode.get('candidate_outcomes') or [])[:2]:facts.append({'kind':'candidate_outcome','code':str(outcome)[:80]})
 facts=facts[:MAX_FACTS]
 request={'contract_version':CONTRACT_VERSION,'purpose':'state_grounded_internal_voice_verbalization','source_episode_digest':str(episode['episode_digest'])[:64],'facts':facts,'style_constraints':{'first_person':True,'max_sentences':2,'max_output_chars':MAX_OUTPUT_CHARS,'avoid_claiming_literal_transcript':True,'avoid_inventing_evidence':True,'avoid_action_claims':True},'enabled':bool(enabled),'provider_contact_authorized':False,'execution_ready':False,'requires_explicit_runtime_enablement':True,'raw_prompt_included':False,'raw_provider_output_included':False,'raw_reasoning_included':False,'tool_arguments_included':False,'hidden_reasoning_exposed':False,'authority_broadened':False}
 request['request_digest']=_digest(request);return request

def validate_verbalization_candidate(request:Mapping[str,Any],text:str)->dict[str,Any]:
 if not isinstance(request,Mapping) or len(str(request.get('request_digest') or ''))!=64:raise ValueError('valid verbalization request required')
 candidate=' '.join(str(text or '').split())[:MAX_OUTPUT_CHARS]
 if not candidate:raise ValueError('candidate text required')
 row={'ok':True,'contract_version':CONTRACT_VERSION,'source_request_digest':str(request['request_digest']),'voice_text':candidate,'representation_kind':'provider_candidate_state_grounded_internal_voice','candidate_only':True,'provider_result_admitted':False,'claims_literal_thought_transcript':False,'hidden_reasoning_exposed':False,'authority_broadened':False}
 row['candidate_digest']=_digest(row);return row
__all__=['CONTRACT_VERSION','prepare_internal_voice_verbalization_request','validate_verbalization_candidate']
