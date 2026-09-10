import json, subprocess, sys, tempfile
from pathlib import Path
from conscious_agent.understandable_cognitive_control_configuration import create_cognitive_control_configuration_preview
from conscious_agent.understandable_cognitive_controls_intake_checkpoint import build_understandable_cognitive_controls_intake_checkpoint
from conscious_agent.api_server import dispatch_api
ROOT=Path(__file__).resolve().parents[1]; checks=[]
def req(x):
    if not x: raise AssertionError
    checks.append(True)
with tempfile.TemporaryDirectory() as td:
    runtime=Path(td)/'runtime'; create_cognitive_control_configuration_preview({'domain':'resource_use','mode':'minimal','intensity':.1},runtime_root=runtime)
    r=build_understandable_cognitive_controls_intake_checkpoint(runtime,source_root=ROOT)
    req(r['contract_version']=='v1146.2'); req(r['ok']); req(r['passed']==r['total']==26); req(r['read_only']); req(not r['post_available']); req(r['summary']['control_domain_count']==6)
proc=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'understandable-cognitive-controls-intake-checkpoint'],cwd=ROOT,text=True,capture_output=True)
req(proc.returncode==0 and json.loads(proc.stdout)['contract_version']=='v1146.2')
status,payload=dispatch_api('GET','/api/cognition/understandable-cognitive-controls-intake-checkpoint'); req(status==200 and payload['data']['contract_version']=='v1146.2')
status,_=dispatch_api('POST','/api/cognition/understandable-cognitive-controls-intake-checkpoint'); req(status in {404,405})
dash=(ROOT/'conscious_agent/dashboard_first_use.py').read_text(); req('understandable-cognitive-controls-intake-checkpoint-panel' in dash and '/api/cognition/understandable-cognitive-controls-intake-checkpoint' in dash)
print(json.dumps({'passed':len(checks),'total':10,'suite':'v1146.2'}))
