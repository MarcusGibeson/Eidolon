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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1197-9-data-"))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.runtime_lifecycle_checkpoint import (
    CONTRACT_VERSION,
    build_runtime_lifecycle_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


with tempfile.TemporaryDirectory(prefix="eidolon-v1197-9-") as temporary:
    runtime = Path(temporary) / "runtime-must-not-exist"
    report = build_runtime_lifecycle_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(not runtime.exists())

for key, expected in (
    ("ok", True), ("contract_version", "v1197.9"), ("read_only", True),
    ("post_available", False), ("content_free", True), ("source_unchanged", True),
    ("runtime_mutated", False), ("production_source_modified", False),
    ("runtime_read", False), ("backup_created", False), ("migration_applied", False),
    ("upgrade_applied", False), ("rollback_applied", False),
    ("fresh_install_performed", False), ("files_written", False), ("files_deleted", False),
    ("automatic_recovery", False), ("automatic_retry", False),
    ("recovery_executed", False), ("retry_executed", False),
    ("operation_executed", False), ("application_authorized", False),
    ("approval_created", False), ("approval_consumed", False),
    ("provider_contacted", False), ("model_contacted", False),
    ("thread_started", False), ("process_started", False),
    ("installation_performed", False), ("promotion_performed", False),
    ("certification_performed", False), ("publication_performed", False),
    ("release_performed", False), ("automatic_continuation", False),
    ("global_profile_pass_claimed", False), ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 150)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 50)
require(report["privacy"]["ok"] is True)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1197.9"),
    ("foundation_contract_version", "v1197.2"),
    ("review_contract_version", "v1197.5"),
    ("reliability_contract_version", "v1197.8"),
    ("retained_checkpoint_count", 3), ("operation_count", 5),
    ("operations", ["backup", "migration", "upgrade", "rollback", "fresh_install"]),
    ("review_action_count", 5), ("decision_count", 3),
    ("decisions", ["approve", "reject", "defer"]),
    ("review_count", 15), ("reliability_event_class_count", 8),
    ("content_free", True), ("read_only", True), ("privacy_preserved", True),
    ("authority_boundary_preserved", True), ("original_runtime_preserved", True),
    ("backup_truth_preserved", True), ("rollback_truth_preserved", True),
    ("fresh_install_isolated", True), ("existing_runtime_untouched", True),
    ("exact_lineage_verified", True), ("operator_review_accountable", True),
    ("foreground_available", True), ("recovery_review_required", True),
    ("historical_truth_preserved", True), ("current_regressions_separate", True),
    ("inherited_debt_visible", True), ("runtime_read", False),
    ("backup_created", False), ("migration_applied", False),
    ("upgrade_applied", False), ("rollback_applied", False),
    ("fresh_install_performed", False), ("files_written", False),
    ("files_deleted", False), ("automatic_recovery", False),
    ("automatic_retry", False), ("recovery_executed", False),
    ("retry_executed", False), ("operation_executed", False),
    ("application_authorized", False), ("approval_created", False),
    ("approval_consumed", False), ("runtime_mutated", False),
    ("production_source_modified", False), ("provider_contacted", False),
    ("model_contacted", False), ("thread_started", False),
    ("process_started", False), ("installation_performed", False),
    ("promotion_performed", False), ("certification_performed", False),
    ("publication_performed", False), ("release_performed", False),
    ("automatic_continuation", False), ("global_profile_pass_claimed", False),
    ("authority_state", "separate_not_granted"), ("authority_granted", False),
):
    require(summary.get(key) == expected)
require(len(summary["checkpoint_digest"]) == 64)
require(summary["blocked_case_count"] == len(report["blocked_cases"]))
require(summary["reliability_event_classes"] == [
    "stale_runtime_state", "backup_integrity_failure", "migration_interruption",
    "upgrade_interruption", "rollback_failure", "fresh_install_contamination",
    "schema_compatibility_drift", "recovery_reentry",
])

