from __future__ import annotations
import shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
import live_execution_monitoring_operator_intervention as monitoring
import execution_session_pause_resume_cancel_recovery as control
from v1228_control_fixture import build_control_fixture


def _apply_direct(fixture, action):
    state=control.inspect_execution_session_control(fixture['launch']['launch_id'],runtime_root=fixture['runtime'])
    auth=control.prepare_execution_session_transition_authorization(
        action,control_id=state['control_id'],expected_control_digest=state['control_digest'],runtime_root=fixture['runtime']
    )
    assert auth.get('ok'),auth
    transition=control.apply_execution_session_transition(
        auth['authorization_id'],expected_authorization_digest=auth['authorization_digest'],
        expected_control_id=state['control_id'],expected_control_digest=state['control_digest'],
        exact_phrase=auth['authorize_phrase'],expected_action=action,runtime_root=fixture['runtime']
    )
    assert transition.get('ok'),transition
    return transition


def build_outcome_fixture(seed='v1229',mode='completed'):
    fixture=build_control_fixture(seed)
    runtime=fixture['runtime']; launch=fixture['launch']; launch_id=launch['launch_id']
    if mode=='completed':
        monitor=monitoring.record_live_execution_progress(
            launch_id,expected_launch_digest=launch['launch_digest'],event_type='session_completed_pending_review',
            current_stage='completed_pending_review',completed_units=4,total_units=4,blocker_codes=[],risk_codes=['none'],runtime_root=runtime
        )
        assert monitor.get('ok'),monitor
    elif mode=='failed':
        monitor=monitoring.record_live_execution_progress(
            launch_id,expected_launch_digest=launch['launch_digest'],event_type='blocker_reported',
            current_stage='blocked',completed_units=2,total_units=4,blocker_codes=['dependency_blocked'],
            risk_codes=['uncertainty_high'],operator_attention_required=True,runtime_root=runtime
        )
        assert monitor.get('ok'),monitor
    elif mode=='cancelled' or mode=='abandoned':
        _apply_direct(fixture,'cancel')
    elif mode=='paused':
        _apply_direct(fixture,'pause')
    elif mode=='recovered':
        shutil.rmtree(control._runtime_namespace_path(launch_id,runtime),ignore_errors=True)
        required=control.inspect_execution_session_control(launch_id,runtime_root=runtime,reconcile_runtime=True)
        assert required.get('session_state')=='recovery_required',required
        _apply_direct(fixture,'recover')
    elif mode=='inconclusive':
        pass
    else:
        raise ValueError(mode)
    fixture['monitor']=monitoring.inspect_live_execution_monitoring(launch_id,runtime_root=runtime)
    if fixture['monitor'].get('ok') is not True:
        fixture['monitor']=monitoring.load_live_execution_monitoring(launch_id,runtime_root=runtime)
    fixture['control']=control.inspect_execution_session_control(launch_id,runtime_root=runtime,reconcile_runtime=False)
    return fixture
