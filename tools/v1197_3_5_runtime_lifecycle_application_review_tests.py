from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1197-5-data-"))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.runtime_lifecycle_application_review import (
    CONTRACT_VERSION,
    DECISIONS,
    REASON_CODES,
    REVIEW_ACTIONS,
    REVIEW_ACTION_BY_OPERATION,
    _digest,
    build_lifecycle_application_review_decision,
    build_lifecycle_application_review_request,
    public_lifecycle_application_review_summary,
    review_runtime_lifecycle_application,
)
from conscious_agent.runtime_lifecycle_application_review_checkpoint import (
    build_runtime_lifecycle_application_review_checkpoint,
)
from conscious_agent.runtime_lifecycle_migration import LIFECYCLE_OPERATIONS

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


def d(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


with tempfile.TemporaryDirectory(prefix="eidolon-v1197-5-") as temp:
    runtime = Path(temp) / "runtime-must-not-exist"
    report = build_runtime_lifecycle_application_review_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(not runtime.exists())

for key, expected in (
    ("ok", True), ("contract_version", "v1197.5"), ("read_only", True),
    ("post_available", False), ("content_free", True), ("source_unchanged", True),
    ("runtime_mutated", False), ("production_source_modified", False),
    ("runtime_read", False), ("backup_created", False), ("migration_applied", False),
    ("upgrade_applied", False), ("rollback_applied", False),
    ("fresh_install_performed", False), ("files_written", False), ("files_deleted", False),
    ("approval_created", False), ("approval_consumed", False),
    ("provider_contacted", False), ("model_contacted", False),
    ("thread_started", False), ("process_started", False),
    ("automatic_continuation", False), ("application_authorized", False),
    ("operation_executed", False), ("global_profile_pass_claimed", False),
    ("authority_granted", False),
):
    require(report.get(key) == expected)
require(report["passed"] == report["total"])
require(report["total"] >= 200)
require(len(report["limitations"]) == 5)
require(len(report["blocked_cases"]) >= 45)

summary = report["summary"]
for key, expected in (
    ("contract_version", "v1197.5"),
    ("review_count", len(LIFECYCLE_OPERATIONS) * len(DECISIONS)),
    ("operation_count", len(LIFECYCLE_OPERATIONS)),
    ("operations", list(LIFECYCLE_OPERATIONS)),
    ("decision_count", len(DECISIONS)),
    ("decisions", list(DECISIONS)),
    ("all_reviews_valid", True), ("content_free", True), ("presentation_only", True),
    ("exact_lineage_verified", True), ("original_runtime_preserved", True),
    ("backup_truth_preserved", True), ("rollback_truth_preserved", True),
    ("fresh_install_isolation_preserved", True),
    ("separate_application_authorization_required", True),
    ("runtime_read", False), ("backup_created", False), ("migration_applied", False),
    ("upgrade_applied", False), ("rollback_applied", False),
    ("fresh_install_performed", False), ("files_written", False), ("files_deleted", False),
    ("runtime_mutated", False), ("source_modified", False),
    ("provider_contacted", False), ("model_contacted", False),
    ("thread_started", False), ("process_started", False),
    ("approval_created", False), ("approval_consumed", False),
    ("automatic_continuation", False), ("application_authorized", False),
    ("operation_executed", False), ("global_profile_pass_claimed", False),
    ("authority_state", "separate_not_granted"), ("authority_granted", False),
):
    require(summary.get(key) == expected)
require(tuple(REVIEW_ACTION_BY_OPERATION) == LIFECYCLE_OPERATIONS)
require(tuple(REVIEW_ACTION_BY_OPERATION[operation] for operation in LIFECYCLE_OPERATIONS) == REVIEW_ACTIONS)
require(DECISIONS == ("approve", "reject", "defer"))
require("evidence_sufficient" in REASON_CODES)

for name in (
    "stale-snapshot", "stale-context", "stale-plan", "stale-evidence", "stale-assessment",
    "wrong-operation", "unsupported-action", "wrong-sequence", "runtime-read", "backup-created",
    "migration-applied", "upgrade-applied", "rollback-applied", "fresh-install", "files-written",
    "files-deleted", "runtime-mutated", "source-modified", "provider-contact", "model-contact",
    "thread-start", "process-start", "approval-created", "approval-consumed",
    "automatic-continuation", "application-authority", "authority", "private-field",
    "unsupported-decision", "request-mismatch", "bad-operator-digest", "unsupported-reason",
    "operation-executed", "decision-runtime-read", "decision-files-written", "decision-files-deleted",
    "decision-runtime-mutated", "decision-source-modified", "decision-provider", "decision-model",
    "decision-thread", "decision-process", "decision-approval-created", "decision-approval-consumed",
    "decision-continuation", "application-authorized", "authority-granted", "decision-private",
):
    require(name in report["blocked_cases"])
    require(bool(report["blocked_cases"][name]))

# Direct contract exercise with exact five-operation review lineage.
lifecycle_id = "direct-runtime-lifecycle"
snapshot = d("direct:snapshot")
context = d("direct:context")
plan = d("direct:plan")
assessment = d("direct:assessment")
previous = ""
results = []
for sequence, operation in enumerate(LIFECYCLE_OPERATIONS, 1):
    request = build_lifecycle_application_review_request(
        review_id=f"direct:{operation}", lifecycle_id=lifecycle_id, operation=operation,
        sequence=sequence, snapshot_digest=snapshot, context_digest=context,
        plan_digest=plan, evidence_digest=d(f"direct:evidence:{operation}"),
        assessment_digest=assessment, previous_review_receipt_digest=previous,
        purpose_code=f"direct_{operation}_review",
    )
    require(request["action"] == REVIEW_ACTION_BY_OPERATION[operation])
    require(request["request_digest"] == _digest({k: v for k, v in request.items() if k != "request_digest"}))
    decision = build_lifecycle_application_review_decision(
        request_digest=request["request_digest"], decision="approve",
        operator_review_digest=d(f"direct:operator:{operation}"), reason_code="evidence_sufficient",
    )
    result = review_runtime_lifecycle_application(
        request=request, decision=decision, expected_lifecycle_id=lifecycle_id,
        expected_operation=operation, expected_sequence=sequence,
        expected_snapshot_digest=snapshot, expected_context_digest=context,
        expected_plan_digest=plan, expected_evidence_digest=d(f"direct:evidence:{operation}"),
        expected_assessment_digest=assessment,
        expected_previous_review_receipt_digest=previous,
    )
    require(result["ok"] is True)
    require(result["status"] == "application_review_approved")
    require(result["exact_lineage_verified"] is True)
    require(result["operation_executed"] is False)
    require(result["application_authorized"] is False)
    require(result["authority_granted"] is False)
    require(len(result["review_receipt_digest"]) == 64)
    results.append(result)
    previous = result["review_receipt_digest"]

direct_summary = public_lifecycle_application_review_summary(results)
require(direct_summary["review_count"] == 5)
require(direct_summary["operation_count"] == 5)
require(direct_summary["decision_count"] == 1)
require(direct_summary["all_reviews_valid"] is True)
require(direct_summary["runtime_mutated"] is False)
require(direct_summary["application_authorized"] is False)
require(direct_summary["authority_state"] == "separate_not_granted")

# Tamper and broken-lineage checks not dependent on the checkpoint's negative matrix.
request = build_lifecycle_application_review_request(
    review_id="tamper", lifecycle_id=lifecycle_id, operation="backup", sequence=1,
    snapshot_digest=snapshot, context_digest=context, plan_digest=plan,
    evidence_digest=d("tamper:evidence"), assessment_digest=assessment,
    previous_review_receipt_digest="", purpose_code="tamper_test",
)
decision = build_lifecycle_application_review_decision(
    request_digest=request["request_digest"], decision="defer",
    operator_review_digest=d("tamper:operator"), reason_code="more_evidence_required",
)
tampered_request = dict(request); tampered_request["purpose_code"] = "changed"
tampered = review_runtime_lifecycle_application(
    request=tampered_request, decision=decision, expected_lifecycle_id=lifecycle_id,
    expected_operation="backup", expected_sequence=1, expected_snapshot_digest=snapshot,
    expected_context_digest=context, expected_plan_digest=plan,
    expected_evidence_digest=d("tamper:evidence"), expected_assessment_digest=assessment,
    expected_previous_review_receipt_digest="",
)
require(tampered["ok"] is False)
require("request_tamper" in tampered["errors"])
require(tampered["operation_executed"] is False)

broken_request = build_lifecycle_application_review_request(
    review_id="broken", lifecycle_id=lifecycle_id, operation="migration", sequence=2,
    snapshot_digest=snapshot, context_digest=context, plan_digest=plan,
    evidence_digest=d("broken:evidence"), assessment_digest=assessment,
    previous_review_receipt_digest=d("wrong-prior"), purpose_code="broken_lineage",
)
broken_decision = build_lifecycle_application_review_decision(
    request_digest=broken_request["request_digest"], decision="reject",
    operator_review_digest=d("broken:operator"), reason_code="evidence_rejected",
)
broken = review_runtime_lifecycle_application(
    request=broken_request, decision=broken_decision, expected_lifecycle_id=lifecycle_id,
    expected_operation="migration", expected_sequence=2, expected_snapshot_digest=snapshot,
    expected_context_digest=context, expected_plan_digest=plan,
    expected_evidence_digest=d("broken:evidence"), expected_assessment_digest=assessment,
    expected_previous_review_receipt_digest=d("actual-prior"),
)
require(broken["ok"] is False)
require("broken_review_lineage" in broken["errors"])
require(broken["authority_granted"] is False)

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next((row for row in registry["checkpoints"] if row["checkpoint_id"] == "runtime-lifecycle-application-review-checkpoint"), None)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == "v1197.5")
require((descriptor or {}).get("builder") == "build_runtime_lifecycle_application_review_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "runtime-lifecycle-application-review-checkpoint"],
    cwd=ROOT, text=True, capture_output=True,
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1197-5-cli-")},
)
require(process.returncode == 0)
try:
    cli_report = json.loads(process.stdout.strip().splitlines()[-1])
    require(cli_report["ok"] is True)
    require(cli_report["contract_version"] == "v1197.5")
    require(cli_report["summary"]["operation_count"] == 5)
    require(cli_report["summary"]["decision_count"] == 3)
    require(cli_report["summary"]["operation_executed"] is False)
    require(cli_report["summary"]["application_authorized"] is False)
