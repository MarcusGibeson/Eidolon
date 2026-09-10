from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1193-2-'))
from conscious_agent.verifier_ownership import *
from conscious_agent.verifier_ownership_checkpoint import build_verifier_ownership_checkpoint
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[]
def req(v): checks.append(bool(v)); assert v
r=build_verifier_ownership_checkpoint(source_root=ROOT)
for k,v in {'ok':True,'contract_version':'v1193.2','checkpoint_id':'verifier-ownership:v1193.2','read_only':True,'content_free':True,'source_unchanged':True,'runtime_mutated':False,'fixture_deleted':False,'verifier_retired':False,'global_profile_pass_claimed':False,'execution_invoked':False,'authority_granted':False}.items():req(r.get(k)==v)
req(r['passed']==r['total']);req(r['total']>=35);s=r['summary']
for k,v in {'record_count':6,'owner_count':5,'current_regression_count':1,'retained_checkpoint_count':3,'historical_debt_count':2,'debt_separated':True,'content_free':True}.items():req(s.get(k)==v)
req(s['profile_budgets_seconds']=={'focused':30,'full':870,'quick':840})
for name in ('duplicate-id','invalid-owner','missing-origin','private-field','authority','tamper'):req(name in r['blocked_cases']);req(bool(r['blocked_cases'][name]))
row=create_verifier_record(verifier_id='x',owner='release',classification='current_regression',suite_path='tools/x.py',source_version='1193.2',fixture_group='x',expected_checks=1,budget_seconds=5,profile_membership=['focused'])
req(validate_verifier_records([row])==[]);req(build_ownership_registry([row])['status']=='registered');req(public_ownership_summary(build_ownership_registry([row]))['current_regression_count']==1)
mut=dict(row);mut['owner']='bad';req('invalid_owner' in validate_verifier_records([mut]))
mut=dict(row);mut['record_digest']='0'*64;req('record_tamper' in validate_verifier_records([mut]))
mut=dict(row);mut['prompt']='x';req('private_field' in validate_verifier_records([mut]))
reg=inspect_checkpoint_registry(source_root=ROOT);entry=next(x for x in reg['checkpoints'] if x['checkpoint_id']=='verifier-ownership-checkpoint');req(entry['contract_version']=='v1193.2');req(entry['builder']=='build_verifier_ownership_checkpoint')
p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'verifier-ownership-checkpoint'],cwd=ROOT,text=True,capture_output=True);req(p.returncode==0);req(json.loads(p.stdout)['ok'] is True)
status,payload=dispatch_api('GET','/api/cognition/verifier-ownership-checkpoint');req(status==200);req(payload['data']['ok'] is True)
status,_=dispatch_api('POST','/api/cognition/verifier-ownership-checkpoint');req(status in {404,405})
html=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');req('verifier-ownership-checkpoint-panel' in html);req('/api/cognition/verifier-ownership-checkpoint' in html)
meta=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8');req('WORKING_SOURCE_VERSION = "1193.2"' in meta);req('v1193.3-v1193.5' in meta)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8');req(release.count('v1193.2-verifier-ownership-foundations')==1);req(release.count('v1193_0_2_verifier_ownership_tests.py')==1)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/name).read_text(encoding='utf-8');req('v1193.0-v1193.2 Verifier Ownership and Historical-Debt Foundations' in t);req('v1193.3-v1193.5' in t)
print(json.dumps({'suite':'v1193.0-v1193.2-verifier-ownership','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True))
