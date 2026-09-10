from __future__ import annotations
"""v1314 source-declared runtime topology, never a live runtime claim."""
from pathlib import Path
from project_evidence_store import *
from symbol_graph import build_symbol_graph,load_symbol_graph
from repository_inventory import load_repository_inventory
CONTRACT_VERSION='v1314.8'
def _path(wid,runtime_root=None):return evidence_root('runtime_topology',runtime_root)/'records'/f'{wid}.json'
def build_runtime_topology(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None):
 pub=build_symbol_graph(source_root,runtime_root=runtime_root,now_unix=now_unix)['symbol_graph'];wid=pub['workspace_digest'];existing=load_runtime_topology(wid,runtime_root=runtime_root)
 if existing and existing.get('source_manifest_digest')==pub.get('source_manifest_digest'):return {'ok':True,'status':'runtime_topology_current','runtime_topology':existing,'action_executed':False,**DENIED_AUTHORITY}
 sg=load_symbol_graph(wid,runtime_root=runtime_root,include_private=True);inv=load_repository_inventory(wid,runtime_root=runtime_root,include_private=True);nodes=[]
 for s in sg.get('symbols') or []:
  if s.get('kind')=='route':nodes.append({'kind':'route','source_path_digest':s.get('relative_path_digest'),'evidence_digest':s.get('symbol_id')})
 for f in inv.get('files') or []:
  rel=f['relative_path'].lower();kind='user_surface' if any(x in rel for x in ('dashboard','ui','.html','.css')) else 'storage' if any(x in rel for x in ('storage','database','schema','migration')) else 'cli' if rel.endswith('.py') and any(x in rel for x in ('cli','command','eidolon.py')) else ''
  if kind:nodes.append({'kind':kind,'source_path_digest':f['relative_path_digest'],'evidence_digest':f['content_digest']})
 nodes=list({(x['kind'],x['source_path_digest']):x for x in nodes}.values())[:4096];row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':pub['source_manifest_digest'],'nodes':nodes,'node_count':len(nodes),'runtime_behavior_observed':False,'ports_probed':False,'processes_probed':False,'provider_contacted':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'runtime_topology_ready','runtime_topology':public_runtime_topology(row),'action_executed':False,**DENIED_AUTHORITY}
def public_runtime_topology(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'node_count':int(row.get('node_count',0)),'kind_counts':{k:sum(1 for x in row.get('nodes') or [] if x.get('kind')==k) for k in ('route','user_surface','storage','cli')},'runtime_behavior_observed':False,'ports_probed':False,'processes_probed':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_runtime_topology(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (dict(row) if include_private else public_runtime_topology(row)) if row and valid(row) else {}
__all__=['CONTRACT_VERSION','build_runtime_topology','load_runtime_topology','public_runtime_topology']
