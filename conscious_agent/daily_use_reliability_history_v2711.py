from __future__ import annotations
"""v2711 bounded content-free daily-use reliability history and trend."""
from pathlib import Path
from typing import Any,Mapping
import hashlib,json,os
try: from json_storage import load_json_file, write_json_atomic
except ImportError: from json_storage import load_json_file, write_json_atomic
CONTRACT_VERSION='v2711.0';MAX_ROWS=192
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _path(root=None)->Path:
    if root is not None:r=Path(root).expanduser().resolve()
    else:r=Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
    return r/'daily_use_reliability_history_v2711.json'
def append_daily_use_reliability(reliability:Mapping[str,Any],*,operation_id:str,runtime_root=None)->dict[str,Any]:
    if not str(operation_id or '').strip():raise ValueError('operation_id_required')
    row={'operation_ref_digest':hashlib.sha256(str(operation_id).encode()).hexdigest(),'state':str(reliability.get('state') or 'insufficient_data')[:32],'concern_count':int(reliability.get('concern_count') or 0),'strength_count':int(reliability.get('strength_count') or 0),'unknown_dimension_count':int(reliability.get('unknown_dimension_count') or 0),'reliability_digest':str(reliability.get('reliability_digest') or '')[:64],'raw_conversation_text_stored':False,'authority_granted':False};row['row_digest']=_digest(row)
    path=_path(runtime_root);path.parent.mkdir(parents=True,exist_ok=True);state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or []);rows.append(row);rows=rows[-MAX_ROWS:];payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_conversation_text_stored':False,'authority_granted':False};payload['history_digest']=_digest(payload);write_json_atomic(path,payload,expected_type=dict,sort_keys=True);return payload
def load_daily_use_reliability_history(runtime_root=None)->dict[str,Any]:
    s=load_json_file(_path(runtime_root),{'rows':[]},expected_type=dict);return {'contract_version':CONTRACT_VERSION,'rows':list(s.get('rows') or [])[-MAX_ROWS:],'raw_conversation_text_stored':False,'authority_granted':False}
def build_daily_use_reliability_trend(rows,*,window:int=10)->dict[str,Any]:
    items=[dict(r) for r in rows if isinstance(r,Mapping)];w=max(3,min(32,int(window or 10)));recent=items[-w:];prior=items[-2*w:-w]
    score=lambda rs:sum(-3 if r.get('state')=='degraded' else -1 if r.get('state')=='attention' else 1 if r.get('state')=='nominal' else 0 for r in rs)
    a,b=score(recent),score(prior)
    direction='insufficient_history' if not prior or len(recent)<3 else ('improving' if a>b+1 else 'worsening' if a+1<b else 'stable')
    out={'ok':True,'contract_version':CONTRACT_VERSION,'direction':direction,'recent_score':a,'prior_score':b,'recent_observations':len(recent),'prior_observations':len(prior),'automatic_policy_change':False,'raw_conversation_text_stored':False,'authority_granted':False};out['trend_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','append_daily_use_reliability','load_daily_use_reliability_history','build_daily_use_reliability_trend']
