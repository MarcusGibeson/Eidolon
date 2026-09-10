from __future__ import annotations
from pathlib import Path
from typing import Any,Mapping
from collections import Counter
import hashlib,json,os
try:
 from json_storage import load_json_file, write_json_atomic
except ImportError:
 from json_storage import load_json_file, write_json_atomic
CONTRACT_VERSION='v2691.0';MAX_ROWS=96
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _path(runtime_root=None)->Path:
 if runtime_root is not None: root=Path(runtime_root).expanduser().resolve()
 else: root=Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'cognition'
 return root/'conversation_target_outcome_history_v2691.json'
def append_conversation_target_outcome(outcome:Mapping[str,Any],*,operation_id:str,runtime_root=None)->dict[str,Any]:
 if not str(operation_id or '').strip():raise ValueError('operation_id_required')
 row={'operation_ref_digest':hashlib.sha256(str(operation_id).encode()).hexdigest(),'repair_signal_count':int(outcome.get('repair_signal_count') or 0),'repair_signals':[str(x)[:80] for x in outcome.get('repair_signals') or []],'severity':str(outcome.get('severity') or 'none')[:20],'outcome_digest':str(outcome.get('outcome_digest') or '')[:64],'raw_response_stored':False};row['row_digest']=_digest(row)
 path=_path(runtime_root);path.parent.mkdir(parents=True,exist_ok=True);state=load_json_file(path,{'rows':[]},expected_type=dict);rows=list(state.get('rows') or []);rows.append(row);rows=rows[-MAX_ROWS:];payload={'contract_version':CONTRACT_VERSION,'rows':rows,'raw_response_stored':False,'raw_prompt_stored':False,'authority_granted':False};payload['history_digest']=_digest(payload);write_json_atomic(path,payload,expected_type=dict,sort_keys=True);return payload
def build_conversation_target_learning_profile(runtime_root=None)->dict[str,Any]:
 state=load_json_file(_path(runtime_root),{'rows':[]},expected_type=dict);rows=list(state.get('rows') or [])[-MAX_ROWS:];counts=Counter(sig for r in rows if isinstance(r,Mapping) for sig in (r.get('repair_signals') or []));repair_events=sum(bool(r.get('repair_signal_count')) for r in rows if isinstance(r,Mapping));high=sum(str(r.get('severity'))=='high' for r in rows if isinstance(r,Mapping));
 if len(rows)<4:status='insufficient_history'
 elif high>=3 or repair_events>=5:status='conversation_coherence_review_due'
 elif repair_events:status='mixed_coherence_evidence'
 else:status='stable_no_repairs_observed'
 out={'ok':True,'contract_version':CONTRACT_VERSION,'observation_count':len(rows),'repair_event_count':repair_events,'high_severity_count':high,'top_repair_signals':[{'signal':k,'count':v} for k,v in counts.most_common(4)],'state':status,'automatic_policy_change':False,'raw_response_stored':False,'authority_granted':False};out['profile_digest']=_digest(out);return out
__all__=['CONTRACT_VERSION','append_conversation_target_outcome','build_conversation_target_learning_profile']
