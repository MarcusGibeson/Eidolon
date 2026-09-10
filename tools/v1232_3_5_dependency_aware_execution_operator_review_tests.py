from __future__ import annotations

import hashlib
import json
import subprocess
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
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
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
fixture = build_dependency_fixture("v1232-review", accepted_revision=True)
base = fixture["runtime"]
launch = fixture["launch"]
accepted = fixture["accepted_revision"]["proposal"]


def state(rt):
    return control.inspect_execution_session_control(launch["launch_id"], runtime_root=rt, reconcile_runtime=False)


def monitor(rt):
    return monitoring.inspect_live_execution_monitoring(launch["launch_id"], runtime_root=rt)


def exact_prepare(rt, spec=None):
    current_monitor = monitor(rt)
    current_control = state(rt)
    evidence = spec if spec is not None else dependency_spec("satisfied", "satisfied", "satisfied", salt="d")
    text = (
        f"Prepare dependency-aware execution assessment for bounded development execution session {launch['launch_id']} "
        f"digest {launch['launch_digest']} monitor digest {current_monitor['monitor_digest']} "
        f"control digest {current_control['control_digest']} revision digest {accepted['revision_digest']} "
        f"with dependency evidence {evidence}."
    )
    return text, process_ordinary_chat_development_turn(text, runtime_root=rt)


# Exact ordinary-chat preparation.
rt = clone_runtime(base, "v1232-review-chat")
text, turn = exact_prepare(rt)
row = turn.get("dependency_aware_execution") or {}
check(turn.get("active") is True)
check(row.get("ok"))
check(row.get("status") == "dependency_aware_execution_assessment_ready_for_operator_review")
check(row.get("readiness_state") == "ready_pending_operator_review")
check("grants no launch or resume authority" in turn.get("response", "").lower())
assessment_id = row.get("assessment_id")
assessment_digest = row.get("assessment_digest")

# Exact readiness confirmation changes no session control state.
control_before = state(rt)
confirm_text = (
    f"Review dependency-aware execution assessment confirm ready for assessment {assessment_id} "
    f"digest {assessment_digest}."
)
confirmed_turn = process_ordinary_chat_development_turn(confirm_text, runtime_root=rt)
review = confirmed_turn.get("dependency_aware_execution") or {}
control_after = state(rt)
check(confirmed_turn.get("active") is True)
check(review.get("ok"))
check(review.get("disposition") == "confirm_ready")
check(review.get("readiness_confirmed") is True)
check(review.get("confirmed_readiness_requires_fresh_execution_authority") is True)
check(review.get("confirmed_readiness_does_not_launch_session") is True)
check(review.get("confirmed_readiness_does_not_resume_session") is True)
check(control_before.get("control_digest") == control_after.get("control_digest"))
check(control_before.get("session_state") == control_after.get("session_state") == "active")
for key, expected in dependency.AUTHORITY_FLAGS.items():
    check(review.get(key) is expected)

# Exact replay, conflicting decision, and stale digest closure.
replay = process_ordinary_chat_development_turn(confirm_text, runtime_root=rt).get("dependency_aware_execution") or {}
check(replay.get("ok"))
check(replay.get("operation_status") == "replayed")
check(replay.get("review_id") == review.get("review_id"))
conflict = dependency.review_dependency_aware_execution_assessment(
    assessment_id,
    expected_assessment_digest=assessment_digest,
    disposition="hold",
    runtime_root=rt,
)
check(conflict.get("ok") is False)
check(conflict.get("status") == "dependency_aware_execution_review_conflict_blocked")
stale = dependency.review_dependency_aware_execution_assessment(
    assessment_id,
    expected_assessment_digest="0" * 64,
    disposition="confirm_ready",
    runtime_root=rt,
)
check(stale.get("ok") is False)
check(stale.get("status") == "dependency_aware_execution_review_stale_digest")

# Independent exact review dispositions.
for decision in ("hold", "reject", "request_changes"):
    decision_rt = clone_runtime(base, f"v1232-review-{decision}")
    _, prepared_turn = exact_prepare(decision_rt)
    assessment = prepared_turn.get("dependency_aware_execution") or {}
    phrase = decision.replace("_", " ")
    command = (
        f"Review dependency-aware execution assessment {phrase} for assessment {assessment['assessment_id']} "
        f"digest {assessment['assessment_digest']}."
    )
    outcome = process_ordinary_chat_development_turn(command, runtime_root=decision_rt)
    reviewed = outcome.get("dependency_aware_execution") or {}
    check(outcome.get("active") is True)
    check(reviewed.get("ok"))
    check(reviewed.get("disposition") == decision)
    check(reviewed.get("readiness_confirmed") is False)
    check(reviewed.get("provider_execution_authorized") is False)
    check(reviewed.get("resume_authorized") is False)
    check(reviewed.get("project_mutation_authorized") is False)