except Exception:
    for _ in range(6):
        require(False)

status, payload = dispatch_api("GET", "/api/cognition/runtime-lifecycle-application-review-checkpoint", {}, None)
require(status == 200)
require(payload["ok"] is True)
require(payload["data"]["contract_version"] == "v1197.5")
require(payload["data"]["summary"]["operation_count"] == 5)
require(payload["data"]["summary"]["decision_count"] == 3)
require(payload["data"]["summary"]["runtime_mutated"] is False)
require(payload["data"]["summary"]["authority_granted"] is False)
status_post, payload_post = dispatch_api("POST", "/api/cognition/runtime-lifecycle-application-review-checkpoint", {}, {})
require(status_post in {404, 405})
require(payload_post.get("ok") is False)

html = render_first_use_shell()
require("runtime-lifecycle-application-review-checkpoint-panel" in html)
require("runtime-lifecycle-application-review-checkpoint-state" in html)
require("runtime-lifecycle-application-review-checkpoint-summary" in html)
require("/api/cognition/runtime-lifecycle-application-review-checkpoint" in html)
require("v1197.6-v1197.8" in html)
require("presentation-only" in html.lower())
require("no runtime data" in html.lower())

for relative in (
    "README.md", "README_NEXT_STEPS.md", "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md", "README_RELEASE_HISTORY.md",
    "conscious_agent/release_metadata.py", "tools/release_verify.py",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    require("v1197.3-v1197.5" in text or "v1197_3_5" in text)
    require("v1197.6-v1197.8" in text)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1197.5"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1197.2"' in metadata)
require("Operator-Reviewed Runtime Lifecycle Application" in metadata)
require('WORKING_SOURCE_VERSION = "1197.2"' in metadata)
release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release.count("v1197.5-runtime-lifecycle-application-review") == 1)
require(release.count("v1197_3_5_runtime_lifecycle_application_review_tests.py") == 1)
require(release.count("v1197.2-runtime-lifecycle-migration") == 1)
require(release.count("v1197_0_2_runtime_lifecycle_migration_tests.py") == 1)

print(f"v1197.3-v1197.5 runtime lifecycle application review: {sum(checks)}/{len(checks)} PASS")
