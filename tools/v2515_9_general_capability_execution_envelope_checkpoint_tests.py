from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_execution_envelope_v2515 import *
c=[]
def req(v,n):c.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
ad={'admitted':True,'adapter_invocation_allowed':True,'capability_id':'calendar.read','adapter_id':'calendar.read.v1','adapter_digest':d('adapter'),'admission_digest':d('admission'),'operation_digest':d('op')}
e=build_execution_envelope(admission=ad,argument_digest=d('args'),invocation_id='inv-1')
req(e['execution_ready'] and not e['execution_performed'],'envelope_ready_not_executed'); req(e['exactly_once_required'],'exactly_once')
r=build_execution_result_receipt(e,status='not_invoked'); req(not r['adapter_invoked'] and not r['execution_performed'],'not_invoked_receipt')
s=build_execution_result_receipt(e,status='succeeded',result_digest=d('result')); req(s['adapter_invoked'] and s['exactly_once_consumed'],'result_consumes_once'); req(not s['raw_output_stored'],'content_minimized')
try: build_execution_envelope(admission={'admitted':False},argument_digest=d('x'),invocation_id='bad'); ok=False
except ValueError: ok=True
req(ok,'unadmitted_rejected')
print({'ok':True,'checkpoint_version':'2515.9','passed':len(c),'total':len(c),'checks':c})
