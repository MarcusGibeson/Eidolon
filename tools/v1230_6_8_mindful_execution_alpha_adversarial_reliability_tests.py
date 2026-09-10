from __future__ import annotations
import json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
from v1230_mindful_execution_fixture import build_mindful_execution_fixture
import execution_session_authorization_bounded_launch as launch_module
import execution_session_pause_resume_cancel_recovery as control_module
import execution_outcome_reflection_learning_integration as learning
checks=[]
def check(v): checks.append(bool(v))
fixture=build_mindful_execution_fixture('v1230-adversarial','completed')
runtime=fixture['runtime']; session=fixture['prepared_session']; auth=fixture['launch_authorization']; launch=fixture['launch']; review=fixture['lesson_review']
# Restart-safe deterministic inspection.
for v in (
    launch_module.inspect_bounded_development_execution_session(launch['launch_id'],runtime_root=runtime).get('launch_digest')==launch['launch_digest'],
    control_module.inspect_execution_session_control(launch['launch_id'],runtime_root=runtime,reconcile_runtime=False).get('control_digest')==fixture['control']['control_digest'],
    learning.public_execution_outcome_lesson_reviews(runtime_root=runtime).get('review_count')==1,
): check(v)
# Launch authorization replay does not create a second authority consumption or launch.
replay=launch_module.launch_bounded_development_execution_session(
    auth['authorization_id'], expected_authorization_digest=auth['authorization_digest'],
    expected_session_id=session['session_id'], expected_session_digest=session['session_digest'], runtime_root=runtime,
)
check(replay.get('ok') is True); check(replay.get('launch_id')==launch['launch_id']); check(replay.get('operation_status') in {'replayed','resumed','created'})
# Stale/tampered digests fail closed.
stale=launch_module.prepare_bounded_launch_authorization(session['session_id'],expected_session_digest='0'*64,runtime_root=runtime)
check(stale.get('ok') is False); check(stale.get('provider_execution_authorized') is False)
# Crash reconciliation cannot reactivate automatically.
namespace=launch_module._runtime_namespace_path(launch['launch_id'],runtime)
shutil.rmtree(namespace,ignore_errors=True)
reconciled=control_module.inspect_execution_session_control(launch['launch_id'],runtime_root=runtime,reconcile_runtime=True)
check(reconciled.get('session_state')=='recovery_required')
recovery_auth=control_module.prepare_execution_session_transition_authorization('recover',control_id=reconciled['control_id'],expected_control_digest=reconciled['control_digest'],runtime_root=runtime)
check(recovery_auth.get('ok') is True)
recovered=control_module.apply_execution_session_transition(
    recovery_auth['authorization_id'], expected_authorization_digest=recovery_auth['authorization_digest'],
    expected_control_id=reconciled['control_id'], expected_control_digest=reconciled['control_digest'],
    exact_phrase=recovery_auth['authorize_phrase'], expected_action='recover', runtime_root=runtime,
)
check(recovered.get('ok') is True); check(recovered.get('to_state')=='paused' and (recovered.get('control') or {}).get('session_state')=='paused'); check(recovered.get('resume_applied') is False)
# Accepted learning remains project-scoped and does not become action authority.
for key in ('provider_execution_authorized','command_execution_authorized','test_execution_authorized','workspace_materialization_authorized','project_mutation_authorized','queue_mutation_authorized','schedule_mutation_authorized','launch_authorized','cognition_write_authorized','old_authority_reusable'):
    check(review.get(key) is False)
check(review.get('durable_project_scoped_learning_recorded') is True); check(review.get('generalized_beyond_project') is False)
# Contradictory active lesson is rejected against the same project.
reflection=fixture['reflection']
contradiction=learning.review_execution_outcome_lesson(
    reflection['reflection_id'], expected_reflection_digest=reflection['reflection_digest'],
    disposition='revise', revised_lesson_codes=['avoid_repeating_approach'], runtime_root=runtime,
)
check(contradiction.get('ok') is False); check(contradiction.get('status') in {'execution_outcome_lesson_review_conflict','execution_outcome_lesson_review_already_recorded','execution_outcome_lesson_review_blocked'})
# Tampered sealed outcome is no longer usable.
outcome_path=learning._outcome_path(fixture['outcome']['outcome_id'],runtime)
row=json.loads(outcome_path.read_text(encoding='utf-8')); row['achievement_classification']='failed'; outcome_path.write_text(json.dumps(row,sort_keys=True),encoding='utf-8')
blocked=learning.prepare_execution_outcome_reflection(fixture['outcome']['outcome_id'],expected_outcome_digest=fixture['outcome']['outcome_digest'],runtime_root=runtime)
check(blocked.get('ok') is False)
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
