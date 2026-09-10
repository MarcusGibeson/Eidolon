from __future__ import annotations
"""Read-only v1241.9 Unified Operator Dashboard checkpoint."""
import ast,hashlib
from pathlib import Path
from checkpoint_registry import inspect_checkpoint_registry
from unified_operator_dashboard import AUTHORITY_FLAGS,CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,MILESTONE_NAME,ROADMAP_PATH,build_unified_operator_dashboard_snapshot,dashboard_panel_registry,render_unified_operator_dashboard_html
CONTRACT_VERSION="v1241.9"; CHECKPOINT_ID="unified-operator-dashboard-checkpoint"
def _sig(root):
 rows=[]; count=0
 for p in sorted(Path(root).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}: rows.append(f"{p.relative_to(root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}"); count+=1
 return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),count
def _quick(text):
 names=set()
 try:
  tree=ast.parse(text)
  for n in tree.body:
   if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in {'QUICK_STAGE_NAMES','LEGACY_QUICK_STAGE_NAMES'} for x in n.targets): names.update(ast.literal_eval(n.value))
 except Exception: pass
 return names
def build_unified_operator_dashboard_checkpoint(*,source_root=None,runtime_root=None):
 del runtime_root; source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); before,n1=_sig(source)
 reg=dashboard_panel_registry(); snap=build_unified_operator_dashboard_snapshot(); page=render_unified_operator_dashboard_html(snap)
 desc=next((x for x in inspect_checkpoint_registry(source_root=source).get('checkpoints',[]) if x.get('checkpoint_id')==CHECKPOINT_ID),{})
 names=('conscious_agent/release_metadata.py','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','tools/release_verify.py','conscious_agent/api_server.py','eidolon.py','conscious_agent/ordinary_chat_development_campaign.py','conscious_agent/dashboard.py')
 f={n:(source/n).read_text(encoding='utf-8') for n in names}; stages={"v1241.2-unified-operator-dashboard-foundations","v1241.5-unified-operator-dashboard-workflows","v1241.8-unified-operator-dashboard-reliability","v1241.9-unified-operator-dashboard-checkpoint"}
 docs=('archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1241_0_2.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1241_3_5.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1241_6_8.md','archive/docs/legacy_dependencies/validation/Eidolon_v1241_9_FINAL_VALIDATION.md','archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1241_9.md')
 c={'registry_ok':reg.get('ok') is True,'panel_count':reg.get('panel_count')==14,'snapshot_ok':snap.get('ok') is True,'snapshot_records':snap.get('record_count')==14,'privacy':snap.get('private_fields_suppressed') is True,
 'page':'command-deck operator-console' in page and 'No button, filter, sort, or record view grants authority' in page,
 'metadata':'WORKING_SOURCE_VERSION = "1241.9"' in f['conscious_agent/release_metadata.py'] and 'v1241.9 Unified Operator Dashboard Checkpoint' in f['conscious_agent/release_metadata.py'] and 'v1242.0-v1242.2 Installation, Upgrade, Backup, and Rollback Integration Foundations' in f['conscious_agent/release_metadata.py'],
 'readmes':'v1241.9' in f['README_NEXT_STEPS.md'] and 'v1241.9 Unified Operator Dashboard' in f['README_RELEASE_HISTORY.md'],
 'chat':'process_unified_operator_dashboard_control' in f['conscious_agent/ordinary_chat_development_campaign.py'],'api':all(x in f['conscious_agent/api_server.py'] for x in ('unified-operator-dashboard-registry','unified-operator-dashboard-snapshot',CHECKPOINT_ID)),
 'cli':all(f'"{x}"' in f['eidolon.py'] for x in ('unified-operator-dashboard-registry','unified-operator-dashboard-snapshot',CHECKPOINT_ID)),'dashboard':'/unified-operator-dashboard' in f['conscious_agent/dashboard.py'] and '/api/unified-operator-dashboard' in f['conscious_agent/dashboard.py'],
 'release_stages':stages.issubset(_quick(f['tools/release_verify.py'])),'release_commands':all(x in f['tools/release_verify.py'] for x in stages),'docs':all((source/x).is_file() for x in docs),
 'registry_present':bool(desc),'registry_version':desc.get('contract_version')==CONTRACT_VERSION,'registry_read_only':desc.get('read_only') is True,'registry_no_inputs':desc.get('required_input_count')==0,
 'open_no_mutation':snap.get('opening_record_mutates_state') is False,'filter_no_mutation':snap.get('filtering_mutates_state') is False,'sort_no_mutation':snap.get('sorting_mutates_state') is False,'cross_project':snap.get('cross_project_records_kept_separate') is True}
 for k,v in AUTHORITY_FLAGS.items(): c['authority_'+k]=snap.get(k) is v
 after,n2=_sig(source); c['source_unchanged']=before==after and n1==n2; passed=sum(map(bool,c.values())); total=len(c); ok=passed==total
 return {'ok':ok,'status':'unified_operator_dashboard_checkpoint_ready' if ok else 'unified_operator_dashboard_checkpoint_blocked','checkpoint_id':CHECKPOINT_ID,'contract_version':CONTRACT_VERSION,'retained_contract_version':RETAINED_CONTRACT_VERSION,'milestone_name':MILESTONE_NAME,'roadmap_path':ROADMAP_PATH,'passed':passed,'total':total,'checks':c,'source_signature_before':before,'source_signature_after':after,'source_signature_unchanged':before==after,'source_file_count_before':n1,'source_file_count_after':n2,'read_only':True,'content_free':True,'runtime_data_read':False,'runtime_data_written':False,'provider_contacted':False,'commands_executed':False,'tests_executed':False,'project_modified':False,'source_modified':False,'cognition_written':False,'authority_granted':False,**AUTHORITY_FLAGS}
