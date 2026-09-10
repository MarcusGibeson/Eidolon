from __future__ import annotations
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest,validate_capability_manifest
from conscious_agent.general_action_governance_v2509 import evaluate_capability_eligibility,prepare_general_action_intent
from conscious_agent.general_action_receipts_v2509 import build_action_review_receipt
checks=[]
def req(v,n):checks.append(n);assert v,n
def d(s):return hashlib.sha256(s.encode()).hexdigest()
manifests=[
 build_capability_manifest(capability_id='calendar.read',description_code='calendar_read',side_effect_class='none',privacy_scope='personal',approval_class='none',access_surfaces=['external_system'],required_evidence_codes=['account_scope']),
 build_capability_manifest(capability_id='email.send',description_code='email_send',side_effect_class='external_reversible',privacy_scope='personal',approval_class='operator_each_time',access_surfaces=['communication','external_system'],reversible=True,cancellation_supported=True,required_evidence_codes=['recipient','body_shape']),
 build_capability_manifest(capability_id='filesystem.delete',description_code='filesystem_delete',side_effect_class='destructive',privacy_scope='workspace',approval_class='protected_action',access_surfaces=['filesystem'],reversible=False,required_evidence_codes=['exact_path','operator_reason']),
]
req(all(validate_capability_manifest(m)['ok'] for m in manifests),'representative_manifests_valid')
read=manifests[0]; e=evaluate_capability_eligibility(read,evidence_codes=['account_scope'],evidence_digests=[d('r')])
req(e['eligible_for_proposal'],'read_eligible_without_selection_when_none_required')
send=manifests[1]; e2=evaluate_capability_eligibility(send,evidence_codes=['recipient','body_shape'],evidence_digests=[d('a'),d('b')],operator_selection_digest=d('selection'))
req(e2['eligible_for_proposal'] and e2['operator_selection_bound'],'side_effect_selection_bound')
i=prepare_general_action_intent(manifest=send,eligibility=e2,operation_code='send_message',argument_shape_digest=d('shape'))
r=build_action_review_receipt(i)
req(i['approval_required'] and not i['execution_admitted'],'intent_preserves_approval')
req(r['review_state']=='awaiting_operator_review','review_only')
req(not r['approval_granted'] and not r['authorization_granted'] and not r['execution_performed'],'no_authority')
req(not r['adapter_invoked'] and not r['side_effect_performed'],'no_adapter_or_side_effect')
req(r['content_free'],'receipt_content_free')
print({'ok':True,'checkpoint_version':'2509.9','passed':len(checks),'total':len(checks),'checks':checks})
