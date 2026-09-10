from __future__ import annotations
"""Shared content-minimized external-runtime evidence storage for v1311+ project understanding."""
import json,hashlib,os,tempfile
from pathlib import Path
from typing import Any,Iterable
from ordinary_chat_development_campaign import _store_root
from cognitive_coding_foundations import digest,DENIED_AUTHORITY
CHUNK_TARGET_BYTES=180_000
SKIP_PARTS={'.git','__pycache__','data','.venv','venv','node_modules','.pytest_cache','.mypy_cache','.ruff_cache','logs','cache','caches'}

def evidence_root(kind:str,runtime_root=None)->Path:return _store_root(runtime_root)/'project_understanding_evidence'/kind
def atomic_json(path:Path,value:Any)->None:
 path.parent.mkdir(parents=True,exist_ok=True);payload=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode();fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=str(path.parent));os.close(fd);Path(tmp).write_bytes(payload);os.replace(tmp,path)
def read_json(path:Path)->dict[str,Any]:
 try:x=json.loads(path.read_text())
 except (OSError,json.JSONDecodeError):return {}
 return x if isinstance(x,dict) else {}
def seal(row:dict[str,Any])->dict[str,Any]:out=dict(row);out.pop('record_digest',None);out['record_digest']=digest(out);return out
def valid(row:dict[str,Any])->bool:
 body=dict(row);sup=body.pop('record_digest','');return sup==digest(body)
def iter_source_files(root:Path)->Iterable[Path]:
 for p in root.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(root)
  if any(part in SKIP_PARTS for part in rel.parts):continue
  yield p
def workspace_digest(root:Path)->str:return hashlib.sha256(str(root.resolve()).encode()).hexdigest()
def write_collection(kind:str,key:str,name:str,rows:list[dict[str,Any]],runtime_root=None)->dict[str,Any]:
 base=evidence_root(kind,runtime_root)/'chunks'/key/name;base.mkdir(parents=True,exist_ok=True);chunks=[];cur=[];size=2
 def flush():
  nonlocal cur,size
  if not cur:return
  idx=len(chunks);payload={'items':cur};payload['chunk_digest']=digest(payload);atomic_json(base/f'{idx:05d}.json',payload);chunks.append(payload['chunk_digest']);cur=[];size=2
 for row in rows:
  n=len(json.dumps(row,sort_keys=True,separators=(',',':')).encode())+1
  if cur and size+n>CHUNK_TARGET_BYTES:flush()
  cur.append(row);size+=n
 flush();desc={'sharded':True,'item_count':len(rows),'chunk_count':len(chunks),'collection_digest':digest(chunks),'chunk_digests':chunks if len(chunks)<=64 else []};return desc
def read_collection(kind:str,key:str,name:str,desc:dict[str,Any],runtime_root=None)->list[dict[str,Any]]:
 if not desc.get('sharded'):return list(desc.get('items') or [])
 out=[];dig=[];base=evidence_root(kind,runtime_root)/'chunks'/key/name
 for i in range(int(desc.get('chunk_count') or 0)):
  row=read_json(base/f'{i:05d}.json');body=dict(row);sup=body.pop('chunk_digest','');
  if sup!=digest(body):return []
  dig.append(sup);out.extend(body.get('items') or [])
 if len(out)!=int(desc.get('item_count') or 0) or digest(dig)!=desc.get('collection_digest'):return []
 return out
__all__=['CHUNK_TARGET_BYTES','SKIP_PARTS','evidence_root','atomic_json','read_json','seal','valid','iter_source_files','workspace_digest','write_collection','read_collection','digest','DENIED_AUTHORITY']
