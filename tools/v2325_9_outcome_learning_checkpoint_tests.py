from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'conscious_agent')); sys.dont_write_bytecode=True
os.environ['EIDOLON_DATA_DIR']=tempfile.mkdtemp(prefix='eidolon-v2325-data-')
from outcome_learning_governance_v2300 import *
checks=[]
def req(v,n): checks.append(n); assert v,n
runtime=Path(tempfile.mkdtemp(prefix='eidolon-v2325-runtime-'))
D='a'*64
r1=record_verified_outcome(outcome_id='o1',task_type='repair',result='failed',evidence_digest=D,strategy_code='s1',failure_class='syntax',repair_class='edit',applicability=['python'],event_id='e1',runtime_root=runtime)
req(r1['ok'] and r1['status']=='verified_outcome_recorded','verified_outcome_recorded')
req(r1['outcome']['retained_receipt_digest'],'retained_outcome_owner_bound')
rep=record_verified_outcome(outcome_id='o1',task_type='repair',result='failed',evidence_digest=D,strategy_code='s1',failure_class='syntax',repair_class='edit',applicability=['python'],event_id='e1',runtime_root=runtime)
req(rep['status']=='outcome_record_replayed' and rep['idempotent'],'outcome_replay_exactly_once')
req(not record_verified_outcome(outcome_id='bad',task_type='repair',result='success',evidence_digest='nope',event_id='e2',runtime_root=runtime)['ok'],'invalid_digest_rejected')
req(not record_verified_outcome(outcome_id='bad2',task_type='repair',result='maybe',evidence_digest=D,event_id='e3',runtime_root=runtime)['ok'],'invalid_result_rejected')
req(extract_bounded_lessons(runtime_root=runtime)['lesson_count']==0,'one_result_not_generalized')
r2=record_verified_outcome(outcome_id='o2',task_type='repair',result='failed',evidence_digest='b'*64,strategy_code='s1',failure_class='syntax',repair_class='edit',applicability=['python'],event_id='e4',runtime_root=runtime)
req(r2['ok'],'second_outcome_recorded')
ex=extract_bounded_lessons(runtime_root=runtime)
req(ex['lesson_count']==1 and ex['lessons'][0]['guidance']=='avoid_or_reassess_strategy','repeated_failure_becomes_bounded_lesson')
req(ex['lessons'][0]['automatic_generalization_permitted'] is False,'universalization_denied')
pers=persist_lesson_candidates(event_id='p1',runtime_root=runtime)
req(pers['ok'] and pers['lesson_count']==1,'lesson_persisted')
pers2=persist_lesson_candidates(event_id='p1',runtime_root=runtime)
req(pers2['status']=='lesson_persistence_replayed','lesson_persistence_replay')
state=inspect_learning_state(runtime_root=runtime)
req(state['lesson_count']==1 and state['content_free'],'public_learning_state_content_free')
adapt=build_policy_adaptation(task_type='repair',runtime_root=runtime)
req(adapt['ok'] and len(adapt['selected_lessons'])==1,'policy_adaptation_uses_verified_lesson')
req(adapt['adaptation_is_advisory'] and not adapt['authority_expanded'],'adaptation_non_authorizing')
lesson=ex['lessons'][0]
rev=revise_lesson(lesson_id=lesson['lesson_id'],expected_digest=lesson['lesson_digest'],action='retract',event_id='rv1',runtime_root=runtime)
req(rev['ok'] and rev['lesson_state']=='retracted','digest_bound_retraction')
stale=revise_lesson(lesson_id=lesson['lesson_id'],expected_digest='c'*64,action='retain',event_id='rv2',runtime_root=runtime)
req(not stale['ok'] and stale['status']=='stale_lesson_digest','stale_lesson_digest_rejected')
path=runtime/'learning'/'era9_outcome_learning.json'; path.write_text('{broken',encoding='utf-8')
corrupt=inspect_learning_state(runtime_root=runtime)
req(not corrupt['ok'] and corrupt['mutation_permitted'] is False,'corrupt_store_fails_closed')
blocked=record_verified_outcome(outcome_id='o3',task_type='repair',result='success',evidence_digest=D,event_id='e5',runtime_root=runtime)
req(not blocked['ok'] and blocked.get('store_preserved'),'corrupt_store_not_overwritten')
held=evaluate_policy_adaptation(
    baseline_trials=[{'success':False,'evidence_digest':'1'*64},{'success':True,'evidence_digest':'2'*64}],
    adapted_trials=[{'success':True,'evidence_digest':'3'*64},{'success':True,'evidence_digest':'4'*64}],
)
req(held['ok'] and held['measurable_improvement'] and held['absolute_improvement']==0.5,'held_out_improvement_measured')
leaky=evaluate_policy_adaptation(baseline_trials=[{'success':True,'evidence_digest':'5'*64}],adapted_trials=[{'success':True,'evidence_digest':'5'*64}])
req(not leaky['ok'] and leaky['status']=='invalid_or_leaky_held_out_evaluation','held_out_leakage_rejected')
req(all(not r1[k] for k in ('model_training_performed','source_modified','installation_authorized','authority_expanded')),'outcome_learning_authority_inert')
print(json.dumps({'suite':'v2325.9-outcome-learning','ok':True,'passed':len(checks),'failed':0,'checks':checks},sort_keys=True))
