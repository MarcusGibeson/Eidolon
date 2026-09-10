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
import execution_session_pause_resume_cancel_recovery as control
import live_execution_monitoring_operator_intervention as monitoring
import resource_concurrency_governance as resource
from v1231_plan_revision_fixture import _apply_transition
from v1232_dependency_fixture import dependency_spec
from v1233_resource_fixture import build_resource_fixture, clone_runtime, resource_claim_spec

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
fixture = build_resource_fixture("v1233-foundations")
base = fixture["runtime"]
launch = fixture["launch"]

lineage_paths = [
    __import__("supervised_work_dispatch_execution_session_preparation")._session_path(launch["source_session_id"], base),
    __import__("execution_session_authorization_bounded_launch")._launch_path(launch["launch_id"], base),
    monitoring._monitor_path(launch["launch_id"], base),
    control._control_path(launch["launch_id"], base),
    dependency._assessment_path(fixture["dependency_assessment"]["assessment_id"], base),
    dependency._review_path(fixture["dependency_review"]["review_id"], base),
]
immutable_before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in lineage_paths}


def current(rt):
    return (
        monitoring.inspect_live_execution_monitoring(launch["launch_id"], runtime_root=rt),
        control.inspect_execution_session_control(launch["launch_id"], runtime_root=rt, reconcile_runtime=False),
    )


def prepare(rt, spec=None, *, ld=None, md=None, cd=None, da=None, dad=None, dr=None, drd=None, limit=2):
    monitor, state = current(rt)
    return resource.prepare_resource_concurrency_governance_assessment(
        launch["launch_id"],
        expected_launch_digest=ld or launch["launch_digest"],
        expected_monitor_digest=md or monitor.get("monitor_digest", "0" * 64),
        expected_control_digest=cd or state.get("control_digest", "0" * 64),
        dependency_assessment_id=da or fixture["dependency_assessment"]["assessment_id"],
        expected_dependency_assessment_digest=dad or fixture["dependency_assessment"]["assessment_digest"],
        dependency_review_id=dr or fixture["dependency_review"]["review_id"],
        expected_dependency_review_digest=drd or fixture["dependency_review"]["review_digest"],
        concurrency_limit=limit,
        resource_claims=resource_claim_spec() if spec is None else spec,
        runtime_root=rt,
    )


# Exact ready assessment and immutable lineage.
rt = clone_runtime(base, "v1233-foundation-ready")
result = prepare(rt)
check(result.get("ok"))
check(result.get("status") == "resource_concurrency_governance_assessment_ready_for_operator_review")
check(result.get("admission_state") == "admissible_pending_operator_review")
check(result.get("admission_confirmable") is True)
check(result.get("dependency_readiness_confirmed") is True)
check(result.get("resource_claim_count") == 3)
check(result.get("active_confirmed_admission_count") == 0)
check(result.get("prospective_concurrency") == 1)
check(result.get("concurrency_limit") == 2)
check(result.get("concurrency_limit_exceeded") is False)
check(result.get("exclusive_conflict_count") == 0)
check(result.get("capacity_conflict_count") == 0)
check(result.get("stale_existing_claim_conflict_count") == 0)
check(result.get("preemption_proposal_eligible") is False)
check(result.get("starvation_risk_detected") is False)
check(result.get("priority_rank") == fixture["prepared_session"].get("priority_rank"))
check(result.get("source_schedule_digest") == fixture["prepared_session"].get("source_schedule_digest"))
check(result.get("source_queue_digest") == fixture["prepared_session"].get("source_queue_digest"))
check(result.get("dependency_assessment_id") == fixture["dependency_assessment"]["assessment_id"])
check(result.get("dependency_review_id") == fixture["dependency_review"]["review_id"])
check(result.get("session_state_at_assessment") == "active")
check(result.get("safe_boundary_pause_recommended") is False)
check(result.get("fresh_resume_review_eligible") is False)
check(result.get("resource_lease_created") is False)
check(result.get("preemption_performed") is False)
check(all("shared_workspace" not in json.dumps(row) for row in result.get("resource_claims") or []))
check(all(str(row.get("resource_reference", "")).startswith("resource_") for row in result.get("resource_claims") or []))
for key, expected in resource.AUTHORITY_FLAGS.items():
    check(result.get(key) is expected)
for key in (
    "provider_contacted", "commands_executed", "tests_executed", "workspace_materialized",
    "project_modified", "queue_modified", "schedule_modified", "session_preempted",
    "resource_lease_created", "cognition_written", "source_modified", "hidden_retry_created",
):
    check(result.get(key) is False)

# Deterministic replay while review is pending.
replay = prepare(rt)
check(replay.get("ok"))
check(replay.get("operation_status") == "replayed")
check(replay.get("assessment_id") == result.get("assessment_id"))
check(replay.get("assessment_digest") == result.get("assessment_digest"))

# Resource-state outcomes are deterministic and non-executing.
for index, (state_name, expected_state) in enumerate((
    ("unavailable", "blocked_resource_unavailable"),
    ("stale", "blocked_resource_stale"),
    ("contradictory", "blocked_resource_contradictory"),
    ("unknown", "blocked_resource_unknown"),
)):
    case_rt = clone_runtime(base, f"v1233-foundation-{state_name}")
    case = prepare(case_rt, resource_claim_spec(workspace_state=state_name, salt=f"{index + 2:x}"))
    check(case.get("ok"))
    check(case.get("admission_state") == expected_state)
    check(case.get("admission_confirmable") is False)
    check(case.get("safe_boundary_pause_recommended") is True)
    check(case.get("operator_intervention_required") is True)
    check(case.get("pause_authorized") is False)

