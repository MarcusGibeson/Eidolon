from __future__ import annotations

import hashlib
import json
import os
import sys
import time
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
from v1233_resource_fixture import add_second_session, build_resource_fixture, clone_runtime, resource_claim_spec

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
fixture = build_resource_fixture("v1233-reliability")
base = fixture["runtime"]
launch = fixture["launch"]


def inspect_state(rt, session_fixture):
    return control.inspect_execution_session_control(
        session_fixture["launch"]["launch_id"], runtime_root=rt, reconcile_runtime=False
    )


def inspect_monitor(rt, session_fixture):
    return monitoring.inspect_live_execution_monitoring(
        session_fixture["launch"]["launch_id"], runtime_root=rt
    )


def assess(rt, session_fixture, spec, *, limit=2, da=None, dad=None, dr=None, drd=None, ld=None, md=None, cd=None):
    current_launch = session_fixture["launch"]
    current_monitor = inspect_monitor(rt, session_fixture)
    current_control = inspect_state(rt, session_fixture)
    dep_assessment = session_fixture["dependency_assessment"]
    dep_review = session_fixture["dependency_review"]
    return resource.prepare_resource_concurrency_governance_assessment(
        current_launch["launch_id"],
        expected_launch_digest=ld or current_launch["launch_digest"],
        expected_monitor_digest=md or current_monitor.get("monitor_digest", "0" * 64),
        expected_control_digest=cd or current_control.get("control_digest", "0" * 64),
        dependency_assessment_id=da or dep_assessment["assessment_id"],
        expected_dependency_assessment_digest=dad or dep_assessment["assessment_digest"],
        dependency_review_id=dr or dep_review["review_id"],
        expected_dependency_review_digest=drd or dep_review["review_digest"],
        concurrency_limit=limit,
        resource_claims=spec,
        runtime_root=rt,
    )


def confirm(rt, assessment):
    return resource.review_resource_concurrency_governance_assessment(
        assessment["assessment_id"], expected_assessment_digest=assessment["assessment_digest"],
        disposition="confirm_admissible", runtime_root=rt,
    )


# Pending-review closure and fresh append-only generation.
pending_rt = clone_runtime(base, "v1233-reliability-pending")
first = assess(pending_rt, fixture, resource_claim_spec(salt="a"))
changed_while_pending = assess(pending_rt, fixture, resource_claim_spec(salt="b"))
check(first.get("ok"))
check(changed_while_pending.get("ok") is False)
check(changed_while_pending.get("status") == "resource_concurrency_governance_pending_review")
held = resource.review_resource_concurrency_governance_assessment(
    first["assessment_id"], expected_assessment_digest=first["assessment_digest"],
    disposition="hold", runtime_root=pending_rt,
)
second_generation = assess(pending_rt, fixture, resource_claim_spec(salt="b"))
check(held.get("ok"))
check(second_generation.get("ok"))
check(second_generation.get("generation") == 2)
check(second_generation.get("previous_assessment_id") == first.get("assessment_id"))
check(second_generation.get("previous_assessment_digest") == first.get("assessment_digest"))
check(resource.load_resource_concurrency_governance_assessment(first["assessment_id"], runtime_root=pending_rt).get("assessment_digest") == first.get("assessment_digest"))

# Own-capacity exhaustion is visible without another session.
own_capacity_rt = clone_runtime(base, "v1233-reliability-own-capacity")
own_capacity = assess(
    own_capacity_rt, fixture,
    resource_claim_spec(workspace_mode="shared", workspace_units=2, workspace_capacity=1, salt="c"),
)
check(own_capacity.get("ok"))
check(own_capacity.get("admission_state") == "blocked_capacity")
check(own_capacity.get("capacity_conflict_count") >= 1)
check(own_capacity.get("admission_confirmable") is False)

# Multi-session base supports real contention tests without synthetic launch receipts.
multi_fixture = build_resource_fixture("v1233-reliability-multi")
second_session = add_second_session(multi_fixture)
multi_base = multi_fixture["runtime"]

# Exclusive conflict.
exclusive_rt = clone_runtime(multi_base, "v1233-reliability-exclusive")
existing = assess(exclusive_rt, second_session, resource_claim_spec(salt="a"))
check(existing.get("ok"))
check(confirm(exclusive_rt, existing).get("ok"))
current = assess(exclusive_rt, multi_fixture, resource_claim_spec(salt="b"))
check(current.get("ok"))
check(current.get("admission_state") == "blocked_exclusive_conflict")
check(current.get("exclusive_conflict_count") >= 1)
check(current.get("conflicting_launch_ids") == [second_session["launch"]["launch_id"]])
check(current.get("preemption_proposal_eligible") is True)
check(current.get("preemption_performed") is False)

