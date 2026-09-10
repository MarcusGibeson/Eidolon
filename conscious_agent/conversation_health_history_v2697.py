from __future__ import annotations
"""v2697 bounded content-free conversation-health history."""
from pathlib import Path
from typing import Any,Mapping
import hashlib,json,os
try:
 from json_storage import load_json_file, write_json_atomic
except ImportError:
 from json_storage import load_json_file, write_json_atomic
CONTRACT_VERSION='v2697.0';MAX_ROWS=128
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _path(runtime_root=None)->Path:
 if runtime_root is not None:root=Path(runtime_root).expanduser().resolve()
 else:root=Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
 return root/'conversation_health_history_v2697.json'
def append_conversation_health(health:Mapping[str,Any],*,operation_id:str,runtime_root=None)->dict[str,Any]:
 if not str(operation_id or '').strip():raise ValueError('operation_id_required')
 row={'operation_ref_digest':hashlib.sha256(str(operation_id).encode()).hexdigest(),'state':str(health.get('state') or 'nominal')[:20],'concern_count':max(0,int(health.get('concern_count') or 0)),'concerns':[str(x)[:80] for x in (health.get('concerns') or [])[:6]],'health_digest':str(health.get('health_digest') or '')[:64],'raw_conversation_text_stored':False,'authority_granted':False};row['row_digest']=_digest(row)
 path=_path(runtime_root);path.parent.mkdir(parents=True,exist_ok=True);state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or []);rows.append(row);rows=rows[-MAX_ROWS:];payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_conversation_text_stored':False,'authority_granted':False};payload['history_digest']=_digest(payload);write_json_atomic(path,payload,expected_type=dict,sort_keys=True);return payload
def load_conversation_health_history(runtime_root=None)->dict[str,Any]:
 state=load_json_file(_path(runtime_root),{'rows':[]},expected_type=dict);return {'contract_version':CONTRACT_VERSION,'rows':list(state.get('rows') or [])[-MAX_ROWS:],'raw_conversation_text_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','append_conversation_health','load_conversation_health_history']
