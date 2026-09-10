from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,source_only_manifest
from isolated_self_modification import execute_isolated_self_modification
from intelligent_test_selection import select_tests_for_isolated_self_candidate,explain_selected_tests
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir();(p/'data').mkdir()
    files={
      'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n',
      'conscious_agent/release_metadata.py':'WORKING_SOURCE_VERSION="fixture"\n',
      'conscious_agent/checkpoint_registry.py':'CHECKPOINTS=[]\n',
      'conscious_agent/package_integrity.py':'POLICY=True\n',
      'README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n',
      'tools/v1250_3_release_metadata_consolidation_tests.py':'def test_release():\n    assert True\n',
      'tools/v1250_4_checkpoint_registry_consolidation_tests.py':'def test_registry():\n    assert True\n',
      'tools/v1247_9_privacy_security_secret_management_audit_tests.py':'def test_privacy():\n    assert True\n',
      'tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'def test_selfmod():\n    assert True\n'}
    for rel,text in files.items(): q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    (p/'data/private.json').write_text('{"secret":"x"}\n',encoding='utf-8');return p
with tempfile.TemporaryDirectory(prefix='eidolon-v1266-integration-') as td:
    base=Path(td);p=fixture(base);sm=base/'sm';ts=base/'ts';before=source_only_manifest(p)['source_manifest_digest']
    b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'3'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'4'*64}])
    rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm)
    calls=[]
    def provider(req):
        calls.append(1);return {'changes':[{'path':'conscious_agent/release_authority.py','action':'modify','content':'WORKING_SOURCE_VERSION="fixture2"\n'},{'path':'conscious_agent/checkpoint_registry.py','action':'modify','content':'CHECKPOINTS=["fixture2"]\n'}]}
    done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=sm,authorization_phrase=rec['authorization_phrase'],provider=provider);req(len(calls)==1 and done['phase']=='sealed','candidate_created_once')
    sel=select_tests_for_isolated_self_candidate(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts);req(sel['status']=='intelligent_test_selection_ready','integrated_selection_ready')
    paths=[r['relative_path'] for r in sel['selected_tests']];req('tools/v1250_3_release_metadata_consolidation_tests.py' in paths,'release_metadata_regression_selected');req('tools/v1250_4_checkpoint_registry_consolidation_tests.py' in paths,'registry_regression_selected')
    req('release_control' in sel['affected_surfaces'],'release_control_surface_detected');req(sel['risk_band']=='high','governance_change_high_risk')
    explanation=explain_selected_tests(sel);req(explanation['ok'] and explanation['selected_test_count']==sel['selected_test_count'],'explanation_ready');req(explanation['tier_counts']['regression']>=1,'regression_tier_explained');req(explanation['content_minimized'],'explanation_content_minimized')
    req(explanation['tests_executed'] is False and explanation['test_execution_authorized'] is False,'explanation_does_not_execute')
    req(source_only_manifest(p)['source_manifest_digest']==before,'active_source_still_unchanged');req(len(calls)==1,'selection_does_not_recontact_provider')
print(json.dumps({'ok':True,'suite':'v1266.3-v1266.5-intelligent-test-selection-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_calls':len(calls),'tests_executed':False,'active_source_modified':False},indent=2,sort_keys=True))
