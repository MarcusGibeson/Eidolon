from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1195-9-data-"))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.long_session_multi_day_soak_consolidated_checkpoint import (
    CONTRACT_VERSION,
    build_long_session_multi_day_soak_consolidated_checkpoint,
)

checks: list[bool] = []

def require(value: object) -> None:
    checks.append(bool(value))
    assert value

with tempfile.TemporaryDirectory(prefix="eidolon-v1195-9-") as temporary:
    report = build_long_session_multi_day_soak_consolidated_checkpoint(
        source_root=ROOT, runtime_root=Path(temporary) / "runtime"
    )

for key, expected in (
    ("ok", True), ("contract_version", "v1195.9"), ("read_only", True),
    ("post_available", False), ("content_free", True), ("source_unchanged", True),
    ("runtime_mutated", False), ("production_source_modified", False),
    ("actual_waiting_started", False), ("automatic_continuation", False),
    ("progression_started", False), ("pause_executed", False),
    ("resume_executed", False), ("approval_created", False),
    ("approval_consumed", False), ("cancellation_executed", False),
    ("automatic_recovery", False), ("automatic_retry", False),
    ("recovery_executed", False), ("execution_invoked", False),
    ("provider_contacted", False), ("model_contacted", False),
    ("thread_started", False), ("process_started", False),
    ("global_profile_pass_claimed", False), ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 180)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 40)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1195.9"),
    ("foundation_contract_version", "v1195.2"),
    ("progression_contract_version", "v1195.5"),
    ("reliability_contract_version", "v1195.8"),
    ("retained_checkpoint_count", 3), ("soak_mode_count", 2),
    ("domain_count", 9), ("decision_count", 3),
    ("progression_action_count", 9), ("reliability_event_class_count", 8),
    ("terminal_disposition_count", 4), ("interval_count", 9),
    ("session_count", 3), ("day_count", 3), ("cycle_count", 90),
    ("transition_count", 9), ("reliability_ready_count", 8),
    ("foreground_path_available", True), ("latency_within_budget", True),
    ("resource_budgets_within_bounds", True), ("progress_observed", True),
    ("exact_lineage_verified", True), ("original_evidence_preserved", True),
    ("current_regressions_separate", True), ("inherited_debt_visible", True),
    ("operator_review_accountable", True), ("multi_session_lineage_verified", True),
    ("historical_truth_preserved", True), ("content_free", True),
    ("read_only", True), ("actual_waiting_started", False),
    ("automatic_continuation", False), ("progression_started", False),
    ("pause_executed", False), ("resume_executed", False),
    ("cancellation_executed", False), ("automatic_recovery", False),
    ("automatic_retry", False), ("recovery_executed", False),
    ("execution_invoked", False), ("approval_created", False),
    ("approval_consumed", False), ("runtime_mutated", False),
    ("production_source_modified", False), ("provider_contacted", False),
    ("model_contacted", False), ("thread_started", False),
    ("process_started", False), ("global_profile_pass_claimed", False),
    ("authority_state", "separate_not_granted"), ("authority_granted", False),
):
    require(summary.get(key) == expected)
require(len(summary["checkpoint_digest"]) == 64)
require(summary["blocked_case_count"] == len(report["blocked_cases"]))

for name in (
    "private-field", "foundation-contract-drift", "progression-contract-drift",
    "reliability-contract-drift", "retained-count", "mode-count", "domain-count",
    "decision-count", "action-count", "event-count", "terminal-count",
    "foreground-block", "latency-budget-loss", "resource-budget-loss",
    "progress-loss", "lineage-loss", "evidence-loss",
    "verification-boundary-loss", "debt-hidden", "review-accountability-loss",
    "multi-session-lineage-loss", "historical-truth-loss", "actual-wait",
    "automatic-continuation", "progression-start", "pause-execution",
    "resume-execution", "cancellation-execution", "automatic-recovery",
    "automatic-retry", "hidden-recovery", "hidden-execution", "approval-create",
    "approval-consume", "runtime-mutation", "source-mutation", "provider-contact",
    "model-contact", "thread-start", "process-start", "global-pass-claim",
    "authority-state", "authority", "tamper",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

for key, version, total in (
    ("foundations", "v1195.2", 212),
    ("progression", "v1195.5", 340),
    ("reliability", "v1195.8", 133),
):
    retained = report["retained_checkpoints"][key]
    require(retained["contract_version"] == version)
    require(retained["passed"] == total)
    require(retained["total"] == total)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "long-session-multi-day-soak-consolidated-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
require((descriptor or {}).get("builder") == "build_long_session_multi_day_soak_consolidated_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])
for checkpoint_id in (
    "long-session-multi-day-soak-checkpoint",
    "operator-reviewed-soak-progression-checkpoint",
    "soak-reliability-adversarial-checkpoint",
    "long-session-multi-day-soak-consolidated-checkpoint",
):
    require(any(row["checkpoint_id"] == checkpoint_id for row in registry["checkpoints"]))

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "long-session-multi-day-soak-consolidated-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1195-9-cli-")},
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1195.9")
    require(cli_report["summary"]["domain_count"] == 9)
    require(cli_report["summary"]["progression_action_count"] == 9)
    require(cli_report["summary"]["reliability_event_class_count"] == 8)
    require(cli_report["summary"]["execution_invoked"] is False)
except Exception:
    for _ in range(6): require(False)

status, payload = dispatch_api("GET", "/api/cognition/long-session-multi-day-soak-consolidated-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1195.9")
require(payload["data"]["summary"]["soak_mode_count"] == 2)
require(payload["data"]["summary"]["domain_count"] == 9)
require(payload["data"]["summary"]["decision_count"] == 3)
require(payload["data"]["summary"]["reliability_event_class_count"] == 8)
require(payload["data"]["summary"]["actual_waiting_started"] is False)
require(payload["data"]["summary"]["execution_invoked"] is False)
status_post, payload_post = dispatch_api("POST", "/api/cognition/long-session-multi-day-soak-consolidated-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("long-session-multi-day-soak-consolidated-checkpoint-panel" in html)
require("long-session-multi-day-soak-consolidated-checkpoint-state" in html)
require("long-session-multi-day-soak-consolidated-checkpoint-summary" in html)
require("/api/cognition/long-session-multi-day-soak-consolidated-checkpoint" in html)
require("next bounded unit: v1196.0-v1196.2" in html.lower())
require("no real waiting" in html.lower())
require("global pass not claimed" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "README_RELEASE_HISTORY.md", "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1195.9" in text or "v1195_9" in text)
    require("v1196.0-v1196.2" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1195.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1195.8"' in metadata)
require("Long-Session and Multi-Day Soak Checkpoint" in metadata)
require('WORKING_SOURCE_VERSION = "1195.8"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1195.5"' in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1195.9-long-session-multi-day-soak-checkpoint") == 1)
require(release.count("v1195_9_long_session_multi_day_soak_checkpoint_tests.py") == 1)

print(f"v1195.9 long-session multi-day soak checkpoint: {sum(checks)}/{len(checks)} PASS")
