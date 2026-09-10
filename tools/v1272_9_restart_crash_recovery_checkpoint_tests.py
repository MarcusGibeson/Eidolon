from __future__ import annotations
import json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from restart_crash_recovery_checkpoint import build_restart_crash_recovery_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
r=build_restart_crash_recovery_checkpoint(source_root=ROOT)
req(r['ok'],'checkpoint_ok');req(r['checkpoint_version']=='1272.9','checkpoint_version');req(r['status']=='restart_crash_recovery_checkpoint_ready','checkpoint_status')
req(r['details']['checkpoint_executes_provider'] is False,'checkpoint_no_provider');req(r['details']['checkpoint_executes_tests'] is False,'checkpoint_no_tests');req(r['details']['checkpoint_executes_update'] is False,'checkpoint_no_update')
req(r['details']['checkpoint_mutates_source'] is False and r['details']['checkpoint_resumes_work'] is False,'checkpoint_read_only_behavior')
req(r['details']['next_bounded_unit']=='v1273 Ownership and Concurrency','next_v1273');req(r['read_only'] is True,'checkpoint_read_only')
reg=inspect_checkpoint_registry(source_root=ROOT);row=next((x for x in reg['checkpoints'] if x.get('module')=='conscious_agent.restart_crash_recovery_checkpoint'),{})
req(bool(row),'registry_present');req(row.get('contract_version')=='v1272.9','registry_contract')
print(json.dumps({'ok':True,'suite':'v1272.9-restart-crash-recovery-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
