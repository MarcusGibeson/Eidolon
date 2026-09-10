from __future__ import annotations
"""v1311 incremental repository inventory with bounded private sharding."""
import hashlib,time
from pathlib import Path
from typing import Any
from project_evidence_store import *
CONTRACT_VERSION='v1311.8';INLINE_FILE_LIMIT=256
LANG={'.py':'python','.js':'javascript','.ts':'typescript','.html':'html','.css':'css','.java':'java','.ps1':'powershell','.sql':'sql','.json':'json','.yaml':'yaml','.yml':'yaml','.toml':'toml','.md':'markdown'}
def _path(wid,runtime_root=None):return evidence_root('repository_inventory',runtime_root)/'records'/f'{wid}.json'
def build_repository_inventory(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None)->dict[str,Any]:
 root=Path(source_root).resolve();wid=workspace_digest(root);rows=[]
 for p in iter_source_files(root):
  rel=p.relative_to(root).as_posix();b=p.read_bytes();rows.append({'relative_path':rel,'relative_path_digest':hashlib.sha256(rel.encode()).hexdigest(),'content_digest':hashlib.sha256(b).hexdigest(),'size_bytes':len(b),'suffix':p.suffix.lower(),'language':LANG.get(p.suffix.lower(),'other'),'test':p.name.startswith('test_') or '/tests/' in '/'+rel})
 rows.sort(key=lambda x:x['relative_path']);manifest=digest([(x['relative_path_digest'],x['content_digest'],x['size_bytes']) for x in rows]);old=read_json(_path(wid,runtime_root));seq=int(old.get('snapshot_sequence',0))+1 if old and valid(old) else 1;desc={'sharded':False,'items':rows} if len(rows)<=INLINE_FILE_LIMIT else write_collection('repository_inventory',wid,'files',rows,runtime_root)
 counts={}
 for x in rows:counts[x['language']]=counts.get(x['language'],0)+1
 row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':manifest,'snapshot_sequence':seq,'observed_unix':int(time.time() if now_unix is None else now_unix),'file_collection':desc,'file_count':len(rows),'language_counts':counts,'test_file_count':sum(x['test'] for x in rows),'generated_content_count':0,'runtime_state_excluded':True,'source_paths_public':False,'raw_source_content_persisted':False,'read_only_inventory':True,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'repository_inventory_ready','inventory':public_repository_inventory(row),'action_executed':False,**DENIED_AUTHORITY}
def _inflate(row,runtime_root=None):
 out=dict(row);out['files']=read_collection('repository_inventory',str(row.get('workspace_digest')), 'files',row.get('file_collection') or {},runtime_root);return out
def public_repository_inventory(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'snapshot_sequence':int(row.get('snapshot_sequence',0)),'file_count':int(row.get('file_count',0)),'language_counts':dict(row.get('language_counts') or {}),'test_file_count':int(row.get('test_file_count',0)),'inventory_sharded':bool((row.get('file_collection') or {}).get('sharded')),'source_paths_exposed':False,'raw_source_content_exposed':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_repository_inventory(workspace_digest_value,*,runtime_root=None,include_private=False):
 row=read_json(_path(workspace_digest_value,runtime_root));return (_inflate(row,runtime_root) if include_private else public_repository_inventory(row)) if row and valid(row) else {}
def assess_repository_inventory_freshness(source_root:str|Path,*,runtime_root=None):
 root=Path(source_root).resolve();wid=workspace_digest(root);old=load_repository_inventory(wid,runtime_root=runtime_root);new=build_repository_inventory(root,runtime_root=runtime_root)['inventory'];return {'ok':bool(old),'status':'current' if old and old.get('source_manifest_digest')==new.get('source_manifest_digest') else ('stale' if old else 'missing'),'current':bool(old) and old.get('source_manifest_digest')==new.get('source_manifest_digest'),'action_executed':False,**DENIED_AUTHORITY}
__all__=['CONTRACT_VERSION','build_repository_inventory','load_repository_inventory','public_repository_inventory','assess_repository_inventory_freshness']
