from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1195-2-data-"))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.long_session_multi_day_soak import (
    SOAK_DOMAINS,
    assess_soak_evidence,
    create_soak_interval,
    create_soak_plan,
    public_soak_summary,
)
from conscious_agent.long_session_multi_day_soak_checkpoint import (
    build_long_session_multi_day_soak_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


def h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


with tempfile.TemporaryDirectory(prefix="eidolon-v1195-2-") as temp:
    report = build_long_session_multi_day_soak_checkpoint(
        source_root=ROOT,
        runtime_root=Path(temp) / "runtime",
    )

for key, expected in (
    ("ok", True),
    ("contract_version", "v1195.2"),
    ("read_only", True),
    ("post_available", False),
    ("content_free", True),
    ("source_unchanged", True),
    ("runtime_mutated", False),
    ("production_source_modified", False),
    ("actual_waiting_started", False),
    ("automatic_continuation", False),
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
require(report["total"] >= 200)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 25)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1195.2"),
    ("soak_mode", "multi_day"),
    ("interval_count", 9),
    ("domain_count", 9),
    ("session_count", 3),
    ("day_count", 3),
    ("cycle_count", 90),
    ("foreground_path_available", True),
    ("latency_within_budget", True),
    ("resource_budgets_within_bounds", True),
    ("progress_observed", True),
    ("exact_lineage_verified", True),
    ("original_evidence_preserved", True),
    ("current_regressions_separate", True),
    ("inherited_debt_visible", True),
    ("actual_waiting_started", False),
    ("automatic_continuation", False),
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
    ("content_free", True),
):
    require(summary.get(key) == expected)
require(len(summary["soak_digest"]) == 64)

for name in (
    "duplicate-id",
    "duplicate-sequence",
    "broken-lineage",
    "stale-snapshot",
    "stale-context",
    "unsupported-domain",
    "unsupported-state",
    "malformed-digest",
    "oversized",
    "elapsed-budget",
    "cycle-budget",
    "latency-budget",
    "token-budget",
    "disk-budget",
    "memory-budget",
    "duplicate-cycle",
    "stalled-progress",
    "private-field",
    "hidden-wait",
    "automatic-continuation",
    "hidden-execution",
    "cancellation",
    "recovery",
    "provider-contact",
    "thread-start",
    "runtime-mutation",
    "authority",
    "global-pass",
    "tamper",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

# Directly exercise a bounded long-session case distinct from the checkpoint's multi-day case.
snapshot = h("v1195.2:long-session:snapshot")
context = h("v1195.2:long-session:context")
plan = create_soak_plan(
    soak_id="long-session-0001",
    soak_mode="long_session",
    snapshot_digest=snapshot,
    context_digest=context,
    purpose_code="operator_long_session_review",
    planned_days=1,
    planned_sessions=1,
    max_intervals=16,
    max_elapsed_seconds=86_400,
    max_cycles=1_000,
    foreground_latency_budget_ms=500,
    token_budget=100_000,
    disk_budget_bytes=10_000_000,
    memory_budget_mb=2_048,
    deadline_mode="bounded_deadline",
    deadline_epoch_ms=1_800_000_000_000,
)
rows = []
previous = ""
for index, domain in enumerate(SOAK_DOMAINS):
    row = create_soak_interval(
        soak_id=plan["soak_id"],
        interval_id=f"long-session-interval-{index}",
        domain=domain,
        sequence=index,
        session_index=0,
        day_index=0,
        cycle_start=index * 5,
        cycle_end=index * 5 + 5,
        elapsed_seconds=300,
        observed_latency_ms=75,
        observed_tokens=500,
        observed_disk_bytes=10_000,
        observed_memory_mb=256,
        snapshot_digest=snapshot,
        context_digest=context,
        artifact_digest=h(f"{domain}:artifact"),
        receipt_digest=h(f"{domain}:receipt"),
        previous_interval_digest=previous,
        purpose_code="bounded_long_session_observation",
        interruption_state="observed" if domain == "interruption" else "none",
        restart_state="observed" if domain == "restart" else "not_observed",
        recovery_state="review_required_not_executed" if domain == "recovery" else "not_applicable",
    )
    rows.append(row)
    previous = row["interval_digest"]
verification = {
    "content_free": True,
    "current_regressions_separate": True,
    "inherited_debt_visible": True,
    "global_profile_pass_claimed": False,
}
long_session = assess_soak_evidence(
    plan,
    rows,
    current_snapshot_digest=snapshot,
    current_context_digest=context,
    verification_summary=verification,
)
require(long_session["status"] == "ready_for_operator_review")
require(long_session["errors"] == [])
long_summary = public_soak_summary(long_session)
require(long_summary["soak_mode"] == "long_session")
require(long_summary["session_count"] == 1)
require(long_summary["day_count"] == 1)
require(long_summary["cycle_count"] == 45)
require(long_summary["interruption_evidence_count"] == 1)
require(long_summary["restart_evidence_count"] == 1)
require(long_summary["recovery_review_count"] == 1)
require(long_summary["actual_waiting_started"] is False)
require(long_summary["execution_invoked"] is False)
require(long_summary["authority_granted"] is False)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next(
    (
        row
        for row in registry["checkpoints"]
        if row["checkpoint_id"] == "long-session-multi-day-soak-checkpoint"
    ),
    None,
)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1195.2")
require((descriptor or {}).get("builder") == "build_long_session_multi_day_soak_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "long-session-multi-day-soak-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1195-2-cli-"),
    },
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1195.2")
    require(cli_report["summary"]["domain_count"] == 9)
    require(cli_report["summary"]["actual_waiting_started"] is False)
    require(cli_report["summary"]["global_profile_pass_claimed"] is False)
except Exception:
    require(False)
    require(False)
    require(False)
    require(False)
    require(False)

status, payload = dispatch_api(
    "GET", "/api/cognition/long-session-multi-day-soak-checkpoint", {}, None
)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1195.2")
require(payload["data"]["summary"]["interval_count"] == 9)
require(payload["data"]["summary"]["domain_count"] == 9)
require(payload["data"]["summary"]["actual_waiting_started"] is False)
require(payload["data"]["summary"]["execution_invoked"] is False)
status_post, payload_post = dispatch_api(
    "POST", "/api/cognition/long-session-multi-day-soak-checkpoint", {}, {}
)
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("long-session-multi-day-soak-checkpoint-panel" in html)
require("long-session-multi-day-soak-checkpoint-state" in html)
require("long-session-multi-day-soak-checkpoint-summary" in html)
require("/api/cognition/long-session-multi-day-soak-checkpoint" in html)
require("v1195.3-v1195.5" in html)
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
    require("v1195.0-v1195.2" in text or "v1195_0_2" in text)
    require("v1195.3-v1195.5" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1195.2"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1194.9"' in metadata)
require("Long-Session and Multi-Day Soak Foundations" in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1195.2-long-session-multi-day-soak") == 1)
require(release.count("v1195_0_2_long_session_multi_day_soak_tests.py") == 1)

print(
    f"v1195.0-v1195.2 long-session multi-day soak foundations: "
    f"{sum(checks)}/{len(checks)} PASS"
)
