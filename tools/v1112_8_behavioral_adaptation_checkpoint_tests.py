from pathlib import Path
import json,os,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];passed=0
def req(x):
 global passed
 assert x;passed+=1
with tempfile.TemporaryDirectory() as td:
 base=Path(td);root=base/'runtime'/'cognition';root.mkdir(parents=True);os.environ['EIDOLON_DATA_DIR']=str(base/'runtime')
 from conscious_agent.behavioral_adaptation_checkpoint import build_behavioral_adaptation_checkpoint
 c=build_behavioral_adaptation_checkpoint(root,source_root=ROOT);req(c['contract_version']=='v1112.8' and c['runtime_mutated'] is False);req(all(x['status']=='pass' for x in c['checks']));req(not c['behavior_changed'] and not c['authorization_granted'] and not c['external_action_executed'])
 from conscious_agent.api_server import dispatch_api
 status,p=dispatch_api('GET','/api/cognition/behavioral-adaptation-checkpoint');req(status==200 and (p.get('data') or {}).get('contract_version')=='v1112.8');status2,_=dispatch_api('POST','/api/cognition/behavioral-adaptation-checkpoint',body={});req(status2!=200)
 run=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'behavioral-adaptation-checkpoint','--json'],capture_output=True,text=True,env=dict(os.environ),timeout=60);req(run.returncode==0 and json.loads(run.stdout)['contract_version']=='v1112.8')
 dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('behavioral-adaptation-checkpoint-panel' in dash and '/api/cognition/behavioral-adaptation-checkpoint' in dash);req(not c['hidden_reasoning_exposed'] and not c['raw_messages_exposed']);req(c['desktop_verification_status']=='pending');req(c['summary']['proposal_count']==0)
print(json.dumps({'passed':passed,'total':10,'suite':'v1112.8'}))
