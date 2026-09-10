from pathlib import Path
import json, os, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.supervised_development_proposal_integration_checkpoint import build_supervised_development_proposal_integration_checkpoint
from conscious_agent.api_server import dispatch_api

def main():
 with tempfile.TemporaryDirectory() as td:
  out=build_supervised_development_proposal_integration_checkpoint(Path(td),source_root=ROOT); assert out['ok'] and len(out['checks'])==19 and not out['runtime_mutated'] and not out['source_modified']
 with tempfile.TemporaryDirectory() as td:
  env=dict(os.environ); env['EIDOLON_DATA_DIR']=td; cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'supervised-development-proposal-integration-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True); assert cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1136.8'
 status,payload=dispatch_api('GET','/api/cognition/supervised-development-proposal-integration-checkpoint'); assert status==200 and payload['data']['contract_version']=='v1136.8'
 post,_=dispatch_api('POST','/api/cognition/supervised-development-proposal-integration-checkpoint',body={}); assert post!=200
 dashboard=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(); assert 'supervised-development-proposal-integration-checkpoint-panel' in dashboard and '/api/cognition/supervised-development-proposal-integration-checkpoint' in dashboard
 print('v1136.8 supervised development proposal integration checkpoint: 5/5 passed')
if __name__=='__main__': main()
