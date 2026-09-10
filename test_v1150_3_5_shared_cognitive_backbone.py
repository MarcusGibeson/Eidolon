from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from unittest.mock import patch

from conscious_agent.conversation_cognitive_backbone import (
    build_turn_cognitive_context, inspect_conversation_cognitive_backbone, record_turn_completion,
)
from conscious_agent.cognitive_contract_review import build_cognitive_contract_review

checks=[]
def check(name, condition):
    if not condition: raise AssertionError(name)
    checks.append(name)

with tempfile.TemporaryDirectory() as td:
    os.environ['EIDOLON_DATA_DIR']=td
    context=build_turn_cognitive_context(
        'Please help me continue this topic', operation_id='conversation_test', session_id='session_test',
        memories=[
            {'type':'reflection','conclusion':'Stay consistent with the current topic.','use_in_conversation':True},
            {'type':'conversation_user','content':'private raw user text'},
        ], self_model={'focus':'Maintain topic continuity'}, desires={'helpfulness':0.9,'novelty':0.2},
    )
    check('bounded prompt', len(context['prompt_section']) <= 1800)
    check('eligible reflection included', 'Stay consistent' in context['prompt_section'])
    check('ordinary raw memory excluded', 'private raw user text' not in context['prompt_section'])
    check('authority preserved in context', context['authority_broadened'] is False)
    fake_thought={'type':'thought','thought':'Consider the user request carefully.'}
    fake_reflection={'type':'reflection','conclusion':'Continue coherently.'}
    with patch('conscious_agent.conversation_cognitive_backbone.load_self_model', return_value={'name':'Eidolon'}), \
         patch('conscious_agent.conversation_cognitive_backbone.load_desires', return_value={'helpfulness':0.9}), \
         patch('conscious_agent.conversation_cognitive_backbone.load_memories', return_value=[]), \
         patch('conscious_agent.conversation_cognitive_backbone.generate_inner_thought', return_value=fake_thought), \
         patch('conscious_agent.conversation_cognitive_backbone.reflect_on_thought', return_value=fake_reflection), \
         patch('conscious_agent.conversation_cognitive_backbone.store_memory_batch') as store:
        first=record_turn_completion(operation_id='conversation_test',session_id='session_test',user_message='secret',assistant_response='secret reply',source='test',context_summary=context)
        second=record_turn_completion(operation_id='conversation_test',session_id='session_test',user_message='different',assistant_response='different',source='test',context_summary=context)
        check('completion idempotent', first == second)
        check('memory batch once', store.call_count == 1)
        items=store.call_args.args[0]
        check('reflection eligible next turn', any(i.get('use_in_conversation') for i in items))
        check('thought not automatically eligible', any(i.get('conversation_side_effect_phase')=='thought' and not i.get('use_in_conversation') for i in items))
    ledger=json.loads((Path(td)/'cognition'/'ordinary_conversation_turns.json').read_text())
    check('content-free ledger', 'secret' not in json.dumps(ledger))
    inspection=inspect_conversation_cognitive_backbone()
    check('one ledger turn', inspection['turn_count']==1)
    check('ledger authority preserved', inspection['authority_preserved'])

review=build_cognitive_contract_review(Path(__file__).resolve().parent)
open_ids={r['finding_id'] for r in review['findings']}
resolved={r['finding_id'] for r in review['resolved_findings']}
check('v1145 path resolved', 'v1145-contracts-not-in-ordinary-turn-path' in resolved and 'v1145-contracts-not-in-ordinary-turn-path' not in open_ids)
check('reflection split resolved', 'post-reply-reflection-split-from-authoritative-runtime' in resolved and 'post-reply-reflection-split-from-authoritative-runtime' not in open_ids)
check('review connected', review['status']=='connected')
print(f'PASS {len(checks)}/{len(checks)}')
for c in checks: print('PASS',c)
