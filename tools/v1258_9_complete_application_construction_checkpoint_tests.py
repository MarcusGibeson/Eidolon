from __future__ import annotations

import hashlib, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for path in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(path) not in sys.path: sys.path.insert(0,str(path))

from checkpoint_registry import checkpoint_registry_manifest, lookup_checkpoint, validate_checkpoint_report
from complete_application_construction_checkpoint import build_complete_application_construction_checkpoint
from release_authority import CODEX_REVIEW_STATE, NEXT_BOUNDED_UNIT, PREVIOUS_WORKING_SOURCE_VERSION, WORKING_SOURCE_VERSION

CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)

def source_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

before=source_signature(); report=build_complete_application_construction_checkpoint(source_root=ROOT); details=report['details']; validation=validate_checkpoint_report(report,source_root=ROOT); manifest=checkpoint_registry_manifest(source_root=ROOT); record=lookup_checkpoint('1258.9')
require(report['ok'] and validation['ok'],'checkpoint_report_ok')
require(report['checkpoint_version']=='1258.9' and report['contract_version']=='v1258.9','checkpoint_version_exact')
require(report['status']=='complete_application_construction_checkpoint_ready','checkpoint_status_exact')
require(all(report['checks'].values()),'all_structural_checkpoint_checks_pass')
require(report['read_only'] and report['content_free'],'checkpoint_read_only_content_free')
require(report['provider_contact_authorized'] is False and report['commands_executed'] is False and report['tests_executed'] is False,'checkpoint_executes_nothing')
require(report['source_mutation_authorized'] is False and report['project_mutation_authorized'] is False,'checkpoint_mutates_nothing')
require(report['installation_authorized'] is False and report['release_authorized'] is False,'checkpoint_grants_no_install_or_release')
require(report['independent_authority_granted'] is False,'checkpoint_grants_no_independent_authority')
require(details['coherent_multi_file_construction'] is True,'coherent_multi_file_construction_recorded')
require(details['dependency_installation_performed'] is False and details['dependency_installation_authorized'] is False,'dependency_installation_remains_denied')
require(details['accessibility_structural_verification'] and details['responsive_structural_verification'],'accessibility_and_responsive_verification_recorded')
require(details['quality_failure_can_enter_v1257_repair'],'construction_quality_connected_to_v1257_repair')
require(details['ordinary_chat_explicit_complete_app_integration'],'ordinary_chat_complete_app_integration_recorded')
require(details['selected_project_application_separate_v1255_authority'],'v1255_application_authority_remains_separate')
require(details['project_mutation_authorized'] is False,'project_mutation_denied')
require(details['installation_authorized'] is False and details['promotion_authorized'] is False and details['certification_authorized'] is False,'install_promotion_certification_denied')
require(details['permanent_approval_granted'] is False and details['independent_authority_granted'] is False,'permanent_independent_authority_denied')
require(details['native_windows_and_real_browser_validation']=='desktop_review_required','native_windows_browser_review_honest')
require(len(details['behavioral_evidence'])==3,'three_behavioral_suites_named')
require(details['present_source_count']==details['required_source_count']==9,'required_checkpoint_surfaces_hashed')
require(all(len(v)==64 for v in details['source_sha256'].values()),'checkpoint_hashes_complete')
working_parts=tuple(int(part) for part in WORKING_SOURCE_VERSION.split('.'))
require(working_parts>=(1258,9),'release_metadata_retains_v1258_9_or_later')
require(bool(CODEX_REVIEW_STATE),'desktop_review_state_present')
require(bool(NEXT_BOUNDED_UNIT),'later_next_unit_present')
require(record is not None and record.test_selector=='tools/v1258_9_complete_application_construction_checkpoint_tests.py','checkpoint_selector_exact')
require(record is not None and record.lifecycle=='complete_application_construction_arc','checkpoint_lifecycle_exact')
require(manifest['ok'] and manifest['working_source_version']==WORKING_SOURCE_VERSION,'registry_manifest_tracks_current_source')
for version,selector in {'1258.0':'tools/v1258_0_2_complete_application_construction_foundations_tests.py','1258.3':'tools/v1258_3_5_complete_application_construction_integration_tests.py','1258.6':'tools/v1258_6_8_complete_application_construction_reliability_tests.py','1258.9':'tools/v1258_9_complete_application_construction_checkpoint_tests.py'}.items():
    row=lookup_checkpoint(version); require(row is not None and row.test_selector==selector and row.lifecycle=='complete_application_construction_arc',f'registry_selector_{version}_coherent')
for name in ('README.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md'):
    active=(ROOT/name).read_text(encoding='utf-8').split('<details id="retained-pre-v1250-compatibility">',1)[0]
    require('v1258.9' in active,f'{name}_current_checkpoint_visible')
    require('v1259' in active,f'{name}_next_section_visible')
next_text=(ROOT/'README_NEXT_STEPS.md').read_text(encoding='utf-8')
require('v1255' in next_text and 'Application remains separately governed' in next_text,'application_authority_separation_documented')
require(source_signature()==before,'checkpoint_builder_preserves_source_immutability')
print(json.dumps({'ok':True,'suite':'v1258.9-complete-application-construction-checkpoint','passed':len(CHECKS),'failed':0,'checks':CHECKS,'read_only_checkpoint':True,'provider_contacted':False,'application_authorized':False,'release_authorized':False,'independent_authority_granted':False},indent=2,sort_keys=True))
