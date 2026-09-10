from __future__ import annotations
import json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1298-'))
from repeated_self_maintenance_checkpoint import build_repeated_self_maintenance_checkpoint
from repeated_self_maintenance_foundations import DENIED_AUTHORITY
from checkpoint_registry import validate_checkpoint_report
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
r=build_repeated_self_maintenance_checkpoint(source_root=ROOT);req(r['ok'],'ok');req(r['checkpoint_version']=='1298.9','version');req(r['status']=='repeated_self_maintenance_checkpoint_ready','status');req(r['passed']==r['total']==7,'checks');req(r['details']['checkpoint_executes_work'] is False,'noexec');req(r['details']['next_bounded_unit']=='v1299 Final Supervised Autonomy Rehearsal','next');req('duplicate_work_suppression' in r['details']['contract'],'duplicate');req('bounded_proposal_growth' in r['details']['contract'],'growth');req(r['details']['native_windows_validation']=='desktop_review_required','native');req(not any(r.get(k) for k in DENIED_AUTHORITY),'authority');req(validate_checkpoint_report(r,source_root=ROOT)['ok'],'registry')
print(json.dumps({'suite':'v1298.9-repeated-self-maintenance-checkpoint','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
