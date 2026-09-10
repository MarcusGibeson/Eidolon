from __future__ import annotations
import hashlib,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT,ROOT/'conscious_agent'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
sys.dont_write_bytecode=True
from conscious_agent.general_capability_manifest_v2509 import build_capability_manifest
from conscious_agent.general_action_governance_v2509 import evaluate_capability_eligibility,prepare_general_action_intent
from conscious_agent.general_action_receipts_v2509 import build_action_review_receipt
from conscious_agent.live_cognitive_activity_v2510 import project_live_activity
from conscious_agent.internal_voice_projection_v2512 import project_activity_internal_voice
from conscious_agent.mental_activity_timeline_v2511 import MentalActivityTimeline
checks=[]
def req(v,n):checks.append(n);assert v,n
def d(s):return hashlib.sha256(s.encode()).hexdigest()
m=build_capability_manifest(capability_id='calendar.create',description_code='create_event',side_effect_class='external_reversible',privacy_scope='personal',approval_class='operator_each_time',access_surfaces=['external_system'],reversible=True,cancellation_supported=True,rollback_supported=True,required_evidence_codes=['account','time'])
e=evaluate_capability_eligibility(m,evidence_codes=['account','time'],evidence_digests=[d('a')],operator_selection_digest=d('sel'))
i=prepare_general_action_intent(manifest=m,eligibility=e,operation_code='create_event',argument_shape_digest=d('shape'))
r=build_action_review_receipt(i)
req(e['eligible_for_proposal'],'capability_eligible')
req(i['proposal_ready'] and i['approval_required'],'proposal_not_approval')
req(not r['approval_granted'] and not r['execution_performed'],'action_unexecuted')
a=project_live_activity({'event':'status','stage':'governed_action','message':'raw private status'},operation_id='op')
v=project_activity_internal_voice(a)
req(a['summary'] and not a['hidden_reasoning_exposed'],'safe_activity')
req(v and not v['claims_literal_thought_transcript'],'safe_internal_voice')
req('raw private status' not in str(a)+str(v),'raw_status_absent')
with tempfile.TemporaryDirectory() as td:
 t=MentalActivityTimeline(td)
 t.append('a',event_kind='action',transition='proposal_ready',source_digest=r['receipt_digest'],outcome_code='calendar.create')
 t.append('c',event_kind='cognitive',transition='cycle_started',source_digest=d('c'),outcome_code='REFLECT')
 recent=t.recent(limit=10)
 req(recent['event_count']==2,'timeline_integrates')
 req(all(not x['authority_granted'] for x in recent['events']),'timeline_no_authority')
 req(not t.inspection_summary()['authority_boundary']['can_execute_action'],'timeline_cannot_execute')
src=(ROOT/'conscious_agent'/'dashboard_chat_console.py').read_text(encoding='utf-8')
req("type === 'activity'" in src and "type === 'internal_voice'" in src,'dashboard_streams_both')
req('children.length > 8' in src,'dashboard_stream_bounded')
print({'ok':True,'checkpoint_version':'2512.9','passed':len(checks),'total':len(checks),'checks':checks})
