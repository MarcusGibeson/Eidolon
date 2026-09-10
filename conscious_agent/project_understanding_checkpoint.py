from __future__ import annotations
"""v1320 integrated project-understanding checkpoint over v1311-v1319 evidence."""
from pathlib import Path
from project_evidence_store import *
from repository_inventory import build_repository_inventory
from symbol_graph import build_symbol_graph
from dependency_graph import build_dependency_graph
from runtime_topology import build_runtime_topology
from behavioral_map import build_behavioral_map
from architecture_summaries import build_architecture_summaries
from change_history_understanding import build_change_history_understanding
from impact_analysis import build_impact_analysis
from project_unknown_detection import build_project_unknown_detection
from deep_project_understanding import build_deep_repository_model
CONTRACT_VERSION='v1320.8';LAYERS=('repository_inventory','symbol_graph','dependency_graph','runtime_topology','behavioral_map','architecture_summaries','change_history','impact_analysis','unknown_detection')
def _path(wid,runtime_root=None):return evidence_root('project_understanding_checkpoint',runtime_root)/'records'/f'{wid}.json'
def build_project_understanding_checkpoint(source_root:str|Path,*,changed_paths=(),runtime_root=None,now_unix:int|None=None):
 root=Path(source_root).resolve();results={};results['repository_inventory']=build_repository_inventory(root,runtime_root=runtime_root,now_unix=now_unix)['inventory'];results['symbol_graph']=build_symbol_graph(root,runtime_root=runtime_root,now_unix=now_unix)['symbol_graph'];results['dependency_graph']=build_dependency_graph(root,runtime_root=runtime_root,now_unix=now_unix)['dependency_graph'];results['runtime_topology']=build_runtime_topology(root,runtime_root=runtime_root,now_unix=now_unix)['runtime_topology'];results['behavioral_map']=build_behavioral_map(root,runtime_root=runtime_root,now_unix=now_unix)['behavioral_map'];results['architecture_summaries']=build_architecture_summaries(root,runtime_root=runtime_root,now_unix=now_unix)['architecture_summaries'];results['change_history']=build_change_history_understanding(root,runtime_root=runtime_root,now_unix=now_unix)['change_history'];results['impact_analysis']=build_impact_analysis(root,changed_paths,runtime_root=runtime_root,now_unix=now_unix)['impact_analysis'];results['unknown_detection']=build_project_unknown_detection(root,runtime_root=runtime_root,now_unix=now_unix)['project_unknowns'];wid=results['repository_inventory']['workspace_digest'];manifest=results['repository_inventory']['source_manifest_digest'];consistent=all(v.get('source_manifest_digest')==manifest for v in results.values());deep=build_deep_repository_model(root,runtime_root=runtime_root,now_unix=now_unix)['repository_model'];deep_consistent=deep.get('source_manifest_digest')==manifest;row=seal({'contract_version':CONTRACT_VERSION,'workspace_digest':wid,'source_manifest_digest':manifest,'layer_count':len(results),'layer_digests':{k:digest(v) for k,v in results.items()},'manifest_consistent':consistent,'deep_repository_model_digest':digest(deep),'deep_repository_model_consistent':deep_consistent,'deep_repository_model_available':True,'unfamiliar_project_supported':True,'live_runtime_verified':False,'native_windows_verified':False,'measured_coverage_claimed':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(wid,runtime_root),row);return {'ok':consistent,'status':'project_understanding_checkpoint_ready' if consistent else 'project_understanding_manifest_conflict','project_understanding':public_checkpoint(row),'action_executed':False,**DENIED_AUTHORITY}
def public_checkpoint(row):return {'contract_version':CONTRACT_VERSION,'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'layer_count':int(row.get('layer_count',0)),'manifest_consistent':bool(row.get('manifest_consistent')),'deep_repository_model_available':bool(row.get('deep_repository_model_available')),'deep_repository_model_consistent':bool(row.get('deep_repository_model_consistent')),'unfamiliar_project_supported':bool(row.get('unfamiliar_project_supported')),'live_runtime_verified':False,'native_windows_verified':False,'measured_coverage_claimed':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_project_understanding_checkpoint(wid,*,runtime_root=None,include_private=False):
 row=read_json(_path(wid,runtime_root));return (row if include_private else public_checkpoint(row)) if row and valid(row) else {}
def process_project_understanding_checkpoint_control(text:str,*,project_root=None,runtime_root=None):
 if str(text or '').strip().lower() not in {'inspect project understanding','show project understanding'}:return {'active':False}
 if not project_root:return {'active':True,'ok':False,'status':'project_root_required','action_executed':False,**DENIED_AUTHORITY}
 return {'active':True,**build_project_understanding_checkpoint(project_root,runtime_root=runtime_root)}
__all__=['CONTRACT_VERSION','LAYERS','build_project_understanding_checkpoint','load_project_understanding_checkpoint','process_project_understanding_checkpoint_control']
