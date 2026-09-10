from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1197-8-data-"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.runtime_lifecycle_reliability_adversarial import (
    CONTRACT_VERSION,
    EVENT_CLASSES,
    OPERATIONS,
    _digest,
    build_runtime_lifecycle_reliability_event,
    inspect_runtime_lifecycle_reliability_event,
    public_runtime_lifecycle_reliability_summary,
)
from conscious_agent.runtime_lifecycle_reliability_adversarial_checkpoint import (
    build_runtime_lifecycle_reliability_adversarial_checkpoint,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


report = build_runtime_lifecycle_reliability_adversarial_checkpoint(source_root=ROOT)
require(report["ok"] is True)
require(report["passed"] == report["total"])
require(report["contract_version"] == "v1197.8")
require(report["summary"]["event_count"] == 8)
require(report["summary"]["event_class_count"] == 8)
require(report["summary"]["operation_count"] == 5)
require(report["summary"]["all_events_valid"] is True)
for field in (
    "runtime_read", "backup_created", "migration_applied", "upgrade_applied",
    "rollback_applied", "fresh_install_performed", "automatic_recovery",
    "automatic_retry", "runtime_mutated", "authority_granted", "global_profile_pass_claimed",
):
    require(report["summary"][field] is False)

for name in (
    "stale-lifecycle", "stale-snapshot", "stale-context", "stale-plan", "stale-evidence",
    "stale-assessment", "stale-review", "stale-runtime", "stale-backup", "stale-rollback",
    "stale-manifest", "unsupported-event", "unsupported-operation", "wrong-sequence", "latency",
    "foreground-block", "runtime-loss", "backup-truth-loss", "rollback-truth-loss",
    "runtime-touched", "runtime-read", "backup-created", "migration-applied", "upgrade-applied",
    "rollback-applied", "fresh-install", "files-written", "files-deleted", "recovery", "retry",
    "provider", "model", "thread", "process", "approval-created", "approval-consumed",
    "runtime-mutated", "source-modified", "global-pass", "authority", "authority-state",
    "private-field", "tamper", "broken-lineage",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

lifecycle_id = "direct:v1197.8"
snapshot = h("direct:snapshot")
context = h("direct:context")
plan = h("direct:plan")
assessment = h("direct:assessment")
review = h("direct:review")
source_runtime = h("direct:source-runtime")
backup = h("direct:backup")
rollback = h("direct:rollback")
manifest = h("direct:manifest")
operation_by_event = {
    "stale_runtime_state": "backup",
    "backup_integrity_failure": "backup",
    "migration_interruption": "migration",
    "upgrade_interruption": "upgrade",
    "rollback_failure": "rollback",
    "fresh_install_contamination": "fresh_install",
    "schema_compatibility_drift": "upgrade",
    "recovery_reentry": "rollback",
}
metrics = {
    "stale_runtime_state": {"integrity_failure_count": 1},
    "backup_integrity_failure": {"integrity_failure_count": 1},
    "migration_interruption": {"interruption_count": 1},
    "upgrade_interruption": {"interruption_count": 1},
    "rollback_failure": {"rollback_failure_count": 1},
    "fresh_install_contamination": {"contamination_finding_count": 1},
    "schema_compatibility_drift": {"schema_drift_score": 5},
    "recovery_reentry": {"recovery_reentry_count": 2},
}
previous = ""
results = []
for sequence, event_class in enumerate(EVENT_CLASSES, 1):
    operation = operation_by_event[event_class]
    evidence = h(f"direct:evidence:{operation}")
    event = build_runtime_lifecycle_reliability_event(
        event_id=f"direct:{event_class}", lifecycle_id=lifecycle_id,
        event_class=event_class, operation=operation, sequence=sequence,
        snapshot_digest=snapshot, context_digest=context, plan_digest=plan,
        evidence_digest=evidence, assessment_digest=assessment,
        application_review_receipt_digest=review,
        source_runtime_digest=source_runtime, backup_digest=backup,
        rollback_digest=rollback, manifest_digest=manifest,
        artifact_digest=h(f"direct:artifact:{sequence}"),
        receipt_digest=h(f"direct:receipt:{sequence}"),
        previous_event_receipt_digest=previous,
        foreground_latency_ms=10, latency_budget_ms=250,
        **metrics[event_class],
    )
    require(event["event_digest"] == _digest({k: v for k, v in event.items() if k != "event_digest"}))
    result = inspect_runtime_lifecycle_reliability_event(
        event=event, expected_lifecycle_id=lifecycle_id,
        expected_operation=operation, expected_sequence=sequence,
        expected_snapshot_digest=snapshot, expected_context_digest=context,
        expected_plan_digest=plan, expected_evidence_digest=evidence,
        expected_assessment_digest=assessment,
        expected_application_review_receipt_digest=review,
        expected_source_runtime_digest=source_runtime,
        expected_backup_digest=backup, expected_rollback_digest=rollback,
        expected_manifest_digest=manifest,
        expected_previous_event_receipt_digest=previous,
    )
    require(result["ok"] is True)
    require(result["status"] == "reliability_evidence_ready")
    require(result["exact_lineage_verified"] is True)
    require(result["original_runtime_preserved"] is True)
    require(result["backup_truth_preserved"] is True)
    require(result["rollback_truth_preserved"] is True)
    require(result["existing_runtime_untouched"] is True)
    require(result["foreground_available"] is True)
    require(result["recovery_review_required"] is True)
    for field in (
        "runtime_read", "backup_created", "migration_applied", "upgrade_applied",
        "rollback_applied", "fresh_install_performed", "files_written", "files_deleted",
        "automatic_recovery", "automatic_retry", "provider_contacted", "model_contacted",
        "thread_started", "process_started", "approval_created", "approval_consumed",
        "runtime_mutated", "source_modified", "global_profile_pass_claimed", "authority_granted",
    ):
        require(result[field] is False)
    require(len(result["reliability_receipt_digest"]) == 64)
    previous = result["reliability_receipt_digest"]
    results.append(result)

summary = public_runtime_lifecycle_reliability_summary(results)
require(summary["event_count"] == len(EVENT_CLASSES))
require(summary["event_class_count"] == len(EVENT_CLASSES))
require(summary["operation_count"] == len(OPERATIONS))
require(summary["all_events_valid"] is True)
require(summary["exact_lineage_verified"] is True)
require(summary["runtime_mutated"] is False)
require(summary["authority_state"] == "separate_not_granted")

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "runtime-lifecycle-reliability-adversarial-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1197.8")
require((descriptor or {}).get("builder") == "build_runtime_lifecycle_reliability_adversarial_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "runtime-lifecycle-reliability-adversarial-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1197-8-cli-")},
)
require(process.returncode == 0)
cli_report = json.loads(process.stdout.strip().splitlines()[-1])
require(cli_report["ok"] is True)
require(cli_report["contract_version"] == "v1197.8")
require(cli_report["summary"]["event_class_count"] == 8)
require(cli_report["summary"]["runtime_mutated"] is False)
require(cli_report["summary"]["authority_granted"] is False)

status, payload = dispatch_api("GET", "/api/cognition/runtime-lifecycle-reliability-adversarial-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1197.8")
require(payload["data"]["summary"]["event_class_count"] == 8)
require(payload["data"]["summary"]["runtime_mutated"] is False)
require(payload["data"]["summary"]["authority_granted"] is False)
status_post, payload_post = dispatch_api("POST", "/api/cognition/runtime-lifecycle-reliability-adversarial-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("runtime-lifecycle-reliability-adversarial-checkpoint-panel" in html)
require("runtime-lifecycle-reliability-adversarial-checkpoint-state" in html)
require("runtime-lifecycle-reliability-adversarial-checkpoint-summary" in html)
require("/api/cognition/runtime-lifecycle-reliability-adversarial-checkpoint" in html)
require("v1197.9" in html)
require("evidence-only" in html.lower())
require("no runtime data" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md",
    "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1197.6-v1197.8" in text or "v1197_6_8" in text)
    require("v1197.9" in text)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1197.8"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1197.5"' in metadata)
require("Runtime Lifecycle Reliability and Adversarial Hardening" in metadata)
require('WORKING_SOURCE_VERSION = "1197.5"' in metadata)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1197.8-runtime-lifecycle-reliability-adversarial") == 1)
require(release.count("v1197_6_8_runtime_lifecycle_reliability_adversarial_tests.py") == 1)
require(release.count("v1197.5-runtime-lifecycle-application-review") == 1)

print(f"v1197.6-v1197.8 runtime lifecycle reliability adversarial: {sum(checks)}/{len(checks)} PASS")
