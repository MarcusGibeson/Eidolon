from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1152-')
sys.path.insert(0,str(root/'conscious_agent'))
from belief_uncertainty_foundations import build_belief_candidate, classify_uncertainty, inspect_belief_candidates
from evidence_grounded_reflection import build_evidence_grounded_reflection
from conversation_cognitive_backbone import record_turn_completion, build_turn_cognitive_context
from memory import load_memories
checks=[]
def check(n,v): assert v,n; checks.append(n)
r=build_evidence_grounded_reflection(operation_id='r1',user_message='The provider timed out during deployment.',assistant_response='That is evidence of a provider failure.',thought={'thought':'Provider reliability may be degraded.'},desires={},prior_reflections=[])
b=build_belief_candidate(reflection=r,operation_id='r1',prior_candidates=[])
check('candidate-provisional',b['epistemic_status']=='provisional')
check('evidence-linked',b['evidence_count']>=2 and b['origin_reflection_id']==r['reflection_id'])
check('uncertainty-explicit',b['uncertainty_state'] in {'low','material','high','insufficient_evidence'})
check('revisable',b['revisable'])
check('no-authority',b['recommended_action']=='store_only' and not b['action_executed'])
low=classify_uncertainty(.95,2,True); missing=classify_uncertainty(.95,0,False)
check('low-uncertainty',low['uncertainty_state']=='low')
check('insufficient-evidence',missing['uncertainty_state']=='insufficient_evidence')
r2=build_evidence_grounded_reflection(operation_id='r2',user_message='Actually, correction: the provider did not time out; I cancelled it.',assistant_response='The prior failure interpretation is corrected.',thought={'thought':'The user corrected the evidence.'},desires={},prior_reflections=[r])
b2=build_belief_candidate(reflection=r2,operation_id='r2',prior_candidates=[b])
check('correction-supersedes',b2['supersedes_belief_candidate_id']==b['belief_candidate_id'])
check('correction-retires',b['belief_candidate_id'] in b2['retires_belief_candidate_ids'])
check('history-preserved',b2['historical_records_preserved'])
res=record_turn_completion(operation_id='runtime-belief-1',session_id='s',user_message='The migration preserved all memory files.',assistant_response='That supports a provisional belief that the copy was complete.',source='test',context_summary={})
check('runtime-complete',res['completion_state']=='completed' and res['belief_candidate_recorded'])
rows=load_memories(); candidates=[x for x in rows if x.get('conversation_side_effect_phase')=='belief_candidate']
check('runtime-candidate',len(candidates)==1)
check('runtime-uncertainty',bool(candidates[0].get('uncertainty_state')))
ctx=build_turn_cognitive_context('Were the memory files preserved?',operation_id='ctx',session_id='s',memories=rows,self_model={},desires={})
check('ordinary-context', 'belief_candidate' in ctx['categories'])
check('bounded-context',ctx['prompt_chars']<=1800)
summary=inspect_belief_candidates(rows)
check('inspection-content-free',summary['candidate_count']==1 and not summary['raw_content_exposed'])
check('inspection-authority',summary['authority_preserved'])
print(f'v1152.0-v1152.2 belief revision and uncertainty foundations: {len(checks)}/{len(checks)} passed')
