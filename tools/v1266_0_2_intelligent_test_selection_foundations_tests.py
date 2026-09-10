from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,source_only_manifest
from isolated_self_modification import execute_isolated_self_modification
from intelligent_test_selection_foundations import TEST_SELECTION_DENIED_AUTHORITY,prepare_intelligent_test_selection,validate_test_selection
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def sig(root):
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and not p.is_symlink(): rows.append((p.relative_to(root).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir();(p/'docs').mkdir();(p/'data').mkdir()
    files={
      'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n',
      'conscious_agent/package_integrity.py':'POLICY=True\n',
      'README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n',
      'conscious_agent/app.py':'def value():\n    return 1\n',
      'conscious_agent/helper.py':'from app import value\ndef helper():\n    return value()\n',
      'tools/test_app.py':'from app import value\ndef test_value():\n    assert value()==1\n',
      'tools/test_helper.py':'from helper import helper\ndef test_helper():\n    assert helper()==1\n',
      'tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'def test_checkpoint():\n    assert True\n',
      'tools/v1247_9_privacy_security_secret_management_audit_tests.py':'def test_privacy():\n    assert True\n',
      'docs/architecture.md':'# Architecture\n'}
    for rel,text in files.items(): q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    (p/'data/private.json').write_text('{"memory":"never"}\n',encoding='utf-8');return p
def candidate(p,runtime):
    b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'1'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'2'*64}])
    rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=runtime)
    def provider(req): return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]}
    done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=runtime,authorization_phrase=rec['authorization_phrase'],provider=provider)
    return done
before=sig(ROOT)
with tempfile.TemporaryDirectory(prefix='eidolon-v1266-foundations-') as td:
    base=Path(td);p=fixture(base);sm=base/'sm';ts=base/'ts';active=source_only_manifest(p)['source_manifest_digest'];done=candidate(p,sm)
    req(done['phase']=='sealed','v1265_candidate_sealed');sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts)
    req(sel['status']=='intelligent_test_selection_ready','selection_ready');req(validate_test_selection(sel)['ok'],'selection_valid')
    req(sel['changed_paths']==['conscious_agent/app.py'],'changed_path_exact');req('python_runtime' in sel['affected_surfaces'],'python_surface_detected')
    paths=[r['relative_path'] for r in sel['selected_tests']];req('tools/test_app.py' in paths,'direct_import_test_selected');req('tools/test_helper.py' in paths,'transitive_dependent_test_selected')
    req(sel['focused_test_count']>=1,'focused_tests_present');req(sel['regression_test_count']>=1,'regression_expansion_present')
    req(all(r['content_exposed'] is False and r['reason_code'] for r in sel['selected_tests']),'selection_evidence_content_minimized')
    req(sel['tests_executed'] is False and sel['commands_executed'] is False and sel['provider_contacted'] is False,'selection_has_no_execution_side_effect')
    req(source_only_manifest(p)['source_manifest_digest']==active,'active_source_immutable')
    restored=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts);req(restored['selection_id']==sel['selection_id'] and restored['operation_status']=='restored','duplicate_selection_idempotent')
    for k,v in TEST_SELECTION_DENIED_AUTHORITY.items(): req(sel[k] is v,f'{k}_exact')
req(sig(ROOT)==before,'foundation_suite_preserves_repository')
print(json.dumps({'ok':True,'suite':'v1266.0-v1266.2-intelligent-test-selection-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'tests_executed':False,'provider_contacted':False,'active_source_modified':False},indent=2,sort_keys=True))
