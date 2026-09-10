from __future__ import annotations
"""v1313 internal dependency graph over repository/symbol evidence."""
from pathlib import Path
from project_evidence_store import *
from symbol_graph import build_symbol_graph,load_symbol_graph
from repository_inventory import load_repository_inventory
CONTRACT_VERSION='v1313.8'
def _path(wid,runtime_root=None):return evidence_root('dependency_graph',runtime_root)/'records'/f'{wid}.json'
def _target_candidates(target):
 t=str(target or '').lstrip('.').replace('.','/');return {t+'.py',t+'/__init__.py',t+'.js',t+'.ts'}
def build_dependency_graph(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None):
 pub=build_symbol_graph(source_root,runtime_root=runtime_root,now_unix=now_unix)['symbol_graph'];wid=pub['workspace_digest'];existing=load_dependency_graph(wid,runtime_root=runtime_root)
 if existing and existing.get('source_manifest_digest')==pub.get('source_manifest_digest'):return {'ok':True,'status':'dependency_graph_current','dependency_graph':existing,'action_executed':False,**DENIED_AUTHORITY}
 sg=load_symbol_graph(wid,runtime_root=runtime_root,include_private=True);inv=load_repository_inventory(wid,runtime_root=runtime_root,include_private=True);byrel={x['relative_path']:x for x in inv.get('files') or []};edges=[]
 for e in sg.get('edges') or []:
  if e.get('edge_kind')!='import':continue
  matches=[byrel[x] for x in _target_candidates(e.get('target')) if x in byrel]
  for m in matches:edges.append({'source_path_digest':e.get('source_path_digest'),'target_path_digest':m['relative_path_digest'],'target':str(e.get('target') or ''),'kind':'internal_import'})
 desc=write_collection('dependency_graph',wid,'edges',edges,runtime_root) if len(edges)>256 else {'sharded':False,'items':edges};row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':pub['source_manifest_digest'],'edge_collection':desc,'edge_count':len(edges),'graph_sharded':bool(desc.get('sharded')),'provider_contacted':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'dependency_graph_ready','dependency_graph':public_dependency_graph(row),'action_executed':False,**DENIED_AUTHORITY}
def _inflate(row,runtime_root=None):out=dict(row);out['edges']=read_collection('dependency_graph',row['workspace_digest'],'edges',row.get('edge_collection') or {},runtime_root);return out
def public_dependency_graph(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'edge_count':row.get('edge_count',0),'graph_sharded':bool(row.get('graph_sharded')),'provider_contacted':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_dependency_graph(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (_inflate(row,runtime_root) if include_private else public_dependency_graph(row)) if row and valid(row) else {}
__all__=['CONTRACT_VERSION','build_dependency_graph','load_dependency_graph','public_dependency_graph']
