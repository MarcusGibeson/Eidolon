from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from development_observability_checkpoint import build_development_observability_checkpoint
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_development_observability_checkpoint(source_root=ROOT);req(r['ok'],'ok');req(r['status']=='development_observability_checkpoint_ready','status');req(r['checkpoint_version']=='1277.9','version')
for k,v in r['checks'].items():req(v,'check_'+k)
d=r['details'];req(d['v1270_monolithic_probe_finding_preserved_as_performance_signal'],'v1270_finding');req(d['global_timeout_increase_is_not_the_fix'],'no_timeout_fix');req(d['next_bounded_unit']=='v1278 Security and Privacy Hardening','next');req(d['v1278_started'] is False,'not_started')
for k in ['checkpoint_executes_provider','checkpoint_executes_commands','checkpoint_executes_tests','checkpoint_executes_install','checkpoint_executes_update','checkpoint_mutates_source','private_provider_payloads_required']:req(d[k] is False,'readonly_'+k)
print(json.dumps({'ok':True,'suite':'v1277.9-development-observability-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
