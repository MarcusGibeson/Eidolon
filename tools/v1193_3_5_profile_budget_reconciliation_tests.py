from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1193-5-'))
from conscious_agent.verifier_profile_reconciliation import *
from conscious_agent.verifier_profile_reconciliation_checkpoint import build_verifier_profile_reconciliation_checkpoint
from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
checks=[]
def req(v):checks.append(bool(v));assert v
r=build_verifier_profile_reconciliation_checkpoint(source_root=ROOT)
for k,v in {'ok':True,'contract_version':'v1193.5','checkpoint_id':'verifier-profile-reconciliation:v1193.5','read_only':True,'content_free':True,'source_unchanged':True,'runtime_mutated':False,'fixture_deleted':False,'verifier_retired':False,'global_profile_pass_claimed':False,'execution_invoked':False,'authority_granted':False}.items():req(r.get(k)==v)
req(r['passed']==r['total']);req(r['total']>=20)
f=r['summaries']['focused'];q=r['summaries']['quick'];u=r['summaries']['full']
for v in (f['global_profile_pass'] is True,f['result_count']==1,q['current_regressions_passed'] is True,q['global_profile_pass'] is False,q['inherited_nonpass_count']==1,q['historical_debt_separate'] is True,q['within_profile_budget'] is True,u['profile']=='full'):req(v)
for name in ('tamper','private-field','authority','order-mismatch','duplicate-expected','mixed-profile','invalid-budget'):req(name in r['blocked_cases']);req(bool(r['blocked_cases'][name]))
row=create_profile_result(verifier_id='x',classification='current_regression',profile='focused',sequence=0,expected_checks=1,actual_checks=1,budget_seconds=5,elapsed_milliseconds=25,outcome='passed')
req(validate_profile_results([row])==[]);rep=reconcile_profile(profile='focused',expected_verifiers=['x'],results=[row],profile_budget_seconds=5);req(rep['status']=='reconciled');s=public_profile_summary(rep);req(s['global_profile_pass'] is True);req(s['current_failure_count']==0)
for field,value,error in [('profile','bad','invalid_profile'),('result_digest','0'*64,'result_tamper'),('prompt','x','private_field'),('authority_state','granted','authority_expansion')]:
 mut=dict(row);mut[field]=value;req(error in validate_profile_results([mut]))
debt=create_profile_result(verifier_id='d',classification='historical_debt',profile='quick',sequence=0,expected_checks=2,actual_checks=0,budget_seconds=5,elapsed_milliseconds=10,outcome='blocked',debt_group='old');req(validate_profile_results([debt])==[])
reg=inspect_checkpoint_registry(source_root=ROOT);entry=next(x for x in reg['checkpoints'] if x['checkpoint_id']=='verifier-profile-reconciliation-checkpoint');req(entry['contract_version']=='v1193.5');req(entry['builder']=='build_verifier_profile_reconciliation_checkpoint')
p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'verifier-profile-reconciliation-checkpoint'],cwd=ROOT,text=True,capture_output=True);req(p.returncode==0);req(json.loads(p.stdout)['ok'] is True)
status,payload=dispatch_api('GET','/api/cognition/verifier-profile-reconciliation-checkpoint');req(status==200);req(payload['data']['ok'] is True);status,_=dispatch_api('POST','/api/cognition/verifier-profile-reconciliation-checkpoint');req(status in {404,405})
html=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8');req('verifier-profile-reconciliation-checkpoint-panel' in html);req('/api/cognition/verifier-profile-reconciliation-checkpoint' in html)
meta=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8');req('WORKING_SOURCE_VERSION = "1193.5"' in meta);req('v1193.6-v1193.8' in meta)
release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8');req(release.count('v1193.5-profile-budget-reconciliation')==1);req(release.count('v1193_3_5_profile_budget_reconciliation_tests.py')==1)
for name in ('README.md','README_NEXT_STEPS.md','archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md','README_RELEASE_HISTORY.md'):
 t=(ROOT/name).read_text(encoding='utf-8');req('v1193.3-v1193.5 Deterministic Profile and Budget Reconciliation' in t);req('v1193.6-v1193.8' in t)
print(json.dumps({'suite':'v1193.3-v1193.5-profile-budget-reconciliation','passed':sum(checks),'total':len(checks),'ok':all(checks)},sort_keys=True))
