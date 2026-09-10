from __future__ import annotations
"""v2686 persist only content-free response-grounding audit summaries."""
from pathlib import Path
from typing import Any, Mapping
import hashlib,json,os
try:
 from json_storage import load_json_file, write_json_atomic
except ImportError:
 from json_storage import load_json_file, write_json_atomic
CONTRACT_VERSION='v2686.0';MAX_ROWS=64
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _path(runtime_root=None)->Path:
 if runtime_root is not None: root=Path(runtime_root).expanduser().resolve()
 else: root=Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
 return root/'response_grounding_output_audit_history_v2686.json'
def record_response_grounding_output_audit(audit:Mapping[str,Any],*,operation_id:str,runtime_root=None)->dict[str,Any]:
 if not str(operation_id or '').strip(): raise ValueError('operation_id_required')
 row={'operation_ref_digest':hashlib.sha256(str(operation_id).encode()).hexdigest(),'ok':bool(audit.get('ok')),'concern_count':max(0,int(audit.get('concern_count') or 0)),'memory_claim_shape_count':max(0,int(audit.get('memory_claim_shape_count') or 0)),'execution_claim_shape_count':max(0,int(audit.get('execution_claim_shape_count') or 0)),'concerns':[str(x)[:80] for x in (audit.get('concerns') or [])[:4]],'audit_digest':str(audit.get('audit_digest') or '')[:64],'raw_response_stored':False,'raw_prompt_stored':False,'authority_granted':False};row['row_digest']=_digest(row)
 path=_path(runtime_root);path.parent.mkdir(parents=True,exist_ok=True);state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or []);rows.append(row);rows=rows[-MAX_ROWS:];payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_response_stored':False,'raw_prompt_stored':False,'authority_granted':False};payload['history_digest']=_digest(payload);write_json_atomic(path,payload,expected_type=dict,sort_keys=True);return {'ok':True,'contract_version':CONTRACT_VERSION,'row_count':len(rows),'latest':row,'history_digest':payload['history_digest'],'authority_granted':False}
def load_response_grounding_output_audit_observability(runtime_root=None)->dict[str,Any]:
 state=load_json_file(_path(runtime_root),{'rows':[]},expected_type=dict);rows=list(state.get('rows') or [])[-MAX_ROWS:];concerns=sum(int(r.get('concern_count') or 0) for r in rows if isinstance(r,Mapping));return {'ok':True,'contract_version':CONTRACT_VERSION,'observation_count':len(rows),'concern_event_count':sum(bool(r.get('concern_count')) for r in rows if isinstance(r,Mapping)),'total_concern_count':concerns,'latest':dict(rows[-1]) if rows else {},'raw_response_stored':False,'raw_prompt_stored':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','record_response_grounding_output_audit','load_response_grounding_output_audit_observability']
