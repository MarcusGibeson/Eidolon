from __future__ import annotations
import os, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v1152b-')
sys.path.insert(0,str(root/'conscious_agent'))
from belief_revision import BeliefRevisionStore
from belief_uncertainty_foundations import build_belief_candidate
from evidence_grounded_reflection import build_evidence_grounded_reflection
from conversation_cognitive_backbone import record_turn_completion, build_turn_cognitive_context
from memory import load_memories
checks=[]
def check(n,v): assert v,n; checks.append(n)

def candidate(op,user,assistant,priors_r=(),priors_b=()):
    r=build_evidence_grounded_reflection(operation_id=op,user_message=user,assistant_response=assistant,thought={'thought':'Evaluate the supplied evidence.'},desires={},prior_reflections=list(priors_r))
    return r,build_belief_candidate(reflection=r,operation_id=op,prior_candidates=list(priors_b))

store=BeliefRevisionStore(Path(os.environ['EIDOLON_DATA_DIR'])/'cognition')
r1,b1=candidate('a1','The deployment provider timed out.','That supports a provisional provider-timeout belief.')
i1=store.integrate_candidate('integrate:a1',candidate=b1)
check('candidate-integrated',i1['status']=='candidate_integrated' and i1['result']['created'])
snap=store.snapshot(); beliefs=snap['beliefs']
check('durable-belief',len(beliefs)==1 and beliefs[0]['source_candidate_id']==b1['belief_candidate_id'])
check('evidence-mapped',len(beliefs[0]['evidence'])==len(b1['evidence_refs']))
check('authority-preserved',not beliefs[0]['authority']['authorizes_action'] and not beliefs[0]['authority']['executes_action'])
dup=store.integrate_candidate('integrate:a1',candidate=b1)
check('integration-idempotent',dup['idempotent'] and len(store.snapshot()['beliefs'])==1)
# Same proposition merges evidence rather than spawning another active belief.
b1_more=dict(b1); b1_more['belief_candidate_id']='belief-candidate-extra'; b1_more['evidence_refs']=list(b1['evidence_refs'])+['evidence-extra']; b1_more['confidence']=.85
merged=store.integrate_candidate('integrate:a2',candidate=b1_more)
check('same-belief-merged',merged['status']=='candidate_evidence_merged' and len(store.snapshot()['beliefs'])==1)
check('confidence-recomputed',store.snapshot()['beliefs'][0]['confidence']>=beliefs[0]['confidence'])
# Competing proposition on the same semantic subject creates a conflict set.
b_conflict=dict(b1); b_conflict.update({'belief_candidate_id':'belief-candidate-conflict','proposition':'The deployment provider did not time out.','content':'The deployment provider did not time out.','revision_basis':'new_evidence','retires_belief_candidate_ids':[]})
conf=store.integrate_candidate('integrate:a3',candidate=b_conflict)
state=store.snapshot()
check('competing-belief-created',conf['result']['created'] and len(state['beliefs'])==2)
check('conflict-set-created',bool(conf['result']['conflict_id']) and len(state['conflict_sets'])==1)
check('competing-beliefs-contested',all(x['lifecycle_state']=='contested' for x in state['beliefs']))
check('contested-projection-suppressed',not conf['result']['projection']['use_in_conversation'])
# Explicit correction supersedes matching active/contested history without deleting it.
b_correct=dict(b_conflict); b_correct.update({'belief_candidate_id':'belief-candidate-corrected','proposition':'The deployment was cancelled by the user.','content':'The deployment was cancelled by the user.','revision_basis':'explicit_user_correction','retires_belief_candidate_ids':[b1['belief_candidate_id'],b_conflict['belief_candidate_id']]})
corrected=store.integrate_candidate('integrate:a4',candidate=b_correct)
state=store.snapshot(); active=[x for x in state['beliefs'] if x['lifecycle_state']=='active']; superseded=[x for x in state['beliefs'] if x['lifecycle_state']=='superseded']
check('correction-active',len(active)==1 and active[0]['source_candidate_id']==b_correct['belief_candidate_id'])
check('history-superseded',len(superseded)==2 and len(state['beliefs'])==3)
check('correction-no-action-authority',corrected['result']['projection']['recommended_action']=='store_only' and corrected['result']['projection']['operator_authority_required_for_action'])
# Ordinary runtime performs candidate and durable revision phases once.
res=record_turn_completion(operation_id='runtime-b1',session_id='s',user_message='The migration copied all memory files.',assistant_response='That supports a provisional belief that the migration copy completed.',source='test',context_summary={})
check('runtime-revision-complete',res['completion_state']=='completed' and res['belief_candidate_recorded'] and res['belief_revision_recorded'])
rows=load_memories(); revisions=[x for x in rows if x.get('conversation_side_effect_phase')=='belief_revision']
check('revision-projection-stored',len(revisions)==1 and revisions[0]['type']=='belief_revision')
repeat=record_turn_completion(operation_id='runtime-b1',session_id='s',user_message='ignored retry',assistant_response='ignored retry',source='test',context_summary={})
check('runtime-idempotent',repeat['attempt_count']==res['attempt_count'] and len([x for x in load_memories() if x.get('conversation_side_effect_phase')=='belief_revision'])==1)
ctx=build_turn_cognitive_context('Did the migration preserve memory files?',operation_id='ctx',session_id='s',memories=load_memories(),self_model={},desires={})
check('durable-projection-in-context','belief_revision' in ctx['categories'])
check('prompt-bounded',ctx['prompt_chars']<=1800 and ctx['authority_broadened'] is False)
summary=store.inspection_summary()
check('inspection-conflicts-visible',summary['active_conflict_count']==1 and summary['raw_chain_of_thought_stored'] is False)
check('inspection-authority',summary['authority_boundary']['operator_authority_unchanged'])
print(f'v1152.3-v1152.5 belief revision integration: {len(checks)}/{len(checks)} passed')
