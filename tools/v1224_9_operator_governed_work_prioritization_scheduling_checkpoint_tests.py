from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from conscious_agent.operator_governed_work_prioritization_scheduling_checkpoint import build_operator_governed_work_prioritization_scheduling_checkpoint
START=time.monotonic(); CHECKS=[]
def require(v,d=None):
 CHECKS.append(bool(v))
 if not v: raise AssertionError(d)
runtime=tempfile.mkdtemp(prefix='eidolon-v1224-checkpoint-')
try:
 report=build_operator_governed_work_prioritization_scheduling_checkpoint(source_root=ROOT,runtime_root=runtime)
 require(report['ok'] is True,report); require(report['status']=='operator_governed_work_prioritization_scheduling_checkpoint_ready')
 require(report['contract_version']=='v1224.9'); require(report['read_only'] is True)
 require(report['runtime_data_read'] is False); require(report['source_modified'] is False)
 require(report['project_modified'] is False); require(report['authority_granted'] is False)
 require(report['schedule_execution_authorized'] is False); require(report['work_dispatch_authorized'] is False)
 require(report['checks']==report['passed'] and report['checks']>=60,report)
 cli=subprocess.run([sys.executable,str(ROOT/'eidolon.py'),'operator-governed-work-prioritization-scheduling-checkpoint'],cwd=ROOT,text=True,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 require(cli.returncode==0,cli.stderr); cli_report=json.loads(cli.stdout)
 require(cli_report['ok'] is True); require(cli_report['contract_version']=='v1224.9')
 api=(ROOT/'conscious_agent'/'api_server.py').read_text(encoding='utf-8')
 require('parts == ["cognition", "operator-governed-work-prioritization-scheduling-checkpoint"]' in api)
 release=(ROOT/'tools'/'release_verify.py').read_text(encoding='utf-8')
 require('v1224.9-operator-governed-work-prioritization-scheduling-checkpoint' in release)
 ordinary=(ROOT/'conscious_agent'/'ordinary_chat_development_campaign.py').read_text(encoding='utf-8')
 require('process_operator_governed_work_prioritization_control' in ordinary)
 metadata=(ROOT/'conscious_agent'/'release_metadata.py').read_text(encoding='utf-8')
 require('WORKING_SOURCE_VERSION = "1224.9"' in metadata)
finally: shutil.rmtree(runtime,ignore_errors=True)
print(json.dumps({'ok':True,'version':'1224.9','checks':len(CHECKS),'passed':sum(CHECKS),'elapsed_seconds':round(time.monotonic()-START,4),'internal_checkpoint_checks':report['checks'],'read_only':True,'execution_authorized':False},sort_keys=True))
