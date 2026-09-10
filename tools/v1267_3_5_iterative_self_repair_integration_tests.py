from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,source_only_manifest,load_self_modification
from isolated_self_modification import execute_isolated_self_modification
from intelligent_test_selection_foundations import prepare_intelligent_test_selection
from iterative_self_repair_foundations import prepare_iterative_self_repair
from iterative_self_repair import execute_iterative_self_repair
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir();
    files={'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n','conscious_agent/package_integrity.py':'POLICY=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n','conscious_agent/app.py':'def value():\n    return 1\n','tools/test_app.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parents[1]/"conscious_agent"))\nfrom app import value\nassert value()==1\n','tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'assert True\n','tools/v1247_9_privacy_security_secret_management_audit_tests.py':'assert True\n'}
    for rel,text in files.items():q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    return p
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-int-') as td:
    base=Path(td);p=fixture(base);sm=base/'sm';ts=base/'ts';rr=base/'rr';b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'3'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'4'*64}]);selfrec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm);done=execute_isolated_self_modification(selfrec['operation_id'],p,runtime_root=sm,authorization_phrase=selfrec['authorization_phrase'],provider=lambda r:{'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]});sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts);repair=prepare_iterative_self_repair(sel['selection_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr);active=source_only_manifest(p)['source_manifest_digest'];calls=[]
    def provider(req):
        calls.append(dict(req));return {'strategy_code':'restore_expected_behavior','changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 1\n'}]}
    denied=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase='go ahead',provider=provider);req(denied['status']=='iterative_self_repair_exact_authorization_required','vague_auth_denied');req(len(calls)==0,'no_provider_without_exact_auth')
    result=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=provider);req(result['phase']=='passed' and result['status']=='iterative_self_repair_candidate_verified','repair_campaign_passed');req(len(calls)==1,'one_repair_provider_call');req(result['verification']['passed'] is True and result['verification']['test_run_count']==2,'failed_then_passed_tests');req(len(result['attempts'])==1 and result['attempts'][0]['strategy_code']=='restore_expected_behavior','repair_attempt_recorded');req(result['attempts'][0]['content_minimized'],'repair_evidence_minimized');workspace=Path(load_self_modification(done['operation_id'],runtime_root=sm)['workspace_path']);req('return 1' in (workspace/'conscious_agent/app.py').read_text(),'candidate_repaired');req(source_only_manifest(p)['source_manifest_digest']==active,'active_source_unchanged');req(calls[0]['active_source_mutation_authorized'] is False and calls[0]['application_authorized'] is False,'provider_request_authority_denied');replay=execute_iterative_self_repair(repair['repair_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr,authorization_phrase=repair['authorization_phrase'],provider=provider);req(replay['operation_status']=='restored' and replay['provider_called_this_invocation'] is False,'passed_replay_idempotent');req(len(calls)==1,'replay_no_provider')
print(json.dumps({'ok':True,'suite':'v1267.3-v1267.5-iterative-self-repair-integration','passed':len(C),'failed':0,'checks':C,'provider_calls':len(calls),'active_source_modified':False},indent=2,sort_keys=True))
