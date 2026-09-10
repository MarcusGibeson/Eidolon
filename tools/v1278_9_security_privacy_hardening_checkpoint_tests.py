from __future__ import annotations
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from security_privacy_hardening_checkpoint import build_security_privacy_hardening_checkpoint
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
r=build_security_privacy_hardening_checkpoint(source_root=ROOT);req(r['ok'],'ok');req(r['status']=='security_privacy_hardening_checkpoint_ready','status');req(r['checkpoint_version']=='1278.9','version')
for k,v in r['checks'].items():req(v,'check_'+k)
d=r['details'];req(d['next_bounded_unit']=='v1279 Operator Experience','next');req(d['v1279_started'] is False,'not_started');req(d['path_containment_hardened'],'path');req(d['archive_structure_hardened'],'archive');req(d['provider_material_content_minimized'],'provider');req(d['generic_approval_remains_non_authorizing'],'auth');req(d['governed_update_authority_unchanged'],'update_authority')
for k in ['checkpoint_executes_provider','checkpoint_executes_commands','checkpoint_executes_tests','checkpoint_executes_install','checkpoint_executes_update','checkpoint_mutates_source','private_provider_payloads_required']:req(d[k] is False,'readonly_'+k)
print(json.dumps({'ok':True,'suite':'v1278.9-security-privacy-hardening-checkpoint','passed':len(C),'failed':0,'checks':C},sort_keys=True))
