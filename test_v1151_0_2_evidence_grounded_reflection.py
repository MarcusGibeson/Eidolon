from __future__ import annotations
import os, tempfile
from pathlib import Path

root=Path(__file__).resolve().parent
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1151-')
import sys
sys.path.insert(0,str(root/'conscious_agent'))

from evidence_grounded_reflection import build_evidence_packet, build_evidence_grounded_reflection
from conversation_cognitive_backbone import record_turn_completion, build_turn_cognitive_context
from memory import load_memories

checks=[]
def check(name, value):
    assert value, name
    checks.append(name)

packet=build_evidence_packet(operation_id='conversation_test_1', user_message='Help me plan a safe migration for my memories.', assistant_response='We should preserve the old copy and verify hashes.', thought={'thought':'A copy-only migration reduces loss risk.'})
check('subject-from-real-turn', 'migration' in packet['subject'])
check('explicit-evidence', packet['evidence_count']==3)
check('bounded-evidence', packet['content_bounded'])
check('operator-evidence-marked', packet['evidence'][0]['operator_supplied'])
check('no-authority', not packet['authority_broadened'])

reflection=build_evidence_grounded_reflection(operation_id='conversation_test_1', user_message='Help me plan a safe migration for my memories.', assistant_response='We should preserve the old copy and verify hashes.', thought={'thought':'A copy-only migration reduces loss risk.'}, desires={'truthfulness':1.0})
check('meaningful-subject', 'migration' in reflection['subject'])
check('traceable-evidence', len(reflection['evidence_refs'])==3)
check('uncertainty-present', bool(reflection['uncertainty']))
check('revisable', reflection['revisable'])
check('action-remains-governed', reflection['recommended_action']=='store_only' and reflection['operator_authority_required_for_action'])

result=record_turn_completion(operation_id='conversation_test_2', session_id='session', user_message='My provider timed out twice.', assistant_response='The failure should be reported without switching models.', source='test', context_summary={})
check('completion-recorded', result['completion_state']=='completed')
memories=load_memories()
rows=[r for r in memories if r.get('conversation_operation_id')=='conversation_test_2']
refl=next(r for r in rows if r.get('conversation_side_effect_phase')=='reflection')
check('ordinary-reflection-evidence-grounded', refl.get('evidence_count',0)>=2 and 'provider' in refl.get('subject',''))
check('ordinary-reflection-conversation-eligible', refl.get('use_in_conversation') is True)
ctx=build_turn_cognitive_context('What happened with the provider?', operation_id='conversation_test_3', session_id='session', memories=memories, self_model={}, desires={})
check('later-turn-admission', ctx['item_count']>=1 and 'reflection' in ctx['categories'])
check('content-bound', ctx['prompt_chars']<=1800)
print(f'v1151.0-v1151.2 evidence-grounded reflection: {len(checks)}/{len(checks)} passed')