# A blocked graph cannot be confirmed ready but can be held for operator action.
blocked_rt = clone_runtime(base, "v1232-review-blocked")
_, blocked_turn = exact_prepare(blocked_rt, dependency_spec("satisfied", "pending", salt="e"))
blocked = blocked_turn.get("dependency_aware_execution") or {}
blocked_confirm = dependency.review_dependency_aware_execution_assessment(
    blocked["assessment_id"],
    expected_assessment_digest=blocked["assessment_digest"],
    disposition="confirm_ready",
    runtime_root=blocked_rt,
)
check(blocked.get("readiness_state") == "blocked_pending")
check(blocked_confirm.get("ok") is False)
check(blocked_confirm.get("status") == "dependency_aware_execution_readiness_confirmation_blocked")
held = dependency.review_dependency_aware_execution_assessment(
    blocked["assessment_id"],
    expected_assessment_digest=blocked["assessment_digest"],
    disposition="hold",
    runtime_root=blocked_rt,
)
check(held.get("ok"))
check(held.get("assessment_held") is True)

# Paused readiness confirmation remains paused and creates no resume authority.
paused_rt = clone_runtime(base, "v1232-review-paused")
_apply_transition({**fixture, "runtime": paused_rt}, "pause")
_, paused_turn = exact_prepare(paused_rt)
paused_assessment = paused_turn.get("dependency_aware_execution") or {}
paused_before = state(paused_rt)
paused_review = dependency.review_dependency_aware_execution_assessment(
    paused_assessment["assessment_id"],
    expected_assessment_digest=paused_assessment["assessment_digest"],
    disposition="confirm_ready",
    runtime_root=paused_rt,
)
paused_after = state(paused_rt)
check(paused_review.get("ok"))
check(paused_assessment.get("fresh_resume_review_eligible") is True)
check(paused_review.get("resume_authorized") is False)
check(paused_before.get("session_state") == paused_after.get("session_state") == "paused")
check(paused_before.get("control_digest") == paused_after.get("control_digest"))

# Inspection and listing controls are exact and content-free.
inspect_rt = clone_runtime(base, "v1232-review-inspection")
_, inspect_turn = exact_prepare(inspect_rt)
assessment = inspect_turn.get("dependency_aware_execution") or {}
show = process_ordinary_chat_development_turn(
    f"Show dependency-aware execution assessment {assessment['assessment_id']}.", runtime_root=inspect_rt
)
check(show.get("active") is True)
check((show.get("dependency_aware_execution") or {}).get("assessment_id") == assessment.get("assessment_id"))
listed = process_ordinary_chat_development_turn(
    "Show dependency-aware execution assessments.", runtime_root=inspect_rt
).get("dependency_aware_execution") or {}
check(listed.get("ok"))
check(listed.get("assessment_count") == 1)
dependency.review_dependency_aware_execution_assessment(
    assessment["assessment_id"],
    expected_assessment_digest=assessment["assessment_digest"],
    disposition="hold",
    runtime_root=inspect_rt,
)
reviews = process_ordinary_chat_development_turn(
    "Show dependency-aware execution reviews.", runtime_root=inspect_rt
).get("dependency_aware_execution") or {}
check(reviews.get("ok"))
check(reviews.get("review_count") == 1)

# CLI inspection uses the same content-free runtime records.
for command, expected_key, expected_count in (
    ("dependency-aware-execution-assessments", "assessment_count", 1),
    ("dependency-aware-execution-reviews", "review_count", 1),
):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), command, "--runtime-root", str(inspect_rt)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
    )
    check(proc.returncode == 0)
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        check(payload.get("ok") is True)
        check(payload.get(expected_key) == expected_count)
    except Exception:
        check(False)
        check(False)

