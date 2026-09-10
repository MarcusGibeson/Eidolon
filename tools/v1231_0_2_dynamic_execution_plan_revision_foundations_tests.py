from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
import dynamic_execution_plan_revision as revision
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
import supervised_work_dispatch_execution_session_preparation as preparation
import execution_session_authorization_bounded_launch as launching
from v1228_control_fixture import build_control_fixture
from v1231_plan_revision_fixture import clone_runtime
checks=[]
def check(v): checks.append(bool(v))
def tree_signature():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
            rows.append(f"{p.relative_to(ROOT).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}")
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest(),len(rows)
before=tree_signature()
fixture=build_control_fixture('v1231-foundations'); launch=fixture['launch']; base=fixture['runtime']
monitor=monitoring.record_live_execution_progress(
    launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='blocker_reported',current_stage='blocked',
    completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['scope_drift','test_coverage_gap'],operator_attention_required=True,runtime_root=base)
assert monitor.get('ok'),monitor
state=control.inspect_execution_session_control(launch['launch_id'],runtime_root=base,reconcile_runtime=False)
prepared_path=preparation._session_path(launch['source_session_id'],base); launch_path=launching._launch_path(launch['launch_id'],base)
monitor_path=monitoring._monitor_path(launch['launch_id'],base); control_path=control._control_path(launch['launch_id'],base)
immutable_before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (prepared_path,launch_path,monitor_path,control_path)}

def prepare(rt,codes=('dependency_state_changed','test_evidence_changed'),ld=None,md=None,cd=None):
    m=monitoring.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=rt)
    c=control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=False)
    return revision.prepare_dynamic_execution_plan_revision(
        launch['launch_id'],expected_launch_digest=ld or launch['launch_digest'],expected_monitor_digest=md or m.get('monitor_digest','0'*64),
        expected_control_digest=cd or c.get('control_digest','0'*64),verified_change_codes=codes,runtime_root=rt)

# Active foundation and explanation completeness.
rt=clone_runtime(base,'v1231-foundation-active'); result=prepare(rt)
check(result.get('ok')); check(result.get('status')=='dynamic_execution_plan_revision_ready_for_operator_review')
check(result.get('session_state_at_proposal')=='active'); check(result.get('generation')==1)
check(result.get('original_plan_digest')==launch.get('source_session_digest')); check(result.get('original_plan_immutable') is True)
check(result.get('historical_receipts_immutable') is True); check(result.get('operator_review_required') is True)
for key in ('changed_assumption_codes','proposed_scope_change_codes','new_or_changed_dependency_codes','risk_codes','test_implication_codes','rollback_implication_codes','original_plan_insufficiency_codes'):
    check(isinstance(result.get(key),list) and len(result.get(key))>=1)
check(result.get('goal_alignment')=='preserved_with_operator_revalidation'); check(result.get('uncertainty')=='medium')
check(result.get('verified_change_codes')==['dependency_state_changed','test_evidence_changed'])
for key in revision.AUTHORITY_FLAGS: check(result.get(key) is revision.AUTHORITY_FLAGS[key])
for key in ('provider_contacted','commands_executed','tests_executed','workspace_materialized','project_modified','queue_modified','schedule_modified','cognition_written','source_modified','hidden_retry_created'):
    check(result.get(key) is False)
