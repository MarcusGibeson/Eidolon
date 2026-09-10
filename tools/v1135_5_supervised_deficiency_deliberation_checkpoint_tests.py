from pathlib import Path
import json, os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.supervised_deficiency_deliberation_checkpoint import build_supervised_deficiency_deliberation_checkpoint
from conscious_agent.api_server import dispatch_api
def main():
 with tempfile.TemporaryDirectory() as td:
  out=build_supervised_deficiency_deliberation_checkpoint(Path(td),source_root=ROOT); assert out['ok'] and len(out['checks'])==21 and not out['runtime_mutated'] and not out['source_modified']
 with tempfile.TemporaryDirectory() as td:
  env=dict(os.environ); env['EIDOLON_DATA_DIR']=td; cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'supervised-deficiency-deliberation-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True); assert cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1135.5'
 status,payload=dispatch_api('GET','/api/cognition/supervised-deficiency-deliberation-checkpoint'); assert status==200 and payload['data']['contract_version']=='v1135.5'
 post,_=dispatch_api('POST','/api/cognition/supervised-deficiency-deliberation-checkpoint',body={}); assert post!=200
 dashboard=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8'); assert 'supervised-deficiency-deliberation-checkpoint-panel' in dashboard and '/api/cognition/supervised-deficiency-deliberation-checkpoint' in dashboard
 print('v1135.5 supervised deficiency deliberation checkpoint: 5/5 passed')
if __name__=='__main__': main()
