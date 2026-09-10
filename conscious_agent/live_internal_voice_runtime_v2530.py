from __future__ import annotations
"""v2530 live internal-voice runtime with deterministic fallback and optional admitted provider wording."""
from typing import Any, Callable, Mapping
from state_grounded_internal_voice_v2523 import project_episode_internal_voice
from internal_voice_verbalization_contract_v2525 import prepare_internal_voice_verbalization_request
from internal_voice_provider_admission_v2526 import admit_internal_voice_provider_request
from internal_voice_provider_runtime_v2527 import run_internal_voice_verbalization
from internal_voice_provider_guard_v2528 import admit_provider_voice_candidate
CONTRACT_VERSION='v2530.4'
def project_live_internal_voice(episode:Mapping[str,Any],*,runtime_root,event_id:str,provider_generate:Callable[[str],str]|None=None,provider_enabled:bool=False,provider_allowed:bool=False)->dict[str,Any]:
 fallback=project_episode_internal_voice(episode)
 request=prepare_internal_voice_verbalization_request(episode,enabled=bool(provider_enabled))
 admission=admit_internal_voice_provider_request(request,runtime_enabled=bool(provider_enabled),provider_allowed=bool(provider_allowed))
 if not admission.get('admitted') or provider_generate is None:
  return {'ok':True,'status':'deterministic_voice_fallback','voice_events':fallback,'provider_contacted':False,'provider_candidate_used':False,'fallback_preserved':True,'hidden_reasoning_exposed':False,'authority_broadened':False}
 result=run_internal_voice_verbalization(request,admission,provider_generate=provider_generate)
 guard=admit_provider_voice_candidate(result,runtime_root=runtime_root,event_id=event_id)
 if not guard.get('emit'):
  return {'ok':True,'status':'provider_voice_fallback','voice_events':fallback,'provider_contacted':bool(result.get('provider_contacted')),'provider_candidate_used':False,'fallback_preserved':True,'hidden_reasoning_exposed':False,'authority_broadened':False}
 row={'event':'internal_voice','voice_kind':'process','voice_text':guard['voice_text'],'episode_digest':str(episode.get('episode_digest') or '')[:64],'representation_kind':'provider_verbalized_state_grounded_internal_voice','provider_contacted':True,'claims_literal_thought_transcript':False,'hidden_reasoning_exposed':False,'content_minimized':True}
 return {'ok':True,'status':'provider_voice_projected','voice_events':[row],'provider_contacted':True,'provider_candidate_used':True,'fallback_preserved':True,'hidden_reasoning_exposed':False,'authority_broadened':False}
__all__=['CONTRACT_VERSION','project_live_internal_voice']
