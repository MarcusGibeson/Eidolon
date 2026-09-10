import json,subprocess,sys,tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_configuration import create_cognitive_control_configuration_preview
from conscious_agent.understandable_cognitive_control_activation import activate_cognitive_control_preview,CONFIRMATION_PHRASE
from conscious_agent.understandable_cognitive_control_enforcement import evaluate_cognitive_control
from conscious_agent.understandable_cognitive_controls_execution_checkpoint import build_understandable_cognitive_controls_execution_checkpoint
from conscious_agent.api_server import dispatch_api
ROOT=Path(__file__).resolve().parents[1];checks=[]
def req(x):
 if not x: raise AssertionError
 checks.append(True)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime';p=create_cognitive_control_configuration_preview({'domain':'attention','mode':'focused','intensity':.5},runtime_root=r)
 activate_cognitive_control_preview(runtime_root=r,preview_id=p['configuration_id'],preview_digest=p['structural_digest'],confirmation=CONFIRMATION_PHRASE,operator_id='op',request_id='a1')
 evaluate_cognitive_control(runtime_root=r,domain='attention',event_id='e1',consumer_id='attention',requested_intensity=.8)
 x=build_understandable_cognitive_controls_execution_checkpoint(r,source_root=ROOT);req(x['contract_version']=='v1146.5');req(x['ok']);req(x['passed']==x['total']==27);req(x['read_only']);req(not x['post_available']);req(x['summary']['active_control_count']==1)
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'understandable-cognitive-controls-execution-checkpoint'],cwd=ROOT,text=True,capture_output=True);req(proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1146.5')
status,payload=dispatch_api('GET','/api/cognition/understandable-cognitive-controls-execution-checkpoint');req(status==200 and payload['data']['contract_version']=='v1146.5')
status,_=dispatch_api('POST','/api/cognition/understandable-cognitive-controls-execution-checkpoint');req(status in {404,405})
dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('understandable-cognitive-controls-execution-checkpoint-panel' in dash and '/api/cognition/understandable-cognitive-controls-execution-checkpoint' in dash)
print(json.dumps({'passed':len(checks),'total':10,'suite':'v1146.5'}))
