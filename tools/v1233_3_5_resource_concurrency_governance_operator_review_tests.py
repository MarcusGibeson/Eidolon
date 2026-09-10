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

import execution_session_pause_resume_cancel_recovery as control
import resource_concurrency_governance as resource
from ordinary_chat_development_campaign import process_ordinary_chat_development_turn
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
fixture = build_resource_fixture("v1233-review")
base = fixture["runtime"]
launch = fixture["launch"]


def state(rt, launch_id=None):
    return control.inspect_execution_session_control(
        launch_id or launch["launch_id"], runtime_root=rt, reconcile_runtime=False
    )


def exact_prepare(rt, spec=None, *, current_fixture=None, limit=2):
    current_fixture = current_fixture or fixture
    current_launch = current_fixture["launch"]
    current_monitor = __import__("live_execution_monitoring_operator_intervention").inspect_live_execution_monitoring(
        current_launch["launch_id"], runtime_root=rt
    )
    current_control = state(rt, current_launch["launch_id"])
    dep_assessment = current_fixture["dependency_assessment"]
    dep_review = current_fixture["dependency_review"]
    evidence = spec if spec is not None else resource_claim_spec(salt="a")
    text = (
        f"Prepare resource and concurrency governance assessment for bounded development execution session "
        f"{current_launch['launch_id']} digest {current_launch['launch_digest']} "
        f"monitor digest {current_monitor['monitor_digest']} control digest {current_control['control_digest']} "
        f"dependency assessment {dep_assessment['assessment_id']} digest {dep_assessment['assessment_digest']} "
        f"dependency review {dep_review['review_id']} digest {dep_review['review_digest']} "
        f"concurrency limit {limit} with resource claims {evidence}."
    )
    return text, process_ordinary_chat_development_turn(text, runtime_root=rt)


# Exact ordinary-chat assessment and confirmation.
rt = clone_runtime(base, "v1233-review-chat")
text, turn = exact_prepare(rt)
row = turn.get("resource_concurrency_governance") or {}
check(turn.get("active") is True)
check(row.get("ok"))
check(row.get("status") == "resource_concurrency_governance_assessment_ready_for_operator_review")
check(row.get("admission_state") == "admissible_pending_operator_review")
check("no launch, resume, lease, or preemption authority" in turn.get("response", "").lower())
assessment_id = row.get("assessment_id")
assessment_digest = row.get("assessment_digest")
control_before = state(rt)
confirm_text = (
    f"Review resource and concurrency governance assessment confirm admissible for assessment "
    f"{assessment_id} digest {assessment_digest}."
)
confirmed_turn = process_ordinary_chat_development_turn(confirm_text, runtime_root=rt)
review = confirmed_turn.get("resource_concurrency_governance") or {}
control_after = state(rt)
check(confirmed_turn.get("active") is True)
check(review.get("ok"))
check(review.get("disposition") == "confirm_admissible")
check(review.get("admission_confirmed") is True)
check(review.get("confirmed_admissibility_requires_fresh_execution_authority") is True)
check(review.get("confirmed_admissibility_does_not_launch_session") is True)
check(review.get("confirmed_admissibility_does_not_resume_session") is True)
check(review.get("resource_lease_created") is False)
check(review.get("preemption_performed") is False)
check(control_before.get("control_digest") == control_after.get("control_digest"))
check(control_before.get("session_state") == control_after.get("session_state") == "active")
for key, expected in resource.AUTHORITY_FLAGS.items():
    check(review.get(key) is expected)

# Exact replay, conflict, and stale digest closure.
replay = process_ordinary_chat_development_turn(confirm_text, runtime_root=rt).get("resource_concurrency_governance") or {}
check(replay.get("ok"))
check(replay.get("operation_status") == "replayed")
check(replay.get("review_id") == review.get("review_id"))
conflict = resource.review_resource_concurrency_governance_assessment(
    assessment_id, expected_assessment_digest=assessment_digest, disposition="hold", runtime_root=rt
)
check(conflict.get("ok") is False)
check(conflict.get("status") == "resource_concurrency_governance_review_conflict_blocked")
stale = resource.review_resource_concurrency_governance_assessment(
    assessment_id, expected_assessment_digest="0" * 64, disposition="confirm_admissible", runtime_root=rt
)
check(stale.get("ok") is False)
check(stale.get("status") == "resource_concurrency_governance_review_stale_digest")

