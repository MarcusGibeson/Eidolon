from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest
from conscious_agent.general_capability_recovery_v2518 import prepare_control_request
c=[]
def req(v,n):c.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
m=build_capability_manifest(capability_id='fixture.write',description_code='fixture_write',side_effect_class='local_reversible',approval_class='operator_each_time',reversible=True,cancellation_supported=True,rollback_supported=True)
e={'envelope_digest':d('env')}; failed={'receipt_digest':d('rf'),'envelope_digest':e['envelope_digest'],'status':'failed','side_effect_performed':False}
cr=prepare_control_request(manifest=m,envelope=e,result_receipt=failed,control='cancel',operator_selection_digest=d('sel'));req(cr['request_ready'] and not cr['control_performed'],'cancel_candidate_only')
succ={'receipt_digest':d('rs'),'envelope_digest':e['envelope_digest'],'status':'succeeded','side_effect_performed':True}
rr=prepare_control_request(manifest=m,envelope=e,result_receipt=succ,control='rollback',operator_selection_digest=d('sel2'));req(rr['operator_authorization_still_required'],'rollback_requires_authority');req(not rr['adapter_invoked'] and not rr['side_effect_performed'],'recovery_does_not_execute')
try: prepare_control_request(manifest=m,envelope=e,result_receipt=succ,control='cancel',operator_selection_digest=d('s'));ok=False
except ValueError:ok=True
req(ok,'completed_success_not_cancelled')
print({'ok':True,'checkpoint_version':'2518.9','passed':len(c),'total':len(c),'checks':c})
