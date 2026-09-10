from __future__ import annotations

"""v2506.6-v2506.8 unified memory consolidation coordinator.

Consumes the retained unified-memory projection, adds typed cognitive roles,
and stages review candidates. It never writes/retracts/deletes memories itself.
"""

from pathlib import Path
from typing import Any,Iterable
from memory_consolidation_candidates_v2506 import MemoryConsolidationCandidateStore, derive_memory_consolidation_candidates
from unified_memory_context import build_unified_memory_runtime_projection
from unified_memory_roles_v2506 import build_unified_memory_role_projection

CONTRACT_VERSION='v2506.8'

def prepare_memory_consolidation(event_id:str,*,runtime_root:str|Path,message:object='',memory_records:object=None,conversation_history:object=None,project_state:object=None,protected_operator_constraints:Iterable[str]=())->dict[str,Any]:
    unified=build_unified_memory_runtime_projection(message,memory_records=memory_records,conversation_history=conversation_history,project_state=project_state,protected_operator_constraints=protected_operator_constraints)
    roles=build_unified_memory_role_projection(unified);candidates=derive_memory_consolidation_candidates(roles);stored=MemoryConsolidationCandidateStore(runtime_root).record(event_id,candidates)
    return {'ok':True,'contract_version':CONTRACT_VERSION,'coordination_posture':unified['policy']['coordination_posture'],'role_counts':roles['role_counts'],'role_projection_digest':roles['projection_digest'],'candidate_count':candidates['candidate_count'],'candidate_types':[x['candidate_type'] for x in candidates['candidates']],'candidate_set_digest':candidates['candidate_set_digest'],'record_id':stored['record_id'],'candidate_applied':False,'memory_mutated':False,'memory_deleted':False,'memory_retracted':False,'provider_contacted':False,'model_trained':False,'historical_truth_preserved':True,'authority_broadened':False}

__all__=['CONTRACT_VERSION','prepare_memory_consolidation']
