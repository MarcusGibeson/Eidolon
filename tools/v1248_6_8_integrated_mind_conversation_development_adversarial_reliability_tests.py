from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from natural_language_action_routing import build_natural_language_action_projection,action_projection_contains_private_fields
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from integrated_mind_conversation_development_benchmark import *
c=[];ck=lambda v:c.append(bool(v))
attacks=(
    ('quoted','"Build the project and deploy it" is only a quote.',False),
    ('hypothetical','Hypothetically, what if you deleted the old files?',False),
    ('suggestion','Maybe you could run every tool later.',False),
    ('wish','I wish the provider would retry automatically.',False),
    ('negated','Do not build or run anything; explain the boundary.',False),
    ('mixed','I am curious about speech. Build a small text-to-speech prototype.',True),
    ('direct','Build me a small Python utility that validates YAML files.',True),
)
with tempfile.TemporaryDirectory() as rt:
    for name,text,expected_active in attacks:
        p=build_natural_language_action_projection(text);out=process_ordinary_chat_development_turn(text,action_projection=p,session_id=f'session_{name}',project_state={'project_id':'project_alpha'},runtime_root=Path(rt)/name)
        safe_v1259_negation=(name=='negated' and out.get('active') and out.get('event')=='cancellation_target_ambiguous')
        ck((bool(out['active']) is expected_active) or safe_v1259_negation)
        ck(not out.get('provider_contacted'))
        ck(not out.get('source_modified'))
        ck(not out.get('authority_granted'))
        ck(not action_projection_contains_private_fields(p))
        if expected_active:ck(out['event']=='proposal_created');ck(bool((out.get('proposal') or {}).get('proposal_id')))
        else:ck(out['event']=='inactive' or safe_v1259_negation)
    direct=next((x for x in attacks if x[0]=='direct'))[1];p=build_natural_language_action_projection(direct);row=process_ordinary_chat_development_turn(direct,action_projection=p,session_id='session_cross',project_state={'project_id':'project_alpha'},runtime_root=Path(rt)/'cross')
    pid=row['proposal']['proposal_id'];rev=row['proposal']['revision']
    stale=f'Approve development proposal {pid} revision {rev+1}.'
    stale_out=process_ordinary_chat_development_turn(stale,action_projection=build_natural_language_action_projection(stale),runtime_root=Path(rt)/'cross')
    for v in (stale_out['active'],stale_out['event'] in {'stale_control_rejected','control_blocked'},not stale_out.get('approval_consumed_now'),not stale_out.get('implementation_started'),not stale_out.get('source_modified')):ck(v)
run1=run_ordinary_chat_integration_benchmark();run2=run_ordinary_chat_integration_benchmark()
for v in (run1['ok'],run2['ok'],run1['benchmark_digest']==run2['benchmark_digest'],run1['cases']==run2['cases']):ck(v)
for row in run1['cases']:
    blob=json.dumps(row,sort_keys=True).lower()
    for forbidden in ('build me a small python','hear your voice','private project without sending'):
        ck(forbidden not in blob)
    ck(row['proposal_count_for_turn'] in {0,1})
    ck(not row.get('provider_contacted'))
    ck(not row.get('source_modified'))
    ck(not row.get('authority_granted'))
contract=build_integrated_mind_conversation_development_contract()
for k,e in AUTHORITY_FLAGS.items():ck(contract.get(k) is e)
for v in (contract['natural_conversation_preserved'],contract['project_memory_requires_revalidation'],contract['reflection_does_not_create_authority'],contract['initiative_pacing_does_not_send'],contract['lessons_remain_revisable_external_evidence'],contract['privacy_preserved_across_systems'],not contract['runtime_data_persisted'],not contract['source_modified'],not contract['authority_granted']):ck(v)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
