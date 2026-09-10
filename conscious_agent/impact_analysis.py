from __future__ import annotations
"""v1318 conservative pre-edit impact prediction from project-understanding evidence."""
from pathlib import Path,PurePosixPath
from project_evidence_store import *
from dependency_graph import build_dependency_graph,load_dependency_graph
from repository_inventory import load_repository_inventory
from symbol_graph import load_symbol_graph
from runtime_topology import build_runtime_topology,load_runtime_topology
CONTRACT_VERSION='v1318.8';PROTECTED_HINTS=('release_authority','authority_profile','standing_session','self_update','self_update','rollback','recovery','secret','privacy','approval','authorization')
def _path(key,runtime_root=None):return evidence_root('impact_analysis',runtime_root)/'records'/f'{key}.json'
def _norm(p):
 s=str(p or '').replace('\\','/').strip().lstrip('/')
 if not s or '..' in PurePosixPath(s).parts:return ''
 return PurePosixPath(s).as_posix()
def build_impact_analysis(source_root:str|Path,changed_paths,*,runtime_root=None,now_unix:int|None=None):
 root=Path(source_root).resolve();pub=build_dependency_graph(root,runtime_root=runtime_root,now_unix=now_unix)['dependency_graph'];wid=pub['workspace_digest'];build_runtime_topology(root,runtime_root=runtime_root,now_unix=now_unix);dep=load_dependency_graph(wid,runtime_root=runtime_root,include_private=True);inv=load_repository_inventory(wid,runtime_root=runtime_root,include_private=True);sg=load_symbol_graph(wid,runtime_root=runtime_root,include_private=True);top=load_runtime_topology(wid,runtime_root=runtime_root,include_private=True)
 rows={f['relative_path']:f for f in inv.get('files') or []};requested=[]
 for p in changed_paths or []:
  n=_norm(p)
  if n and n not in requested:requested.append(n)
 known=[p for p in requested if p in rows];unknown=[p for p in requested if p not in rows];dig={p:rows[p]['relative_path_digest'] for p in known};affected=set(dig.values());changed=set(affected)
 more=True
 while more:
  more=False
  for e in dep.get('edges') or []:
   if e.get('target_path_digest') in affected and e.get('source_path_digest') not in affected:affected.add(e.get('source_path_digest'));more=True
 cov=sg.get('coverage_link_candidates') or [];symbols={x.get('symbol_id'):x for x in sg.get('symbols') or []};tests=set()
 for c in cov:
  s=symbols.get(c.get('symbol_id'))
  if s and s.get('relative_path_digest') in affected:tests.add(c.get('test_file_digest'))
 ui=any(n.get('source_path_digest') in affected and n.get('kind') in {'route','user_surface'} for n in top.get('nodes') or []);mig=any(any(tok in p.lower() for tok in ('migration','schema','.sql')) for p in known);protected=any(any(h in p.lower() for h in PROTECTED_HINTS) for p in known)
 key=digest({'workspace':wid,'manifest':pub['source_manifest_digest'],'paths':requested});row=seal({'contract_version':CONTRACT_VERSION,'analysis_id':'impact-'+key[:20],'workspace_digest':wid,'source_manifest_digest':pub['source_manifest_digest'],'requested_path_digests':[digest(p) for p in requested],'known_changed_path_digests':sorted(changed),'unknown_path_digests':[digest(p) for p in unknown],'affected_path_digests':sorted(affected),'candidate_test_digests':sorted(tests),'ui_impact_predicted':ui,'migration_impact_predicted':mig,'protected_authority_surface_predicted':protected,'predictions_not_proof':True,'tests_executed':False,'source_modified':False,'action_executed':False,**DENIED_AUTHORITY});atomic_json(_path(key,runtime_root),row);return {'ok':True,'status':'impact_analysis_ready','impact_analysis':public_impact_analysis(row),'action_executed':False,**DENIED_AUTHORITY}
def public_impact_analysis(row):return {'contract_version':CONTRACT_VERSION,'analysis_id':row.get('analysis_id'),'workspace_digest':row.get('workspace_digest'),'source_manifest_digest':row.get('source_manifest_digest'),'changed_path_count':len(row.get('known_changed_path_digests') or []),'unknown_path_count':len(row.get('unknown_path_digests') or []),'affected_path_count':len(row.get('affected_path_digests') or []),'candidate_test_count':len(row.get('candidate_test_digests') or []),'ui_impact_predicted':bool(row.get('ui_impact_predicted')),'migration_impact_predicted':bool(row.get('migration_impact_predicted')),'protected_authority_surface_predicted':bool(row.get('protected_authority_surface_predicted')),'predictions_not_proof':True,'tests_executed':False,'source_modified':False,'read_only':True,'action_executed':False,**DENIED_AUTHORITY}
def load_impact_analysis(analysis_id,*,runtime_root=None,include_private=False):
 base=evidence_root('impact_analysis',runtime_root)/'records'
 for p in base.glob('*.json'):
  row=read_json(p)
  if row and valid(row) and row.get('analysis_id')==analysis_id:return row if include_private else public_impact_analysis(row)
 return {}
def assess_impact_freshness(source_root:str|Path,analysis_id,*,runtime_root=None):
 root=Path(source_root).resolve();old=load_impact_analysis(analysis_id,runtime_root=runtime_root,include_private=True);from repository_inventory import build_repository_inventory
 cur=build_repository_inventory(root,runtime_root=runtime_root)['inventory'];same=bool(old) and old.get('source_manifest_digest')==cur.get('source_manifest_digest');return {'ok':bool(old),'status':'current' if same else ('stale' if old else 'missing'),'current':same,'action_executed':False,**DENIED_AUTHORITY}
def process_impact_analysis_control(text:str,*,project_root=None,runtime_root=None):
 raw=str(text or '').strip();low=raw.lower();prefix='analyze impact:'
 if not low.startswith(prefix):return {'active':False}
 if not project_root:return {'active':True,'ok':False,'status':'project_root_required','action_executed':False,**DENIED_AUTHORITY}
 paths=[x.strip() for x in raw[len(prefix):].split(',') if x.strip()];return {'active':True,**build_impact_analysis(project_root,paths,runtime_root=runtime_root)}
__all__=['CONTRACT_VERSION','build_impact_analysis','load_impact_analysis','assess_impact_freshness','process_impact_analysis_control']
