from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,source_only_manifest
from isolated_self_modification import execute_isolated_self_modification
from intelligent_test_selection_foundations import prepare_intelligent_test_selection
from iterative_self_repair_foundations import ITERATIVE_REPAIR_DENIED_AUTHORITY,MAX_REPAIR_ATTEMPTS,prepare_iterative_self_repair,validate_iterative_self_repair_foundation,public_iterative_self_repair
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tools').mkdir();(p/'data').mkdir()
    files={'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n','conscious_agent/package_integrity.py':'POLICY=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n','conscious_agent/app.py':'def value():\n    return 1\n','tools/test_app.py':'from app import value\nassert value()==1\n','tools/v1265_9_isolated_self_modification_checkpoint_tests.py':'assert True\n','tools/v1247_9_privacy_security_secret_management_audit_tests.py':'assert True\n'}
    for rel,text in files.items():q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    (p/'data/private.json').write_text('{"secret":"never"}\n');return p
def lineage(base):
    p=fixture(base);sm=base/'sm';ts=base/'ts';b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'1'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'2'*64}]);rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=sm)
    done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=sm,authorization_phrase=rec['authorization_phrase'],provider=lambda r:{'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'}]})
    sel=prepare_intelligent_test_selection(done['operation_id'],p,self_modification_runtime_root=sm,runtime_root=ts);return p,sm,ts,done,sel
with tempfile.TemporaryDirectory(prefix='eidolon-v1267-found-') as td:
    base=Path(td);p,sm,ts,done,sel=lineage(base);active=source_only_manifest(p)['source_manifest_digest'];rr=base/'rr';rec=prepare_iterative_self_repair(sel['selection_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr)
    req(rec['status']=='iterative_self_repair_prepared','repair_prepared');req(rec['phase']=='prepared','phase_prepared');req(validate_iterative_self_repair_foundation(rec)['ok'],'foundation_valid');req(rec['max_repair_attempts']==2==MAX_REPAIR_ATTEMPTS,'bounded_two_repairs');req(rec['selected_test_count']>=1,'selected_tests_bound');req(rec['authorization_phrase'].startswith('AUTHORIZE SELF REPAIR '),'exact_authorization_phrase');req(rec['tests_executed'] is False and rec['provider_contacted'] is False,'prepare_has_no_execution');req(rec['candidate_workspace_modified'] is False and rec['active_source_modified'] is False,'prepare_no_mutation');req(source_only_manifest(p)['source_manifest_digest']==active,'active_source_immutable');rest=prepare_iterative_self_repair(sel['selection_id'],p,self_modification_runtime_root=sm,test_selection_runtime_root=ts,runtime_root=rr);req(rest['repair_id']==rec['repair_id'] and rest['operation_status']=='restored','duplicate_prepare_idempotent');pub=public_iterative_self_repair(rec);req(pub['content_minimized'] and pub['attempt_count']==0,'public_content_minimized')
    for k,v in ITERATIVE_REPAIR_DENIED_AUTHORITY.items():req(rec[k] is v,f'{k}_exact')
print(json.dumps({'ok':True,'suite':'v1267.0-v1267.2-iterative-self-repair-foundations','passed':len(C),'failed':0,'checks':C,'tests_executed':False,'provider_contacted':False,'active_source_modified':False},indent=2,sort_keys=True))
