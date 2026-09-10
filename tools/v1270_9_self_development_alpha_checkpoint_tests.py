from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from self_development_alpha_checkpoint import build_self_development_alpha_checkpoint
r=build_self_development_alpha_checkpoint(source_root=ROOT)
checks=[]
def req(v,l):
    if not v:raise AssertionError(l)
    checks.append(l)
req(r['ok'],'checkpoint_ok');req(r['checkpoint_version']=='1270.9','checkpoint_version');req(r['read_only'] is True,'read_only');req(r['details']['checkpoint_executes_provider'] is False,'no_provider');req(r['details']['checkpoint_executes_tests'] is False,'no_tests');req(r['details']['checkpoint_mutates_source'] is False,'no_source_mutation');req(r['details']['checkpoint_applies_update'] is False,'no_update');req(r['details']['next_bounded_unit']=='v1271 Long-Running Work Sessions','next_unit')
print(json.dumps({'ok':True,'suite':'v1270.9-self-development-alpha-checkpoint','passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
