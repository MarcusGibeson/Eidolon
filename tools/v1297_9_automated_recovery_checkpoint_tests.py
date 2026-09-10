from __future__ import annotations
import json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1297-test-'))
from automated_recovery_checkpoint import build_automated_recovery_checkpoint
from automated_recovery_foundations import DENIED_AUTHORITY
from checkpoint_registry import validate_checkpoint_report
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
r=build_automated_recovery_checkpoint(source_root=ROOT);req(r['ok'],'ok');req(r['checkpoint_version']=='1297.9','version');req(r['status']=='automated_recovery_checkpoint_ready','status');req(r['passed']==r['total']==6,'checks');req(r['details']['checkpoint_executes_recovery'] is False,'readonly');req(r['details']['next_bounded_unit']=='v1298 Repeated Self-Maintenance Cycles','next');req(r['details']['native_windows_validation']=='desktop_review_required','native');req('separate_operator_rollback_preserved' in r['details']['contract'],'separate');req(not any(r.get(k) for k in DENIED_AUTHORITY),'authority');req(validate_checkpoint_report(r,source_root=ROOT)['ok'],'registry')
text=(ROOT/'conscious_agent/automated_recovery.py').read_text();req('exact_pre_update_backup_only' in text or 'candidate_reapplied' in text,'bounded_restore')
print(json.dumps({'suite':'v1297.9-automated-recovery-checkpoint','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
