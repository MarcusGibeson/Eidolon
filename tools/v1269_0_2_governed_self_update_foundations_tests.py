from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1269_fixture import approved_chain
from governed_self_update_foundations import *
from isolated_self_modification_foundations import source_only_manifest
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-found-') as td:
    b=Path(td);c=approved_chain(b);rt=b/'update';before=source_only_manifest(c['source'])['source_manifest_digest'];u=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=rt)
    req(u['phase']=='prepared','prepared');req(validate_governed_self_update_packet(u)['ok'],'valid');req(u['fresh_preflight_passed'],'fresh_preflight');req(u['backup_required_before_first_write'],'backup_required');req(u['restart_health_verification_required'],'restart_required');req(u['automatic_rollback_on_failure_required'],'automatic_rollback_required');req(u['changed_file_count']>=1,'changed_files');req(all(not x['content_exposed'] for x in u['changed_files']),'content_minimized');req(source_only_manifest(c['source'])['source_manifest_digest']==before,'prepare_read_only');req(not _read_json(_backup_path(u['update_id'],rt)),'backup_deferred_until_authorization');r=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=rt);req(r['operation_status']=='restored','idempotent_prepare');req(r['update_id']==u['update_id'],'stable_id')
    for k,v in DENIED_AUTHORITY.items():req(u[k] is v,k+'_denied')
print(json.dumps({'ok':True,'suite':'v1269.0-v1269.2-governed-self-update-foundations','passed':len(C),'failed':0,'checks':C},sort_keys=True))
