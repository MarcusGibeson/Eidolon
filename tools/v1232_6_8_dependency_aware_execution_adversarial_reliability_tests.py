from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for value in (ROOT, ROOT / "conscious_agent", ROOT / "tools"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import dependency_aware_execution as dependency
import dynamic_execution_plan_revision as revision
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
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
fixture = build_dependency_fixture("v1232-reliability", accepted_revision=True)
launch = fixture["launch"]
accepted = fixture["accepted_revision"]["proposal"]
base = fixture["runtime"]
names = (
    "restart", "generation", "pending", "stale_monitor", "stale_control", "tamper_assessment",
    "tamper_review", "completed", "cancelled", "recovered", "revision_drift", "cycle", "privacy",
)
runtimes = {name: clone_runtime(base, f"v1232-reliability-{name}") for name in names}


def state(rt):
    return control.inspect_execution_session_control(launch["launch_id"], runtime_root=rt, reconcile_runtime=False)


def monitor(rt):
    return monitoring.inspect_live_execution_monitoring(launch["launch_id"], runtime_root=rt)


def prepare(rt, spec=None, *, revision_digest=None, monitor_digest=None, control_digest=None):
    current_monitor = monitor(rt)
    current_control = state(rt)
    return dependency.prepare_dependency_aware_execution_assessment(
        launch["launch_id"],
        expected_launch_digest=launch["launch_digest"],
        expected_monitor_digest=monitor_digest or current_monitor.get("monitor_digest", "0" * 64),
        expected_control_digest=control_digest or current_control.get("control_digest", "0" * 64),
        expected_revision_digest=revision_digest if revision_digest is not None else accepted["revision_digest"],
        dependency_evidence=spec if spec is not None else dependency_spec("satisfied", "satisfied", "satisfied", salt="1"),
        runtime_root=rt,
    )


# Restart continuity and deterministic replay preserve exact bytes.
rt = runtimes["restart"]
assessment = prepare(rt)
check(assessment.get("ok"))
path = dependency._assessment_path(assessment["assessment_id"], rt)
original_bytes = path.read_bytes()
dependency = importlib.reload(dependency)
loaded = dependency.inspect_dependency_aware_execution_assessment(assessment["assessment_id"], runtime_root=rt)
check(loaded.get("ok"))
check(loaded.get("assessment_digest") == assessment.get("assessment_digest"))
replay = prepare(rt)
check(replay.get("operation_status") == "replayed")
check(replay.get("assessment_id") == assessment.get("assessment_id"))
check(path.read_bytes() == original_bytes)

# A reviewed assessment requires fresh evidence; changed monitor evidence permits append-only generation two.
rt = runtimes["generation"]
first = prepare(rt, dependency_spec("satisfied", "pending", salt="2"))
check(first.get("ok"))
first_path = dependency._assessment_path(first["assessment_id"], rt)
first_bytes = first_path.read_bytes()
held = dependency.review_dependency_aware_execution_assessment(
    first["assessment_id"], expected_assessment_digest=first["assessment_digest"], disposition="hold", runtime_root=rt
)
check(held.get("ok"))
same = prepare(rt, dependency_spec("satisfied", "pending", salt="2"))
check(same.get("ok") is False)
check(same.get("status") == "dependency_aware_execution_fresh_evidence_required")
changed_monitor = monitoring.record_live_execution_progress(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"], event_type="risk_reported",
    current_stage="blocked", completed_units=0, total_units=3, blocker_codes=["dependency_blocked"],
    risk_codes=["uncertainty_high", "operator_attention"], operator_attention_required=True, runtime_root=rt,
)
second = dependency.prepare_dependency_aware_execution_assessment(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    expected_monitor_digest=changed_monitor["monitor_digest"], expected_control_digest=state(rt)["control_digest"],
    expected_revision_digest=accepted["revision_digest"],
    dependency_evidence=dependency_spec("satisfied", "satisfied", "satisfied", salt="3"), runtime_root=rt,
)
check(second.get("ok"))
check(second.get("generation") == 2)
check(second.get("previous_assessment_id") == first.get("assessment_id"))
check(second.get("previous_assessment_digest") == first.get("assessment_digest"))
check(second.get("readiness_state") == "ready_pending_operator_review")
check(first_path.read_bytes() == first_bytes)

# A pending assessment blocks a different hidden replacement.
rt = runtimes["pending"]
pending = prepare(rt, dependency_spec("satisfied", "pending", salt="4"))
check(pending.get("ok"))
replacement = prepare(rt, dependency_spec("satisfied", "failed", salt="5"))
check(replacement.get("ok") is False)
check(replacement.get("status") == "dependency_aware_execution_pending_review")
check(replacement.get("hidden_retry_created") is False)

# Stale monitor and control evidence fail closed after state changes.
rt = runtimes["stale_monitor"]
old_monitor = monitor(rt)
changed = monitoring.record_live_execution_progress(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"], event_type="risk_reported",
    current_stage="blocked", completed_units=0, total_units=3, blocker_codes=["dependency_blocked"],
    risk_codes=["uncertainty_high"], operator_attention_required=True, runtime_root=rt,
)
stale = prepare(rt, monitor_digest=old_monitor["monitor_digest"])
check(changed.get("ok"))
check(stale.get("ok") is False)
check(stale.get("status") == "dependency_aware_execution_stale_monitor_digest")
rt = runtimes["stale_control"]
old_control = state(rt)
_apply_transition({**fixture, "runtime": rt}, "pause")
stale = prepare(rt, control_digest=old_control["control_digest"])
check(stale.get("ok") is False)
check(stale.get("status") == "dependency_aware_execution_stale_control_digest")
check(state(rt).get("session_state") == "paused")

# Tampered assessments cannot be inspected, reviewed, or used as history.
rt = runtimes["tamper_assessment"]
tampered = prepare(rt)
path = dependency._assessment_path(tampered["assessment_id"], rt)
stored = json.loads(path.read_text())
stored["readiness_confirmable"] = True
stored["resume_authorized"] = True
path.write_text(json.dumps(stored, sort_keys=True))
inspect = dependency.inspect_dependency_aware_execution_assessment(tampered["assessment_id"], runtime_root=rt)
check(inspect.get("ok") is False)
check(inspect.get("status") == "dependency_aware_execution_assessment_integrity_blocked")
review_blocked = dependency.review_dependency_aware_execution_assessment(
    tampered["assessment_id"], expected_assessment_digest=tampered["assessment_digest"], disposition="confirm_ready", runtime_root=rt
)
check(review_blocked.get("ok") is False)
check(review_blocked.get("resume_authorized") is False)
listed = dependency.public_dependency_aware_execution_assessments(runtime_root=rt)
check(listed.get("ok") is False)
check(listed.get("status") == "dependency_aware_execution_assessment_list_blocked")

# Tampered review evidence blocks the review inventory.
rt = runtimes["tamper_review"]
ready = prepare(rt)
confirmed = dependency.review_dependency_aware_execution_assessment(
    ready["assessment_id"], expected_assessment_digest=ready["assessment_digest"], disposition="confirm_ready", runtime_root=rt
)
review_path = dependency._review_path(confirmed["review_id"], rt)
stored = json.loads(review_path.read_text())
stored["execution_session_launch_authorized"] = True
review_path.write_text(json.dumps(stored, sort_keys=True))
review_list = dependency.public_dependency_aware_execution_reviews(runtime_root=rt)
check(review_list.get("ok") is False)
check(review_list.get("status") == "dependency_aware_execution_review_list_blocked")

# Terminal and cancelled sessions cannot prepare readiness evidence.
rt = runtimes["completed"]
completed = monitoring.record_live_execution_progress(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"], event_type="session_completed_pending_review",
    current_stage="completed_pending_review", completed_units=3, total_units=3, blocker_codes=[], risk_codes=["none"], runtime_root=rt,
)
terminal = dependency.prepare_dependency_aware_execution_assessment(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    expected_monitor_digest=completed["monitor_digest"], expected_control_digest=state(rt)["control_digest"],
    expected_revision_digest=accepted["revision_digest"], dependency_evidence=dependency_spec("satisfied", salt="6"), runtime_root=rt,
)
check(terminal.get("ok") is False)
check(terminal.get("status") == "dependency_aware_execution_terminal_monitor_state_blocked")
check(terminal.get("execution_session_launch_authorized") is False)
rt = runtimes["cancelled"]
cancel_monitor = monitor(rt)
_apply_transition({**fixture, "runtime": rt}, "cancel")
cancelled_state = state(rt)
cancelled = dependency.prepare_dependency_aware_execution_assessment(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    expected_monitor_digest=cancel_monitor["monitor_digest"],
    expected_control_digest=cancelled_state.get("control_digest", "0" * 64),
    expected_revision_digest=accepted["revision_digest"], dependency_evidence=dependency_spec("satisfied", salt="7"), runtime_root=rt,
)
check(cancelled.get("ok") is False)
check(cancelled.get("status") in {
    "dependency_aware_execution_launch_evidence_unavailable",
    "dependency_aware_execution_control_evidence_unavailable",
    "dependency_aware_execution_session_state_blocked",
})
check(cancelled.get("resume_authorized") is False)
check(cancelled.get("project_mutation_authorized") is False)

# Crash recovery returns to paused; readiness remains evidence only.
rt = runtimes["recovered"]
shutil.rmtree(control._runtime_namespace_path(launch["launch_id"], rt), ignore_errors=True)
required = control.inspect_execution_session_control(launch["launch_id"], runtime_root=rt, reconcile_runtime=True)
check(required.get("session_state") == "recovery_required")
_apply_transition({**fixture, "runtime": rt}, "recover")
recovered = prepare(rt)
check(recovered.get("ok"))
check(recovered.get("session_state_at_assessment") == "paused")
check(recovered.get("fresh_resume_review_eligible") is True)
confirmed = dependency.review_dependency_aware_execution_assessment(
    recovered["assessment_id"], expected_assessment_digest=recovered["assessment_digest"], disposition="confirm_ready", runtime_root=rt
)
check(confirmed.get("ok"))
check(confirmed.get("resume_authorized") is False)
check(state(rt).get("session_state") == "paused")

# A later accepted v1231 revision invalidates the earlier dependency assessment review lineage.
rt = runtimes["revision_drift"]
old = prepare(rt)
changed_monitor = monitoring.record_live_execution_progress(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"], event_type="risk_reported",
    current_stage="blocked", completed_units=0, total_units=3, blocker_codes=["dependency_blocked"],
    risk_codes=["scope_drift", "uncertainty_high"], operator_attention_required=True, runtime_root=rt,
)
new_revision = revision.prepare_dynamic_execution_plan_revision(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    expected_monitor_digest=changed_monitor["monitor_digest"], expected_control_digest=state(rt)["control_digest"],
    verified_change_codes=["risk_profile_changed", "environment_capability_changed"], runtime_root=rt,
)
check(new_revision.get("ok"))
new_review = revision.review_dynamic_execution_plan_revision(
    new_revision["revision_id"], expected_revision_digest=new_revision["revision_digest"], disposition="accept", runtime_root=rt,
)
check(new_review.get("ok"))
old_review = dependency.review_dependency_aware_execution_assessment(
    old["assessment_id"], expected_assessment_digest=old["assessment_digest"], disposition="confirm_ready", runtime_root=rt,
)
check(old_review.get("ok") is False)
check(old_review.get("status") in {
    "dependency_aware_execution_review_monitor_lineage_blocked",
    "dependency_aware_execution_review_plan_revision_lineage_blocked",
})
stale_revision = dependency.prepare_dependency_aware_execution_assessment(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    expected_monitor_digest=changed_monitor["monitor_digest"], expected_control_digest=state(rt)["control_digest"],
    expected_revision_digest=accepted["revision_digest"], dependency_evidence=dependency_spec("satisfied", salt="8"), runtime_root=rt,
)
check(stale_revision.get("ok") is False)
check(stale_revision.get("status") == "dependency_aware_execution_stale_revision_digest")

# Cycles and contradictory evidence remain visible but never self-resolve or authorize retries.
rt = runtimes["cycle"]
cycle_spec = f"alpha:task:satisfied:{'a'*64}:beta;beta:task:contradictory:{'b'*64}:alpha"
cycle = prepare(rt, cycle_spec)
check(cycle.get("ok"))
check(cycle.get("readiness_state") == "blocked_cycle")
check(cycle.get("dependency_cycle_detected") is True)
check(cycle.get("readiness_confirmable") is False)
check(cycle.get("hidden_retry_created") is False)
blocked_confirm = dependency.review_dependency_aware_execution_assessment(
    cycle["assessment_id"], expected_assessment_digest=cycle["assessment_digest"], disposition="confirm_ready", runtime_root=rt,
)
check(blocked_confirm.get("ok") is False)
check(blocked_confirm.get("status") == "dependency_aware_execution_readiness_confirmation_blocked")

# Public evidence suppresses raw dependency codes, paths, and private content.
rt = runtimes["privacy"]
privacy_assessment = prepare(rt, dependency_spec("satisfied", "pending", salt="9"))
dependency.review_dependency_aware_execution_assessment(
    privacy_assessment["assessment_id"], expected_assessment_digest=privacy_assessment["assessment_digest"], disposition="hold", runtime_root=rt,
)
public = dependency.public_dependency_aware_execution_assessments(runtime_root=rt)
reviews = dependency.public_dependency_aware_execution_reviews(runtime_root=rt)
encoded = json.dumps({"assessments": public, "reviews": reviews}, sort_keys=True)
check(public.get("ok"))
check(reviews.get("ok"))
check(str(rt) not in encoded)
check("source_inputs" not in encoded)
check("runtime_tool" not in encoded)
check("private request" not in encoded.lower())
for key in (
    "private_request_exposed", "private_path_exposed", "private_content_exposed",
    "raw_provider_output_exposed", "raw_test_output_exposed",
):
    check(public.get(key) is False)
    check(reviews.get(key) is False)
for key in (
    "execution_session_launch_authorized", "provider_execution_authorized", "command_execution_authorized",
    "test_execution_authorized", "workspace_materialization_authorized", "project_mutation_authorized",
    "queue_mutation_authorized", "schedule_mutation_authorized", "resume_authorized",
    "background_execution_authorized", "cognition_write_authorized", "old_authority_reusable",
):
    check(public.get(key) is False)
    check(reviews.get(key) is False)

check(before == tree_signature())
print(json.dumps({"ok": all(checks), "passed": sum(checks), "total": len(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
