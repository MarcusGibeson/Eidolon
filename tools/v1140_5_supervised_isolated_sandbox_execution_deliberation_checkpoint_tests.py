from pathlib import Path
import json, os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.supervised_isolated_sandbox_execution_deliberation_checkpoint import build_supervised_isolated_sandbox_execution_deliberation_checkpoint
from conscious_agent.api_server import dispatch_api
checks=[]
def check(n,v): checks.append((n,bool(v))); print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition'; report=build_supervised_isolated_sandbox_execution_deliberation_checkpoint(r,source_root=ROOT); check('checkpoint 14/14',report['ok'] and len(report['checks'])==14); check('read only',not report['runtime_mutated'] and not report['source_modified']); check('authority',not report['patch_text_exposed'] and not report['external_action_executed']); env=dict(os.environ); env['EIDOLON_DATA_DIR']=td; cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'supervised-isolated-sandbox-execution-deliberation-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True); check('cli',cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1140.5'); old=os.environ.get('EIDOLON_DATA_DIR'); os.environ['EIDOLON_DATA_DIR']=td
 try:
  status,payload=dispatch_api('GET','/api/cognition/supervised-isolated-sandbox-execution-deliberation-checkpoint'); check('get api',status==200 and payload['data']['contract_version']=='v1140.5'); check('post rejected',dispatch_api('POST','/api/cognition/supervised-isolated-sandbox-execution-deliberation-checkpoint')[0]!=200)
 finally:
  if old is None: os.environ.pop('EIDOLON_DATA_DIR',None)
  else: os.environ['EIDOLON_DATA_DIR']=old
assert all(v for _,v in checks); print(f'RESULT {sum(v for _,v in checks)}/{len(checks)}')
