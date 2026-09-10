from __future__ import annotations
"""Read-only v1231.9 Dynamic Execution Plan Revision checkpoint."""
import ast,hashlib
from pathlib import Path
from typing import Any
from checkpoint_registry import inspect_checkpoint_registry
from checkpoint_progress import retained_checkpoint_progress
from dynamic_execution_plan_revision import AUTHORITY_FLAGS,CONTRACT_VERSION as RETAINED_CONTRACT_VERSION,VERIFIED_CHANGE_CODES,build_dynamic_execution_plan_revision_contract
CONTRACT_VERSION='v1231.9'
CHECKPOINT_ID='dynamic-execution-plan-revision-checkpoint'
MILESTONE_NAME='Dynamic Execution Plan Revision with Operator Review'
ROADMAP_PATH='Balanced Mind-and-Action Path 3'

def _tree_signature(root: Path):
    rows=[]; count=0
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in {'.pyc','.pyo'}: continue
        rows.append(f"{path.relative_to(root).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}"); count+=1
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),count

def _quick_stage_names(text: str):
    names=set()
    try:
        tree=ast.parse(text)
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'QUICK_STAGE_NAMES','LEGACY_QUICK_STAGE_NAMES'} for t in node.targets):
                names.update(str(x) for x in ast.literal_eval(node.value))
    except Exception: pass
    return names

def build_dynamic_execution_plan_revision_checkpoint(*,source_root: str|Path|None=None,runtime_root=None)->dict[str,Any]:
    del runtime_root
    source=Path(source_root or Path(__file__).resolve().parents[1]).resolve(); before,before_count=_tree_signature(source)
    contract=build_dynamic_execution_plan_revision_contract(); registry=inspect_checkpoint_registry(source_root=source)
    descriptor=next((r for r in registry.get('checkpoints',[]) if r.get('checkpoint_id')==CHECKPOINT_ID),{})
    module=(source/'conscious_agent/dynamic_execution_plan_revision.py').read_text(encoding='utf-8'); chat=(source/'conscious_agent/ordinary_chat_development_campaign.py').read_text(encoding='utf-8'); api=(source/'conscious_agent/api_server.py').read_text(encoding='utf-8'); cli=(source/'eidolon.py').read_text(encoding='utf-8'); metadata=(source/'conscious_agent/release_metadata.py').read_text(encoding='utf-8'); roadmap=(source/'README_NEXT_STEPS.md').read_text(encoding='utf-8'); history=(source/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8'); verifier=(source/'tools/release_verify.py').read_text(encoding='utf-8')
    expected_stages={'v1231.2-dynamic-execution-plan-revision-foundations','v1231.5-dynamic-execution-plan-revision-operator-review','v1231.8-dynamic-execution-plan-revision-adversarial-reliability','v1231.9-dynamic-execution-plan-revision-checkpoint'}
    expected_docs=('archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1231_0_2.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1231_3_5.md','archive/docs/legacy_dependencies/bundle_reviews/BUNDLE_REVIEW_V1231_6_8.md','archive/docs/legacy_dependencies/validation/Eidolon_v1231_9_FINAL_VALIDATION.md','archive/docs/legacy_dependencies/handoffs/DESKTOP_CODEX_HANDOFF_V1231_9.md')
    progress=retained_checkpoint_progress(source,checkpoint_version='1231.9',successor_version='1232.0',successor_surface='conscious_agent/dependency_aware_execution.py')
    checks={
      'contract_ok':contract.get('ok') is True,'retained_contract_version':contract.get('contract_version')==RETAINED_CONTRACT_VERSION,
      'roadmap_path':contract.get('roadmap_path')==ROADMAP_PATH,'active_or_paused_required':contract.get('active_or_paused_session_required') is True,
      'verified_reality_required':contract.get('verified_reality_required') is True,'operator_review_required':contract.get('operator_review_required') is True,
      'original_plan_immutable':contract.get('original_plan_immutable') is True,'historical_receipts_immutable':contract.get('historical_receipts_immutable') is True,
      'exact_chat_controls':contract.get('ordinary_chat_exact_controls') is True,'hardening_required':contract.get('restart_replay_stale_tamper_privacy_contradiction_hardening_required') is True,
      'change_code_coverage':len(VERIFIED_CHANGE_CODES)>=10,'module_prepare':'def prepare_dynamic_execution_plan_revision(' in module,
      'module_review':'def review_dynamic_execution_plan_revision(' in module,'module_public_list':'def public_dynamic_execution_plan_revisions(' in module,
      'module_public_reviews':'def public_dynamic_execution_plan_revision_reviews(' in module,'module_original_plan':'original_plan_immutable' in module,
      'module_scope_expansion_false':'"scope_expansion_authorized": False' in module,'module_fresh_launch':'"fresh_launch_authorization_required": True' in module,
      'module_fresh_resume':'"fresh_resume_authorization_required": True' in module,'chat_route':'process_dynamic_execution_plan_revision_control' in chat,
      'api_revisions':'dynamic-execution-plan-revisions' in api,'api_reviews':'dynamic-execution-plan-revision-reviews' in api,'api_checkpoint':CHECKPOINT_ID in api,
      'cli_revisions':'"dynamic-execution-plan-revisions"' in cli,'cli_reviews':'"dynamic-execution-plan-revision-reviews"' in cli,'cli_checkpoint':f'"{CHECKPOINT_ID}"' in cli,
      'metadata_version':progress.get('checkpoint_retained') is True,'metadata_milestone':progress.get('coherent') is True,
      'metadata_next':progress.get('started') is True,'roadmap_current':'v1231.9' in roadmap,'roadmap_next':'v1232' in roadmap,
      'history_current':'v1231.9' in history,'release_stages_registered':expected_stages.issubset(_quick_stage_names(verifier)),
      'release_commands_registered':all(x in verifier for x in expected_stages),'docs_present':all((source/x).is_file() for x in expected_docs),
      'registry_present':bool(descriptor),'registry_version':descriptor.get('contract_version')==CONTRACT_VERSION,'registry_read_only':descriptor.get('read_only') is True,
      'registry_no_inputs':descriptor.get('required_input_count')==0,
    }
    for key,expected in AUTHORITY_FLAGS.items(): checks[f'authority_{key}']=contract.get(key) is expected
    after,after_count=_tree_signature(source); unchanged=before==after and before_count==after_count; checks['source_signature_unchanged']=unchanged
    passed=sum(bool(v) for v in checks.values()); total=len(checks); ok=passed==total
    return {'ok':ok,'status':'dynamic_execution_plan_revision_checkpoint_ready' if ok else 'dynamic_execution_plan_revision_checkpoint_blocked','checkpoint_id':CHECKPOINT_ID,'contract_version':CONTRACT_VERSION,'retained_contract_version':RETAINED_CONTRACT_VERSION,'milestone_name':MILESTONE_NAME,'roadmap_path':ROADMAP_PATH,'checks':checks,'passed':passed,'total':total,'read_only':True,'content_free':True,'source_signature_before':before,'source_signature_after':after,'source_signature_unchanged':unchanged,'source_file_count_before':before_count,'source_file_count_after':after_count,'runtime_data_read':False,'runtime_data_written':False,'provider_contacted':False,'commands_executed':False,'tests_executed':False,'project_modified':False,'queue_modified':False,'schedule_modified':False,'cognition_written':False,'source_modified':False,'authority_granted':False,**AUTHORITY_FLAGS}
