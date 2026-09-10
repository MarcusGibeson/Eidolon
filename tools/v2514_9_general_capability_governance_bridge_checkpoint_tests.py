from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest
from conscious_agent.general_action_governance_v2509 import evaluate_capability_eligibility,prepare_general_action_intent
from conscious_agent.general_capability_adapter_registry_v2513 import build_adapter_descriptor
from conscious_agent.general_capability_governance_bridge_v2514 import build_governed_action_admission
c=[]
def req(v,n):c.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
m=build_capability_manifest(capability_id='calendar.read',description_code='read',approval_class='none',privacy_scope='personal',access_surfaces=['external_system'])
e=evaluate_capability_eligibility(m,evidence_codes=[],evidence_digests=[d('e')]); i=prepare_general_action_intent(manifest=m,eligibility=e,operation_code='read',argument_shape_digest=d('shape'))
a=build_adapter_descriptor(manifest=m,adapter_id='calendar.read.v1',adapter_kind='external_read',handler_code='read_calendar',enabled=True)
policy={'allowed_by_policy_ceiling':True,'external_authority_receipt_still_required':True,'decision_digest':d('p')}
auth={'authorization_granted':True,'execution_admitted':True,'execution_performed':False,'executor_invoked':False,'authorization_digest':d('a'),'operation_digest':d('o'),'execution_admission_digest':d('x')}
r=build_governed_action_admission(intent=i,adapter=a,policy_decision=policy,authority_receipt=auth)
req(r['admitted'],'exact_bridge_admits'); req(r['adapter_invocation_allowed'],'invocation_allowed_only_after_all_gates'); req(not r['adapter_invoked'] and not r['execution_performed'],'bridge_does_not_execute')
bad=dict(auth);bad['authorization_granted']=False
rb=build_governed_action_admission(intent=i,adapter=a,policy_decision=policy,authority_receipt=bad); req(not rb['admitted'],'missing_authority_denied')
ad=dict(a);ad['enabled']=False
rd=build_governed_action_admission(intent=i,adapter=ad,policy_decision=policy,authority_receipt=auth); req(not rd['admitted'],'disabled_adapter_denied')
print({'ok':True,'checkpoint_version':'2514.9','passed':len(c),'total':len(c),'checks':c})
