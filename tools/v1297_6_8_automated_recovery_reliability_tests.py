from __future__ import annotations
import json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1297-test-'))
from automated_recovery_foundations import *
from automated_recovery import *
from automated_recovery_reliability import *
from v1297_test_support import make_applied_fixture,d
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
td,source,runtime,uid,*_=make_applied_fixture();c=prepare_recovery_contract(uid,source,runtime_root=runtime,health_policy_digest=d('p'),prepared_unix=1e3,observation_window_seconds=300);t=recovery_trigger(c,trigger_code='candidate_manifest_mismatch',evidence_digest=d('e'),observed_unix=1050);r=perform_automatic_recovery(c,t,source,runtime_root=runtime);a=audit_recovery_result(r);req(a['ok'],'audit');req(r['original_exact_update_authorization_was_consumed'],'original_auth');req(not r['new_update_authorization_consumed'],'no_new_auth');req(not r['operator_initiated_rollback_authorized'],'separate_rollback')
for patch in ({'candidate_reapplied':True},{'arbitrary_content_written':True},{'new_update_authorization_consumed':True},{'general_rollback_authorized':True}):req(not audit_recovery_result({**r,**patch})['ok'],'tamper')
# trigger identity tamper and private evidence fail closed
td2,s2,rt2,u2,*_=make_applied_fixture();c2=prepare_recovery_contract(u2,s2,runtime_root=rt2,health_policy_digest=d('p2'),prepared_unix=2000,observation_window_seconds=300);t2=recovery_trigger(c2,trigger_code='startup_failure',evidence_digest=d('e2'),observed_unix=2050);req(not evaluate_recovery_trigger(c2,{**t2,'recovery_contract_id':'wrong'})['ok'],'identity');req(not evaluate_recovery_trigger(c2,{**t2,'private_finding_count':1})['ok'],'private');req(not evaluate_recovery_trigger(c2,{**t2,'fresh':False})['ok'],'stale')
h=inspect_automated_recovery_surface_health(source_root=ROOT);req(h['ok'],'surface');req(h['native_windows_validation']=='desktop_review_required','native');req(not any(h[k] for k in DENIED_AUTHORITY),'authority');req(CONTRACT_VERSION=='v1297.8','version')
td.cleanup();td2.cleanup();print(json.dumps({'suite':'v1297.6-v1297.8-automated-recovery-reliability','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
