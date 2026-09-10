from __future__ import annotations
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1240-checkpoint-')
from integrated_developer_beta_checkpoint import build_integrated_developer_beta_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.api_server import handle_api_get,dispatch_api
checks=[]
def check(v): checks.append(bool(v))
r=build_integrated_developer_beta_checkpoint(source_root=ROOT)
for v in (r.get('ok'),r.get('status')=='integrated_developer_beta_checkpoint_ready',r.get('checkpoint_id')=='integrated-developer-beta-checkpoint',r.get('contract_version')=='v1240.9',r.get('retained_contract_version')=='v1240.8',r.get('milestone_name')=='Integrated Developer Beta',r.get('roadmap_path')=='Balanced Mind-and-Action Path 3',r.get('passed')==r.get('total'),r.get('read_only') is True,r.get('content_free') is True,r.get('source_signature_unchanged') is True,r.get('source_file_count_before')==r.get('source_file_count_after'),r.get('runtime_data_read') is False,r.get('runtime_data_written') is False,r.get('provider_contacted') is False,r.get('commands_executed') is False,r.get('tests_executed') is False,r.get('project_modified') is False,r.get('source_modified') is False,r.get('cognition_written') is False,r.get('authority_granted') is False): check(v)
p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'integrated-developer-beta-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=300,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}); check(p.returncode==0)
try: cli=json.loads(p.stdout.strip().splitlines()[-1]); check(cli.get('ok')); check(cli.get('checkpoint_id')=='integrated-developer-beta-checkpoint')
except Exception: check(False); check(False)
reg=inspect_checkpoint_registry(source_root=ROOT); row=next((x for x in reg.get('checkpoints',[]) if x.get('checkpoint_id')=='integrated-developer-beta-checkpoint'),{}); check(row.get('contract_version')=='v1240.9'); check(row.get('read_only') is True); check(row.get('required_input_count')==0)
code,payload=handle_api_get('/api/cognition/integrated-developer-beta-checkpoint'); check(code==200); check(payload.get('ok')); check((payload.get('data') or {}).get('checkpoint_id')=='integrated-developer-beta-checkpoint')
code,payload=dispatch_api('POST','/api/cognition/integrated-developer-beta-benchmark',body={}); check(code in {404,405}); check(not payload.get('ok'))
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks),'checkpoint':{'external':r.get('passed'),'internal':r.get('total')}},sort_keys=True)); raise SystemExit(0 if all(checks) else 1)
