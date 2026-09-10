from __future__ import annotations
"""v1315 source-evidence behavioral workflow map."""
from pathlib import Path
from project_evidence_store import *
from runtime_topology import build_runtime_topology,load_runtime_topology
from symbol_graph import load_symbol_graph
from dependency_graph import build_dependency_graph,load_dependency_graph
CONTRACT_VERSION='v1315.8'
def _path(wid,runtime_root=None):return evidence_root('behavioral_map',runtime_root)/'records'/f'{wid}.json'
def build_behavioral_map(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None):
 pub=build_runtime_topology(source_root,runtime_root=runtime_root,now_unix=now_unix)['runtime_topology'];wid=pub['workspace_digest'];build_dependency_graph(source_root,runtime_root=runtime_root,now_unix=now_unix);existing=load_behavioral_map(wid,runtime_root=runtime_root)
 if existing and existing.get('source_manifest_digest')==pub.get('source_manifest_digest'):return {'ok':True,'status':'behavioral_map_current','behavioral_map':existing,'action_executed':False,**DENIED_AUTHORITY}
 top=load_runtime_topology(wid,runtime_root=runtime_root,include_private=True);sg=load_symbol_graph(wid,runtime_root=runtime_root,include_private=True);dep=load_dependency_graph(wid,runtime_root=runtime_root,include_private=True);work=[]
 for n in top.get('nodes') or []:
  work.append({'workflow_code':f"surface_{n.get('kind')}_{str(n.get('source_path_digest'))[:12]}",'entry_kind':n.get('kind'),'handler_path_digest':n.get('source_path_digest'),'state_mutation_observed':False,'recovery_path_observed':False,'candidate_test_digests':[]})
 # attach candidate tests when any symbol shares handler file
 cov=sg.get('coverage_link_candidates') or [];symbols={x.get('symbol_id'):x for x in sg.get('symbols') or []}
 bypath={}
 for c in cov:
  sym=symbols.get(c.get('symbol_id')); 
  if sym:bypath.setdefault(sym.get('relative_path_digest'),set()).add(c.get('test_file_digest'))
 reverse={};
 for e in dep.get('edges') or []: reverse.setdefault(e.get('source_path_digest'),set()).add(e.get('target_path_digest'))
 for w in work:
  candidates=set(bypath.get(w.get('handler_path_digest'),set()))
  for target in reverse.get(w.get('handler_path_digest'),set()): candidates.update(bypath.get(target,set()))
  w['candidate_test_digests']=sorted(candidates)[:32]
 desc=write_collection('behavioral_map',wid,'workflows',work,runtime_root) if len(work)>256 else {'sharded':False,'items':work};row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':pub['source_manifest_digest'],'workflow_collection':desc,'workflow_count':len(work),'map_sharded':bool(desc.get('sharded')),'live_behavior_observed':False,'measured_test_coverage':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'behavioral_map_ready','behavioral_map':public_behavioral_map(row),'action_executed':False,**DENIED_AUTHORITY}
def _inflate(row,runtime_root=None):out=dict(row);out['workflows']=read_collection('behavioral_map',row['workspace_digest'],'workflows',row.get('workflow_collection') or {},runtime_root);return out
def public_behavioral_map(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'workflow_count':int(row.get('workflow_count',0)),'map_sharded':bool(row.get('map_sharded')),'live_behavior_observed':False,'measured_test_coverage':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_behavioral_map(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (_inflate(row,runtime_root) if include_private else public_behavioral_map(row)) if row and valid(row) else {}
__all__=['CONTRACT_VERSION','build_behavioral_map','load_behavioral_map','public_behavioral_map']