# Degraded but available evidence remains reviewable rather than silently rejected.
degraded_rt = clone_runtime(base, "v1233-foundation-degraded")
degraded = prepare(degraded_rt, resource_claim_spec(workspace_state="degraded", salt="d"))
check(degraded.get("ok"))
check(degraded.get("admission_state") == "admissible_pending_operator_review")
check(degraded.get("resource_state_counts", {}).get("degraded") == 1)

# Paused sessions require fresh dependency lineage and remain paused.
paused_rt = clone_runtime(base, "v1233-foundation-paused")
_apply_transition({**fixture, "runtime": paused_rt}, "pause")
paused_monitor = monitoring.inspect_live_execution_monitoring(launch["launch_id"], runtime_root=paused_rt)
paused_control = control.inspect_execution_session_control(launch["launch_id"], runtime_root=paused_rt, reconcile_runtime=False)
paused_dep = dependency.prepare_dependency_aware_execution_assessment(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    expected_monitor_digest=paused_monitor["monitor_digest"], expected_control_digest=paused_control["control_digest"],
    expected_revision_digest="none", dependency_evidence=dependency_spec("satisfied", "satisfied", salt="e"),
    runtime_root=paused_rt,
)
check(paused_dep.get("ok"))
paused_dep_review = dependency.review_dependency_aware_execution_assessment(
    paused_dep["assessment_id"], expected_assessment_digest=paused_dep["assessment_digest"],
    disposition="confirm_ready", runtime_root=paused_rt,
)
check(paused_dep_review.get("ok"))
paused = resource.prepare_resource_concurrency_governance_assessment(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    expected_monitor_digest=paused_monitor["monitor_digest"], expected_control_digest=paused_control["control_digest"],
    dependency_assessment_id=paused_dep["assessment_id"], expected_dependency_assessment_digest=paused_dep["assessment_digest"],
    dependency_review_id=paused_dep_review["review_id"], expected_dependency_review_digest=paused_dep_review["review_digest"],
    concurrency_limit=2, resource_claims=resource_claim_spec(salt="e"), runtime_root=paused_rt,
)
paused_after = control.inspect_execution_session_control(launch["launch_id"], runtime_root=paused_rt, reconcile_runtime=False)
check(paused.get("ok"))
check(paused.get("session_state_at_assessment") == "paused")
check(paused.get("fresh_resume_review_eligible") is True)
check(paused.get("resume_authorized") is False)
check(paused_after.get("session_state") == "paused")
check(paused_after.get("control_digest") == paused_control.get("control_digest"))

# Input and stale-lineage closure.
invalid_specs = (
    ("", "resource_claims_required"),
    (f"one:unsupported:shared:1:1:available:{'1'*64}", "unsupported_resource_type"),
    (f"one:workspace:unsupported:1:1:available:{'1'*64}", "unsupported_claim_mode"),
    (f"one:workspace:shared:0:1:available:{'1'*64}", "invalid_requested_units"),
    (f"one:workspace:shared:1:0:available:{'1'*64}", "invalid_available_capacity"),
    (f"one:workspace:shared:1:1:unsupported:{'1'*64}", "unsupported_resource_state"),
    ("one:workspace:shared:1:1:available:notadigest", "invalid_resource_evidence_digest"),
    (f"dup:workspace:shared:1:1:available:{'1'*64};dup:workspace:exclusive:1:1:available:{'2'*64}", "duplicate_resource_reference"),
)
for index, (spec, reason) in enumerate(invalid_specs):
    blocked = prepare(clone_runtime(base, f"v1233-invalid-{index}"), spec)
    check(blocked.get("ok") is False)
    check(blocked.get("status") == "resource_concurrency_governance_evidence_blocked")
    check(reason in blocked.get("reason", ""))

for label, kwargs, expected_status in (
    ("launch", {"ld": "0" * 64}, "resource_concurrency_governance_stale_launch_digest"),
    ("monitor", {"md": "0" * 64}, "resource_concurrency_governance_stale_monitor_digest"),
    ("control", {"cd": "0" * 64}, "resource_concurrency_governance_stale_control_digest"),
):
    blocked = prepare(clone_runtime(base, f"v1233-stale-{label}"), **kwargs)
    check(blocked.get("ok") is False)
    check(blocked.get("status") == expected_status)

for label, kwargs, reason in (
    ("dependency-assessment", {"dad": "0" * 64}, "stale_dependency_assessment_digest"),
    ("dependency-review", {"drd": "0" * 64}, "stale_dependency_review_digest"),
):
    blocked = prepare(clone_runtime(base, f"v1233-stale-{label}"), **kwargs)
    check(blocked.get("ok") is False)
    check(blocked.get("status") == "resource_concurrency_governance_dependency_lineage_blocked")
    check(reason in blocked.get("reason", ""))

bad_limit = prepare(clone_runtime(base, "v1233-invalid-limit"), limit=0)
check(bad_limit.get("ok") is False)
check("invalid_concurrency_limit" in bad_limit.get("reason", ""))

# Preparation never rewrites retained lineage.
immutable_after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in lineage_paths}
check(immutable_before == immutable_after)
check(before == tree_signature())

print(json.dumps({"ok": all(checks), "passed": sum(checks), "total": len(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
