from __future__ import annotations
import json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1297-test-'))
from automated_recovery_foundations import prepare_recovery_contract,recovery_trigger
from automated_recovery import evaluate_recovery_trigger,perform_automatic_recovery
from governed_self_update_foundations import load_governed_self_update,_backup_path,_read_json,_write_json
from isolated_self_modification_foundations import source_only_manifest
from v1297_test_support import make_applied_fixture,d
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
td,source,runtime,uid,bm,cm,before,after=make_applied_fixture();c=prepare_recovery_contract(uid,source,runtime_root=runtime,health_policy_digest=d('policy'),prepared_unix=1000,observation_window_seconds=300);tr=recovery_trigger(c,trigger_code='defined_behavior_regression',evidence_digest=d('regression'),observed_unix=1050);g=evaluate_recovery_trigger(c,tr);req(g['ok'] and g['status']=='automatic_recovery_required','gate');res=perform_automatic_recovery(c,tr,source,runtime_root=runtime);req(res['ok'] and res['status']=='automatic_recovery_complete','recovered');req(res['source_restored_to_baseline'],'baseline_restored');req((source/'main.py').read_bytes()==before,'content_restored');req(source_only_manifest(source)['source_manifest_digest']==bm['source_manifest_digest'],'manifest_restored');req(res['candidate_reapplied'] is False and res['arbitrary_content_written'] is False,'no_arbitrary');req(res['new_update_authorization_consumed'] is False,'no_new_auth');rec=load_governed_self_update(uid,runtime_root=runtime);req(rec['phase']=='rolled_back','sealed_phase');again=perform_automatic_recovery(c,tr,source,runtime_root=runtime);req(again.get('operation_status')=='restored','idempotent')
# candidate-state conflict blocks
td2,s2,r2,u2,b2,c2,before2,after2=make_applied_fixture();contract2=prepare_recovery_contract(u2,s2,runtime_root=r2,health_policy_digest=d('p2'),prepared_unix=2000,observation_window_seconds=300);trigger2=recovery_trigger(contract2,trigger_code='startup_failure',evidence_digest=d('e2'),observed_unix=2050);(s2/'main.py').write_text("VALUE='third-state'\n");blocked=perform_automatic_recovery(contract2,trigger2,s2,runtime_root=r2);req(blocked['status']=='automatic_recovery_source_conflict','source_conflict')
# missing/corrupt backup blocks before write
td3,s3,r3,u3,*_=make_applied_fixture();contract3=prepare_recovery_contract(u3,s3,runtime_root=r3,health_policy_digest=d('p3'),prepared_unix=3000,observation_window_seconds=300);trigger3=recovery_trigger(contract3,trigger_code='privacy_security_regression',evidence_digest=d('e3'),observed_unix=3050);backup=_read_json(_backup_path(u3,r3));backup['backup_digest']=d('wrong');_write_json(_backup_path(u3,r3),backup);blocked2=perform_automatic_recovery(contract3,trigger3,s3,runtime_root=r3);req(blocked2['status']=='automatic_recovery_backup_invalid','backup_blocked')
for x in (td,td2,td3):x.cleanup()
print(json.dumps({'suite':'v1297.3-v1297.5-automated-recovery-integration','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
