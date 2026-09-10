from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.operator_reviewed_soak_progression import (
    ACTIONS,
    ACTION_TARGETS,
    create_soak_progression_request,
    create_soak_progression_review,
    public_soak_progression_summary,
    review_soak_progression,
)
from conscious_agent.operator_reviewed_soak_progression_checkpoint import (
    build_operator_reviewed_soak_progression_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


def h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


with tempfile.TemporaryDirectory(prefix="eidolon-v1195-5-") as temp:
    report = build_operator_reviewed_soak_progression_checkpoint(
        source_root=ROOT,
        runtime_root=Path(temp) / "runtime",
    )

for key, expected in (
    ("ok", True),
    ("contract_version", "v1195.5"),
    ("read_only", True),
    ("post_available", False),
    ("content_free", True),
    ("source_unchanged", True),
    ("runtime_mutated", False),
    ("production_source_modified", False),
    ("actual_waiting_started", False),
    ("automatic_continuation", False),
    ("progression_started", False),
    ("pause_executed", False),
    ("resume_executed", False),
    ("approval_created", False),
    ("approval_consumed", False),
    ("execution_invoked", False),
    ("cancellation_executed", False),
    ("recovery_executed", False),
    ("provider_contacted", False),
    ("model_contacted", False),
    ("thread_started", False),
    ("process_started", False),
    ("global_profile_pass_claimed", False),
    ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 300)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 30)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1195.5"),
    ("status", "progression_presented"),
    ("decision", "approve"),
    ("action", "continue_observation"),
    ("current_lifecycle_state", "review_required"),
    ("presented_lifecycle_state", "observation_only"),
    ("decision_count", 3),
    ("action_count", 9),
    ("transition_count", 9),
    ("approve_status", "progression_presented"),
    ("reject_status", "progression_rejected"),
    ("defer_status", "progression_deferred"),
    ("all_actions_presented", True),
    ("multi_session_lineage_verified", True),
    ("terminal_disposition_count", 4),
    ("accountable_transition_presented", True),
    ("continuation_eligible", True),
    ("content_free", True),
    ("foreground_path_available", True),
    ("exact_lineage_verified", True),
    ("original_evidence_preserved", True),
    ("current_regressions_separate", True),
    ("inherited_debt_visible", True),
    ("actual_waiting_started", False),
    ("automatic_continuation", False),
    ("progression_started", False),
    ("pause_executed", False),
    ("resume_executed", False),
    ("approval_created", False),
    ("approval_consumed", False),
    ("execution_invoked", False),
    ("cancellation_executed", False),
    ("recovery_executed", False),
    ("runtime_mutated", False),
    ("provider_contacted", False),
    ("model_contacted", False),
    ("thread_started", False),
    ("process_started", False),
    ("global_profile_pass_claimed", False),
    ("authority_granted", False),
):
    require(summary.get(key) == expected)
require(len(summary["transition_digest"]) == 64)

