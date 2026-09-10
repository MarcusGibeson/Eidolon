from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest
from conscious_agent.general_action_governance_v2509 import evaluate_capability_eligibility,prepare_general_action_intent
from conscious_agent.general_action_receipts_v2509 import build_action_review_receipt
checks=[]
def req(v,n): checks.append(n); assert v,n
def d(s):return hashlib.sha256(s.encode()).hexdigest()
m=build_capability_manifest(capability_id='calendar.create',description_code='create_event',side_effect_class='external_reversible',privacy_scope='personal',approval_class='operator_each_time',access_surfaces=['external_system'],reversible=True,cancellation_supported=True,rollback_supported=True,required_evidence_codes=['calendar_account','time_range'])
e=evaluate_capability_eligibility(m,evidence_codes=['calendar_account'],evidence_digests=[d('e')],operator_selection_digest=d('sel'))
req(not e['eligible_for_proposal'],'missing_evidence_blocks')
e=evaluate_capability_eligibility(m,evidence_codes=['calendar_account','time_range'],evidence_digests=[d('e1'),d('e2')],operator_selection_digest=d('sel'))
req(e['eligible_for_proposal'],'eligible_for_proposal')
req(e['operator_selection_bound'],'selection_bound')
req(not e['approval_granted'] and not e['execution_admitted'],'eligibility_not_authority')
i=prepare_general_action_intent(manifest=m,eligibility=e,operation_code='create_event',argument_shape_digest=d('shape'))
req(i['proposal_ready'],'intent_ready')
req(i['approval_required'],'approval_still_required')
req(not i['execution_performed'] and not i['adapter_invoked'],'intent_not_execution')
r=build_action_review_receipt(i)
req(r['review_state']=='awaiting_operator_review','review_receipt')
req(not r['approval_granted'] and not r['authorization_granted'],'review_not_approval')
req(not r['side_effect_performed'],'no_side_effect')
req(r['content_free'] and not r['raw_arguments_stored'],'content_minimized')
print({'ok':True,'passed':len(checks),'total':len(checks),'checks':checks})
