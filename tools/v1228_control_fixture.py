from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for value in (ROOT/'conscious_agent',ROOT/'tools'):
    if str(value) not in sys.path: sys.path.insert(0,str(value))
import live_execution_monitoring_operator_intervention as monitoring
import execution_session_pause_resume_cancel_recovery as control
from v1227_monitoring_fixture import build_monitoring_fixture

def build_control_fixture(seed='v1228'):
    fixture=build_monitoring_fixture(seed)
    runtime=fixture['runtime']; launch=fixture['launch']
    monitor=monitoring.prepare_live_execution_monitoring(
        launch['launch_id'],expected_launch_digest=launch['launch_digest'],runtime_root=runtime
    )
    assert monitor.get('ok'),monitor
    state=control.prepare_execution_session_control(
        launch['launch_id'],expected_launch_digest=launch['launch_digest'],runtime_root=runtime
    )
    assert state.get('ok'),state
    return {**fixture,'monitor':monitor,'control':state}
