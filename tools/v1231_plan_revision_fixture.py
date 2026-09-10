from __future__ import annotations
import shutil, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT,ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
import dynamic_execution_plan_revision as revision
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
from v1228_control_fixture import build_control_fixture


def _apply_transition(fixture, action: str):
    runtime=fixture['runtime']; launch=fixture['launch']
    state=control.inspect_execution_session_control(launch['launch_id'],runtime_root=runtime,reconcile_runtime=False)
    if action=='pause':
        monitor=monitoring.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=runtime)
        request=monitoring.request_live_execution_intervention('pause',monitor_id=monitor['monitor_id'],expected_monitor_digest=monitor['monitor_digest'],runtime_root=runtime)
        assert request.get('ok'),request
        authorization=control.prepare_execution_session_transition_authorization(action,request_id=request['request_id'],expected_request_digest=request['request_digest'],runtime_root=runtime)
    else:
        authorization=control.prepare_execution_session_transition_authorization(action,control_id=state['control_id'],expected_control_digest=state['control_digest'],runtime_root=runtime)
    assert authorization.get('ok'),authorization
    transition=control.apply_execution_session_transition(
        authorization['authorization_id'],expected_authorization_digest=authorization['authorization_digest'],
        expected_control_id=state['control_id'],expected_control_digest=state['control_digest'],
        exact_phrase=authorization['authorize_phrase'],expected_action=action,runtime_root=runtime)
    assert transition.get('ok'),transition
    return transition


def build_plan_revision_fixture(seed='v1231', *, session_state='active', change_codes=('dependency_state_changed','test_evidence_changed')):
    fixture=build_control_fixture(seed); runtime=fixture['runtime']; launch=fixture['launch']
    monitor=monitoring.record_live_execution_progress(
        launch['launch_id'],expected_launch_digest=launch['launch_digest'],event_type='blocker_reported',current_stage='blocked',
        completed_units=0,total_units=2,blocker_codes=['dependency_blocked'],risk_codes=['scope_drift','test_coverage_gap'],
        operator_attention_required=True,runtime_root=runtime)
    assert monitor.get('ok'),monitor
    if session_state=='paused':
        _apply_transition(fixture,'pause')
        monitor=monitoring.inspect_live_execution_monitoring(launch['launch_id'],runtime_root=runtime)
        assert monitor.get('ok'),monitor
    elif session_state!='active':
        raise ValueError(session_state)
    state=control.inspect_execution_session_control(launch['launch_id'],runtime_root=runtime,reconcile_runtime=False)
    assert state.get('ok') and state.get('session_state')==session_state,state
    proposal=revision.prepare_dynamic_execution_plan_revision(
        launch['launch_id'],expected_launch_digest=launch['launch_digest'],expected_monitor_digest=monitor['monitor_digest'],
        expected_control_digest=state['control_digest'],verified_change_codes=change_codes,runtime_root=runtime)
    assert proposal.get('ok'),proposal
    return {**fixture,'monitor':monitor,'control':state,'revision':proposal}


def clone_runtime(runtime_root,label: str):
    parent=Path(tempfile.mkdtemp(prefix=f'eidolon-{label}-')); target=parent/'runtime'
    shutil.copytree(Path(runtime_root),target)
    return target
