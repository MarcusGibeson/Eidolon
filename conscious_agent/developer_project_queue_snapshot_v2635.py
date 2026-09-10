from __future__ import annotations
"""v2635 generation-bound commit manifest for developer queue persistence."""
from pathlib import Path
from typing import Any, Mapping
import hashlib,json,os,tempfile,time
CONTRACT_VERSION='v2635.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _root(runtime_root=None)->Path:
 if runtime_root is not None:return Path(runtime_root).expanduser().resolve()
 return (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'development')
def _atomic(path:Path,value:Mapping[str,Any])->None:
 path.parent.mkdir(parents=True,exist_ok=True);fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=str(path.parent))
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(dict(value),f,sort_keys=True,separators=(',',':'));f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  try:os.unlink(name)
  except FileNotFoundError:pass
def commit_project_queue_snapshot(*,queue:Mapping[str,Any],readiness:Mapping[str,Any],history:Mapping[str,Any],runtime_root=None,generation:int|None=None)->dict[str,Any]:
 root=_root(runtime_root);gen=max(1,int(generation or time.time_ns()))
 artifacts={'queue':dict(queue),'readiness':dict(readiness),'history':dict(history)};digests={k:_digest(v) for k,v in artifacts.items()}
 snap=root/'developer_project_queue_snapshots'/str(gen);snap.mkdir(parents=True,exist_ok=True)
 for k,v in artifacts.items():_atomic(snap/(k+'.json'),v)
 manifest={'contract_version':CONTRACT_VERSION,'generation':gen,'artifact_digests':digests,'queue_digest':str(queue.get('queue_digest') or '')[:64],'committed':True,'runtime_only':True,'authority_granted':False};manifest['manifest_digest']=_digest(manifest);_atomic(snap/'manifest.json',manifest);_atomic(root/'developer_project_queue_current.json',{'generation':gen,'manifest_digest':manifest['manifest_digest']})
 return {'ok':True,**manifest,'snapshot_path_stored':False,'source_mutated':False,'campaign_started':False}
__all__=['CONTRACT_VERSION','commit_project_queue_snapshot']
