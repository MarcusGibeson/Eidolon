from __future__ import annotations
"""v2590 content-free runtime observability for conversation-context attribution."""
from pathlib import Path
from typing import Any, Mapping
import os, hashlib, json
try:
    from json_storage import load_json_file, write_json_atomic
    from mental_activity_timeline_v2511 import MentalActivityTimeline
except ImportError:
    from json_storage import load_json_file, write_json_atomic
    from mental_activity_timeline_v2511 import MentalActivityTimeline
CONTRACT_VERSION='v2590.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _root(runtime_root:str|Path|None=None)->Path:
    if runtime_root is not None:return Path(runtime_root).expanduser().resolve()
    return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def record_conversation_context_observability(attribution:Mapping[str,Any], arbitration:Mapping[str,Any], sufficiency:Mapping[str,Any], *, operation_id:str, runtime_root:str|Path|None=None)->dict[str,Any]:
    if not str(operation_id or '').strip():raise ValueError('operation_id_required')
    root=_root(runtime_root);root.mkdir(parents=True,exist_ok=True);op=hashlib.sha256(str(operation_id).encode()).hexdigest()
    state={'contract_version':CONTRACT_VERSION,'operation_ref_digest':op,'state':str(sufficiency.get('state') or 'unknown')[:48],'budget_pressure':float(attribution.get('budget_pressure') or 0.0),'headroom_tokens':int(attribution.get('headroom_tokens') or 0),'memories_included':int(attribution.get('memories_included') or 0),'history_turns_included':int(attribution.get('history_turns_included') or 0),'advisory_count':int(arbitration.get('advisory_count') or 0),'should_preserve_uncertainty':bool(sufficiency.get('should_preserve_uncertainty')),'raw_prompt_stored':False,'raw_context_stored':False,'raw_memory_text_stored':False,'authority_granted':False}
    state['state_digest']=_digest(state);write_json_atomic(root/'conversation_context_observability_v2590.json',state,expected_type=dict,sort_keys=True)
    MentalActivityTimeline(root).append(f'context:{op[:20]}:{state["state_digest"][:20]}',event_kind='cognitive',transition='context_'+state['state'],source_digest=state['state_digest'],subject_ref=op[:24],outcome_code=state['state'].upper())
    return {'ok':True,'contract_version':CONTRACT_VERSION,**state,'context_mutated':False}
def load_conversation_context_observability(runtime_root:str|Path|None=None)->dict[str,Any]:
    state=load_json_file(_root(runtime_root)/'conversation_context_observability_v2590.json',{},expected_type=dict)
    return {'ok':True,'contract_version':CONTRACT_VERSION,'present':bool(state),**(dict(state) if state else {}),'raw_prompt_stored':False,'raw_context_stored':False}
__all__=['CONTRACT_VERSION','record_conversation_context_observability','load_conversation_context_observability']
