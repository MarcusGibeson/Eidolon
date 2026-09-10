from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'conscious_agent')]
from conscious_agent.curiosity_continuity_checkpoint import build_curiosity_continuity_checkpoint
from conscious_agent.api_server import dispatch_api
def req(x,m='failed'):
 if not x:raise AssertionError(m)
def main():
 base=Path(tempfile.mkdtemp());root=base/'runtime'/'cognition';before=list(root.rglob('*')) if root.exists() else []
 p=build_curiosity_continuity_checkpoint(root,source_root=ROOT);after=list(root.rglob('*')) if root.exists() else []
 req(p['contract_version']=='v1111.2' and p['runtime_mutated'] is False);req(before==after);req(p['consciousness_claimed'] is False and p['provider_contacted'] is False and p['external_browsing_performed'] is False)
 os.environ['EIDOLON_DATA_DIR']=str(base/'runtime');status,payload=dispatch_api('GET','/api/cognition/curiosity-continuity-checkpoint');req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1111.2');status2,_=dispatch_api('POST','/api/cognition/curiosity-continuity-checkpoint',body={});req(status2!=200)
 q=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'curiosity-continuity-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(q.returncode==0 and json.loads(q.stdout)['contract_version']=='v1111.2')
 text=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('curiosity-continuity-checkpoint-panel' in text and '/api/cognition/curiosity-continuity-checkpoint' in text)
 print('{"passed":8,"total":8,"suite":"v1111.2"}')
if __name__=='__main__':main()
