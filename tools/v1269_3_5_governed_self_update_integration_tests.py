from __future__ import annotations
import json,os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1269_fixture import approved_chain
from governed_self_update_foundations import prepare_governed_self_update,load_governed_self_update
from governed_self_update import authorize_and_apply_governed_self_update,prepare_successful_self_update_rollback,authorize_and_rollback_successful_self_update
from isolated_self_modification_foundations import source_only_manifest
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-int-') as td:
    b=Path(td);c=approved_chain(b);rt=b/'update';u=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=rt);before=source_only_manifest(c['source'])['source_manifest_digest']
    bad=authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase='go ahead',restart_health_verifier=lambda r,d:{'ok':True});req(bad['status']=='governed_self_update_exact_authorization_required','exact_authorization_required');req(source_only_manifest(c['source'])['source_manifest_digest']==before,'bad_auth_no_write')
    calls=[]
    def health(root,digest):calls.append((str(root),digest));return {'ok':True,'signals':[{'code':'startup','state':'healthy'},{'code':'import','state':'healthy'}]}
    res=authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=health);req(res['ok'] and res['restart_health_passed'],'update_verified');req(len(calls)==1,'health_once');req(source_only_manifest(c['source'])['source_manifest_digest']==u['candidate_manifest_digest'],'candidate_installed');req(res['release_authorized'] is False,'release_denied');replay=authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=health);req(replay['operation_status']=='restored' and len(calls)==1,'apply_replay_idempotent')
    rb=prepare_successful_self_update_rollback(u['update_id'],c['source'],runtime_root=rt);req(rb['ok'],'rollback_prepared');bad_rb=authorize_and_rollback_successful_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase='rollback');req(not bad_rb['ok'],'rollback_exact_auth');done=authorize_and_rollback_successful_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=rb['authorization_phrase']);req(done['ok'] and done['source_restored_to_baseline'],'rollback_complete');req(source_only_manifest(c['source'])['source_manifest_digest']==before,'baseline_restored')
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-healthfail-') as td:
    b=Path(td);c=approved_chain(b);rt=b/'update';u=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=rt);before=source_only_manifest(c['source'])['source_manifest_digest'];res=authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=lambda r,d:{'ok':False,'signals':[{'code':'startup','state':'failed'}]});req(res['status']=='governed_self_update_rolled_back_after_failure','health_failure_rolls_back');req(res['automatic_rollback_performed'],'automatic_rollback');req(source_only_manifest(c['source'])['source_manifest_digest']==before,'health_failure_baseline_restored')
print(json.dumps({'ok':True,'suite':'v1269.3-v1269.5-governed-self-update-integration','passed':len(C),'failed':0,'checks':C},sort_keys=True))
