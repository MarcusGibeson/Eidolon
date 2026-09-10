from __future__ import annotations

"""Deterministic full conversation-runtime probe for v1259 tests only."""

import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
if str(ROOT/'conscious_agent') not in sys.path:
    sys.path.insert(0,str(ROOT/'conscious_agent'))

import conversation_runtime
from conversation_sessions import create_conversation_session
from ordinary_chat_development_campaign import list_development_campaign_proposals, load_development_campaign_proposal

class FakeLocalModelClient:
    calls=0
    def __init__(self,*args,**kwargs): self.last_retry_count=0
    def generate(self,prompt: str) -> str:
        type(self).calls += 1
        return 'Conversational acknowledgement.'
    def cancel(self): return None
    def close(self): return None

original=conversation_runtime.LocalModelClient
conversation_runtime.LocalModelClient=FakeLocalModelClient
try:
    session=create_conversation_session(title='v1259 ordinary runtime',select_session=False)
    info=conversation_runtime.run_conversation_turn(
        'Could you explain how to build a calculator webpage?',use_ai=True,session_id=session['id'],select_session_on_record=False,
    )
    before=list_development_campaign_proposals(public=False)['proposal_count']
    mixed=conversation_runtime.run_conversation_turn(
        'It would be useful to have a calculator. Build me a calculator webpage.',use_ai=True,session_id=session['id'],select_session_on_record=False,
    )
    rows=list_development_campaign_proposals(public=False)['proposals']
    proposal=rows[0]
    vague=conversation_runtime.run_conversation_turn('Go ahead.',use_ai=True,session_id=session['id'],select_session_on_record=False)
    after_vague=load_development_campaign_proposal(proposal['proposal_id'])
    correction=conversation_runtime.run_conversation_turn(
        'Actually, make it dark mode instead.',use_ai=True,session_id=session['id'],select_session_on_record=False,
    )
    after_correction=load_development_campaign_proposal(proposal['proposal_id'])
    print(json.dumps({
        'info_success':info.success,
        'info_provider_requests':info.provider_request_count,
        'info_act':info.cognitive_context.get('conversational_command_integration',{}).get('primary_act'),
        'proposal_count_before_mixed':before,
        'mixed_success':mixed.success,
        'mixed_provider_requests':mixed.provider_request_count,
        'mixed_response':mixed.response,
        'mixed_act':mixed.cognitive_context.get('conversational_command_integration',{}).get('primary_act'),
        'proposal_count_after_mixed':len(rows),
        'vague_provider_requests':vague.provider_request_count,
        'approval_after_vague':after_vague.get('approval_consumed'),
        'correction_provider_requests':correction.provider_request_count,
        'revision_after_correction':after_correction.get('revision'),
        'fake_provider_calls':FakeLocalModelClient.calls,
    },sort_keys=True))
finally:
    conversation_runtime.LocalModelClient=original
