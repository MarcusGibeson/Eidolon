from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from governed_self_update_checkpoint import build_governed_self_update_checkpoint
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_governed_self_update_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint_ready');req(r['checkpoint_version']=='1269.9','version');req(r['status']=='governed_self_update_checkpoint_ready','status');d=r['details'];req(d['checkpoint_executes_update'] is False and d['checkpoint_restarts_process'] is False and d['checkpoint_mutates_source'] is False,'read_only');req(d['next_bounded_unit']=='v1270 Self-Development Alpha Checkpoint','next_unit');req(d['self_update_authorized'] is False and d['release_authorized'] is False,'authority_denied');req('automatic_failure_rollback' in d['contract'],'rollback_contract');req('separate_success_rollback_authorization' in d['contract'],'separate_rollback')
print(json.dumps({'ok':True,'suite':'v1269.9-governed-self-update-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
