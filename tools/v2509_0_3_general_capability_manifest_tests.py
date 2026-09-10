from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest,validate_capability_manifest
checks=[]
def req(v,n): checks.append(n); assert v,n
m=build_capability_manifest(capability_id='calendar.read',description_code='read_calendar',side_effect_class='none',privacy_scope='personal',approval_class='none',access_surfaces=['external_system'],required_evidence_codes=['account_scope'],max_operations_per_hour=20,max_runtime_seconds=30)
req(validate_capability_manifest(m)['ok'],'manifest_valid')
req(not m['manifest_is_authority_grant'],'manifest_not_grant')
req(not m['execution_authorized'],'execution_denied')
req(m['access_surfaces']==['external_system'],'surface_declared')
try: build_capability_manifest(capability_id='email.send',description_code='send',side_effect_class='external_reversible',privacy_scope='personal',approval_class='none',access_surfaces=['communication'])
except ValueError: req(True,'side_effect_requires_approval')
else: req(False,'side_effect_requires_approval')
try: build_capability_manifest(capability_id='filesystem.delete',description_code='delete',side_effect_class='destructive',privacy_scope='workspace',approval_class='operator_each_time',access_surfaces=['filesystem'])
except ValueError: req(True,'destructive_requires_protected')
else: req(False,'destructive_requires_protected')
try: build_capability_manifest(capability_id='bad',description_code='bad',rollback_supported=True,reversible=False)
except ValueError: req(True,'rollback_requires_reversible')
else: req(False,'rollback_requires_reversible')
req(len(m['manifest_digest'])==64,'digest_bound')
print({'ok':True,'passed':len(checks),'total':len(checks),'checks':checks})
