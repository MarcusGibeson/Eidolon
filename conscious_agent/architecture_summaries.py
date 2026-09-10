from __future__ import annotations
"""v1316 evidence-linked, freshness-bound architecture summaries."""
from pathlib import Path
from typing import Any
from project_evidence_store import *
from behavioral_map import build_behavioral_map,load_behavioral_map
from repository_inventory import load_repository_inventory,build_repository_inventory
from symbol_graph import load_symbol_graph
from dependency_graph import load_dependency_graph
from runtime_topology import load_runtime_topology
CONTRACT_VERSION='v1316.8';LAYERS=('repository_inventory','symbol_graph','dependency_graph','runtime_topology','behavioral_map')
def _path(wid,runtime_root=None):return evidence_root('architecture_summaries',runtime_root)/'records'/f'{wid}.json'
def _summary(code,row):
 counts={k:int(row.get(k,0)) for k in ('file_count','test_file_count','symbol_count','edge_count','node_count','workflow_count') if k in row}
 return {'subsystem_code':code,'evidence_digest':digest(row),'source_manifest_digest':row.get('source_manifest_digest'),'observed_counts':counts,'summary_code':f'{code}_evidence_summary','claims_live_runtime':False,'claims_measured_coverage':False,'content_free':True}
def build_architecture_summaries(source_root:str|Path,*,runtime_root=None,now_unix:int|None=None)->dict[str,Any]:
 root=Path(source_root).resolve();bp=build_behavioral_map(root,runtime_root=runtime_root,now_unix=now_unix)['behavioral_map'];wid=bp['workspace_digest'];existing=load_architecture_summaries(wid,runtime_root=runtime_root)
 if existing and existing.get('source_manifest_digest')==bp.get('source_manifest_digest'):return {'ok':True,'status':'architecture_summaries_current','architecture_summaries':existing,'action_executed':False,**DENIED_AUTHORITY}
 rows={
  'repository_inventory':load_repository_inventory(wid,runtime_root=runtime_root),
  'symbol_graph':load_symbol_graph(wid,runtime_root=runtime_root),
  'dependency_graph':load_dependency_graph(wid,runtime_root=runtime_root),
  'runtime_topology':load_runtime_topology(wid,runtime_root=runtime_root),
  'behavioral_map':load_behavioral_map(wid,runtime_root=runtime_root),
 }
 manifest=bp.get('source_manifest_digest');summaries=[_summary(code,rows[code]) for code in LAYERS]
 row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':manifest,'summary_count':len(summaries),'summaries':summaries,'evidence_layer_digests':{k:digest(v) for k,v in rows.items()},'freshness_bound':True,'raw_source_content_persisted':False,'live_runtime_claimed':False,'measured_coverage_claimed':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':True,'status':'architecture_summaries_ready','architecture_summaries':public_architecture_summaries(row),'action_executed':False,**DENIED_AUTHORITY}
def public_architecture_summaries(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'summary_count':int(row.get('summary_count',0)),'summary_codes':[x.get('summary_code') for x in row.get('summaries') or []],'freshness_bound':True,'raw_source_content_exposed':False,'live_runtime_claimed':False,'measured_coverage_claimed':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_architecture_summaries(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (row if include_private else public_architecture_summaries(row)) if row and valid(row) else {}
def assess_architecture_summary_freshness(source_root:str|Path,*,runtime_root=None):
 root=Path(source_root).resolve();wid=workspace_digest(root);old=load_architecture_summaries(wid,runtime_root=runtime_root,include_private=True);cur=build_repository_inventory(root,runtime_root=runtime_root)['inventory'];same=bool(old) and old.get('source_manifest_digest')==cur.get('source_manifest_digest');return {'ok':bool(old),'status':'current' if same else ('stale' if old else 'missing'),'current':same,'recorded_manifest_digest':old.get('source_manifest_digest') if old else None,'current_manifest_digest':cur.get('source_manifest_digest'),'action_executed':False,**DENIED_AUTHORITY}
def process_architecture_summary_control(text:str,*,project_root=None,runtime_root=None):
 if str(text or '').strip().lower() not in {'show architecture summary','inspect architecture summary','inspect architecture'}:return {'active':False}
 if not project_root:return {'active':True,'ok':False,'status':'project_root_required','action_executed':False,**DENIED_AUTHORITY}
 out=build_architecture_summaries(project_root,runtime_root=runtime_root);return {'active':True,**out}
__all__=['CONTRACT_VERSION','LAYERS','build_architecture_summaries','load_architecture_summaries','assess_architecture_summary_freshness','process_architecture_summary_control']
