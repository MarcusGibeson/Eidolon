from __future__ import annotations

import hashlib, json, os, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True; os.environ['PYTHONDONTWRITEBYTECODE']='1'
for path in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(path) not in sys.path: sys.path.insert(0,str(path))

from conversational_command_integration_foundations import (
    ACT_KINDS, DENIED_AUTHORITY, classify_conversational_command_turn, public_conversational_command_turn,
)
from conversational_command_integration import build_conversational_command_integration, public_conversational_command_integration

CHECKS=[]
def require(v,label):
    if not v: raise AssertionError(label)
    CHECKS.append(label)

def source_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix()
        if '__pycache__' in rel or rel.endswith(('.pyc','.pyo')) or rel.startswith('data/'): continue
        rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

before=source_signature()

def classify(text, kind):
    row=classify_conversational_command_turn(text)
    require(row['primary_act']==kind,f'{kind}:{text}:{row}')
    require(row['act_supported'] is True,f'act_supported:{kind}')
    require(row['provider_contacted'] is False and row['commands_executed'] is False,f'no_execution:{kind}')
    for key,expected in DENIED_AUTHORITY.items(): require(row.get(key) is expected,f'{kind}_{key}_denied')
    return row

# Discussion/wish/suggestion forms stay conversational even with development vocabulary.
for text in (
    'It would be nice to hear your voice.',
    'I wish you had a voice.',
    'Maybe you should build your own text-to-speech system someday.',
    'We could build a calculator later.',
    'The sentence "Build your own text-to-speech system" is an example.',
):
    row=classify(text,'discussion'); require(row['action_text']=='','discussion_has_no_live_action_text')

for text in (
    'What if you built your own text-to-speech system?',
    'Hypothetically, build a calculator app for me.',
    'Imagine you implemented this as a web app.',
):
    row=classify(text,'hypothetical'); require(row['routing_mode']=='conversation_only','hypothetical_conversation_only')

for text in (
    'How do I build a calculator webpage?',
    'Could you explain how to build a calculator webpage?',
    'Tell me how a responsive calculator app should work.',
):
    row=classify(text,'information_request'); require(row['action_text']=='','information_request_not_live_action')

row=classify('Help me plan how to build a calculator app.','planning_request')
require(row['routing_mode']=='conversation_only','planning_request_does_not_execute')

for text in ('Build me a calculator webpage.','Can you build me a calculator webpage?','Please implement the responsive calculator app.'):
    row=classify(text,'action_request')
    require(row['live_action_clause_count']==1,'one_live_action_clause')
    require(bool(row['action_text']),'action_request_retains_private_routing_text')
    require(row['authorization_granted'] is False,'request_not_authorization')

mixed=classify('It would be nice to have a calculator. Build me one now.','action_request')
require(mixed['mixed_turn'] is True,'mixed_conversation_action_detected')
require(mixed['action_text'].lower().startswith('build me one'),'mixed_turn_routes_only_live_clause')

ambiguous=classify('Build me a webpage. Delete my Python utility.','ambiguous_action')
require(ambiguous['requires_clarification'] is True and ambiguous['multiple_live_actions'] is True,'multiple_actions_fail_closed')
require(ambiguous['routing_mode']=='clarification_only','multiple_actions_no_route')

for text in ('Go ahead.','Yes, do it.','Proceed.'):
    row=classify(text,'authorization')
    require(row['generic_authorization_shape'] is True,'generic_authorization_detected')
    require(row['exact_control_shape'] is False,'generic_authorization_not_exact')
    require(row['routing_mode']=='require_exact_authorization','generic_authorization_requires_exact_contract')

exact=classify('Approve development proposal devc_0123456789abcdef01234567 revision 2.','authorization')
require(exact['exact_control_shape'] is True and exact['routing_mode']=='pass_exact_control','exact_proposal_approval_passthrough')

correction=classify('Actually, make it dark mode instead.','correction')
require(correction['target_reference_required'] is True and correction['development_correction_shape'] is True,'correction_requires_target')
for text in ('Actually, I meant Tuesday, not Thursday.','Stop calling me that.'):
    conversational_correction=classify(text,'correction')
    require(conversational_correction['target_reference_required'] is False and conversational_correction['development_correction_shape'] is False,'nondevelopment_correction_does_not_target_proposal')
    require(conversational_correction['routing_mode']=='conversation_only','nondevelopment_correction_stays_conversational')
cancel=classify('Cancel that development proposal.','cancellation')
require(cancel['target_reference_required'] is True,'cancellation_requires_target')
negative=classify('Please do not build that app.','cancellation')
require(negative['authorization_granted'] is False,'negative_instruction_never_authorizes')
exact_cancel=classify('Cancel development proposal devc_0123456789abcdef01234567 revision 2.','cancellation')
require(exact_cancel['exact_control_shape'] is True,'exact_cancellation_passthrough')

public=public_conversational_command_turn(mixed)
require('action_text' not in public and public['private_turn_text_exposed'] is False,'turn_public_projection_hides_private_text')
require(public['raw_command_exposed'] is False and public['raw_authorization_phrase_exposed'] is False,'turn_public_projection_hides_controls')

projection=build_conversational_command_integration('Build me a calculator webpage.')
require(projection['status']=='action_request_routed','integration_routes_live_action')
require(projection['routing_text'].lower().startswith('build me'),'private_routing_text_retained_only_in_private_projection')
public_projection=public_conversational_command_integration(projection)
require('routing_text' not in public_projection and public_projection['raw_turn_text_exposed'] is False,'integration_public_projection_hides_routing_text')
require(public_projection['private_path_exposed'] is False and public_projection['content_minimized'] is True,'integration_public_content_minimized')
for key,expected in DENIED_AUTHORITY.items(): require(projection.get(key) is expected,f'integration_{key}_denied')
require(set(ACT_KINDS)=={'discussion','hypothetical','information_request','planning_request','action_request','authorization','correction','cancellation','ambiguous_action'},'act_contract_complete')
require(source_signature()==before,'foundation_suite_preserves_source_immutability')

print(json.dumps({'ok':True,'suite':'v1259.0-v1259.2-conversational-command-integration-foundations','passed':len(CHECKS),'failed':0,'checks':CHECKS,'provider_contacted':False,'commands_executed':False,'project_modified':False,'authorization_granted':False,'release_authorized':False},indent=2,sort_keys=True))
