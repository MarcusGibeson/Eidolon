from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
 if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest
from conscious_agent.general_action_governance_v2509 import evaluate_capability_eligibility,prepare_general_action_intent
from conscious_agent.general_capability_adapter_registry_v2513 import build_adapter_descriptor,register_adapter,resolve_adapter
from conscious_agent.general_capability_governance_bridge_v2514 import build_governed_action_admission
from conscious_agent.general_capability_execution_envelope_v2515 import build_execution_envelope,build_execution_result_receipt
from conscious_agent.general_capability_preview_adapter_v2516 import invoke_inert_preview
from conscious_agent.general_capability_activity_bridge_v2517 import project_capability_activity
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline
c=[]
def req(v,n):c.append(n);assert v,n
def d(x):return hashlib.sha256(x.encode()).hexdigest()
m=build_capability_manifest(capability_id='fixture.preview',description_code='fixture_preview',side_effect_class='none',privacy_scope='workspace',approval_class='none')
a=build_adapter_descriptor(manifest=m,adapter_id='fixture.preview.v1',adapter_kind='local_read',handler_code='fixture.noop',enabled=True)
reg=register_adapter(None,a);ar=resolve_adapter(reg,capability_id='fixture.preview');req(ar['ok'],'adapter_resolved')
el=evaluate_capability_eligibility(m,evidence_digests=[d('e')]);intent=prepare_general_action_intent(manifest=m,eligibility=el,operation_code='preview',argument_shape_digest=d('shape'))
pol={'allowed_by_policy_ceiling':True,'external_authority_receipt_still_required':True,'decision_digest':d('policy')}; auth={'authorization_granted':True,'execution_admitted':True,'execution_performed':False,'executor_invoked':False,'authorization_digest':d('auth'),'operation_digest':d('op'),'execution_admission_digest':d('exec')}
adm=build_governed_action_admission(intent=intent,adapter=a,policy_decision=pol,authority_receipt=auth);req(adm['admitted'] and not adm['adapter_invoked'],'admission_without_execution')
env=build_execution_envelope(admission=adm,argument_digest=d('args'),invocation_id='fixture-1');pr=invoke_inert_preview(envelope=env,adapter=a,preview_payload_digest=d('payload'));rr=build_execution_result_receipt(env,status='succeeded',result_digest=pr['preview_result_digest'])
req(pr['simulation_only'] and not pr['side_effect_performed'],'inert_preview');req(rr['exactly_once_consumed'],'result_receipt_consumes')
act=project_capability_activity(stage='preview_completed',source={**adm,**a});req(act['content_minimized'] and not act['hidden_reasoning_exposed'],'safe_activity')
with tempfile.TemporaryDirectory() as td:
 t=MentalActivityTimeline(td);out=t.append('cap-fixture-1',event_kind='action',transition='proposal_ready',source_digest=rr['receipt_digest'],subject_ref='fixture.preview',outcome_code='preview_completed');req(out['ok'],'timeline_records_action')
req(not any(bool(x.get(k)) for x in (m,a,adm,env) for k in ['independent_authority_granted','authority_inferred','side_effect_performed'] if k in x),'no_independent_authority')
print({'ok':True,'checkpoint_version':'2517.9','passed':len(c),'total':len(c),'checks':c})
