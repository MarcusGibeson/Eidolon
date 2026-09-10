from __future__ import annotations
import concurrent.futures,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,source_only_manifest
from isolated_self_modification import execute_isolated_self_modification
from intelligent_test_selection_foundations import prepare_intelligent_test_selection
from iterative_self_repair_foundations import prepare_iterative_self_repair,_record_digest,_record_path,_write_json,load_iterative_self_repair
from iterative_self_repair import execute_iterative_self_repair
from iterative_self_repair_reliability import recover_interrupted_iterative_self_repair,cancel_iterative_self_repair,inspect_iterative_self_repair_health,build_iterative_self_repair_operator_handoff
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir();
    for rel,text in {'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n','conscious_agent/package_integrity.py':'POLICY=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n','conscious_agent/app.py':'def value():\n    return 1\n','tools/test_app.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"conscious_agent"))\nfrom app import value\nassert value()==1\n','tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'assert True\n','tools/v1247_9_privacy_security_secret_management_audit_tests.py':'assert True\n'}.items():q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    return p
def chain(base):
    p=fixture(base);sm=base/'sm';ts=base/'ts';rr=base/'rr';b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'5'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'6'*64}]);rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm);done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=sm,authorization_phrase=rec['authorization_phrase'],provider=lambda r:{'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]});sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts);repair=prepare_iterative_self_repair(sel['selection_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr);return p,sm,ts,rr,repair
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-repeat-') as td:
    base=Path(td);p,sm,ts,rr,repair=chain(base);calls=[]
    def ineffective(req):calls.append(dict(req));return {'strategy_code':'wrong_behavior_patch','changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 3\n'}]}
    result=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=ineffective);req(result['status']=='repeated_failed_repair_detected','same_failure_blocks_repeat');req(len(calls)==1,'same_failure_stops_before_second_provider');req(source_only_manifest(p)['source_manifest_digest']==repair['source_manifest_digest'],'repeat_case_active_source_unchanged')
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-testtamper-') as td:
    base=Path(td);p,sm,ts,rr,repair=chain(base);calls=[]
    def testtamper(req):calls.append(1);return {'strategy_code':'weaken_test','changes':[{'path':'tools/test_app.py','action':'modify','content':'assert True\n'}]}
    result=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=testtamper);req(result['status']=='trusted_test_repair_mutation_rejected','trusted_test_mutation_rejected');req(len(calls)==1,'test_tamper_provider_once')
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-providerfail-') as td:
    base=Path(td);p,sm,ts,rr,repair=chain(base);calls=[]
    def fail(req):calls.append(1);raise RuntimeError('offline')
    result=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=fail);req(result['status']=='iterative_self_repair_provider_failed','provider_failure_blocks');again=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=fail);req(again['operation_status']=='restored' and len(calls)==1,'provider_failure_never_auto_retries')
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-recover-') as td:
    base=Path(td);p,sm,ts,rr,repair=chain(base);running=dict(repair);running.update({'phase':'running','status':'iterative_self_repair_provider_pending','authorization_consumed':True,'provider_pending_attempt':1});running['record_digest']=_record_digest(running);_write_json(_record_path(repair['repair_id'],rr),running);rec=recover_interrupted_iterative_self_repair(repair['repair_id'],runtime_root=rr);req(rec['status']=='interrupted_self_repair_requires_operator_review' and rec['interrupted_provider_retry_authorized'] is False,'interrupted_provider_requires_review')
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-cancel-') as td:
    base=Path(td);p,sm,ts,rr,repair=chain(base);c=cancel_iterative_self_repair(repair['repair_id'],runtime_root=rr);req(c['phase']=='cancelled','cancellation_persists');req(cancel_iterative_self_repair(repair['repair_id'],runtime_root=rr)['operation_status']=='restored','cancel_idempotent')
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-stale-') as td:
    base=Path(td);p,sm,ts,rr,repair=chain(base);(p/'README_NEXT_STEPS.md').write_text('changed\n');calls=[];r=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=lambda req:calls.append(1) or {});req(r['status']=='iterative_self_repair_stale_active_source' and not calls,'stale_active_source_blocks_before_provider')

# Two distinct failure states may use the second bounded repair, and the second
# provider request must carry the post-first-repair candidate plus strategy history.
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-two-attempt-') as td:
    base=Path(td);p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir()
    for rel,text in {
      'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n','conscious_agent/package_integrity.py':'POLICY=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n',
      'conscious_agent/app.py':'def value():\n    return 1\n','conscious_agent/helper.py':'from app import value\ndef helper():\n    return value()\n',
      'tools/test_app.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"conscious_agent"))\nfrom app import value\nassert value()==1\n',
      'tools/test_helper.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"conscious_agent"))\nfrom helper import helper\nassert helper()==1\n',
      'tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'assert True\n','tools/v1247_9_privacy_security_secret_management_audit_tests.py':'assert True\n'}.items():
        q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    sm=base/'sm';ts=base/'ts';rr=base/'rr';b,sx,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'b'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'c'*64}]);rec=prepare_isolated_self_modification(p,plan,sx,b,runtime_root=sm);done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=sm,authorization_phrase=rec['authorization_phrase'],provider=lambda r:{'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]});sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts);repair=prepare_iterative_self_repair(sel['selection_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr);requests=[]
    def two_stage(req):
        requests.append(dict(req))
        if len(requests)==1:
            return {'strategy_code':'isolate_helper_from_bad_value','changes':[{'path':'conscious_agent/helper.py','action':'modify','content':'def helper():\n    return 1\n'}]}
        return {'strategy_code':'restore_app_value','changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 1\n'}]}
    result=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=two_stage)
    req(result['phase']=='passed' and len(requests)==2,'distinct_failure_allows_second_bounded_repair');req(requests[1]['candidate_manifest_digest']!=requests[0]['candidate_manifest_digest'],'second_repair_receives_updated_candidate_manifest');req(requests[1]['prior_strategy_codes']==['isolate_helper_from_bad_value'],'second_repair_receives_strategy_history')

health=inspect_iterative_self_repair_health(source_root=ROOT);req(health['ok'],'health_ready');handoff=build_iterative_self_repair_operator_handoff(source_root=ROOT);req(handoff['ok'] and handoff['next_bounded_unit']=='v1268 Operator Review Handoff','handoff_ready');req('application_remains_separately_governed_by_v1255' in handoff['review_boundaries'],'application_boundary_explicit');req('cross_process_repair_lease' in handoff['native_windows_review'],'windows_concurrency_review_explicit')
# Long path preparation remains deterministic.
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-long-') as td:
    deep=Path(td)
    for i in range(5):deep=deep/('seg_'+str(i)+'_'+'x'*30)
    deep.mkdir(parents=True);p,sm,ts,rr,repair=chain(deep);req(len(str(Path(sm).resolve()))>180,'long_path_fixture_deep');req(repair['phase']=='prepared','long_path_repair_prepared')
print(json.dumps({'ok':True,'suite':'v1267.6-v1267.8-iterative-self-repair-reliability','passed':len(C),'failed':0,'checks':C,'active_source_modified':False},indent=2,sort_keys=True))
