from __future__ import annotations
"""v2702 bounded content-free response-quality history."""
from pathlib import Path
from typing import Any, Mapping
import hashlib, json, os
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic
CONTRACT_VERSION='v2702.0';MAX_ROWS=160

def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _path(runtime_root=None)->Path:
    if runtime_root is not None: root=Path(runtime_root).expanduser().resolve()
    else: root=Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
    return root/'response_quality_history_v2702.json'
def append_response_quality(quality:Mapping[str,Any], attribution:Mapping[str,Any], *, operation_id:str, runtime_root=None)->dict[str,Any]:
    op=str(operation_id or '').strip()
    if not op: raise ValueError('operation_id_required')
    row={'operation_ref_digest':hashlib.sha256(op.encode()).hexdigest(),'state':str(quality.get('state') or 'unknown')[:32],
         'evidence_strength':str(quality.get('evidence_strength') or 'none')[:20],
         'positive_signal_count':max(0,int(attribution.get('positive_signal_count') or 0)),
         'negative_signal_count':max(0,int(attribution.get('negative_signal_count') or 0)),
         'eligible_for_positive_learning':bool(quality.get('eligible_for_positive_learning')),
         'eligible_for_negative_learning':bool(quality.get('eligible_for_negative_learning')),
         'quality_digest':str(quality.get('quality_digest') or '')[:64],
         'outcome_digest':str(attribution.get('outcome_digest') or '')[:64],
         'raw_conversation_text_stored':False,'authority_granted':False}
    row['row_digest']=_digest(row)
    path=_path(runtime_root);path.parent.mkdir(parents=True,exist_ok=True)
    state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or []);rows.append(row);rows=rows[-MAX_ROWS:]
    payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_conversation_text_stored':False,'authority_granted':False};payload['history_digest']=_digest(payload)
    write_json_atomic(path,payload,expected_type=dict,sort_keys=True);return payload

def append_retrospective_response_quality(retrospective:Mapping[str,Any],*,runtime_root=None)->dict[str,Any]:
    target=str(retrospective.get('target_operation_ref_digest') or '')[:64]
    if not target or not bool(retrospective.get('evidence_recorded')):
        return load_response_quality_history(runtime_root)
    row={'operation_ref_digest':target,'row_type':'retrospective_revision','state':str(retrospective.get('state') or 'mixed_evidence')[:32],
         'evidence_strength':'explicit','positive_signal_count':0,'negative_signal_count':1 if bool(retrospective.get('adverse_evidence')) else 0,
         'eligible_for_positive_learning':False,'eligible_for_negative_learning':bool(retrospective.get('adverse_evidence')),
         'evidence_operation_ref_digest':str(retrospective.get('evidence_operation_ref_digest') or '')[:64],
         'retrospective_digest':str(retrospective.get('retrospective_digest') or '')[:64],
         'raw_conversation_text_stored':False,'authority_granted':False}
    row['row_digest']=_digest(row)
    path=_path(runtime_root);path.parent.mkdir(parents=True,exist_ok=True);state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or []);rows.append(row);rows=rows[-MAX_ROWS:]
    payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_conversation_text_stored':False,'authority_granted':False};payload['history_digest']=_digest(payload);write_json_atomic(path,payload,expected_type=dict,sort_keys=True);return payload


def append_positive_retrospective_quality(retrospective:Mapping[str,Any],*,runtime_root=None)->dict[str,Any]:
    target=str(retrospective.get('target_operation_ref_digest') or '')[:64]
    if not target or not bool(retrospective.get('evidence_recorded')):
        return load_response_quality_history(runtime_root)
    row={'operation_ref_digest':target,'row_type':'retrospective_revision','state':'supported_success','evidence_strength':'explicit',
         'positive_signal_count':1,'negative_signal_count':0,'eligible_for_positive_learning':True,'eligible_for_negative_learning':False,
         'evidence_operation_ref_digest':str(retrospective.get('evidence_operation_ref_digest') or '')[:64],
         'retrospective_digest':str(retrospective.get('retrospective_digest') or '')[:64],
         'raw_conversation_text_stored':False,'authority_granted':False}
    row['row_digest']=_digest(row);path=_path(runtime_root);path.parent.mkdir(parents=True,exist_ok=True);state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or []);rows.append(row);rows=rows[-MAX_ROWS:]
    payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_conversation_text_stored':False,'authority_granted':False};payload['history_digest']=_digest(payload);write_json_atomic(path,payload,expected_type=dict,sort_keys=True);return payload

def load_response_quality_history(runtime_root=None)->dict[str,Any]:
    state=load_json_file(_path(runtime_root),{'rows':[]},expected_type=dict)
    return {'contract_version':CONTRACT_VERSION,'rows':list(state.get('rows') or [])[-MAX_ROWS:],'raw_conversation_text_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','append_response_quality','append_retrospective_response_quality','append_positive_retrospective_quality','load_response_quality_history']
