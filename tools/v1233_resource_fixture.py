from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import dependency_aware_execution as dependency
import execution_session_authorization_bounded_launch as launching
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
import supervised_work_dispatch_execution_session_preparation as preparation
from v1232_dependency_fixture import build_dependency_fixture, dependency_spec


def resource_claim_spec(
    *,
    workspace_mode: str = "exclusive",
    workspace_units: int = 1,
    workspace_capacity: int = 1,
    workspace_state: str = "available",
    execution_units: int = 1,
    execution_capacity: int = 2,
    execution_state: str = "available",
    salt: str = "a",
    workspace_code: str = "shared_workspace",
) -> str:
    d1 = (("1" * 63) + salt[0].lower())[:64]
    d2 = (("2" * 63) + salt[0].lower())[:64]
    d3 = (("3" * 63) + salt[0].lower())[:64]
    return ";".join((
        f"execution_pool:execution_slot:shared:{execution_units}:{execution_capacity}:{execution_state}:{d1}",
        f"{workspace_code}:workspace:{workspace_mode}:{workspace_units}:{workspace_capacity}:{workspace_state}:{d2}",
        f"python_engine:python_runtime:shared:1:4:available:{d3}",
    ))


def _confirm_dependencies(launch, monitor, state, runtime, *, salt: str = "d"):
    assessment = dependency.prepare_dependency_aware_execution_assessment(
        launch["launch_id"],
        expected_launch_digest=launch["launch_digest"],
        expected_monitor_digest=monitor["monitor_digest"],
        expected_control_digest=state["control_digest"],
        expected_revision_digest="none",
        dependency_evidence=dependency_spec("satisfied", "satisfied", "satisfied", salt=salt),
        runtime_root=runtime,
    )
    assert assessment.get("ok"), assessment
    review = dependency.review_dependency_aware_execution_assessment(
        assessment["assessment_id"],
        expected_assessment_digest=assessment["assessment_digest"],
        disposition="confirm_ready",
        runtime_root=runtime,
    )
    assert review.get("ok"), review
    return assessment, review


def build_resource_fixture(seed: str = "v1233"):
    fixture = build_dependency_fixture(seed, accepted_revision=False)
    runtime = fixture["runtime"]
    launch = fixture["launch"]
    assessment, review = _confirm_dependencies(
        launch, fixture["monitor"], fixture["control"], runtime, salt="a"
    )
    return {
        **fixture,
        "dependency_assessment": assessment,
        "dependency_review": review,
    }


def add_second_session(fixture, *, dependency_ready: bool = True):
    runtime = fixture["runtime"]
    slots = list(fixture["schedule"].get("slots") or [])
    if len(slots) < 2:
        raise AssertionError("second schedule slot required")
    slot = slots[1]
    session = preparation.prepare_development_execution_session(
        slot["queue_item_id"],
        expected_schedule_digest=fixture["schedule"]["schedule_digest"],
        runtime_root=runtime,
    )
    assert session.get("ok"), session
    session_review = preparation.record_prepared_execution_session_review(
        "accept",
        session_id=session["session_id"],
        expected_session_digest=session["session_digest"],
        runtime_root=runtime,
    )
    assert session_review.get("ok"), session_review
    authorization = launching.prepare_bounded_launch_authorization(
        session["session_id"],
        expected_session_digest=session["session_digest"],
        runtime_root=runtime,
    )
    assert authorization.get("ok"), authorization
    launch = launching.launch_bounded_development_execution_session(
        authorization["authorization_id"],
        expected_authorization_digest=authorization["authorization_digest"],
        expected_session_id=session["session_id"],
        expected_session_digest=session["session_digest"],
        runtime_root=runtime,
    )
    assert launch.get("ok"), launch
    monitor = monitoring.prepare_live_execution_monitoring(
        launch["launch_id"], expected_launch_digest=launch["launch_digest"], runtime_root=runtime
    )
    assert monitor.get("ok"), monitor
    state = control.prepare_execution_session_control(
        launch["launch_id"], expected_launch_digest=launch["launch_digest"], runtime_root=runtime
    )
    assert state.get("ok"), state
    monitor = monitoring.record_live_execution_progress(
        launch["launch_id"],
        expected_launch_digest=launch["launch_digest"],
        event_type="blocker_reported",
        current_stage="blocked",
        completed_units=0,
        total_units=2,
        blocker_codes=["dependency_blocked"],
        risk_codes=["budget_pressure"],
        operator_attention_required=True,
        runtime_root=runtime,
    )
    assert monitor.get("ok"), monitor
    state = control.inspect_execution_session_control(
        launch["launch_id"], runtime_root=runtime, reconcile_runtime=False
    )
    assert state.get("ok"), state
    dep_assessment = dependency.prepare_dependency_aware_execution_assessment(
        launch["launch_id"],
        expected_launch_digest=launch["launch_digest"],
        expected_monitor_digest=monitor["monitor_digest"],
        expected_control_digest=state["control_digest"],
        expected_revision_digest="none",
        dependency_evidence=dependency_spec(
            "satisfied" if dependency_ready else "pending", "satisfied", salt="b"
        ),
        runtime_root=runtime,
    )
    assert dep_assessment.get("ok"), dep_assessment
    dep_review = dependency.review_dependency_aware_execution_assessment(
        dep_assessment["assessment_id"],
        expected_assessment_digest=dep_assessment["assessment_digest"],
        disposition="confirm_ready" if dependency_ready else "hold",
        runtime_root=runtime,
    )
    assert dep_review.get("ok"), dep_review
    return {
        "prepared_session": session,
        "prepared_session_review": session_review,
        "launch_authorization": authorization,
        "launch": launch,
        "monitor": monitor,
        "control": state,
        "dependency_assessment": dep_assessment,
        "dependency_review": dep_review,
    }


def clone_runtime(runtime_root, label: str):
    parent = Path(tempfile.mkdtemp(prefix=f"eidolon-{label}-"))
    target = parent / "runtime"
    shutil.copytree(Path(runtime_root), target)
    return target
