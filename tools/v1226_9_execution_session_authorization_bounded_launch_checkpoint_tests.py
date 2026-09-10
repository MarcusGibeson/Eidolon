from __future__ import annotations
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from conscious_agent.execution_session_authorization_bounded_launch_checkpoint import build_execution_session_authorization_bounded_launch_checkpoint
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
runtime=tempfile.mkdtemp(prefix='v1226cp-')
try:
 report=build_execution_session_authorization_bounded_launch_checkpoint(source_root=ROOT,runtime_root=runtime)
 for v in [report['ok'] is True,report['status']=='execution_session_authorization_bounded_launch_checkpoint_ready',report['contract_version']=='v1226.9',report['read_only'] is True,report['runtime_data_read'] is False,report['source_modified'] is False,report['project_modified'] is False,report['authority_granted'] is False,report['provider_contacted'] is False,report['commands_executed'] is False,report['tests_executed'] is False,report['execution_session_launch_authorized'] is False,report['execution_session_launched'] is False,report['checks']==report['passed'] and report['checks']>=70]: r(v,report)
 cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'execution-session-authorization-bounded-launch-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}); r(cli.returncode==0,cli.stderr); cr=json.loads(cli.stdout); r(cr['ok'] is True); r(cr['contract_version']=='v1226.9')
 api=(ROOT/'conscious_agent'/'api_server.py').read_text(); r('parts == ["cognition", "execution-session-authorization-bounded-launch-checkpoint"]' in api)
 rel=(ROOT/'tools'/'release_verify.py').read_text(); r('v1226.9-execution-session-authorization-bounded-launch-checkpoint' in rel)
 ordinary=(ROOT/'conscious_agent'/'ordinary_chat_development_campaign.py').read_text(); r('process_execution_session_authorization_bounded_launch_control' in ordinary)
 meta=(ROOT/'conscious_agent'/'release_metadata.py').read_text(); r('WORKING_SOURCE_VERSION = "1226.9"' in meta); r('NEXT_RECOMMENDED_ARC = "v1227.0-v1227.2 Live Execution Monitoring and Operator Intervention Foundations"' in meta)
finally: shutil.rmtree(runtime,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1226.9','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'internal_checkpoint_checks':report['checks'],'read_only':True,'launch_authority_granted':False},sort_keys=True))
