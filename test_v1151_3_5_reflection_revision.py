from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1151-3-5-')
sys.path.insert(0,str(root/'conscious_agent'))
from evidence_grounded_reflection import build_evidence_grounded_reflection
from conversation_cognitive_backbone import build_turn_cognitive_context, record_turn_completion
from memory import load_memories

checks=[]
def check(name,value):
    assert value,name; checks.append(name)

base=build_evidence_grounded_reflection(operation_id='op1',user_message='The provider timed out twice during chat.',assistant_response='I will record the timeout as a provider failure.',thought={'thought':'Provider reliability may be degraded.'},desires={},prior_reflections=[])
corrected=build_evidence_grounded_reflection(operation_id='op2',user_message='Actually, correction: the provider did not time out; I cancelled the request.',assistant_response='The earlier timeout interpretation should be retired.',thought={'thought':'User correction overrides the earlier interpretation.'},desires={},prior_reflections=[base])
check('stable-semantic-subject-key', bool(base['semantic_subject_key']))
check('correction-detected', corrected['operator_correction'])
check('revision-lineage', corrected['supersedes_reflection_id']==base['reflection_id'])
check('retirement-declared', base['reflection_id'] in corrected['retires_reflection_ids'])
check('historical-preservation', corrected['historical_records_preserved'])
check('correction-confidence', corrected['confidence']>=0.9)
check('authority-preserved', corrected['recommended_action']=='store_only' and not corrected['action_executed'])

ctx=build_turn_cognitive_context('What happened with the provider request?',operation_id='op3',session_id='s',memories=[base,corrected],self_model={},desires={})
check('retired-suppressed', ctx['retired_reflections_suppressed']==1)
check('correction-precedence', ctx['correction_precedence'])
check('uncertainty-weighted', ctx['uncertainty_weighted'])
check('corrected-context-selected', 'operator_correction": true' in ctx['prompt_section'])
check('old-interpretation-absent', base['content'] not in ctx['prompt_section'])
check('bounded-context', ctx['prompt_chars']<=1800)

r1=record_turn_completion(operation_id='runtime-revision-1',session_id='s',user_message='The deployment failed because the provider timed out.',assistant_response='I will preserve that as tentative evidence.',source='test',context_summary={})
r2=record_turn_completion(operation_id='runtime-revision-2',session_id='s',user_message='Actually, correction: the deployment did not fail and the provider did not time out.',assistant_response='The earlier interpretation is superseded.',source='test',context_summary={})
rows=load_memories()
refs=[r for r in rows if r.get('conversation_side_effect_phase')=='reflection']
latest=next(r for r in refs if r.get('conversation_operation_id')=='runtime-revision-2')
check('runtime-completions', r1['completion_state']=='completed' and r2['completion_state']=='completed')
check('runtime-correction-recorded', latest.get('operator_correction') is True)
check('runtime-lineage-recorded', bool(latest.get('supersedes_reflection_id')))
ctx2=build_turn_cognitive_context('Did the deployment fail?',operation_id='op4',session_id='s',memories=rows,self_model={},desires={})
check('runtime-retired-suppressed', ctx2['retired_reflections_suppressed']>=1)
print(f'v1151.3-v1151.5 reflection integration and revision: {len(checks)}/{len(checks)} passed')
