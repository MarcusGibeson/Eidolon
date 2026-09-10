from __future__ import annotations
import concurrent.futures,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification
from isolated_self_modification import execute_isolated_self_modification
from intelligent_test_selection_foundations import _digest,_record_digest,_record_path,_semantic_payload,_write_json,prepare_intelligent_test_selection,validate_test_selection
from intelligent_test_selection_reliability import validate_test_selection_freshness,inspect_intelligent_test_selection_health,build_intelligent_test_selection_operator_handoff
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir();
    files={'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n','conscious_agent/package_integrity.py':'POLICY=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n','conscious_agent/app.py':'def value():\n    return 1\n','tools/test_app.py':'from app import value\ndef test_value():\n    assert value()==1\n','tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'def test_x():\n    assert True\n','tools/v1247_9_privacy_security_secret_management_audit_tests.py':'def test_y():\n    assert True\n'}
    for rel,text in files.items(): q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    return p
def make_candidate(base):
    p=fixture(base);sm=base/'sm';b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'5'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'6'*64}]);rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm)
    def provider(req): return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]}
    done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=sm,authorization_phrase=rec['authorization_phrase'],provider=provider);return p,sm,done
with tempfile.TemporaryDirectory(prefix='eidolon-v1266-reliability-') as td:
    base=Path(td);p,sm,done=make_candidate(base);ts=base/'ts'
    def worker(_): return prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts)['selection_id']
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: ids=list(ex.map(worker,range(8)))
    req(len(set(ids))==1,'concurrent_duplicate_selection_converges');sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts);req(sel['operation_status']=='restored','post_concurrency_restore')
    req(validate_test_selection_freshness(sel['selection_id'],p,self_modification_runtime_root=sm,runtime_root=ts)['ok'],'fresh_selection_valid')
    # Resealing only the outer record digest cannot hide semantic selection tamper.
    tam=dict(sel);tam['selected_tests']=list(tam['selected_tests'])+[{'relative_path':'tools/fake_tests.py','tier':'focused','reason_code':'tampered','evidence_strength':100,'content_exposed':False}];tam['selected_test_count']=len(tam['selected_tests']);tam['record_digest']=_record_digest(tam)
    req(not validate_test_selection(tam)['ok'],'resealed_semantic_tamper_rejected')
    # Even recomputing both public digests cannot make a semantically different selection match the candidate.
    stored=dict(sel);stored['selected_tests']=[];stored['selected_test_count']=0;stored['focused_test_count']=0;stored['regression_test_count']=0;stored['selection_digest']=_digest(_semantic_payload(stored));stored['record_digest']=_record_digest(stored);_write_json(_record_path(sel['selection_id'],ts),stored)
    req(validate_test_selection(stored)['ok'],'resealed_record_is_structurally_valid');semantic_stale=validate_test_selection_freshness(sel['selection_id'],p,self_modification_runtime_root=sm,runtime_root=ts);req(not semantic_stale['ok'] and not semantic_stale['selection_semantics_match'],'recomputed_semantic_tamper_rejected')
    _write_json(_record_path(sel['selection_id'],ts),{k:v for k,v in sel.items() if k!='operation_status'})
    # Candidate workspace change after selection makes the selection stale.
    record=json.loads((sm/'isolated_self_modification/records'/f"{done['operation_id']}.json").read_text());workspace=Path(record['workspace_path']);(workspace/'conscious_agent/app.py').write_text('def value():\n    return 3\n',encoding='utf-8')
    stale=validate_test_selection_freshness(sel['selection_id'],p,self_modification_runtime_root=sm,runtime_root=ts);req(not stale['ok'] and not stale['candidate_manifest_match'],'candidate_change_invalidates_selection')
    health=inspect_intelligent_test_selection_health(source_root=ROOT);req(health['ok'],'health_ready');handoff=build_intelligent_test_selection_operator_handoff(source_root=ROOT);req(handoff['ok'] and handoff['next_bounded_unit']=='v1267 Iterative Self-Repair','operator_handoff_ready');req('real_ntfs_junction_and_reparse_containment' in handoff['native_windows_review'],'windows_reparse_review_explicit');req('selection_does_not_execute_tests' in handoff['review_boundaries'],'execution_boundary_explicit')
# Existing provider-owned test modification is never accepted as trusted verification.
with tempfile.TemporaryDirectory(prefix='eidolon-v1266-test-ownership-') as td:
    base=Path(td);p=fixture(base);sm=base/'sm';b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'7'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'8'*64}]);rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm)
    def weaken(req): return {'changes':[{'path':'tools/test_app.py','action':'modify','content':'def test_value():\n    assert True\n'}]}
    done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=sm,authorization_phrase=rec['authorization_phrase'],provider=weaken)
    try: prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=base/'ts');blocked=False
    except ValueError as e: blocked='trusted_test' in str(e)
    req(blocked,'modified_trusted_test_blocks_selection')
# New candidate tests are supplemental only and cannot become trusted selected evidence.
with tempfile.TemporaryDirectory(prefix='eidolon-v1266-supplemental-') as td:
    base=Path(td);p=fixture(base);sm=base/'sm';b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'9'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'a'*64}]);rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm)
    def addtest(req): return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'},{'path':'tools/test_new.py','action':'create','content':'def test_new():\n    assert True\n'}]}
    done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=sm,authorization_phrase=rec['authorization_phrase'],provider=addtest);sel2=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=base/'ts')
    req('tools/test_new.py' in sel2['supplemental_candidate_tests'],'new_candidate_test_recorded_supplemental');req('tools/test_new.py' not in [r['relative_path'] for r in sel2['selected_tests']],'supplemental_test_not_trusted')

# Deep path determinism.
with tempfile.TemporaryDirectory(prefix='eidolon-v1266-long-') as td:
    deep=Path(td)
    for i in range(5): deep=deep/('segment_'+str(i)+'_'+'x'*35)
    deep.mkdir(parents=True);p,sm,done=make_candidate(deep);sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=deep/'ts');req(sel['selected_test_count']>=1,'long_path_selection_ready')
print(json.dumps({'ok':True,'suite':'v1266.6-v1266.8-intelligent-test-selection-reliability','passed':len(CHECKS),'failed':0,'checks':CHECKS,'tests_executed':False,'provider_contacted_by_selection':False,'active_source_modified':False},indent=2,sort_keys=True))