# Shared-capacity conflict.
capacity_rt = clone_runtime(multi_base, "v1233-reliability-capacity")
shared_claim = resource_claim_spec(workspace_mode="shared", workspace_units=1, workspace_capacity=1, salt="c")
existing = assess(capacity_rt, second_session, shared_claim)
check(confirm(capacity_rt, existing).get("ok"))
current = assess(capacity_rt, multi_fixture, resource_claim_spec(workspace_mode="shared", workspace_units=1, workspace_capacity=1, salt="d"))
check(current.get("admission_state") == "blocked_capacity")
check(current.get("capacity_conflict_count") >= 1)

# Contradictory capacity evidence fails closed.
contradictory_rt = clone_runtime(multi_base, "v1233-reliability-contradictory")
existing = assess(
    contradictory_rt, second_session,
    resource_claim_spec(workspace_mode="shared", workspace_capacity=2, salt="a"),
)
check(confirm(contradictory_rt, existing).get("ok"))
current = assess(
    contradictory_rt, multi_fixture,
    resource_claim_spec(workspace_mode="shared", workspace_capacity=1, salt="b"),
)
check(current.get("admission_state") == "blocked_resource_contradictory")
check(current.get("capacity_disagreement_count") >= 1)

# Global concurrency limit blocks even non-overlapping workspace claims.
limit_rt = clone_runtime(multi_base, "v1233-reliability-limit")
existing = assess(
    limit_rt, second_session,
    resource_claim_spec(workspace_code="workspace_two", salt="c"), limit=1,
)
check(confirm(limit_rt, existing).get("ok"))
current = assess(
    limit_rt, multi_fixture,
    resource_claim_spec(workspace_code="workspace_one", salt="d"), limit=1,
)
check(current.get("admission_state") == "blocked_concurrency_limit")
check(current.get("prospective_concurrency") == 2)
check(current.get("concurrency_limit_exceeded") is True)

# A changed active-session control digest makes its prior claim stale and conservatively blocking.
stale_claim_rt = clone_runtime(multi_base, "v1233-reliability-stale-claim")
existing = assess(stale_claim_rt, second_session, resource_claim_spec(salt="a"))
check(confirm(stale_claim_rt, existing).get("ok"))
_apply_transition({**second_session, "runtime": stale_claim_rt}, "pause")
current = assess(stale_claim_rt, multi_fixture, resource_claim_spec(salt="b"))
check(current.get("admission_state") == "blocked_stale_existing_claim")
check(current.get("stale_existing_admission_count") == 1)
check(current.get("stale_existing_claim_conflict_count") >= 1)
check(current.get("preemption_performed") is False)

# Cancelled sessions become abandoned evidence, not active leases or hidden cleanup actions.
abandoned_rt = clone_runtime(multi_base, "v1233-reliability-abandoned")
existing = assess(abandoned_rt, second_session, resource_claim_spec(salt="c"))
check(confirm(abandoned_rt, existing).get("ok"))
_apply_transition({**second_session, "runtime": abandoned_rt}, "cancel")
current = assess(abandoned_rt, multi_fixture, resource_claim_spec(salt="d"))
check(current.get("ok"))
check(current.get("admission_state") == "admissible_pending_operator_review")
check(current.get("abandoned_admission_count") == 1)
check(current.get("abandoned_claim_cleanup_recommended") is True)
check(current.get("resource_lease_created") is False)
check(current.get("queue_modified") is False)

# Repeated operator holds surface starvation/fairness evidence without automatic promotion.
starve_rt = clone_runtime(base, "v1233-reliability-starvation")
for salt in ("a", "b"):
    row = assess(starve_rt, fixture, resource_claim_spec(workspace_state="unavailable", salt=salt))
    check(row.get("ok"))
    review = resource.review_resource_concurrency_governance_assessment(
        row["assessment_id"], expected_assessment_digest=row["assessment_digest"],
        disposition="hold", runtime_root=starve_rt,
    )
    check(review.get("ok"))
starved = assess(starve_rt, fixture, resource_claim_spec(workspace_state="unavailable", salt="c"))
check(starved.get("ok"))
check(starved.get("prior_hold_count") == 2)
check(starved.get("starvation_risk_detected") is True)
check(starved.get("fairness_review_required") is True)
check(starved.get("admission_confirmable") is False)
check(starved.get("execution_session_launch_authorized") is False)

# Current monitor drift invalidates exact v1232 dependency lineage.
drift_rt = clone_runtime(base, "v1233-reliability-dependency-drift")
progress = monitoring.record_live_execution_progress(
    launch["launch_id"], expected_launch_digest=launch["launch_digest"],
    event_type="risk_reported", current_stage="blocked", completed_units=0, total_units=3,
    blocker_codes=["dependency_blocked"], risk_codes=["budget_pressure"],
    operator_attention_required=True, runtime_root=drift_rt,
)
check(progress.get("ok"))
drift = assess(drift_rt, fixture, resource_claim_spec(salt="d"))
check(drift.get("ok") is False)
check(drift.get("status") == "resource_concurrency_governance_dependency_lineage_blocked")
check("dependency_runtime_lineage_stale" in drift.get("reason", ""))

