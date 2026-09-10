from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1197-2-data-"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.runtime_lifecycle_migration import (
    LIFECYCLE_OPERATIONS,
    _digest,
    assess_runtime_lifecycle,
    create_lifecycle_evidence,
    create_lifecycle_plan,
    public_runtime_lifecycle_summary,
)
from conscious_agent.runtime_lifecycle_migration_checkpoint import build_runtime_lifecycle_migration_checkpoint

checks: list[bool] = []

def require(value: object) -> None:
    checks.append(bool(value))
    assert value

def d(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

with tempfile.TemporaryDirectory(prefix="eidolon-v1197-2-") as temp:
    runtime = Path(temp) / "runtime-must-not-exist"
    report = build_runtime_lifecycle_migration_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(not runtime.exists())

for key, expected in (
    ("ok", True), ("contract_version", "v1197.2"), ("read_only", True), ("post_available", False),
    ("content_free", True), ("source_unchanged", True), ("runtime_mutated", False),
    ("production_source_modified", False), ("runtime_read", False), ("backup_created", False),
    ("migration_applied", False), ("upgrade_applied", False), ("rollback_applied", False),
    ("fresh_install_performed", False), ("files_written", False), ("files_deleted", False),
    ("approval_created", False), ("approval_consumed", False), ("provider_contacted", False),
    ("model_contacted", False), ("thread_started", False), ("process_started", False),
    ("automatic_continuation", False), ("global_profile_pass_claimed", False), ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 70)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 25)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1197.2"), ("status", "ready_for_operator_review"),
    ("source_version", "1196.9"), ("target_version", "1197.2"),
    ("source_schema_version", "1.0"), ("target_schema_version", "2.0"),
    ("operation_count", 5), ("operations", list(LIFECYCLE_OPERATIONS)),
    ("exact_lineage_verified", True), ("backup_truth_preserved", True),
    ("rollback_truth_preserved", True), ("original_runtime_preserved", True),
    ("fresh_install_isolated", True), ("content_free", True), ("runtime_read", False),
    ("backup_created", False), ("migration_applied", False), ("upgrade_applied", False),
    ("rollback_applied", False), ("fresh_install_performed", False), ("files_written", False),
    ("files_deleted", False), ("runtime_mutated", False), ("source_modified", False),
    ("provider_contacted", False), ("model_contacted", False), ("thread_started", False),
    ("process_started", False), ("approval_created", False), ("approval_consumed", False),
    ("automatic_continuation", False), ("global_profile_pass_claimed", False),
    ("authority_state", "separate_not_granted"), ("error_count", 0),
):
    require(summary.get(key) == expected)
require(len(summary["assessment_digest"]) == 64)

for name in (
    "duplicate-id", "broken-lineage", "stale-snapshot", "stale-context", "unsupported-operation",
    "unsupported-state", "malformed-digest", "private-field", "backup-truth", "rollback-truth",
    "runtime-loss", "fresh-install-isolation", "runtime-read", "backup-created", "migration-applied",
    "upgrade-applied", "rollback-applied", "fresh-install-performed", "files-written", "files-deleted",
    "runtime-mutation", "source-mutation", "provider-contact", "thread-start", "process-start", "approval",
    "automatic-continuation", "authority", "oversized",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

# Direct contract exercise with a distinct version transition.
snapshot = d("direct:snapshot")
context = d("direct:context")
plan = create_lifecycle_plan(
    lifecycle_id="direct-lifecycle", snapshot_digest=snapshot, context_digest=context,
    source_version="1190.9", target_version="1197.2", source_schema_version="1.1", target_schema_version="2.1",
    source_runtime_digest=d("direct:runtime"), expected_backup_digest=d("direct:backup"),
    expected_rollback_digest=d("direct:rollback"), purpose_code="direct_foundation_test",
    max_records=5, max_evidence_bytes=50_000, max_runtime_bytes=50_000_000,
)
rows = []
previous = ""
for sequence, operation in enumerate(LIFECYCLE_OPERATIONS, 1):
    row = create_lifecycle_evidence(
        lifecycle_id=plan["lifecycle_id"], evidence_id=f"direct-{operation}", operation=operation,
        sequence=sequence, snapshot_digest=snapshot, context_digest=context,
        source_version=plan["source_version"], target_version=plan["target_version"],
        source_schema_version=plan["source_schema_version"], target_schema_version=plan["target_schema_version"],
        input_runtime_digest=plan["source_runtime_digest"], output_runtime_digest=d(f"direct:output:{operation}"),
        backup_digest=plan["expected_backup_digest"], rollback_digest=plan["expected_rollback_digest"],
        manifest_digest=d(f"direct:manifest:{operation}"), artifact_digest=d(f"direct:artifact:{operation}"),
        receipt_digest=d(f"direct:receipt:{operation}"), previous_evidence_digest=previous,
        estimated_runtime_bytes=1_000_000, estimated_evidence_bytes=1_000,
        purpose_code=f"direct_{operation}_review",
    )
    rows.append(row)
    previous = row["evidence_digest"]
verification = {"content_free": True, "current_regressions_separate": True, "inherited_debt_visible": True, "global_profile_pass_claimed": False}
assessment = assess_runtime_lifecycle(plan, rows, current_snapshot_digest=snapshot, current_context_digest=context, verification_summary=verification)
require(assessment["status"] == "ready_for_operator_review")
require(not assessment["errors"])
direct_summary = public_runtime_lifecycle_summary(assessment)
require(direct_summary["operation_count"] == 5)
require(direct_summary["operations"] == list(LIFECYCLE_OPERATIONS))
require(direct_summary["backup_truth_preserved"] is True)
require(direct_summary["rollback_truth_preserved"] is True)
require(direct_summary["fresh_install_isolated"] is True)
require(direct_summary["runtime_mutated"] is False)
require(direct_summary["authority_state"] == "separate_not_granted")

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "runtime-lifecycle-migration-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1197.2")
require((descriptor or {}).get("builder") == "build_runtime_lifecycle_migration_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "runtime-lifecycle-migration-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1197-2-cli-")},
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1197.2")
    require(cli_report["summary"]["operation_count"] == 5)
    require(cli_report["summary"]["runtime_mutated"] is False)
    require(cli_report["summary"]["fresh_install_performed"] is False)
except Exception:
    for _ in range(5): require(False)

status, payload = dispatch_api("GET", "/api/cognition/runtime-lifecycle-migration-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1197.2")
require(payload["data"]["summary"]["operation_count"] == 5)
require(payload["data"]["summary"]["backup_created"] is False)
require(payload["data"]["summary"]["rollback_applied"] is False)
status_post, payload_post = dispatch_api("POST", "/api/cognition/runtime-lifecycle-migration-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("runtime-lifecycle-migration-checkpoint-panel" in html)
require("runtime-lifecycle-migration-checkpoint-state" in html)
require("runtime-lifecycle-migration-checkpoint-summary" in html)
require("/api/cognition/runtime-lifecycle-migration-checkpoint" in html)
require("v1197.3-v1197.5" in html)
require("no runtime data" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md",
    "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1197.0-v1197.2" in text or "v1197_0_2" in text)
    require("v1197.3-v1197.5" in text)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1197.2"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1196.9"' in metadata)
require("Runtime Migration, Backup, Upgrade, Rollback, and Fresh-Install Foundations" in metadata)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1197.2-runtime-lifecycle-migration") == 1)
require(release.count("v1197_0_2_runtime_lifecycle_migration_tests.py") == 1)

print(f"v1197.0-v1197.2 runtime lifecycle migration foundations: {sum(checks)}/{len(checks)} PASS")
