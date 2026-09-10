from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import dynamic_execution_plan_revision as revision
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
from v1228_control_fixture import build_control_fixture


def dependency_spec(*states: str, salt: str = "a") -> str:
    if not states:
        states = ("satisfied", "satisfied", "satisfied")
    names = ("source_inputs", "runtime_tool", "verification_result", "operator_gate")
    types = ("file", "tool", "test_result", "approval")
    rows = []
    for index, state in enumerate(states):
        code = names[index]
        parent = f":{names[index - 1]}" if index else ""
        digest = (f"{index + 1:x}" * 64)[:63] + salt[0].lower()
        rows.append(f"{code}:{types[index]}:{state}:{digest}{parent}")
    return ";".join(rows)


def build_dependency_fixture(seed: str = "v1232", *, accepted_revision: bool = False):
    fixture = build_control_fixture(seed)
    runtime = fixture["runtime"]
    launch = fixture["launch"]
    monitor = monitoring.record_live_execution_progress(
        launch["launch_id"],
        expected_launch_digest=launch["launch_digest"],
        event_type="blocker_reported",
        current_stage="blocked",
        completed_units=0,
        total_units=3,
        blocker_codes=["dependency_blocked"],
        risk_codes=["scope_drift", "test_coverage_gap"],
        operator_attention_required=True,
        runtime_root=runtime,
    )
    assert monitor.get("ok"), monitor
    state = control.inspect_execution_session_control(
        launch["launch_id"], runtime_root=runtime, reconcile_runtime=False
    )
    assert state.get("ok"), state
    accepted = None
    if accepted_revision:
        proposal = revision.prepare_dynamic_execution_plan_revision(
            launch["launch_id"],
            expected_launch_digest=launch["launch_digest"],
            expected_monitor_digest=monitor["monitor_digest"],
            expected_control_digest=state["control_digest"],
            verified_change_codes=["dependency_state_changed", "test_evidence_changed"],
            runtime_root=runtime,
        )
        assert proposal.get("ok"), proposal
        accepted = revision.review_dynamic_execution_plan_revision(
            proposal["revision_id"],
            expected_revision_digest=proposal["revision_digest"],
            disposition="accept",
            runtime_root=runtime,
        )
        assert accepted.get("ok"), accepted
        accepted = {"proposal": proposal, "review": accepted}
    return {**fixture, "monitor": monitor, "control": state, "accepted_revision": accepted}


def clone_runtime(runtime_root, label: str):
    parent = Path(tempfile.mkdtemp(prefix=f"eidolon-{label}-"))
    target = parent / "runtime"
    shutil.copytree(Path(runtime_root), target)
    return target