# Terminal current sessions cannot be admitted even with fresh current digests.
terminal_rt = clone_runtime(base, "v1233-reliability-terminal")
_apply_transition({**fixture, "runtime": terminal_rt}, "cancel")
terminal = assess(terminal_rt, fixture, resource_claim_spec(salt="e"))
check(terminal.get("ok") is False)
check(terminal.get("status") in {
    "resource_concurrency_governance_session_state_blocked",
    "resource_concurrency_governance_monitor_evidence_unavailable",
    "resource_concurrency_governance_launch_evidence_unavailable",
})

# Assessment tamper closes load, review, and public listing.
tamper_rt = clone_runtime(base, "v1233-reliability-assessment-tamper")
tampered = assess(tamper_rt, fixture, resource_claim_spec(salt="a"))
path = resource._assessment_path(tampered["assessment_id"], tamper_rt)
raw = json.loads(path.read_text(encoding="utf-8"))
raw["concurrency_limit"] = 9
path.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")
loaded = resource.load_resource_concurrency_governance_assessment(tampered["assessment_id"], runtime_root=tamper_rt)
check(loaded.get("ok") is False)
check(loaded.get("status") == "resource_concurrency_governance_assessment_integrity_blocked")
reviewed = resource.review_resource_concurrency_governance_assessment(
    tampered["assessment_id"], expected_assessment_digest=tampered["assessment_digest"],
    disposition="hold", runtime_root=tamper_rt,
)
check(reviewed.get("ok") is False)
check(resource.public_resource_concurrency_governance_assessments(runtime_root=tamper_rt).get("ok") is False)

# Review tamper closes restart listing.
review_tamper_rt = clone_runtime(base, "v1233-reliability-review-tamper")
assessment = assess(review_tamper_rt, fixture, resource_claim_spec(salt="b"))
review = resource.review_resource_concurrency_governance_assessment(
    assessment["assessment_id"], expected_assessment_digest=assessment["assessment_digest"],
    disposition="hold", runtime_root=review_tamper_rt,
)
path = resource._review_path(review["review_id"], review_tamper_rt)
raw = json.loads(path.read_text(encoding="utf-8"))
raw["disposition"] = "confirm_admissible"
path.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")
check(resource.load_resource_concurrency_governance_review(review["review_id"], runtime_root=review_tamper_rt).get("ok") is False)
check(resource.public_resource_concurrency_governance_reviews(runtime_root=review_tamper_rt).get("ok") is False)

# Dependency assessment and review tamper fail closed before resource evidence creation.
dep_tamper_rt = clone_runtime(base, "v1233-reliability-dependency-tamper")
dep_path = dependency._assessment_path(fixture["dependency_assessment"]["assessment_id"], dep_tamper_rt)
raw = json.loads(dep_path.read_text(encoding="utf-8"))
raw["readiness_state"] = "blocked_unknown"
dep_path.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")
blocked = assess(dep_tamper_rt, fixture, resource_claim_spec(salt="c"))
check(blocked.get("ok") is False)
check(blocked.get("status") == "resource_concurrency_governance_dependency_lineage_blocked")
check("dependency_assessment_integrity_blocked" in blocked.get("reason", ""))

# Stale lock cleanup and restart inspection are deterministic.
lock_rt = clone_runtime(base, "v1233-reliability-lock")
lock = resource._root(lock_rt) / "locks" / "resource-concurrency-governance.lock"
lock.mkdir(parents=True, exist_ok=True)
(lock / "owner").write_text("dead", encoding="ascii")
os.utime(lock, (time.time() - 120, time.time() - 120))
locked = assess(lock_rt, fixture, resource_claim_spec(salt="d"))
check(locked.get("ok"))
check(not lock.exists())
restart = resource.public_resource_concurrency_governance_assessments(runtime_root=lock_rt)
check(restart.get("ok"))
check(restart.get("assessment_count") == 1)
check(restart.get("assessments", [])[0].get("assessment_digest") == locked.get("assessment_digest"))

# Public evidence remains content-free across adversarial paths.
encoded = json.dumps({
    "assessments": resource.public_resource_concurrency_governance_assessments(runtime_root=exclusive_rt),
    "reviews": resource.public_resource_concurrency_governance_reviews(runtime_root=exclusive_rt),
}, sort_keys=True)
check(str(exclusive_rt) not in encoded)
check("shared_workspace" not in encoded)
check("python_engine" not in encoded)
check("private-project" not in encoded)
check(before == tree_signature())

print(json.dumps({"ok": all(checks), "passed": sum(checks), "total": len(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