# Pending, deferred, or changes-requested v1231 revisions block dependency evaluation.
plain_fixture = build_dependency_fixture("v1232-review-plain", accepted_revision=False)
for disposition in (None, "defer", "request_changes"):
    unresolved_rt = clone_runtime(plain_fixture["runtime"], f"v1232-review-unresolved-{disposition}")
    proposal = revision.prepare_dynamic_execution_plan_revision(
        plain_fixture["launch"]["launch_id"],
        expected_launch_digest=plain_fixture["launch"]["launch_digest"],
        expected_monitor_digest=plain_fixture["monitor"]["monitor_digest"],
        expected_control_digest=plain_fixture["control"]["control_digest"],
        verified_change_codes=["dependency_state_changed"],
        runtime_root=unresolved_rt,
    )
    check(proposal.get("ok"))
    if disposition:
        reviewed_revision = revision.review_dynamic_execution_plan_revision(
            proposal["revision_id"],
            expected_revision_digest=proposal["revision_digest"],
            disposition=disposition,
            runtime_root=unresolved_rt,
        )
        check(reviewed_revision.get("ok"))
    blocked_result = dependency.prepare_dependency_aware_execution_assessment(
        plain_fixture["launch"]["launch_id"],
        expected_launch_digest=plain_fixture["launch"]["launch_digest"],
        expected_monitor_digest=plain_fixture["monitor"]["monitor_digest"],
        expected_control_digest=plain_fixture["control"]["control_digest"],
        expected_revision_digest="none",
        dependency_evidence=dependency_spec("satisfied", "satisfied", salt="f"),
        runtime_root=unresolved_rt,
    )
    check(blocked_result.get("ok") is False)
    check(blocked_result.get("status") == "dependency_aware_execution_plan_revision_unresolved")

# A rejected revision preserves the original approved-plan basis.
rejected_rt = clone_runtime(plain_fixture["runtime"], "v1232-review-rejected-revision")
proposal = revision.prepare_dynamic_execution_plan_revision(
    plain_fixture["launch"]["launch_id"],
    expected_launch_digest=plain_fixture["launch"]["launch_digest"],
    expected_monitor_digest=plain_fixture["monitor"]["monitor_digest"],
    expected_control_digest=plain_fixture["control"]["control_digest"],
    verified_change_codes=["dependency_state_changed"],
    runtime_root=rejected_rt,
)
revision.review_dynamic_execution_plan_revision(
    proposal["revision_id"], expected_revision_digest=proposal["revision_digest"], disposition="reject",
    runtime_root=rejected_rt,
)
original_basis = dependency.prepare_dependency_aware_execution_assessment(
    plain_fixture["launch"]["launch_id"],
    expected_launch_digest=plain_fixture["launch"]["launch_digest"],
    expected_monitor_digest=plain_fixture["monitor"]["monitor_digest"],
    expected_control_digest=plain_fixture["control"]["control_digest"],
    expected_revision_digest="none",
    dependency_evidence=dependency_spec("satisfied", "satisfied", salt="a"),
    runtime_root=rejected_rt,
)
check(original_basis.get("ok"))
check(original_basis.get("plan_basis") == "original_approved_plan")

# Wishes, hypotheticals, quotations, suggestions, and malformed controls are inert.
for utterance in (
    "It would be nice if dependencies resolved themselves.",
    "Maybe check the dependencies later.",
    "Suppose the dependency graph were ready.",
    'The documentation says "prepare dependency-aware execution assessment".',
    "Please silently launch when the dependencies pass.",
    "Review dependency-aware execution assessment confirm ready.",
):
    inert = dependency.process_dependency_aware_execution_control(utterance, runtime_root=inspect_rt)
    check(inert.get("active") is False)

# Public projections contain no raw dependency codes or private runtime paths.
public = dependency.public_dependency_aware_execution_assessments(runtime_root=inspect_rt)
public_reviews = dependency.public_dependency_aware_execution_reviews(runtime_root=inspect_rt)
encoded = json.dumps({"assessments": public, "reviews": public_reviews}, sort_keys=True)
check(public.get("ok"))
check(public_reviews.get("ok"))
check(str(inspect_rt) not in encoded)
check("source_inputs" not in encoded)
check("runtime_tool" not in encoded)
for key in (
    "private_request_exposed", "private_path_exposed", "private_content_exposed",
    "raw_provider_output_exposed", "raw_test_output_exposed",
):
    check(public.get(key) is False)
    check(public_reviews.get(key) is False)
check(before == tree_signature())

print(json.dumps({"ok": all(checks), "passed": sum(checks), "total": len(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
