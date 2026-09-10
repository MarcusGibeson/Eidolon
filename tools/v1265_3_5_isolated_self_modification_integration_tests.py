from __future__ import annotations
import hashlib,json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from alternative_planning import generate_priority_and_alternative_plan
from isolated_self_modification_foundations import prepare_isolated_self_modification,source_only_manifest
from isolated_self_modification import execute_isolated_self_modification,public_self_modification_result
from isolated_self_modification_reliability import validate_self_modification_candidate
CHECKS=[]
def req(v,l):
    if not v: raise AssertionError(l)
    CHECKS.append(l)
def fixture(base):
    p=base/'Eidolon';(p/'conscious_agent').mkdir(parents=True);(p/'tests').mkdir();(p/'docs').mkdir();(p/'data').mkdir()
    for rel,text in {'conscious_agent/release_authority.py':'WORKING_SOURCE_VERSION="fixture"\n','conscious_agent/package_integrity.py':'POLICY=True\n','README_NEXT_STEPS.md':'next\n','pyproject.toml':'[project]\nname="demo"\n','conscious_agent/app.py':'def value():\n    return 1\n','tests/test_app.py':'def test_value():\n    assert True\n','docs/architecture.md':'# A\n'}.items(): q=p/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(text,encoding='utf-8')
    (p/'data/private.json').write_text('{"approvals":["private"]}\n',encoding='utf-8');return p
with tempfile.TemporaryDirectory(prefix='eidolon-v1265-integration-') as td:
    base=Path(td);p=fixture(base);runtime=base/'runtime';b,s,plan=generate_priority_and_alternative_plan(p,external_evidence=[{'kind':'runtime_health','status':'failed','claim_code':'startup','polarity':'supports','confidence':'high','evidence_digest':'a'*64}],priority_context=[{'objective_code':'investigate_runtime_health_signal:startup','user_value':'critical','urgency':'critical','reversibility':'medium','evidence_digest':'b'*64}]);rec=prepare_isolated_self_modification(p,plan,s,b,runtime_root=runtime);active_before=source_only_manifest(p)['source_manifest_digest'];calls=[]
    def provider(req):
        calls.append(dict(req));return {'changes':[{'path':'conscious_agent/app.py','action':'modify','content':'def value():\n    return 2\n'},{'path':'docs/repair.md','action':'create','content':'# Repair candidate\n'}]}
    denied=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=runtime,authorization_phrase='go ahead',provider=provider);req(not denied['ok'] and denied['status']=='isolated_self_modification_exact_authorization_required','vague_authorization_denied');req(len(calls)==0,'provider_not_contacted_without_exact_authorization')
    done=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=runtime,authorization_phrase=rec['authorization_phrase'],provider=provider);req(done['status']=='isolated_self_modification_candidate_ready' and done['phase']=='sealed','isolated_candidate_sealed');req(len(calls)==1,'provider_called_once');req(calls[0]['active_source_mutation_authorized'] is False and calls[0]['application_authorized'] is False,'provider_request_cannot_mutate_active_source')
    req(source_only_manifest(p)['source_manifest_digest']==active_before,'active_source_manifest_unchanged');workspace=Path(done['workspace_path']);req((workspace/'conscious_agent/app.py').read_text(encoding='utf-8').endswith('return 2\n'),'workspace_source_modified');req((workspace/'docs/repair.md').is_file(),'workspace_file_created');req(not (workspace/'data').exists(),'private_runtime_absent_in_candidate')
    result=done['result'];req(result['changed_file_count']==2 and result['candidate_manifest_digest']!=result['baseline_manifest_digest'],'candidate_diff_recorded');req(all(x['content_exposed'] is False for x in result['changed_files']),'review_evidence_content_minimized');req(result['tests_executed'] is False,'v1266_test_selection_not_preempted')
    pub=public_self_modification_result(done);req(pub['ok'] and pub['candidate_review_available'] if 'candidate_review_available' in pub else pub['changed_file_count']==2,'public_review_ready');req(pub['active_source_modified'] is False and pub['application_authorized'] is False and pub['self_update_authorized'] is False,'public_authority_denied')
    req(validate_self_modification_candidate(rec['operation_id'],p,runtime_root=runtime)['ok'],'sealed_candidate_valid')
    replay=execute_isolated_self_modification(rec['operation_id'],p,runtime_root=runtime,authorization_phrase=rec['authorization_phrase'],provider=provider);req(replay['operation_status']=='restored' and replay['provider_called_this_invocation'] is False,'duplicate_authorization_idempotent');req(len(calls)==1,'duplicate_does_not_recontact_provider')
print(json.dumps({'ok':True,'suite':'v1265.3-v1265.5-isolated-self-modification-integration','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_calls':len(calls),'active_source_modified':False,'tests_executed':False,'application_authorized':False,'release_authorized':False},indent=2,sort_keys=True))
