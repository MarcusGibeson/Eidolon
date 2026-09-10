from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest
from conscious_agent.general_capability_adapter_registry_v2513 import *
c=[]
def req(v,n):c.append(n);assert v,n
m=build_capability_manifest(capability_id='calendar.read',description_code='calendar_read',approval_class='none',privacy_scope='personal',access_surfaces=['external_system'])
a=build_adapter_descriptor(manifest=m,adapter_id='calendar.local.read.v1',adapter_kind='external_read',handler_code='calendar_read_adapter')
req(validate_adapter_descriptor(a)['ok'],'descriptor_valid'); req(a['enabled'] is False,'disabled_default'); req(not a['execution_authorized'],'not_authority')
r=register_adapter(None,a); req(resolve_adapter(r,capability_id='calendar.read')['ok'] is False,'disabled_not_resolved')
ae=build_adapter_descriptor(manifest=m,adapter_id='calendar.local.read.v1',adapter_kind='external_read',handler_code='calendar_read_adapter',enabled=True)
r=register_adapter(r,ae); x=resolve_adapter(r,capability_id='calendar.read'); req(x['ok'] and not x['adapter_invoked'],'enabled_resolves_without_invocation')
print({'ok':True,'checkpoint_version':'2513.9','passed':len(c),'total':len(c),'checks':c})
