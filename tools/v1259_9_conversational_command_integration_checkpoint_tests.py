from __future__ import annotations

import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from checkpoint_registry import checkpoint_registry_manifest,lookup_checkpoint,validate_checkpoint_report
from conversational_command_integration_checkpoint import build_conversational_command_integration_checkpoint
from release_authority import CODEX_REVIEW_STATE,NEXT_BOUNDED_UNIT,PREVIOUS_WORKING_SOURCE_VERSION,WORKING_SOURCE_VERSION
CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)
def signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=signature(); report=build_conversational_command_integration_checkpoint(source_root=ROOT); details=report['details']; validation=validate_checkpoint_report(report,source_root=ROOT); manifest=checkpoint_registry_manifest(source_root=ROOT); record=lookup_checkpoint('1259.9')
require(report['ok'] and validation['ok'],'checkpoint_report_ok')
require(report['checkpoint_version']=='1259.9' and report['contract_version']=='v1259.9','checkpoint_version_exact')
require(report['status']=='conversational_command_integration_checkpoint_ready','checkpoint_status_exact')
require(all(report['checks'].values()),'all_structural_checkpoint_checks_pass')
require(report['read_only'] and report['content_free'],'checkpoint_read_only_content_free')
require(report['provider_contact_authorized'] is False and report['commands_executed'] is False and report['tests_executed'] is False,'checkpoint_executes_nothing')
require(report['source_mutation_authorized'] is False and report['project_mutation_authorized'] is False,'checkpoint_mutates_nothing')
require(details['speech_act_distinction_active'] and details['mixed_conversation_action_supported'],'speech_act_and_mixed_turn_recorded')
require(details['information_request_does_not_create_development_proposal'],'information_request_boundary_recorded')
require(details['generic_authorization_is_not_authority'],'generic_authorization_boundary_recorded')
require(details['correction_revises_pending_proposal_only'],'correction_boundary_recorded')
require(details['cancellation_requires_unique_or_exact_target'],'cancellation_boundary_recorded')
require(details['existing_exact_authority_contracts_preserved'],'exact_authority_contracts_preserved')
require(details['application_authorized'] is False and details['installation_authorized'] is False,'application_install_denied')
require(details['promotion_authorized'] is False and details['certification_authorized'] is False and details['release_authorized'] is False,'release_chain_denied')
require(details['permanent_approval_granted'] is False and details['independent_authority_granted'] is False,'permanent_independent_authority_denied')
require(details['native_windows_multi_process_validation']=='desktop_review_required','native_windows_review_honest')
require(len(details['behavioral_evidence'])==3,'three_behavioral_suites_named')
require(details['present_source_count']==details['required_source_count']==11,'required_checkpoint_surfaces_hashed')
require(all(len(v)==64 for v in details['source_sha256'].values()),'checkpoint_hashes_complete')
require(tuple(int(part) for part in WORKING_SOURCE_VERSION.split('.')) >= (1259,9),'release_metadata_retains_v1259_9_or_later')
require(bool(CODEX_REVIEW_STATE),'desktop_review_state_present')
require(bool(NEXT_BOUNDED_UNIT),'later_next_unit_present')
require(record is not None and record.test_selector=='tools/v1259_9_conversational_command_integration_checkpoint_tests.py','checkpoint_selector_exact')
require(record is not None and record.lifecycle=='conversational_command_integration_arc','checkpoint_lifecycle_exact')
require(manifest['ok'] and manifest['working_source_version']==WORKING_SOURCE_VERSION,'registry_manifest_tracks_current_source')
for version,selector in {'1259.0':'tools/v1259_0_2_conversational_command_integration_foundations_tests.py','1259.3':'tools/v1259_3_5_conversational_command_integration_tests.py','1259.6':'tools/v1259_6_8_conversational_command_integration_reliability_tests.py','1259.9':'tools/v1259_9_conversational_command_integration_checkpoint_tests.py'}.items():
    row=lookup_checkpoint(version); require(row is not None and row.test_selector==selector and row.lifecycle=='conversational_command_integration_arc',f'registry_selector_{version}_coherent')
for name in ('README.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md'):
    active=(ROOT/name).read_text(encoding='utf-8').split('<details id="retained-pre-v1250-compatibility">',1)[0]
    require('v1259.9' in active,f'{name}_current_checkpoint_visible')
    require('v1260' in active,f'{name}_next_section_visible')
require(signature()==before,'checkpoint_builder_preserves_source_immutability')
print(json.dumps({'ok':True,'suite':'v1259.9-conversational-command-integration-checkpoint','passed':len(CHECKS),'failed':0,'checks':CHECKS,'read_only_checkpoint':True,'provider_contacted':False,'application_authorized':False,'release_authorized':False,'independent_authority_granted':False},indent=2,sort_keys=True))
