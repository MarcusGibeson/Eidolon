from __future__ import annotations
import json,os,sys,tempfile,time,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;os.environ['PYTHONDONTWRITEBYTECODE']='1'
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from v1269_fixture import approved_chain
from governed_self_update_foundations import *
from governed_self_update import authorize_and_apply_governed_self_update
from governed_self_update_reliability import *
from isolated_self_modification_foundations import source_only_manifest
C=[]
def req(v,l):
    if not v:raise AssertionError(l)
    C.append(l)
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-stale-') as td:
    b=Path(td);c=approved_chain(b);(c['source']/'README_NEXT_STEPS.md').write_text('drift\n');
    try:prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=b/'u')
    except ValueError as e:req('fresh' in str(e) or 'stale' in str(e),'stale_source_blocked')
    else:req(False,'stale_source_blocked')
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-concurrent-') as td:
    b=Path(td);c=approved_chain(b);rt=b/'u';u=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=rt);calls=[];out=[];lock=threading.Lock()
    def health(root,d):
        with lock:calls.append(d)
        time.sleep(.02);return {'ok':True,'signals':['ok']}
    def run():out.append(authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=health))
    ts=[threading.Thread(target=run) for _ in range(4)];[t.start() for t in ts];[t.join() for t in ts];req(len(calls)==1,'concurrent_update_once');req(all(x.get('ok') for x in out),'concurrent_results_ok')
    h=inspect_governed_self_update_health(u['update_id'],c['source'],runtime_root=rt);req(h['target_state']=='candidate' and h['recovery_disposition']=='separate_exact_rollback_available','health_candidate_state')
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-recovery-') as td:
    b=Path(td);c=approved_chain(b);rt=b/'u';u=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=rt);res=authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=lambda r,d:{'ok':True});req(res['ok'],'recovery_fixture_applied');rec=load_governed_self_update(u['update_id'],runtime_root=rt);rec['phase']='running';rec['status']='governed_self_update_running';rec['lease_expires_unix']=0;rec['write_started']=True;rec.pop('result',None);rec.pop('result_digest',None);rec['record_digest']=_record_digest(rec);_write_json(_update_path(u['update_id'],rt),rec);calls=[];r=authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=lambda root,d:(calls.append(d) or {'ok':True}));req(r['ok'] and len(calls)==1,'expired_running_recovers');req(source_only_manifest(c['source'])['source_manifest_digest']==u['candidate_manifest_digest'],'recovery_candidate_verified')
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-tamper-') as td:
    b=Path(td);c=approved_chain(b);rt=b/'u';u=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=rt);raw=dict(u);raw['candidate_manifest_digest']='0'*64;raw['record_digest']=_record_digest(raw);_write_json(_update_path(u['update_id'],rt),raw);req(validate_governed_self_update_packet(raw)['ok'] is True,'resealed_record_structurally_valid');bad=authorize_and_apply_governed_self_update(u['update_id'],c['source'],runtime_root=rt,authorization_phrase=u['authorization_phrase'],restart_health_verifier=lambda r,d:{'ok':True});req(not bad['ok'] and bad['status']=='governed_self_update_candidate_stale','resealed_semantic_candidate_tamper_blocked')
health=inspect_governed_self_update_surface_health(source_root=ROOT);req(health['ok'],'surface_health');ho=build_governed_self_update_operator_handoff(source_root=ROOT);req(ho['next_bounded_unit']=='v1270 Self-Development Alpha Checkpoint','next_unit');req('external_supervisor_restart' in ho['native_windows_review'],'windows_restart_handoff')
with tempfile.TemporaryDirectory(prefix='eidolon-v1269-long-') as td:
    deep=Path(td)
    for i in range(5):deep=deep/('seg'+str(i)+'_'+'x'*28)
    deep.mkdir(parents=True);c=approved_chain(deep);u=prepare_governed_self_update(c['packet']['review_id'],c['source'],self_modification_runtime_root=c['sm'],review_runtime_root=c['review_rt'],runtime_root=deep/'runtime');req(len(str((deep/'runtime').resolve()))>170,'long_path_fixture');req(u['phase']=='prepared','long_path_prepared')
print(json.dumps({'ok':True,'suite':'v1269.6-v1269.8-governed-self-update-reliability','passed':len(C),'failed':0,'checks':C},sort_keys=True))
