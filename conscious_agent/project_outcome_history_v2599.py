from __future__ import annotations
"""v2599 bounded, content-minimized history of reviewed project outcomes."""
from pathlib import Path
from typing import Any, Mapping
from datetime import datetime, timezone
import os, hashlib, json
try:
    from json_storage import load_json_file, write_json_atomic
except ImportError:
    from json_storage import load_json_file, write_json_atomic
CONTRACT_VERSION='v2599.0';MAX_ROWS=128
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _root(r=None):
    if r is not None:return Path(r).expanduser().resolve()
    return Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
def append_project_outcome_history(review:Mapping[str,Any], *, strategy_code:str='unspecified', predicted_value:float|None=None, realized_value:float|None=None, effort_units:float|None=None, runtime_root=None)->dict[str,Any]:
    rd=str(review.get('review_digest') or '');gd=str(review.get('goal_digest') or '')
    if len(rd)!=64 or len(gd)!=64:raise ValueError('bound_review_required')
    root=_root(runtime_root);root.mkdir(parents=True,exist_ok=True);path=root/'project_outcome_history_v2599.json';state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or [])
    row={'recorded_at':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'project_ref_digest':hashlib.sha256(str(review.get('project_id') or '').encode()).hexdigest(),'goal_digest':gd,'review_digest':rd,'strategy_code':str(strategy_code or 'unspecified')[:80],'criteria_satisfied':bool(review.get('criteria_satisfied')),'evidence_complete':bool(review.get('evidence_complete')),'failed_required_criteria':[str(x)[:120] for x in review.get('failed_required_criteria') or []][:16],'predicted_value':None if predicted_value is None else round(float(predicted_value),4),'realized_value':None if realized_value is None else round(float(realized_value),4),'effort_units':None if effort_units is None else max(0.0,round(float(effort_units),4)),'raw_project_content_stored':False}
    row['row_digest']=_digest(row)
    if not any(isinstance(x,Mapping) and x.get('review_digest')==rd for x in rows):rows.append(row)
    rows=rows[-MAX_ROWS:];payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_project_content_stored':False,'raw_source_stored':False};payload['history_digest']=_digest(payload);write_json_atomic(path,payload,expected_type=dict,sort_keys=True)
    return {'ok':True,'contract_version':CONTRACT_VERSION,'row_count':len(rows),'history_digest':payload['history_digest'],'project_completed':False,'strategy_policy_mutated':False,'authority_granted':False}
def load_project_outcome_history(runtime_root=None)->dict[str,Any]:
    state=load_json_file(_root(runtime_root)/'project_outcome_history_v2599.json',{'rows':[]},expected_type=dict);return {'ok':True,'contract_version':CONTRACT_VERSION,'rows':list(state.get('rows') or [])[-MAX_ROWS:],'raw_project_content_stored':False}
__all__=['CONTRACT_VERSION','append_project_outcome_history','load_project_outcome_history']
