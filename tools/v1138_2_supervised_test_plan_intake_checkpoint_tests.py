import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.supervised_test_plan_intake_checkpoint import build_supervised_test_plan_intake_checkpoint
from conscious_agent.api_server import dispatch_api
p=t=f=0
def check(n,v):
 global p,t,f;t+=1;p+=bool(v);f+=not bool(v);print(('PASS' if v else 'FAIL'),n)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'cognition';report=build_supervised_test_plan_intake_checkpoint(r,source_root=ROOT);check('checkpoint 18/18',report['ok'] and len(report['checks'])==18);check('read only',not report['runtime_mutated'] and not report['source_modified']);check('privacy authority',not report['test_plan_text_exposed'] and not report['test_code_exposed'] and not report['source_modified_by_checkpoint'] and not report['external_action_executed']);env=dict(os.environ);env['EIDOLON_DATA_DIR']=td;cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'supervised-test-plan-intake-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True);check('cli',cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1138.2');old=os.environ.get('EIDOLON_DATA_DIR');os.environ['EIDOLON_DATA_DIR']=td
 try:
  status,payload=dispatch_api('GET','/api/cognition/supervised-test-plan-intake-checkpoint');check('get api',status==200 and payload['data']['contract_version']=='v1138.2');check('post rejected',dispatch_api('POST','/api/cognition/supervised-test-plan-intake-checkpoint')[0]!=200)
 finally:
  if old is None:os.environ.pop('EIDOLON_DATA_DIR',None)
  else:os.environ['EIDOLON_DATA_DIR']=old
print(json.dumps({'passed':p,'total':t,'failed':f,'suite':'v1138.2'}));raise SystemExit(0 if not f else 1)
