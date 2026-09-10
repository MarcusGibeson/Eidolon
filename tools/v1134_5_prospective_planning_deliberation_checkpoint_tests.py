from pathlib import Path
import json, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.prospective_planning_deliberation_checkpoint import build_prospective_planning_deliberation_checkpoint
from conscious_agent.api_server import dispatch_api
def main():
 with tempfile.TemporaryDirectory() as td:
  out=build_prospective_planning_deliberation_checkpoint(Path(td),source_root=ROOT); assert out['ok'] and len(out['checks'])==22; assert not out['runtime_mutated'] and not out['source_modified']
 with tempfile.TemporaryDirectory() as td:
  env=dict(__import__('os').environ); env['EIDOLON_DATA_DIR']=td; cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'prospective-planning-deliberation-checkpoint'],cwd=ROOT,env=env,text=True,capture_output=True); assert cli.returncode==0 and json.loads(cli.stdout)['contract_version']=='v1134.5'
 status,payload=dispatch_api('GET','/api/cognition/prospective-planning-deliberation-checkpoint'); assert status==200 and (payload.get('data') or {}).get('contract_version')=='v1134.5'
 post_status,_=dispatch_api('POST','/api/cognition/prospective-planning-deliberation-checkpoint',body={}); assert post_status!=200
 dashboard=(ROOT/'conscious_agent'/'dashboard_first_use.py').read_text(encoding='utf-8'); assert 'prospective-planning-deliberation-checkpoint-panel' in dashboard and '/api/cognition/prospective-planning-deliberation-checkpoint' in dashboard
 print('v1134.5 prospective planning deliberation checkpoint: 5/5 passed')
if __name__=='__main__': main()
