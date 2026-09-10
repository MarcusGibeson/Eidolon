from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from coding_alpha_checkpoint import build_coding_alpha_checkpoint
from checkpoint_registry import checkpoint_registry_manifest,lookup_checkpoint,validate_checkpoint_report
from release_authority import WORKING_SOURCE_VERSION,PREVIOUS_WORKING_SOURCE_VERSION,NEXT_BOUNDED_UNIT,CODEX_REVIEW_STATE,CHECKPOINT_HISTORY
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
before=sig(); report=build_coding_alpha_checkpoint(source_root=ROOT); validation=validate_checkpoint_report(report,source_root=ROOT); manifest=checkpoint_registry_manifest(source_root=ROOT); record=lookup_checkpoint('1260.9')
req(report['ok'] and validation['ok'],'checkpoint_report_valid'); req(report['checkpoint_version']=='1260.9' and report['contract_version']=='v1260.9','checkpoint_version_exact'); req(all(report['checks'].values()),'checkpoint_checks_all_pass')
req(report['read_only'] and report['content_free'],'checkpoint_read_only_content_free'); req(report['details']['provider_contacted'] is False and report['details']['commands_executed'] is False and report['details']['tests_executed'] is False,'checkpoint_executes_nothing')
req(report['details']['stage_count']==13,'checkpoint_records_full_stage_chain'); req(len(report['details']['behavioral_evidence'])==3,'three_behavioral_suites_named'); req(report['details']['native_windows_multi_process_validation']=='desktop_review_required','native_windows_review_required')
current_key=tuple(int(x) for x in WORKING_SOURCE_VERSION.split('.')); req(current_key >= (1260,9),'release_metadata_at_or_after_v1260_9'); req(any(v=='1260.9' and title=='Coding Alpha Checkpoint' for v,title in CHECKPOINT_HISTORY),'v1260_9_history_retained'); req((WORKING_SOURCE_VERSION=='1260.9' and NEXT_BOUNDED_UNIT=='v1261 Evidence-Based Project Inspection' and CODEX_REVIEW_STATE=='v1260_coding_alpha_checkpoint_ready_for_desktop_codex_review') or WORKING_SOURCE_VERSION!='1260.9','historical_next_and_codex_exact_at_v1260_9')
req(record is not None and record.lifecycle=='coding_alpha_checkpoint_arc','registry_lifecycle_exact'); req(record is not None and record.test_selector=='tools/v1260_9_coding_alpha_checkpoint_tests.py','registry_selector_exact')
req(manifest['ok'] and manifest['working_source_version']==WORKING_SOURCE_VERSION,'registry_manifest_current')
for v,s in {'1260.0':'tools/v1260_0_2_coding_alpha_foundations_tests.py','1260.3':'tools/v1260_3_5_coding_alpha_campaign_tests.py','1260.6':'tools/v1260_6_8_coding_alpha_reliability_tests.py','1260.9':'tools/v1260_9_coding_alpha_checkpoint_tests.py'}.items():
    r=lookup_checkpoint(v); req(r is not None and r.test_selector==s and r.lifecycle=='coding_alpha_checkpoint_arc',f'registry_{v}_coherent')
active_history=(ROOT/'README_RELEASE_HISTORY.md').read_text(encoding='utf-8').split('<details id="retained-pre-v1250-compatibility">',1)[0]; req('v1260.9' in active_history,'v1260_9_visible_in_release_history'); req(f'v{WORKING_SOURCE_VERSION}' in (ROOT/'README.md').read_text(encoding='utf-8').split('<details id="retained-pre-v1250-compatibility">',1)[0],'current_source_visible_after_v1260')
req(sig()==before,'checkpoint_preserves_source')
print(json.dumps({'ok':True,'suite':'v1260.9-coding-alpha-checkpoint','passed':len(CHECKS),'failed':0,'checks':CHECKS,'read_only_checkpoint':True,'provider_contacted':False,'release_authorized':False},indent=2,sort_keys=True))
