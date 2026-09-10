from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_preview_adapter_v2516 import invoke_inert_preview
c=[]
def req(v,n):c.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
ad={'adapter_digest':d('adapter'),'adapter_id':'fixture.preview.v1','adapter_kind':'local_read','handler_code':'fixture.noop','enabled':True,'supports_preview':True}
env={'execution_ready':True,'execution_performed':False,'adapter_digest':ad['adapter_digest'],'invocation_id':'i1','envelope_digest':d('env'),'operation_digest':d('op')}
r=invoke_inert_preview(envelope=env,adapter=ad,preview_payload_digest=d('payload'))
req(r['simulation_only'],'simulation_only');req(r['adapter_invoked'] and r['execution_performed'],'preview_invoked');req(not any(r[k] for k in ['side_effect_performed','network_contacted','provider_contacted','communication_performed','filesystem_mutated','process_spawned','device_control_performed']),'no_external_effects');req(not r['raw_arguments_stored'] and not r['raw_output_stored'],'content_minimized')
bad=dict(ad);bad['adapter_kind']='external_read'
try: invoke_inert_preview(envelope=env,adapter=bad,preview_payload_digest=d('p'));ok=False
except ValueError:ok=True
req(ok,'external_adapter_rejected')
print({'ok':True,'checkpoint_version':'2516.9','passed':len(c),'total':len(c),'checks':c})