# Independent exact review dispositions.
for decision, salt in (("hold", "a"), ("reject", "b"), ("request_changes", "c")):
    decision_rt = clone_runtime(base, f"v1233-review-{decision}")
    _, prepared_turn = exact_prepare(decision_rt, resource_claim_spec(salt=salt))
    assessment = prepared_turn.get("resource_concurrency_governance") or {}
    phrase = decision.replace("_", " ")
    command = (
        f"Review resource and concurrency governance assessment {phrase} for assessment "
        f"{assessment['assessment_id']} digest {assessment['assessment_digest']}."
    )
    outcome = process_ordinary_chat_development_turn(command, runtime_root=decision_rt)
    reviewed = outcome.get("resource_concurrency_governance") or {}
    check(outcome.get("active") is True)
    check(reviewed.get("ok"))
    check(reviewed.get("disposition") == decision)
    check(reviewed.get("admission_confirmed") is False)
    check(reviewed.get("provider_execution_authorized") is False)
    check(reviewed.get("resume_authorized") is False)
    check(reviewed.get("project_mutation_authorized") is False)
    check(reviewed.get("queue_mutation_authorized") is False)
    check(reviewed.get("schedule_mutation_authorized") is False)

# Blocked evidence cannot be confirmed admissible but can be held.
blocked_rt = clone_runtime(base, "v1233-review-blocked")
_, blocked_turn = exact_prepare(blocked_rt, resource_claim_spec(workspace_state="unavailable", salt="b"))
blocked = blocked_turn.get("resource_concurrency_governance") or {}
blocked_confirm = resource.review_resource_concurrency_governance_assessment(
    blocked["assessment_id"], expected_assessment_digest=blocked["assessment_digest"],
    disposition="confirm_admissible", runtime_root=blocked_rt,
)
check(blocked.get("admission_state") == "blocked_resource_unavailable")
check(blocked_confirm.get("ok") is False)
check(blocked_confirm.get("status") == "resource_concurrency_governance_admission_confirmation_blocked")
held = resource.review_resource_concurrency_governance_assessment(
    blocked["assessment_id"], expected_assessment_digest=blocked["assessment_digest"],
    disposition="hold", runtime_root=blocked_rt,
)
check(held.get("ok"))
check(held.get("assessment_held") is True)

# A higher-priority conflicting session may receive a proposal-only preemption review.
preempt_fixture = build_resource_fixture("v1233-review-preemption")
second = add_second_session(preempt_fixture)
preempt_rt = preempt_fixture["runtime"]
_, second_turn = exact_prepare(
    preempt_rt, resource_claim_spec(salt="c"), current_fixture=second, limit=2
)
second_assessment = second_turn.get("resource_concurrency_governance") or {}
second_review = resource.review_resource_concurrency_governance_assessment(
    second_assessment["assessment_id"], expected_assessment_digest=second_assessment["assessment_digest"],
    disposition="confirm_admissible", runtime_root=preempt_rt,
)
check(second_review.get("ok"))
_, primary_turn = exact_prepare(
    preempt_rt, resource_claim_spec(salt="d"), current_fixture=preempt_fixture, limit=2
)
primary = primary_turn.get("resource_concurrency_governance") or {}
check(primary.get("admission_state") == "blocked_exclusive_conflict")
check(primary.get("preemption_proposal_eligible") is True)
check(second["launch"]["launch_id"] in (primary.get("preemption_candidate_launch_ids") or []))
preempt_text = (
    f"Review resource and concurrency governance assessment propose preemption for assessment "
    f"{primary['assessment_id']} digest {primary['assessment_digest']}."
)
preempt_turn = process_ordinary_chat_development_turn(preempt_text, runtime_root=preempt_rt)
preempt_review = preempt_turn.get("resource_concurrency_governance") or {}
check(preempt_review.get("ok"))
check(preempt_review.get("disposition") == "propose_preemption")
check(preempt_review.get("preemption_proposal_recorded") is True)
check(preempt_review.get("preemption_performed") is False)
check(state(preempt_rt, second["launch"]["launch_id"]).get("session_state") == "active")
not_eligible = resource.review_resource_concurrency_governance_assessment(
    row["assessment_id"], expected_assessment_digest=row["assessment_digest"],
    disposition="propose_preemption", runtime_root=rt,
)
check(not_eligible.get("ok") is False)
check(not_eligible.get("status") == "resource_concurrency_governance_review_conflict_blocked")

