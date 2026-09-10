from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from dependency_packaging_checkpoint import build_dependency_packaging_checkpoint
from checkpoint_registry import inspect_checkpoint_registry
C=[]
def req(v,l):
    if not v: raise AssertionError(l)
    C.append(l)
r=build_dependency_packaging_checkpoint(source_root=ROOT)
req(r['ok'],'checkpoint_ok');req(r['checkpoint_version']=='1275.9','checkpoint_version');req(r['status']=='dependency_packaging_management_checkpoint_ready','checkpoint_status');req(r['read_only'] is True,'checkpoint_read_only')
for key in ('checkpoint_executes_provider','checkpoint_executes_commands','checkpoint_executes_tests','checkpoint_executes_install','checkpoint_executes_update','checkpoint_mutates_source'):
    req(r['details'][key] is False,'no_'+key)
req(r['details']['next_bounded_unit']=='v1276 Architecture Boundary Extraction','next_v1276')
reg=inspect_checkpoint_registry(source_root=ROOT);row=next((x for x in reg['checkpoints'] if x.get('module')=='conscious_agent.dependency_packaging_checkpoint'),{})
req(bool(row),'registry_present');req(row.get('contract_version')=='v1275.9','registry_contract')
print(json.dumps({'ok':True,'suite':'v1275.9-dependency-packaging-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
