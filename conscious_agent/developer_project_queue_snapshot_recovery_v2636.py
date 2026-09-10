from __future__ import annotations
"""v2636 exact-generation queue snapshot validation/recovery."""
from pathlib import Path
from typing import Any
import hashlib,json,os
CONTRACT_VERSION='v2636.0'
def _digest(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
def _root(runtime_root=None)->Path:
 if runtime_root is not None:return Path(runtime_root).expanduser().resolve()
 return (Path(os.environ.get('EIDOLON_DATA_DIR') or Path(__file__).resolve().parents[1]/'data').expanduser().resolve()/'development')
def _read(path:Path):
 try:
  v=json.loads(path.read_text(encoding='utf-8'));return v if isinstance(v,dict) else None
 except (OSError,ValueError,TypeError):return None
def recover_committed_project_queue_snapshot(*,runtime_root=None)->dict[str,Any]:
 root=_root(runtime_root);ptr=_read(root/'developer_project_queue_current.json') or {};gen=int(ptr.get('generation') or 0);snap=root/'developer_project_queue_snapshots'/str(gen)
 manifest=_read(snap/'manifest.json') if gen else None;reasons=[];artifacts={}
 if not manifest:reasons.append('missing_commit_manifest')
 elif str(ptr.get('manifest_digest') or '')!=str(manifest.get('manifest_digest') or ''):reasons.append('commit_pointer_digest_mismatch')
 for key in ('queue','readiness','history'):
  v=_read(snap/(key+'.json')) if manifest else None
  if v is None:reasons.append('missing_or_invalid_'+key)
  elif _digest(v)!=str((manifest.get('artifact_digests') or {}).get(key) or ''):reasons.append(key+'_digest_mismatch')
  else:artifacts[key]=v
 ok=not reasons and len(artifacts)==3
 out={'ok':ok,'contract_version':CONTRACT_VERSION,'generation':gen,'queue':artifacts.get('queue',{}) if ok else {},'readiness':artifacts.get('readiness',{}) if ok else {},'history':artifacts.get('history',{}) if ok else {},'failure_reasons':reasons[:8],'operator_review_required':not ok,'automatic_fallback_permitted':False,'automatic_repair_permitted':False,'campaign_started':False,'authority_granted':False};out['recovery_digest']=_digest({k:v for k,v in out.items() if k not in ('queue','readiness','history')});return out
__all__=['CONTRACT_VERSION','recover_committed_project_queue_snapshot']
