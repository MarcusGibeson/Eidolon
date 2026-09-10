from __future__ import annotations
"""v2664 crash-safe runtime persistence for bounded synthetic rehearsal history."""
from pathlib import Path
from typing import Any,Mapping
import hashlib,json,os,tempfile
CONTRACT_VERSION='v2664.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _root(runtime_root=None)->Path:
 if runtime_root is not None:return Path(runtime_root).expanduser().resolve()
 return (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'development')
def persist_rehearsal_history(history:Mapping[str,Any],runtime_root=None)->dict[str,Any]:
 if not history.get('synthetic_evidence_only'):raise ValueError('synthetic_history_required')
 root=_root(runtime_root);root.mkdir(parents=True,exist_ok=True);path=root/'developer_project_rehearsal_history.json';fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=str(root))
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(dict(history),f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  try:os.unlink(name)
  except FileNotFoundError:pass
 out={'ok':True,'contract_version':CONTRACT_VERSION,'history_digest':str(history.get('history_digest') or _digest(history))[:64],'row_count':len(history.get('rows') or []),'runtime_only':True,'real_outcome_history_modified':False,'source_mutated':False,'authority_granted':False};out['persistence_digest']=_digest(out);return out
def load_rehearsal_history(runtime_root=None)->dict[str,Any]:
 try:
  v=json.loads((_root(runtime_root)/'developer_project_rehearsal_history.json').read_text(encoding='utf-8'))
  if isinstance(v,dict) and v.get('synthetic_evidence_only'):return v
 except (OSError,ValueError,TypeError):pass
 return {'ok':True,'contract_version':CONTRACT_VERSION,'rows':[],'count':0,'synthetic_evidence_only':True,'real_outcome_history':False,'authority_granted':False}
__all__=['CONTRACT_VERSION','persist_rehearsal_history','load_rehearsal_history']
