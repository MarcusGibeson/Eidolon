from __future__ import annotations
"""v2584 read-only observability for retrieval outcome learning."""
from pathlib import Path
from typing import Any
try:
    from memory_retrieval_outcome_history_v2580 import load_memory_retrieval_outcome_history
    from memory_retrieval_learning_profile_v2581 import build_memory_retrieval_learning_profile
    from memory_retrieval_learning_advisory_v2582 import build_memory_retrieval_learning_advisory
except ImportError:
    from memory_retrieval_outcome_history_v2580 import load_memory_retrieval_outcome_history
    from memory_retrieval_learning_profile_v2581 import build_memory_retrieval_learning_profile
    from memory_retrieval_learning_advisory_v2582 import build_memory_retrieval_learning_advisory
CONTRACT_VERSION='v2584.0'

def build_memory_retrieval_learning_observability(runtime_root:str|Path|None=None)->dict[str,Any]:
    history=load_memory_retrieval_outcome_history(runtime_root)
    profile=build_memory_retrieval_learning_profile(history.get('rows') or [])
    advisory=build_memory_retrieval_learning_advisory(profile)
    adverse=sum(1 for x in profile.get('profiles') or [] if x.get('history_label')=='adverse_history')
    supportive=sum(1 for x in profile.get('profiles') or [] if x.get('history_label')=='supportive_history')
    state='attention' if adverse else ('learning' if profile.get('observation_count') else 'no_history')
    return {'ok':True,'contract_version':CONTRACT_VERSION,'state':state,'observation_count':int(profile.get('observation_count') or 0),'adverse_state_count':adverse,'supportive_state_count':supportive,'profiles':list(profile.get('profiles') or [])[:8],'advisories':list(advisory.get('advisories') or [])[:8],'automatic_policy_change_permitted':False,'memory_mutation_permitted':False,'raw_memory_text_stored':False,'raw_prompt_stored':False,'raw_response_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','build_memory_retrieval_learning_observability']
