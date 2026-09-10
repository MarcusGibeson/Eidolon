import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
from conscious_agent.curiosity_lifecycle_checkpoint import build_curiosity_lifecycle_checkpoint
from conscious_agent.api_server import dispatch_api
def req(x):
 if not x:raise AssertionError()
base=Path(tempfile.mkdtemp());root=base/'runtime'/'cognition';before=list(root.rglob('*')) if root.exists() else [];p=build_curiosity_lifecycle_checkpoint(root,source_root=ROOT);after=list(root.rglob('*')) if root.exists() else [];req(p['contract_version']=='v1111.8' and p['runtime_mutated'] is False and before==after);req(p['consciousness_claimed'] is False and p['external_browsing_performed'] is False and p['message_sent'] is False);os.environ['EIDOLON_DATA_DIR']=str(base/'runtime');status,payload=dispatch_api('GET','/api/cognition/curiosity-lifecycle-checkpoint');req(status==200 and (payload.get('data') or {}).get('contract_version')=='v1111.8');status2,_=dispatch_api('POST','/api/cognition/curiosity-lifecycle-checkpoint',body={});req(status2!=200);q=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'curiosity-lifecycle-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(q.returncode==0 and json.loads(q.stdout)['contract_version']=='v1111.8');text=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('curiosity-lifecycle-checkpoint-panel' in text and '/api/cognition/curiosity-lifecycle-checkpoint' in text);req(p['action_authority_changed'] is False);print('{"passed":8,"total":8,"suite":"v1111.8"}')
