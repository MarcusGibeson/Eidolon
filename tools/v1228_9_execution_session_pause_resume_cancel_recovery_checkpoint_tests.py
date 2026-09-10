from __future__ import annotations
import json, os, subprocess, sys, tempfile, time, shutil
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from conscious_agent.execution_session_pause_resume_cancel_recovery_checkpoint import build_execution_session_pause_resume_cancel_recovery_checkpoint
S=time.monotonic(); C=[]
def r(v,x=None): C.append(bool(v)); (_ for _ in ()).throw(AssertionError(x)) if not v else None
runtime=tempfile.mkdtemp(prefix='v1228cp-')
try:
 report=build_execution_session_pause_resume_cancel_recovery_checkpoint(source_root=ROOT,runtime_root=runtime)
 for v in [report['ok'] is True,report['status']=='execution_session_pause_resume_cancel_recovery_checkpoint_ready',report['contract_version']=='v1228.9',report['read_only'] is True,report['runtime_data_read'] is False,report['source_modified'] is False,report['project_modified'] is False,report['authority_granted'] is False,report['provider_contacted'] is False,report['commands_executed'] is False,report['tests_executed'] is False,report['pause_applied'] is False,report['resume_applied'] is False,report['cancel_applied'] is False,report['recovery_applied'] is False,report['checks']==report['passed'] and report['checks']>=100]: r(v,report)
 cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'execution-session-pause-resume-cancel-recovery-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=180,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}); r(cli.returncode==0,cli.stderr); cr=json.loads(cli.stdout); r(cr['ok'] is True); r(cr['contract_version']=='v1228.9')
 api=(ROOT/'conscious_agent'/'api_server.py').read_text(); r('execution-session-pause-resume-cancel-recovery-checkpoint' in api)
 rel=(ROOT/'tools'/'release_verify.py').read_text(); r('v1228.9-execution-session-pause-resume-cancel-recovery-checkpoint' in rel)
 ordinary=(ROOT/'conscious_agent'/'ordinary_chat_development_campaign.py').read_text(); r('process_execution_session_pause_resume_cancel_recovery_control' in ordinary)
 meta=(ROOT/'conscious_agent'/'release_metadata.py').read_text(); r('WORKING_SOURCE_VERSION = "1228.9"' in meta); r('NEXT_RECOMMENDED_ARC = "v1229.0-v1229.2 Execution Outcome Reflection and Learning Integration Foundations"' in meta)
finally: shutil.rmtree(runtime,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1228.9','checks':len(C),'passed':sum(C),'elapsed_seconds':round(time.monotonic()-S,4),'checkpoint_read_only':True,'transition_applied':False},sort_keys=True))
