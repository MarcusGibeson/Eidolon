from __future__ import annotations
"""v2576 runtime-only observability for content-minimized memory retrieval feedback."""
from pathlib import Path
from typing import Any, Mapping
import os
try:
    from json_storage import load_json_file, write_json_atomic
    from memory_retrieval_feedback_v2575 import build_memory_retrieval_feedback
    from mental_activity_timeline_v2511 import MentalActivityTimeline
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from memory_retrieval_feedback_v2575 import build_memory_retrieval_feedback
    from mental_activity_timeline_v2511 import MentalActivityTimeline
CONTRACT_VERSION='v2576.0'
def _root(runtime_root:str|Path|None=None)->Path:
    if runtime_root is not None:return Path(runtime_root).expanduser().resolve()
    base=Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve();return base/'cognition'
def record_memory_retrieval_observability(projection:Mapping[str,Any],*,operation_id:str,runtime_root:str|Path|None=None)->dict[str,Any]:
    op=str(operation_id or '').strip()[:160]
    if not op: raise ValueError('operation_id_required')
    root=_root(runtime_root);root.mkdir(parents=True,exist_ok=True);feedback=build_memory_retrieval_feedback(projection)
    state={'contract_version':CONTRACT_VERSION,'operation_ref_digest':__import__('hashlib').sha256(op.encode()).hexdigest(),'feedback':feedback,'raw_memory_text_stored':False,'raw_prompt_stored':False}
    write_json_atomic(root/'memory_retrieval_observability_v2576.json',state,expected_type=dict,sort_keys=True)
    transition={'grounded_correction':'retrieval_grounded','grounded_relevant_memory':'retrieval_grounded','weak_context_only':'retrieval_weak','no_useful_memory':'retrieval_empty'}.get(feedback['state'],'retrieval_observed')
    timeline=MentalActivityTimeline(root).append(f'memory-retrieval:{op}:{feedback["feedback_digest"][:20]}',event_kind='memory',transition=transition,source_digest=feedback['feedback_digest'],subject_ref=state['operation_ref_digest'][:24],outcome_code=feedback['state'].upper())
    return {'ok':True,'contract_version':CONTRACT_VERSION,'feedback':feedback,'timeline_status':timeline.get('status'),'raw_memory_text_stored':False,'raw_prompt_stored':False,'memory_mutated':False,'authority_granted':False}
def load_memory_retrieval_observability(runtime_root:str|Path|None=None)->dict[str,Any]:
    root=_root(runtime_root);state=load_json_file(root/'memory_retrieval_observability_v2576.json',{},expected_type=dict)
    if not state:return {'ok':True,'contract_version':CONTRACT_VERSION,'present':False,'feedback':{},'operation_ref_digest':'','raw_memory_text_stored':False}
    return {'ok':True,'contract_version':CONTRACT_VERSION,'present':True,'feedback':dict(state.get('feedback') or {}),'operation_ref_digest':str(state.get('operation_ref_digest') or ''),'raw_memory_text_stored':False}
__all__=['CONTRACT_VERSION','record_memory_retrieval_observability','load_memory_retrieval_observability']
