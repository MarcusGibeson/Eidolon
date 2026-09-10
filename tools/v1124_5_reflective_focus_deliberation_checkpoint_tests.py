import os,sys,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; r=Path(tempfile.mkdtemp()); os.environ['EIDOLON_DATA_DIR']=str(r); from conscious_agent.reflective_focus_deliberation_checkpoint import build_reflective_focus_deliberation_checkpoint
x=build_reflective_focus_deliberation_checkpoint(); assert x['ok'] and x['passed']==18 and x['total']==18
p=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'reflective-focus-deliberation-checkpoint','--json'],cwd=ROOT,env={**os.environ,'EIDOLON_DATA_DIR':str(r)},capture_output=True,text=True); assert p.returncode==0 and 'v1124.5' in p.stdout
from conscious_agent.api_server import dispatch_api
s,payload=dispatch_api('GET','/api/cognition/reflective-focus-deliberation-checkpoint'); assert s==200 and payload['data']['contract_version']=='v1124.5'; s,_=dispatch_api('POST','/api/cognition/reflective-focus-deliberation-checkpoint',body={}); assert s in (404,405)
assert 'reflective-focus-deliberation-checkpoint-panel' in (ROOT/'conscious_agent/dashboard_first_use.py').read_text(); print('18/18')
