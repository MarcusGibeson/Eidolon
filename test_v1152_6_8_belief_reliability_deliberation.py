from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v1152c-'))
os.environ['EIDOLON_DATA_DIR']=str(runtime)
sys.path.insert(0,str(root/'conscious_agent'))
import conversation_cognitive_backbone as backbone
from belief_revision import BeliefRevisionStore
from belief_deliberation import build_belief_deliberation
from belief_uncertainty_foundations import build_belief_candidate
from evidence_grounded_reflection import build_evidence_grounded_reflection
from memory import load_memories
checks=[]
def check(name,value): assert value,name; checks.append(name)

def candidate(op,user,assistant,priors_r=(),priors_b=()):
    reflection=build_evidence_grounded_reflection(operation_id=op,user_message=user,assistant_response=assistant,thought={'thought':'Compare the available evidence.'},desires={},prior_reflections=list(priors_r))
    return reflection,build_belief_candidate(reflection=reflection,operation_id=op,prior_candidates=list(priors_b))

store=BeliefRevisionStore(runtime/'cognition')
r1,b1=candidate('r1','The backup completed successfully.','That supports a provisional belief that the backup completed.')
first=store.integrate_candidate('integrate:r1',candidate=b1)
belief_id=first['result']['belief_id']
evidence_id=store.snapshot()['beliefs'][0]['evidence'][0]['evidence_id']
retracted=store.retract_evidence('retract:1',belief_id=belief_id,evidence_id=evidence_id,correction_ref='The source report was withdrawn.')
check('retraction-preserves-history',store.snapshot()['beliefs'][0]['evidence'][0]['active'] is False and bool(store.snapshot()['beliefs'][0]['evidence'][0]['reference_digest']))
check('retraction-no-authority',retracted['result']['automatic_resolution'] is False)
history_count=len(store.snapshot()['beliefs'][0]['update_history'])
second=store.retract_evidence('retract:2',belief_id=belief_id,evidence_id=evidence_id,correction_ref='Repeated withdrawal notice.')
check('retraction-idempotent-across-events',second['status']=='evidence_already_retracted' and second['result']['idempotent_retraction'])
check('retraction-history-not-duplicated',len(store.snapshot()['beliefs'][0]['update_history'])==history_count)

# Create an unresolved same-subject conflict.
b2=dict(b1); b2.update({'belief_candidate_id':'belief-candidate-opposite','proposition':'The backup did not complete successfully.','content':'The backup did not complete successfully.','revision_basis':'new_evidence','retires_belief_candidate_ids':[],'confidence':.62})
conf=store.integrate_candidate('integrate:r2',candidate=b2)
conflict_id=conf['result']['conflict_id']
check('conflict-created',bool(conflict_id) and len(store.snapshot()['conflict_sets'])==1)
before_path=(runtime/'cognition'/'belief_revision.json').read_bytes()
deliberation=build_belief_deliberation('Did the backup complete?',runtime_root=runtime/'cognition')
after_path=(runtime/'cognition'/'belief_revision.json').read_bytes()
check('deliberation-read-only',before_path==after_path and deliberation['read_only'])
check('deliberation-relevant',deliberation['conflict_count']==1 and deliberation['conflicts'][0]['conflict_id']==conflict_id)
check('deliberation-options-bounded',2<=len(deliberation['conflicts'][0]['options'])<=3 and all(len(row['proposition'])<=260 for row in deliberation['conflicts'][0]['options']))
check('deliberation-no-resolution-authority',not deliberation['resolution_permitted'] and not deliberation['authority_broadened'])
check('small-margin-seeks-evidence',deliberation['conflicts'][0]['recommendation']=='seek_more_evidence')

ctx=backbone.build_turn_cognitive_context('Did the backup complete?',operation_id='ctx1',session_id='s',memories=[],self_model={},desires={})
check('deliberation-affects-ordinary-context','belief_deliberation' in ctx['categories'] and ctx['belief_conflicts_deliberated']==1)
check('deliberation-prompt-bounded',ctx['prompt_chars']<=1800 and 'reasoning_alpha_state data=' in ctx['prompt_section'] and ctx['multi_step_resolution_permitted'] is False)
check('deliberation-prompt-data-only','authority="none"' in ctx['prompt_section'] and ctx['belief_conflicts_auto_resolved'] is False)

# A malformed active conflict is quarantined rather than trusted.
malformed={'beliefs':[{'belief_id':'only','proposition':'One side','confidence':.9,'uncertainty':.1,'lifecycle_state':'contested','evidence':[]}], 'conflict_sets':[{'conflict_id':'bad','status':'active','belief_ids':['only','missing']}]} 
quarantine=build_belief_deliberation('One side',state=malformed)
check('malformed-conflict-quarantined',quarantine['conflict_count']==0 and quarantine['quarantined_conflict_count']==1)

# Evidence retraction marks an affected conflict for review but never resolves it.
active_evidence=next(row for row in store.snapshot()['beliefs'][1]['evidence'] if row['active'])
review=store.retract_evidence('retract:conflict',belief_id=store.snapshot()['beliefs'][1]['belief_id'],evidence_id=active_evidence['evidence_id'],correction_ref='The contradictory report was retracted.')
state=store.snapshot(); conflict=state['conflict_sets'][0]
check('retraction-flags-conflict-review',conflict.get('needs_review') is True and conflict_id in review['result']['affected_conflict_ids'])
check('retraction-does-not-resolve-conflict',conflict['status']=='active' and not conflict.get('preferred_belief_id'))

# Partial completion after durable integration recovers without duplicate belief state.
original_store=backbone.store_memory_batch
calls={'count':0}
def fail_once(items):
    calls['count']+=1
    if calls['count']==1: raise RuntimeError('injected memory failure after durable integration')
    return original_store(items)
backbone.store_memory_batch=fail_once
try:
    failed=False
    try:
        backbone.record_turn_completion(operation_id='recover-belief',session_id='s',user_message='The cache rebuild completed.',assistant_response='That supports a provisional belief that the rebuild completed.',source='test',context_summary={})
    except RuntimeError:
        failed=True
    check('partial-integration-failure-injected',failed)
finally:
    backbone.store_memory_batch=original_store
belief_count_before=len(BeliefRevisionStore(runtime/'cognition').snapshot()['beliefs'])
recovered=backbone.record_turn_completion(operation_id='recover-belief',session_id='s',user_message='ignored retry',assistant_response='ignored retry',source='test',context_summary={})
belief_count_after=len(BeliefRevisionStore(runtime/'cognition').snapshot()['beliefs'])
check('partial-integration-recovers',recovered['completion_state']=='completed' and recovered['belief_revision_recorded'])
check('partial-integration-no-duplicate-belief',belief_count_after==belief_count_before)
check('partial-integration-single-projection',len([row for row in load_memories() if row.get('conversation_operation_id')=='recover-belief' and row.get('conversation_side_effect_phase')=='belief_revision'])==1)

summary=store.inspection_summary()
check('inspection-authority-unchanged',summary['authority_boundary']['operator_authority_unchanged'])
check('contract-advanced',summary['contract_version']=='v1152.8' and ctx['contract_version'] in {'v1152.8','v1153.2','v1153.5','v1153.8','v1154.5','v1155.5','v1155.8'})
print(f'v1152.6-v1152.8 belief reliability and deliberation: {len(checks)}/{len(checks)} passed')
