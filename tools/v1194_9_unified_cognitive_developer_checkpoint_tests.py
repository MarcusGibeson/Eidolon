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
os.environ.setdefault(
    "EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1194-9-data-")
)

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.unified_cognitive_developer_checkpoint import (
    CONTRACT_VERSION,
    build_unified_cognitive_developer_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


with tempfile.TemporaryDirectory(prefix="eidolon-v1194-9-") as temporary:
    report = build_unified_cognitive_developer_checkpoint(
        source_root=ROOT,
        runtime_root=Path(temporary) / "runtime",
    )

for key, expected in (
    ("ok", True),
    ("contract_version", "v1194.9"),
    ("read_only", True),
    ("post_available", False),
    ("content_free", True),
    ("source_unchanged", True),
    ("runtime_mutated", False),
    ("production_source_modified", False),
    ("subsystem_state_changed", False),
    ("approval_created", False),
    ("approval_consumed", False),
    ("automatic_continuation", False),
    ("recovery_executed", False),
    ("execution_invoked", False),
    ("provider_contacted", False),
    ("model_contacted", False),
    ("thread_started", False),
    ("process_started", False),
    ("global_profile_pass_claimed", False),
    ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 175)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 35)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1194.9"),
    ("foundation_contract_version", "v1194.2"),
    ("coordination_contract_version", "v1194.5"),
    ("reliability_contract_version", "v1194.8"),
    ("retained_checkpoint_count", 3),
    ("domain_count", 9),
    ("work_surface_count", 2),
    ("decision_count", 3),
    ("reliability_event_class_count", 8),
    ("foreground_path_available", True),
    ("background_work_separate", True),
    ("exact_expansion_verified", True),
    ("original_evidence_preserved", True),
    ("current_regressions_separate", True),
    ("inherited_debt_visible", True),
    ("approval_separate", True),
    ("navigation_accountable", True),
    ("latency_within_budget", True),
    ("historical_truth_preserved", True),
    ("content_free", True),
    ("read_only", True),
    ("subsystem_state_changed", False),
    ("approval_created", False),
    ("approval_consumed", False),
    ("automatic_continuation", False),
    ("recovery_executed", False),
    ("execution_invoked", False),
    ("runtime_mutated", False),
    ("production_source_modified", False),
    ("provider_contacted", False),
    ("model_contacted", False),
    ("thread_started", False),
    ("process_started", False),
    ("global_profile_pass_claimed", False),
    ("authority_state", "separate_not_granted"),
    ("authority_granted", False),
):
    require(summary.get(key) == expected)
require(len(summary["checkpoint_digest"]) == 64)
require(summary["blocked_case_count"] == len(report["blocked_cases"]))

for name in (
    "private-field",
    "foundation-contract-drift",
    "coordination-contract-drift",
    "reliability-contract-drift",
    "domain-count",
    "work-surface-count",
    "decision-count",
    "event-count",
    "retained-count",
    "foreground-block",
    "background-boundary-loss",
    "compaction-equivalence-loss",
    "evidence-loss",
    "verification-boundary-loss",
    "debt-hidden",
    "approval-boundary-loss",
    "navigation-accountability-loss",
    "latency-budget-loss",
    "historical-truth-loss",
    "subsystem-mutation",
    "approval-create",
    "approval-consume",
    "automatic-continuation",
    "hidden-recovery",
    "hidden-execution",
    "runtime-mutation",
    "source-mutation",
    "provider-contact",
    "model-contact",
    "thread-start",
    "process-start",
    "global-pass-claim",
    "authority-state",
    "authority",
    "tamper",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

retained = report["retained_checkpoints"]
for key, version, total in (
    ("foundations", "v1194.2", 50),
    ("coordination", "v1194.5", 89),
    ("reliability", "v1194.8", 174),
):
    require(retained[key]["contract_version"] == version)
    require(retained[key]["passed"] == total)
    require(retained[key]["total"] == total)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next(
    (
        row
        for row in registry["checkpoints"]
        if row["checkpoint_id"] == "unified-cognitive-developer-checkpoint"
    ),
    None,
)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
require((descriptor or {}).get("builder") == "build_unified_cognitive_developer_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])
for checkpoint_id in (
    "unified-cognitive-developer-experience-checkpoint",
    "unified-cognitive-developer-coordination-checkpoint",
    "unified-cognitive-developer-reliability-checkpoint",
    "unified-cognitive-developer-checkpoint",
):
    require(any(row["checkpoint_id"] == checkpoint_id for row in registry["checkpoints"]))

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "unified-cognitive-developer-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1194-9-cli-"),
    },
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1194.9")
    require(cli_report["summary"]["domain_count"] == 9)
    require(cli_report["summary"]["global_profile_pass_claimed"] is False)
except Exception:
    require(False)
    require(False)
    require(False)
    require(False)

status, payload = dispatch_api(
    "GET", "/api/cognition/unified-cognitive-developer-checkpoint", {}, None
)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1194.9")
require(payload["data"]["summary"]["domain_count"] == 9)
require(payload["data"]["summary"]["decision_count"] == 3)
require(payload["data"]["summary"]["reliability_event_class_count"] == 8)
require(payload["data"]["global_profile_pass_claimed"] is False)
status_post, payload_post = dispatch_api(
    "POST", "/api/cognition/unified-cognitive-developer-checkpoint", {}, {}
)
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("unified-cognitive-developer-checkpoint-panel" in html)
require("unified-cognitive-developer-checkpoint-state" in html)
require("unified-cognitive-developer-checkpoint-summary" in html)
require("/api/cognition/unified-cognitive-developer-checkpoint" in html)
require("global pass not claimed" in html.lower())
require("next bounded unit: v1195.0-v1195.2" in html.lower())

for relative in (
    "README.md",
    "README_NEXT_STEPS.md",
    "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "README_RELEASE_HISTORY.md",
    "conscious_agent/release_metadata.py",
    "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1194.9" in text or "v1194_9" in text)
    require("v1195.0-v1195.2" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1194.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1194.8"' in metadata)
require("Unified Cognitive and Developer Experience Checkpoint" in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1194.9-unified-cognitive-developer-checkpoint") == 1)
require(release.count("v1194_9_unified_cognitive_developer_checkpoint_tests.py") == 1)

print(
    f"v1194.9 unified cognitive developer checkpoint: "
    f"{sum(checks)}/{len(checks)} PASS"
)
