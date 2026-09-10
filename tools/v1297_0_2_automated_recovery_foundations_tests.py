from __future__ import annotations
import json,sys,tempfile,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1297-test-'))
from automated_recovery_foundations import *
from v1297_test_support import make_applied_fixture,d
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
td,source,runtime,uid,bm,cm,before,after=make_applied_fixture();now=1000.0;c=prepare_recovery_contract(uid,source,runtime_root=runtime,health_policy_digest=d('policy'),observation_window_seconds=300,prepared_unix=now);req(c['recovery_contract_id'].startswith('recovery_'),'id');req(valid_digest(c['recovery_contract_digest']),'digest');req(c['baseline_source_digest']==bm['source_manifest_digest'],'baseline');req(c['candidate_source_digest']==cm['source_manifest_digest'],'candidate');req(c['restore_target']=='exact_pre_update_backup_only','target');req(c['successful_operator_initiated_rollback_still_separately_governed'],'separate_rollback');req(not any(c[k] for k in DENIED_AUTHORITY),'authority')
t=recovery_trigger(c,trigger_code='startup_failure',evidence_digest=d('health'),observed_unix=1100.0);req(t['trigger_code']=='startup_failure' and valid_digest(t['trigger_digest']),'trigger')
for kw in [dict(trigger_code='unknown',evidence_digest=d('x'),observed_unix=1100.0),dict(trigger_code='startup_failure',evidence_digest=d('x'),observed_unix=1400.0),dict(trigger_code='startup_failure',evidence_digest=d('x'),observed_unix=1100.0,fresh=False)]:
 try:recovery_trigger(c,**kw);bad=False
 except ValueError:bad=True
 req(bad,'bad_trigger_rejected')
td2,s2,r2,u2,*_=make_applied_fixture(authorization_consumed=False)
try:prepare_recovery_contract(u2,s2,runtime_root=r2,health_policy_digest=d('p'));bad=False
except ValueError:bad=True
req(bad,'unconsumed_rejected');req(CONTRACT_VERSION=='v1297.2','version');req(TRIGGER_CODES==frozenset({'startup_failure','defined_behavior_regression','candidate_manifest_mismatch','privacy_security_regression'}),'codes')
td.cleanup();td2.cleanup();print(json.dumps({'suite':'v1297.0-v1297.2-automated-recovery-foundations','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
