from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
for p in (R,R/'conscious_agent',R/'tools'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from natural_language_action_routing import build_natural_language_action_projection
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
from integrated_mind_conversation_development_benchmark import *
c=[];ck=lambda v:c.append(bool(v))
with tempfile.TemporaryDirectory() as rt:
    mixed='It would be nice to hear your voice. Build your own text-to-speech system with a voice you choose.'
    projection=build_natural_language_action_projection(mixed)
    first=process_ordinary_chat_development_turn(mixed,action_projection=projection,session_id='session_mix',project_state={'project_id':'project_alpha'},runtime_root=rt)
    second=process_ordinary_chat_development_turn(mixed,action_projection=projection,session_id='session_mix',project_state={'project_id':'project_alpha'},runtime_root=rt)
    for v in (first['active'],first['event']=='proposal_created',second['active'],second['event']=='proposal_resumed',first['proposal']['proposal_id']==second['proposal']['proposal_id'],first['proposal']['revision']==second['proposal']['revision']==1,not first.get('provider_contacted'),not first.get('source_modified'),not first.get('authority_granted')):ck(v)
    pid=first['proposal']['proposal_id']; rev=first['proposal']['revision']
    vague=process_ordinary_chat_development_turn('Go ahead.',action_projection=build_natural_language_action_projection('Go ahead.'),session_id='session_mix',runtime_root=rt)
    vague_safe=(not vague['active'] and vague['event']=='inactive') or (vague['active'] and vague['event']=='generic_authorization_blocked')
    for v in (vague_safe,not vague.get('authority_granted'),not vague.get('provider_contacted'),not vague.get('source_modified')):ck(v)
    exact=f'Approve development proposal {pid} revision {rev}.'
    approved=process_ordinary_chat_development_turn(exact,action_projection=build_natural_language_action_projection(exact),session_id='session_mix',runtime_root=rt)
    replay=process_ordinary_chat_development_turn(exact,action_projection=build_natural_language_action_projection(exact),session_id='session_mix',runtime_root=rt)
    for v in (approved['active'],approved['event']=='approval_consumed',approved.get('approval_consumed_now') is True,replay['active'],replay['event']=='approval_replayed',replay.get('approval_consumed_now') is False,replay.get('idempotent_replay') is True,not approved.get('implementation_started'),not approved.get('source_modified')):ck(v)
    for text,expected in (
        ('I feel discouraged about this project today.','conversation'),
        ('It would be nice if the tests were faster.','conversation'),
        ('What if we changed the database?','question'),
        ('The operator wrote "Run all tests," but this is a quotation.','conversation'),
        ('Maybe we should revisit that later.','conversation'),
        ('Help me plan the migration.','planning_request'),
    ):
        p=build_natural_language_action_projection(text);out=process_ordinary_chat_development_turn(text,action_projection=p,session_id='session_chat',runtime_root=rt)
        for v in (p['intent']['category']==expected,not out['active'],out['event']=='inactive',not out['provider_contacted'],not out['source_modified'],not out['authority_granted']):ck(v)
for text in ('show integrated mind conversation development benchmark registry','show integrated mind conversation development benchmark'):
    with tempfile.TemporaryDirectory() as rt:
        out=process_ordinary_chat_development_turn(text,action_projection=build_natural_language_action_projection(text),runtime_root=rt)
        for v in (out['active'],'integrated_mind_conversation_development_benchmark' in out,not out['action_taken'],not out['authority_granted']):ck(v)
run=run_ordinary_chat_integration_benchmark();
for row in run['cases']:
    for v in (row['expected_behavior_met'],row['no_authority_granted'],row['content_free'],not row['raw_text_returned']):ck(v)
print(json.dumps({'ok':all(c),'passed':sum(c),'total':len(c)},sort_keys=True));raise SystemExit(0 if all(c) else 1)