# Exact inspection/listing controls and CLI share the public content-free records.
inspect_rt = clone_runtime(base, "v1233-review-inspection")
_, inspect_turn = exact_prepare(inspect_rt, resource_claim_spec(salt="e"))
assessment = inspect_turn.get("resource_concurrency_governance") or {}
show = process_ordinary_chat_development_turn(
    f"Show resource and concurrency governance assessment {assessment['assessment_id']}.", runtime_root=inspect_rt
)
check(show.get("active") is True)
check((show.get("resource_concurrency_governance") or {}).get("assessment_id") == assessment.get("assessment_id"))
listed = process_ordinary_chat_development_turn(
    "Show resource and concurrency governance assessments.", runtime_root=inspect_rt
).get("resource_concurrency_governance") or {}
check(listed.get("ok"))
check(listed.get("assessment_count") == 1)
resource.review_resource_concurrency_governance_assessment(
    assessment["assessment_id"], expected_assessment_digest=assessment["assessment_digest"],
    disposition="hold", runtime_root=inspect_rt,
)
reviews = process_ordinary_chat_development_turn(
    "Show resource and concurrency governance reviews.", runtime_root=inspect_rt
).get("resource_concurrency_governance") or {}
check(reviews.get("ok"))
check(reviews.get("review_count") == 1)

for command, expected_key, expected_count in (
    ("resource-concurrency-governance-assessments", "assessment_count", 1),
    ("resource-concurrency-governance-reviews", "review_count", 1),
):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), command, "--runtime-root", str(inspect_rt)],
        cwd=ROOT, text=True, capture_output=True, timeout=120,
    )
    check(proc.returncode == 0)
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        check(payload.get("ok") is True)
        check(payload.get(expected_key) == expected_count)
    except Exception:
        check(False)
        check(False)

# Suggestions, hypotheticals, quotations, malformed controls, and hidden automation requests remain inert.
for utterance in (
    "It would be nice if resource conflicts resolved themselves.",
    "Maybe admit another session later.",
    "Suppose the workspace were available.",
    'The documentation says "prepare resource and concurrency governance assessment".',
    "Please preempt the other session automatically.",
    "Review resource and concurrency governance assessment confirm admissible.",
):
    inert = resource.process_resource_concurrency_governance_control(utterance, runtime_root=inspect_rt)
    check(inert.get("active") is False)

# Public projections contain no raw resource labels or private runtime path.
public = resource.public_resource_concurrency_governance_assessments(runtime_root=inspect_rt)
public_reviews = resource.public_resource_concurrency_governance_reviews(runtime_root=inspect_rt)
encoded = json.dumps({"assessments": public, "reviews": public_reviews}, sort_keys=True)
check(public.get("ok"))
check(public_reviews.get("ok"))
check(str(inspect_rt) not in encoded)
check("shared_workspace" not in encoded)
check("python_engine" not in encoded)
for key in (
    "private_request_exposed", "private_path_exposed", "private_content_exposed",
    "raw_provider_output_exposed", "raw_test_output_exposed",
):
    check(public.get(key) is False)
    check(public_reviews.get(key) is False)
check(before == tree_signature())

print(json.dumps({"ok": all(checks), "passed": sum(checks), "total": len(checks)}, sort_keys=True))
raise SystemExit(0 if all(checks) else 1)
