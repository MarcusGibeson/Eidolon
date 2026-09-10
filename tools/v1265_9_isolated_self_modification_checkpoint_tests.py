from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from isolated_self_modification_checkpoint import build_isolated_self_modification_checkpoint
from checkpoint_registry import checkpoint_registry_manifest,lookup_checkpoint,validate_checkpoint_report
from release_authority import WORKING_SOURCE_VERSION,PREVIOUS_WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT,CODEX_REVIEW_STATE
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def sig():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            r=p.relative_to(ROOT).as_posix()
            if r.startswith('data/') or '__pycache__' in r or r.endswith(('.pyc','.pyo')): continue
            rows.append((r,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
before=sig();report=build_isolated_self_modification_checkpoint(source_root=ROOT);validation=validate_checkpoint_report(report,source_root=ROOT);manifest=checkpoint_registry_manifest(source_root=ROOT);record=lookup_checkpoint('1265.9')
req(report['ok'] and validation['ok'],'checkpoint_report_valid');req(report['checkpoint_version']=='1265.9' and report['contract_version']=='v1265.9','checkpoint_version_exact');req(all(report['checks'].values()),'checkpoint_checks_all_pass')
req(report['read_only'] and report['content_free'],'checkpoint_read_only_content_free');req(report['details']['provider_contacted'] is False and report['details']['commands_executed'] is False and report['details']['tests_executed'] is False,'checkpoint_executes_nothing');req(report['details']['active_source_modified'] is False and report['details']['private_runtime_copied'] is False,'checkpoint_preserves_source_privacy');req(report['details']['candidate_application_authorized'] is False and report['details']['self_update_authorized'] is False,'checkpoint_grants_no_application_or_self_update')
req(report['details']['test_selection_deferred_to_v1266'] is True and report['details']['next_bounded_unit']=='v1266 Intelligent Test Selection','v1266_boundary_exact');req(len(report['details']['behavioral_evidence'])==3,'three_behavioral_suites_named')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.')) >= (1265,9),'release_metadata_at_or_after_v1265_9');req(bool(NEXT_BOUNDED_UNIT),'current_next_arc_present');req(bool(CODEX_REVIEW_STATE),'current_codex_state_present')
req(record is not None and record.lifecycle=='isolated_self_modification_arc','registry_lifecycle_exact');req(record is not None and record.test_selector=='tools/v1265_9_isolated_self_modification_checkpoint_tests.py','registry_selector_exact');req(manifest['ok'] and tuple(int(x) for x in manifest['working_source_version'].split('.')) >= (1265,9),'registry_manifest_at_or_after_v1265_9')
for v,s in {'1265.0':'tools/v1265_0_2_isolated_self_modification_foundations_tests.py','1265.3':'tools/v1265_3_5_isolated_self_modification_integration_tests.py','1265.6':'tools/v1265_6_8_isolated_self_modification_reliability_tests.py','1265.9':'tools/v1265_9_isolated_self_modification_checkpoint_tests.py'}.items():
    r=lookup_checkpoint(v);req(r is not None and r.test_selector==s and r.lifecycle=='isolated_self_modification_arc',f'registry_{v}_coherent')
for name in ('README.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md'):
    active=(ROOT/name).read_text(encoding='utf-8').split('<details id="retained-pre-v1250-compatibility">',1)[0];req('v1265.9' in active,f'{name}_current_visible');req('v1266' in active,f'{name}_next_visible');req('v1264.9' in active,f'{name}_v1264_retained_visible');req('v1255.9' in active,f'{name}_v1255_boundary_visible')
req(sig()==before,'checkpoint_preserves_source')
print(json.dumps({'ok':True,'suite':'v1265.9-isolated-self-modification-checkpoint','passed':len(CHECKS),'failed':0,'checks':CHECKS,'read_only_checkpoint':True,'provider_contacted':False,'active_source_modified':False,'private_runtime_copied':False,'self_update_authorized':False,'release_authorized':False},indent=2,sort_keys=True))
