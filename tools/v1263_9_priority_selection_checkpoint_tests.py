from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from priority_selection_checkpoint import build_priority_selection_checkpoint
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
before=sig();report=build_priority_selection_checkpoint(source_root=ROOT);validation=validate_checkpoint_report(report,source_root=ROOT);manifest=checkpoint_registry_manifest(source_root=ROOT);record=lookup_checkpoint('1263.9')
req(report['ok'] and validation['ok'],'checkpoint_report_valid');req(report['checkpoint_version']=='1263.9' and report['contract_version']=='v1263.9','checkpoint_version_exact');req(all(report['checks'].values()),'checkpoint_checks_all_pass')
req(report['read_only'] and report['content_free'],'checkpoint_read_only_content_free');req(report['details']['provider_contacted'] is False and report['details']['commands_executed'] is False and report['details']['runtime_data_read'] is False,'checkpoint_executes_and_reads_no_private_runtime')
req(report['details']['development_proposal_created'] is False and report['details']['schedule_created'] is False and report['details']['project_modified'] is False,'checkpoint_creates_no_action')
req(set(report['details']['priority_factor_contract'])=={'user_value','reliability_impact','urgency','reversibility','effort_cost','uncertainty_cost','risk_cost','dependency_readiness'},'priority_factor_contract_complete');req(report['details']['tie_handling']=='explicit_no_defensible_selection','tie_handling_exact');req(len(report['details']['behavioral_evidence'])==3,'three_behavioral_suites_named')
req(tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.')) >= (1263,9),'release_metadata_at_or_after_v1263_9');req(bool(NEXT_BOUNDED_UNIT),'current_next_arc_present');req(bool(CODEX_REVIEW_STATE),'current_codex_state_present')
req(record is not None and record.lifecycle=='priority_selection_arc','registry_lifecycle_exact');req(record is not None and record.test_selector=='tools/v1263_9_priority_selection_checkpoint_tests.py','registry_selector_exact')
req(manifest['ok'] and tuple(int(x) for x in manifest['working_source_version'].split('.')) >= (1263,9),'registry_manifest_at_or_after_v1263_9')
for v,s in {'1263.0':'tools/v1263_0_2_priority_selection_foundations_tests.py','1263.3':'tools/v1263_3_5_priority_selection_integration_tests.py','1263.6':'tools/v1263_6_8_priority_selection_reliability_tests.py','1263.9':'tools/v1263_9_priority_selection_checkpoint_tests.py'}.items():
    r=lookup_checkpoint(v);req(r is not None and r.test_selector==s and r.lifecycle=='priority_selection_arc',f'registry_{v}_coherent')
for name in ('README.md','README_NEXT_STEPS.md','README_RELEASE_HISTORY.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md'):
    active=(ROOT/name).read_text(encoding='utf-8').split('<details id="retained-pre-v1250-compatibility">',1)[0];req('v1263.9' in active,f'{name}_current_visible');req('v1264' in active,f'{name}_next_visible');req('v1262.9' in active,f'{name}_v1262_retained_visible')
req(sig()==before,'checkpoint_preserves_source')
print(json.dumps({'ok':True,'suite':'v1263.9-priority-selection-checkpoint','passed':len(CHECKS),'failed':0,'checks':CHECKS,'read_only_checkpoint':True,'provider_contacted':False,'runtime_data_read':False,'proposal_created':False,'schedule_created':False,'release_authorized':False},indent=2,sort_keys=True))