for name in (
    "stale-snapshot",
    "stale-context",
    "stale-soak",
    "stale-plan",
    "stale-terminal",
    "unsupported-action",
    "unsupported-decision",
    "unsupported-purpose",
    "invalid-transition",
    "target-mismatch",
    "malformed-digest",
    "review-mismatch",
    "private-field",
    "hidden-wait",
    "automatic-continuation",
    "hidden-execution",
    "pause-execution",
    "resume-execution",
    "cancellation",
    "recovery",
    "runtime-mutation",
    "provider-contact",
    "thread-start",
    "approval-consumption",
    "authority",
    "foreground-block",
    "evidence-loss",
    "lineage-loss",
    "hidden-debt",
    "global-pass",
    "tamper",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

# Directly prove a deterministic three-session pause/resume/completion chain.
snapshot = h("v1195.5:direct:snapshot")
context = h("v1195.5:direct:context")
soak_summary = {
    "soak_digest": h("v1195.5:direct:soak"),
    "plan_digest": h("v1195.5:direct:plan"),
    "terminal_interval_digest": h("v1195.5:direct:terminal"),
    "interruption_evidence_count": 1,
    "restart_evidence_count": 1,
    "foreground_path_available": True,
    "exact_lineage_verified": True,
    "original_evidence_preserved": True,
    "current_regressions_separate": True,
    "inherited_debt_visible": True,
    "actual_waiting_started": False,
    "automatic_continuation": False,
    "execution_invoked": False,
    "cancellation_executed": False,
    "recovery_executed": False,
    "runtime_mutated": False,
    "provider_contacted": False,
    "model_contacted": False,
    "thread_started": False,
    "process_started": False,
    "global_profile_pass_claimed": False,
    "authority_granted": False,
    "content_free": True,
}

def request_for(action: str, current: str, sequence: int, previous: str, session: int, day: int):
    return create_soak_progression_request(
        progression_id=f"direct:{sequence}:{action}",
        soak_id="direct-soak",
        soak_digest=soak_summary["soak_digest"],
        plan_digest=soak_summary["plan_digest"],
        terminal_interval_digest=soak_summary["terminal_interval_digest"],
        snapshot_digest=snapshot,
        context_digest=context,
        action=action,
        current_lifecycle_state=current,
        target_lifecycle_state=ACTION_TARGETS[action],
        purpose_code="operator_interval_disposition" if action.startswith("present_") else (
            "operator_pause_review" if action == "pause_observation" else (
                "operator_resume_review" if action == "resume_observation" else "operator_soak_progression"
            )
        ),
        session_index=session,
        day_index=day,
        transition_sequence=sequence,
        previous_transition_digest=previous,
        artifact_digest=h(f"artifact:{sequence}"),
        receipt_digest=h(f"receipt:{sequence}"),
    )

previous = None
direct_results = []
for sequence, (action, current, session, day) in enumerate((
    ("continue_observation", "review_required", 0, 0),
    ("pause_observation", "observation_only", 1, 0),
    ("resume_observation", "paused_evidence_only", 2, 1),
    ("present_completion", "observation_only", 3, 2),
)):
    request = request_for(action, current, sequence, previous["transition_digest"] if previous else "", session, day)
    review = create_soak_progression_review(
        request_digest=request["request_digest"],
        review_id=f"direct-review:{sequence}",
        decision="approve",
        operator_review_digest=h(f"operator:{sequence}"),
        reason_code="operator_approved",
    )
    result = review_soak_progression(
        soak_summary=soak_summary,
        request=request,
        review=review,
        current_snapshot_digest=snapshot,
        current_context_digest=context,
        previous_transition=previous,
    )
    direct_results.append(result)
    previous = result
    require(result["status"] == "progression_presented")
    require(result["transition_sequence"] == sequence)
    require(result["session_index"] == session)
    require(result["day_index"] == day)
    require(result["exact_lineage_verified"] is True)
    require(result["progression_started"] is False)
    require(result["execution_invoked"] is False)
    require(result["runtime_mutated"] is False)
    require(result["authority_granted"] is False)
require(direct_results[0]["continuation_eligible"] is True)
require(direct_results[1]["pause_presented"] is True)
require(direct_results[2]["resume_eligible"] is True)
require(direct_results[3]["terminal_disposition_presented"] is True)
require(direct_results[3]["presented_lifecycle_state"] == "completed_evidence_only")
public = public_soak_progression_summary(direct_results[-1])
require(public["content_free"] is True)
require(public["execution_invoked"] is False)
require(public["authority_granted"] is False)
require("errors" not in public)
require("soak_id" not in public)

# Broken cross-session lineage remains blocked.
bad = request_for("continue_observation", "review_required", 1, h("wrong"), 1, 1)
bad_review = create_soak_progression_review(
    request_digest=bad["request_digest"],
    review_id="bad-lineage-review",
    decision="approve",
    operator_review_digest=h("bad-lineage-operator"),
    reason_code="operator_approved",
)
bad_result = review_soak_progression(
    soak_summary=soak_summary,
    request=bad,
    review=bad_review,
    current_snapshot_digest=snapshot,
    current_context_digest=context,
    previous_transition=direct_results[0],
)
require(bad_result["status"] == "blocked")
require("broken_transition_lineage" in bad_result["errors"])
require(bad_result["progression_started"] is False)
require(bad_result["execution_invoked"] is False)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next(
    (row for row in registry["checkpoints"] if row["checkpoint_id"] == "operator-reviewed-soak-progression-checkpoint"),
    None,
)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1195.5")
require((descriptor or {}).get("builder") == "build_operator_reviewed_soak_progression_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "operator-reviewed-soak-progression-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1195-5-cli-"),
    },
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1195.5")
    require(cli_report["summary"]["decision_count"] == 3)
    require(cli_report["summary"]["action_count"] == 9)
    require(cli_report["summary"]["multi_session_lineage_verified"] is True)
    require(cli_report["summary"]["execution_invoked"] is False)
except Exception:
    for _ in range(6):
        require(False)

status, payload = dispatch_api(
    "GET", "/api/cognition/operator-reviewed-soak-progression-checkpoint", {}, None
)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1195.5")
require(payload["data"]["summary"]["decision_count"] == 3)
require(payload["data"]["summary"]["action_count"] == 9)
require(payload["data"]["summary"]["multi_session_lineage_verified"] is True)
require(payload["data"]["summary"]["progression_started"] is False)
require(payload["data"]["summary"]["execution_invoked"] is False)
status_post, payload_post = dispatch_api(
    "POST", "/api/cognition/operator-reviewed-soak-progression-checkpoint", {}, {}
)
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("operator-reviewed-soak-progression-panel" in html)
require("operator-reviewed-soak-progression-state" in html)
require("operator-reviewed-soak-progression-summary" in html)
require("/api/cognition/operator-reviewed-soak-progression-checkpoint" in html)
require("v1195.6-v1195.8" in html)
require("presentation-only progression" in html.lower())
require("no real waiting" in html.lower())

for relative in (
    "README.md",
    "README_NEXT_STEPS.md",
    "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/release_metadata.py",
    "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1195.3-v1195.5" in text or "v1195_3_5" in text)
    require("v1195.6-v1195.8" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1195.5"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1195.2"' in metadata)
require("Operator-Reviewed Soak Progression" in metadata)
require('WORKING_SOURCE_VERSION = "1195.2"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1194.9"' in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1195.5-operator-reviewed-soak-progression") == 1)
require(release.count("v1195_3_5_operator_reviewed_soak_progression_tests.py") == 1)

print(
    f"v1195.3-v1195.5 operator-reviewed soak progression: "
    f"{sum(checks)}/{len(checks)} PASS"
)
