from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from long_running_work_sessions_checkpoint import build_long_running_work_sessions_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_long_running_work_sessions_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint_ok');req(r['checkpoint_version']=='1271.9','checkpoint_version');req(r['status']=='long_running_work_sessions_checkpoint_ready','checkpoint_status');req(r['details']['v1270_harness_duration_finding_preserved'] is True,'harness_finding_preserved');req(r['details']['checkpoint_executes_provider'] is False and r['details']['checkpoint_executes_tests'] is False,'checkpoint_read_only_execution');req(r['details']['next_bounded_unit']=='v1272 Restart and Crash Recovery','next_v1272');req(r['read_only'] is True,'checkpoint_read_only')
reg=inspect_checkpoint_registry(source_root=ROOT);row=next((x for x in reg['checkpoints'] if x.get('module')=='conscious_agent.long_running_work_sessions_checkpoint'),{});req(bool(row),'registry_present');req(row.get('contract_version')=='v1271.9','registry_contract')
print(json.dumps({'ok':True,'suite':'v1271.9-long-running-work-sessions-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
