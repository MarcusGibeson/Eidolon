import json,subprocess,sys,tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_continuity import record_cognitive_control_continuity
from conscious_agent.understandable_cognitive_control_reliability import review_cognitive_control_reliability
from conscious_agent.understandable_cognitive_controls_reliability_checkpoint import build_understandable_cognitive_controls_reliability_checkpoint
from conscious_agent.api_server import dispatch_api
ROOT=Path(__file__).resolve().parents[1];checks=[]
def req(x):
 if not x: raise AssertionError
 checks.append(True)
with tempfile.TemporaryDirectory() as td:
 r=Path(td)/'runtime';record_cognitive_control_continuity(runtime_root=r,cycle_id='c1');review_cognitive_control_reliability(runtime_root=r,review_id='r1');x=build_understandable_cognitive_controls_reliability_checkpoint(r,source_root=ROOT);req(x['contract_version']=='v1146.8');req(x['ok']);req(x['passed']==x['total']==26);req(x['read_only']);req(not x['post_available']);req(x['summary']['continuity_record_count']==1)
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'understandable-cognitive-controls-reliability-checkpoint'],cwd=ROOT,text=True,capture_output=True);req(proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1146.8')
status,payload=dispatch_api('GET','/api/cognition/understandable-cognitive-controls-reliability-checkpoint');req(status==200 and payload['data']['contract_version']=='v1146.8')
status,_=dispatch_api('POST','/api/cognition/understandable-cognitive-controls-reliability-checkpoint');req(status in {404,405})
dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text();req('understandable-cognitive-controls-reliability-checkpoint-panel' in dash and '/api/cognition/understandable-cognitive-controls-reliability-checkpoint' in dash)
print(json.dumps({'passed':len(checks),'total':10,'suite':'v1146.8'}))
