from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest
from conscious_agent.general_capability_adapter_registry_v2513 import build_adapter_descriptor
from conscious_agent.general_capability_execution_envelope_v2515 import build_execution_envelope,build_execution_result_receipt
from conscious_agent.general_capability_recovery_v2518 import prepare_control_request
from conscious_agent.general_capability_lifecycle_reconciliation_v2519 import reconcile_capability_lifecycle
c=[]
def req(v,n):c.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
m=build_capability_manifest(capability_id='fixture.reversible',description_code='fixture',side_effect_class='local_reversible',approval_class='operator_each_time',reversible=True,cancellation_supported=True,rollback_supported=True)
a=build_adapter_descriptor(manifest=m,adapter_id='fixture.rev.v1',adapter_kind='local_reversible',handler_code='fixture.noop',enabled=True,supports_cancellation=True,supports_rollback=True)
adm={'admitted':True,'adapter_invocation_allowed':True,'capability_id':m['capability_id'],'adapter_id':a['adapter_id'],'adapter_digest':a['adapter_digest'],'admission_digest':d('adm'),'operation_digest':d('op')}
e=build_execution_envelope(admission=adm,argument_digest=d('arg'),invocation_id='r1');r=build_execution_result_receipt(e,status='succeeded',result_digest=d('result'),side_effect_performed=True,rollback_available=True)
ctrl=prepare_control_request(manifest=m,envelope=e,result_receipt=r,control='rollback',operator_selection_digest=d('sel'));rec=reconcile_capability_lifecycle(envelope=e,result_receipts=[r],control_requests=[ctrl])
req(rec['status']=='succeeded','result_reconciled');req(rec['pending_controls']==['rollback'],'rollback_pending');req(not rec['control_performed_by_reconciliation'],'reconcile_does_not_rollback');req(ctrl['operator_authorization_still_required'],'rollback_not_self_authorized');req(not ctrl['authority_inferred'] and not rec['authority_inferred'],'no_authority_inference')
print({'ok':True,'checkpoint_version':'2520.9','passed':len(c),'total':len(c),'checks':c})
