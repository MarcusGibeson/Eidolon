from __future__ import annotations

import hashlib
import json
import sys
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
from v1231_plan_revision_fixture import _apply_transition
from v1232_dependency_fixture import build_dependency_fixture, clone_runtime, dependency_spec

checks: list[bool] = []

def check(value):
    checks.append(bool(value))


def tree_signature():
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
            rows.append(f"{path.relative_to(ROOT).as_posix()}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest(), len(rows)


before = tree_signature()
fixture = build_dependency_fixture("v1232-foundations", accepted_revision=True)
launch = fixture["launch"]
base = fixture["runtime"]
accepted = fixture["accepted_revision"]["proposal"]

prepared_path = preparation._session_path(launch["source_session_id"], base)
launch_path = launching._launch_path(launch["launch_id"], base)
monitor_path = monitoring._monitor_path(launch["launch_id"], base)
control_path = control._control_path(launch["launch_id"], base)
revision_path = __import__("dynamic_execution_plan_revision")._proposal_path(accepted["revision_id"], base)
immutable_before = {
    str(path): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (prepared_path, launch_path, monitor_path, control_path, revision_path)
}


def state(rt):
    return control.inspect_execution_session_control(launch["launch_id"], runtime_root=rt, reconcile_runtime=False)


def monitor(rt):
    return monitoring.inspect_live_execution_monitoring(launch["launch_id"], runtime_root=rt)


def prepare(rt, spec=None, *, ld=None, md=None, cd=None, rd=None):
    current_monitor = monitor(rt)
    current_control = state(rt)
    return dependency.prepare_dependency_aware_execution_assessment(
        launch["launch_id"],
        expected_launch_digest=ld or launch["launch_digest"],
        expected_monitor_digest=md or current_monitor.get("monitor_digest", "0" * 64),
        expected_control_digest=cd or current_control.get("control_digest", "0" * 64),
        expected_revision_digest=rd if rd is not None else accepted["revision_digest"],
        dependency_evidence=dependency_spec("satisfied", "satisfied", "satisfied", salt="a") if spec is None else spec,
        runtime_root=rt,
    )


# Exact satisfied dependency graph and accepted v1231 revision binding.
rt = clone_runtime(base, "v1232-foundation-ready")
result = prepare(rt)
check(result.get("ok"))
check(result.get("status") == "dependency_aware_execution_assessment_ready_for_operator_review")
check(result.get("readiness_state") == "ready_pending_operator_review")
check(result.get("readiness_confirmable") is True)
check(result.get("all_required_dependencies_satisfied") is True)
check(result.get("dependency_count") == 3)
check(result.get("satisfied_dependency_count") == 3)
check(result.get("unresolved_dependency_count") == 0)
check(result.get("blocking_dependency_count") == 0)
check(result.get("dependency_cycle_detected") is False)
check(result.get("plan_basis") == "accepted_dynamic_plan_revision")
check(result.get("accepted_revision_id") == accepted.get("revision_id"))
check(result.get("accepted_revision_digest") == accepted.get("revision_digest"))
check(result.get("accepted_revision_generation") == accepted.get("generation"))
check(result.get("revision_dependency_change_count") >= 1)
check(result.get("original_plan_digest") == launch.get("source_session_digest"))
check(result.get("session_state_at_assessment") == "active")
check(result.get("safe_boundary_pause_recommended") is False)
check(result.get("operator_intervention_required") is False)
check(result.get("fresh_resume_review_eligible") is False)
check(result.get("readiness_confirmation_granted") is False)
check(len(result.get("dependencies") or []) == 3)
check(all("code" not in row for row in result.get("dependencies") or []))
check(all(str(row.get("dependency_reference", "")).startswith("dependency_") for row in result.get("dependencies") or []))
check(all(len(str(row.get("evidence_digest") or "")) == 64 for row in result.get("dependencies") or []))
for key, expected in dependency.AUTHORITY_FLAGS.items():
    check(result.get(key) is expected)
for key in (
    "provider_contacted", "commands_executed", "tests_executed", "workspace_materialized",
    "project_modified", "queue_modified", "schedule_modified", "cognition_written",
    "source_modified", "hidden_retry_created",
):
    check(result.get(key) is False)

# Deterministic replay before review.
replay = prepare(rt)
check(replay.get("ok"))
check(replay.get("operation_status") == "replayed")
check(replay.get("assessment_id") == result.get("assessment_id"))
check(replay.get("assessment_digest") == result.get("assessment_digest"))

# Original plan basis without any v1231 revision.
plain = build_dependency_fixture("v1232-foundation-original", accepted_revision=False)
plain_launch = plain["launch"]
plain_rt = plain["runtime"]
plain_result = dependency.prepare_dependency_aware_execution_assessment(
    plain_launch["launch_id"],
    expected_launch_digest=plain_launch["launch_digest"],
    expected_monitor_digest=plain["monitor"]["monitor_digest"],
    expected_control_digest=plain["control"]["control_digest"],
    expected_revision_digest="none",
    dependency_evidence=dependency_spec("satisfied", "satisfied", salt="b"),
    runtime_root=plain_rt,
)
check(plain_result.get("ok"))
check(plain_result.get("plan_basis") == "original_approved_plan")
check(plain_result.get("accepted_revision_id") == "")
check(plain_result.get("accepted_revision_digest") == "")

# Deterministic readiness states and safe-boundary behavior.
state_cases = (
    (("satisfied", "pending"), "blocked_pending"),
    (("satisfied", "blocked"), "blocked_dependency"),
    (("satisfied", "failed"), "blocked_failed"),
    (("satisfied", "stale"), "blocked_stale"),
    (("satisfied", "contradictory"), "blocked_contradictory"),
    (("satisfied", "unknown"), "blocked_unknown"),
)
for index, (states, expected_state) in enumerate(state_cases):
    case_rt = clone_runtime(base, f"v1232-foundation-{expected_state}")
    case = prepare(case_rt, dependency_spec(*states, salt=f"{index + 2:x}"))
    check(case.get("ok"))
    check(case.get("readiness_state") == expected_state)
    check(case.get("readiness_confirmable") is False)
    check(case.get("all_required_dependencies_satisfied") is False)
    check(case.get("unresolved_dependency_count") >= 1)
    check(case.get("blocking_dependency_count") >= 1)
    check(case.get("safe_boundary_pause_recommended") is True)
    check(case.get("operator_intervention_required") is True)
    check(case.get("pause_authorized") is False)

# A graph cycle is visible evidence, not an authorization or hidden retry.
cycle_rt = clone_runtime(base, "v1232-foundation-cycle")
cycle_spec = f"first:task:satisfied:{'a'*64}:second;second:task:satisfied:{'b'*64}:first"
cycle = prepare(cycle_rt, cycle_spec)
check(cycle.get("ok"))
check(cycle.get("readiness_state") == "blocked_cycle")
check(cycle.get("dependency_cycle_detected") is True)
check(cycle.get("readiness_confirmable") is False)
check(cycle.get("hidden_retry_created") is False)

# Paused sessions can be assessed but never resumed by readiness.
paused_rt = clone_runtime(base, "v1232-foundation-paused")
_apply_transition({**fixture, "runtime": paused_rt}, "pause")
paused_before = state(paused_rt)
paused = prepare(paused_rt, dependency_spec("satisfied", "satisfied", salt="c"))
paused_after = state(paused_rt)
check(paused.get("ok"))
check(paused.get("session_state_at_assessment") == "paused")
check(paused.get("fresh_resume_review_eligible") is True)
check(paused.get("resume_authorized") is False)
check(paused_before.get("control_digest") == paused_after.get("control_digest"))
check(paused_after.get("session_state") == "paused")

# Input and stale lineage closure.
invalid_cases = (
    (f"dup:file:satisfied:{'1'*64};dup:tool:satisfied:{'2'*64}", "duplicate_dependency_code"),
    (f"one:file:satisfied:{'1'*64}:missing", "unknown_dependency_parent"),
    (f"one:unsupported:satisfied:{'1'*64}", "unsupported_dependency_type"),
    (f"one:file:unsupported:{'1'*64}", "unsupported_dependency_state"),
    ("one:file:satisfied:notadigest", "invalid_dependency_evidence_digest"),
    ("", "dependency_evidence_required"),
)
for index, (spec, reason) in enumerate(invalid_cases):
    blocked = prepare(clone_runtime(base, f"v1232-invalid-{index}"), spec)
    check(blocked.get("ok") is False)
    check(blocked.get("status") == "dependency_aware_execution_evidence_blocked")
    check(reason in blocked.get("reason", ""))

for label, kwargs, expected_status in (
    ("launch", {"ld": "0" * 64}, "dependency_aware_execution_stale_launch_digest"),
    ("monitor", {"md": "0" * 64}, "dependency_aware_execution_stale_monitor_digest"),
    ("control", {"cd": "0" * 64}, "dependency_aware_execution_stale_control_digest"),
    ("revision", {"rd": "0" * 64}, "dependency_aware_execution_stale_revision_digest"),
):
    blocked = prepare(clone_runtime(base, f"v1232-stale-{label}"), **kwargs)
    check(blocked.get("ok") is False)
    check(blocked.get("status") == expected_status)

# Preparation does not rewrite any retained lineage.
immutable_after = {
    str(path): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (prepared_path, launch_path, monitor_path, control_path, revision_path)
}
check(immutable_before == immutable_after)
check(before == tree_signature())

print(json.dumps({"ok": all(checks), "passed": sum(checks), "total": len(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