for name in (
    "private-field", "foundation-contract-drift", "review-contract-drift",
    "reliability-contract-drift", "retained-count", "operation-count",
    "review-action-count", "decision-count", "review-count",
    "reliability-event-count", "privacy-loss", "authority-boundary-loss",
    "runtime-loss", "backup-truth-loss", "rollback-truth-loss",
    "fresh-install-isolation-loss", "runtime-touched", "lineage-loss",
    "review-accountability-loss", "foreground-block", "recovery-review-loss",
    "historical-truth-loss", "verification-boundary-loss", "debt-hidden",
    "runtime-read", "backup-created", "migration-applied", "upgrade-applied",
    "rollback-applied", "fresh-install", "files-written", "files-deleted",
    "automatic-recovery", "automatic-retry", "recovery-execution",
    "retry-execution", "operation-execution", "application-authority",
    "approval-create", "approval-consume", "runtime-mutation", "source-mutation",
    "provider-contact", "model-contact", "thread-start", "process-start",
    "installation", "promotion", "certification", "publication", "release",
    "automatic-continuation", "global-pass-claim", "authority-state", "authority",
    "tamper",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

for key, version, total in (
    ("foundations", "v1197.2", 94),
    ("review", "v1197.5", 306),
    ("reliability", "v1197.8", 420),
):
    retained = report["retained_checkpoints"][key]
    require(retained["contract_version"] == version)
    require(retained["passed"] == total)
    require(retained["total"] == total)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "runtime-lifecycle-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
require((descriptor or {}).get("builder") == "build_runtime_lifecycle_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])
for checkpoint_id in (
    "runtime-lifecycle-migration-checkpoint",
    "runtime-lifecycle-application-review-checkpoint",
    "runtime-lifecycle-reliability-adversarial-checkpoint",
    "runtime-lifecycle-checkpoint",
):
    require(any(row["checkpoint_id"] == checkpoint_id for row in registry["checkpoints"]))

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "runtime-lifecycle-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1197-9-cli-")},
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1197.9")
    require(cli_report["summary"]["operation_count"] == 5)
    require(cli_report["summary"]["decision_count"] == 3)
    require(cli_report["summary"]["reliability_event_class_count"] == 8)
    require(cli_report["summary"]["runtime_mutated"] is False)
except Exception:
    for _ in range(7):
        require(False)

status, payload = dispatch_api("GET", "/api/cognition/runtime-lifecycle-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1197.9")
require(payload["data"]["summary"]["operation_count"] == 5)
require(payload["data"]["summary"]["review_count"] == 15)
require(payload["data"]["summary"]["reliability_event_class_count"] == 8)
require(payload["data"]["summary"]["runtime_mutated"] is False)
status_post, payload_post = dispatch_api("POST", "/api/cognition/runtime-lifecycle-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("runtime-lifecycle-checkpoint-panel" in html)
require("runtime-lifecycle-checkpoint-state" in html)
require("runtime-lifecycle-checkpoint-summary" in html)
require("/api/cognition/runtime-lifecycle-checkpoint" in html)
require("next bounded unit: v1198.0-v1198.2" in html.lower())
require("no runtime data" in html.lower())
require("global pass not claimed" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
    "README_RELEASE_HISTORY.md", "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1197.9" in text or "v1197_9" in text)
    require("v1198.0-v1198.2" in text)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1197.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1197.8"' in metadata)
require("Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install Checkpoint" in metadata)
require('WORKING_SOURCE_VERSION = "1197.8"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1197.5"' in metadata)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1197.9-runtime-lifecycle-checkpoint") == 1)
require(release.count("v1197_9_runtime_lifecycle_checkpoint_tests.py") == 1)
require(release.count("v1197.8-runtime-lifecycle-reliability-adversarial") == 1)

print(f"v1197.9 runtime lifecycle checkpoint: {sum(checks)}/{len(checks)} PASS")
