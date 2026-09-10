from __future__ import annotations
import json,sys,tempfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE','1');os.environ.setdefault('EIDOLON_DATA_DIR',tempfile.mkdtemp(prefix='eidolon-v1296-'))
from canary_self_updates_checkpoint import build_canary_self_updates_checkpoint
from canary_self_updates_foundations import DENIED_AUTHORITY
from checkpoint_registry import validate_checkpoint_report
checks=[]
def req(v,n):checks.append(bool(v));assert v,n
r=build_canary_self_updates_checkpoint(source_root=ROOT);req(r['ok'],'checkpoint');req(r['checkpoint_version']=='1296.9','version');req(r['status']=='canary_self_updates_checkpoint_ready','status');req(r['passed']==r['total']==6,'checks');req(r['read_only'] and r['content_free'],'readonly');req(r['details']['checkpoint_executes_canary'] is False,'no_exec');req(r['details']['checkpoint_applies_update'] is False,'no_apply');req(r['details']['next_bounded_unit']=='v1297 Automated Recovery','next');req(r['details']['native_windows_validation']=='desktop_review_required','native');req(not any(r.get(k) for k in DENIED_AUTHORITY),'authority');v=validate_checkpoint_report(r,source_root=ROOT);req(v['ok'],'registry_validation')
text=(ROOT/'conscious_agent/canary_self_updates.py').read_text();req('requires_separate_v1269_exact_authorization' in text,'auth_contract')
print(json.dumps({'suite':'v1296.9-canary-self-updates-checkpoint','ok':all(checks),'passed':sum(checks),'failed':len(checks)-sum(checks)},sort_keys=True))