# Deterministic exact replay.
replay=prepare(rt); check(replay.get('ok')); check(replay.get('operation_status')=='replayed'); check(replay.get('revision_id')==result.get('revision_id')); check(replay.get('revision_digest')==result.get('revision_digest'))
# Paused sessions are eligible and remain paused.
rt=clone_runtime(base,'v1231-foundation-paused')
from v1231_plan_revision_fixture import _apply_transition
_apply_transition({**fixture,'runtime':rt},'pause'); paused_before=control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=False)
paused=prepare(rt,['risk_profile_changed']); paused_after=control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=False)
check(paused.get('ok')); check(paused.get('session_state_at_proposal')=='paused'); check(paused_before.get('control_digest')==paused_after.get('control_digest')); check(paused_after.get('session_state')=='paused')
# Scope expansion is proposed but not authorized.
rt=clone_runtime(base,'v1231-foundation-expansion'); expansion=prepare(rt,['scope_expansion_required'])
check(expansion.get('ok')); check(expansion.get('scope_expansion_proposed') is True); check(expansion.get('scope_expansion_authorized') is False); check('propose_scope_expansion_only' in expansion.get('proposed_scope_change_codes',[]))
# High uncertainty.
rt=clone_runtime(base,'v1231-foundation-unknown'); unknown=prepare(rt,['unknown_verified_change'])
check(unknown.get('ok')); check(unknown.get('uncertainty')=='high')
# Input and stale-state closure.
for rt,codes,ld,md,cd,status in (
    (clone_runtime(base,'v1231-foundation-bad-code'),['unsupported_change'],None,None,None,'dynamic_execution_plan_revision_change_codes_blocked'),
    (clone_runtime(base,'v1231-foundation-contradictory'),['scope_contraction_required','scope_expansion_required'],None,None,None,'dynamic_execution_plan_revision_change_codes_blocked'),
    (clone_runtime(base,'v1231-foundation-stale-launch'),['dependency_state_changed'],'0'*64,None,None,'dynamic_execution_plan_revision_stale_launch_digest'),
    (clone_runtime(base,'v1231-foundation-stale-monitor'),['dependency_state_changed'],None,'0'*64,None,'dynamic_execution_plan_revision_stale_monitor_digest'),
    (clone_runtime(base,'v1231-foundation-stale-control'),['dependency_state_changed'],None,None,'0'*64,'dynamic_execution_plan_revision_stale_control_digest'),
):
    blocked=prepare(rt,codes,ld,md,cd); check(blocked.get('ok') is False); check(blocked.get('status')==status); check(blocked.get('resume_authorized') is False); check(blocked.get('project_mutation_authorized') is False)
# Different revision cannot bypass pending review.
rt=clone_runtime(base,'v1231-foundation-pending'); first=prepare(rt,['dependency_state_changed']); check(first.get('ok'))
changed=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='risk_reported',current_stage='blocked',completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['uncertainty_high'],operator_attention_required=True,runtime_root=rt)
pending=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=changed['monitor_digest'],expected_control_digest=control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=False)['control_digest'],verified_change_codes=['risk_profile_changed'],runtime_root=rt)
check(pending.get('ok') is False); check(pending.get('status')=='dynamic_execution_plan_revision_pending_review')
# Completed monitoring state is not revisable.
rt=clone_runtime(base,'v1231-foundation-completed'); completed=monitoring.record_live_execution_progress(launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='session_completed_pending_review',current_stage='completed_pending_review',completed_units=2,total_units=2,blocker_codes=[],risk_codes=['none'],runtime_root=rt)
terminal=revision.prepare_dynamic_execution_plan_revision(launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=completed['monitor_digest'],expected_control_digest=control.inspect_execution_session_control(launch['launch_id'],runtime_root=rt,reconcile_runtime=False)['control_digest'],verified_change_codes=['unknown_verified_change'],runtime_root=rt)
check(terminal.get('ok') is False); check(terminal.get('status')=='dynamic_execution_plan_revision_terminal_monitor_state_blocked')
# Public projection is bounded and private-free.
public=revision.public_dynamic_execution_plan_revisions(runtime_root=clone_runtime(rt,'v1231-foundation-public-empty'))
check(public.get('ok')); check(public.get('content_free') is True); check(public.get('private_content_exposed') is False)
# Exact source lineage in the original base remained byte-identical.
immutable_after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (prepared_path,launch_path,monitor_path,control_path)}
check(immutable_before==immutable_after); check(before==tree_signature())
print(json.dumps({'ok':all(checks),'passed':sum(checks),'total':len(checks)},sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
