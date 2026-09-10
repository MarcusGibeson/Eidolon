from __future__ import annotations
"""Read-only v1242.9 Installation Lifecycle Integration checkpoint."""
import ast,hashlib
from pathlib import Path
from checkpoint_registry import inspect_checkpoint_registry
from installation_upgrade_backup_rollback_integration import (
    AUTHORITY_FLAGS,
    CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,
    MILESTONE_NAME,
    ROADMAP_PATH,
    build_installation_lifecycle_integration_contract,
    installation_lifecycle_dashboard_record,
    lifecycle_operation_registry,
    render_installation_lifecycle_dashboard_html,
)
CONTRACT_VERSION="v1242.9"
CHECKPOINT_ID="installation-lifecycle-integration-checkpoint"

def _sig(root):
 rows=[];count=0
 for p in sorted(Path(root).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
   rows.append(f"{p.relative_to(root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}");count+=1
 return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),count

def _quick(text):
 try:
  tree=ast.parse(text)
  for n in tree.body:
   if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='QUICK_STAGE_NAMES' for x in n.targets):return set(ast.literal_eval(n.value))
 except Exception:pass
 return set()

def build_installation_lifecycle_integration_checkpoint(*,source_root=None,runtime_root=None):
 del runtime_root
 source=Path(source_root or Path(__file__).resolve().parents[1]).resolve();before,n1=_sig(source)
 contract=build_installation_lifecycle_integration_contract();registry=lifecycle_operation_registry();dashboard=installation_lifecycle_dashboard_record();page=render_installation_lifecycle_dashboard_html()
 desc=next((x for x in inspect_checkpoint_registry(source_root=source).get('checkpoints',[]) if x.get('checkpoint_id')==CHECKPOINT_ID),{})
 names=('conscious_agent/release_metadata.py','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','tools/release_verify.py','conscious_agent/api_server.py','eidolon.py','conscious_agent/ordinary_chat_development_campaign.py','conscious_agent/dashboard.py')
 f={n:(source/n).read_text(encoding='utf-8') for n in names}
 stages={"v1242.2-installation-lifecycle-integration-foundations","v1242.5-installation-lifecycle-integration-workflows","v1242.8-installation-lifecycle-integration-reliability","v1242.9-installation-lifecycle-integration-checkpoint"}
 docs=('archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1242_0_2.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1242_3_5.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1242_6_8.md','archive/docs/legacy_dependencies/validation/Eidolon_v1242_9_FINAL_VALIDATION.md','archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1242_9.md')
 c={
  'contract_ok':contract.get('ok') is True,'retained_modules':contract.get('retained_lifecycle_module_count')==7,'registry_ok':registry.get('ok') is True,'operation_count':registry.get('operation_count')==4,
  'dashboard_read_only':dashboard.get('read_only') is True,'dashboard_no_authority':dashboard.get('installation_authorized') is False,'dashboard_page':'Installation Lifecycle Integration' in page and 'GET-only inspection' in page,
  'metadata':'WORKING_SOURCE_VERSION = "1242.9"' in f['conscious_agent/release_metadata.py'] and 'v1242.9 Installation, Upgrade, Backup, and Rollback Integration Checkpoint' in f['conscious_agent/release_metadata.py'] and 'v1243.0-v1243.2 Provider Fallback and Model Governance Foundations' in f['conscious_agent/release_metadata.py'],
  'readmes':'v1242.9' in f['README_NEXT_STEPS.md'] and 'v1242.9' in f['README_RELEASE_HISTORY.md'],
  'chat':'process_installation_lifecycle_control' in f['conscious_agent/ordinary_chat_development_campaign.py'],
  'api':all(x in f['conscious_agent/api_server.py'] for x in ('installation-lifecycle-registry','installation-lifecycle-preflights','installation-lifecycle-proposals','installation-lifecycle-recovery-assessments',CHECKPOINT_ID)),
  'cli':all(f'"{x}"' in f['eidolon.py'] for x in ('installation-lifecycle-registry','installation-lifecycle-preflights','installation-lifecycle-proposals','installation-lifecycle-recovery-assessments',CHECKPOINT_ID)),
  'dashboard_routes':'/installation-lifecycle' in f['conscious_agent/dashboard.py'] and '/api/installation-lifecycle' in f['conscious_agent/dashboard.py'],
  'release_stages':stages.issubset(_quick(f['tools/release_verify.py'])),'release_commands':all(x in f['tools/release_verify.py'] for x in stages),'docs':all((source/x).is_file() for x in docs),
  'registry_present':bool(desc),'registry_version':desc.get('contract_version')==CONTRACT_VERSION,'registry_read_only':desc.get('read_only') is True,'registry_no_inputs':desc.get('required_input_count')==0,
  'exact_lineage':contract.get('exact_target_version_artifact_manifest_binding') is True,'backup_before_mutation':contract.get('backup_before_existing_installation_mutation') is True,'rollback_binding':contract.get('rollback_bound_to_exact_backup_and_target') is True,
  'recovery_proposal_only':contract.get('interrupted_state_recovery_is_proposal_only') is True,'no_automatic_retry':contract.get('automatic_retry_authorized') is False,'no_old_authority':contract.get('old_authority_reusable') is False,
 }
 for k,v in AUTHORITY_FLAGS.items():c['authority_'+k]=contract.get(k) is v and registry.get(k) is v and dashboard.get(k) is v
 after,n2=_sig(source);c['source_unchanged']=before==after and n1==n2
 passed=sum(map(bool,c.values()));total=len(c);ok=passed==total
 return {'ok':ok,'status':'installation_lifecycle_integration_checkpoint_ready' if ok else 'installation_lifecycle_integration_checkpoint_blocked','checkpoint_id':CHECKPOINT_ID,'contract_version':CONTRACT_VERSION,'retained_contract_version':RETAINED_CONTRACT_VERSION,'milestone_name':MILESTONE_NAME,'roadmap_path':ROADMAP_PATH,'passed':passed,'total':total,'checks':c,'source_signature_before':before,'source_signature_after':after,'source_signature_unchanged':before==after,'source_file_count_before':n1,'source_file_count_after':n2,'read_only':True,'content_free':True,'runtime_data_read':False,'runtime_data_written':False,'provider_contacted':False,'commands_executed':False,'tests_executed':False,'project_modified':False,'source_modified':False,'cognition_written':False,'authority_granted':False,**AUTHORITY_FLAGS}
