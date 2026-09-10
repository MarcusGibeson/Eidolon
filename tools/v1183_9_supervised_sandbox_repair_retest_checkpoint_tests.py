from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.supervised_sandbox_repair_retest_checkpoint import (
    build_supervised_sandbox_repair_retest_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory(prefix="eidolon-v1183-9-tests-") as directory:
    runtime = Path(directory) / "runtime"
    report = build_supervised_sandbox_repair_retest_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report.get("ok") is True)
    require(report.get("passed") == report.get("total"))
    require(int(report.get("total") or 0) >= 240)
    require(report.get("contract_version") == "v1183.9")
    require(report.get("checkpoint_id") == "supervised-sandbox-repair-retest:v1183.9")
    require(report.get("read_only") is True)
    require(report.get("post_available") is False)
    require(report.get("content_free") is True)
    require(report.get("authority_preserved") is True)
    require(report.get("operator_review_required") is True)
    require(report.get("operator_promotion_required") is True)
    require(report.get("desktop_verification_deferred_until_v1200") is True)
    for key in (
        "supervised_sandbox_repair_retest_checkpoint_completed",
        "retained_repair_draft_checkpoint_completed",
        "retained_repair_materialization_checkpoint_completed",
        "retained_governed_retesting_checkpoint_completed",
        "compile_timeout_blocked_repair_lineage_exercised",
        "operator_repair_review_exercised",
        "isolated_sandbox_repair_materialization_exercised",
        "rollback_evidence_exercised",
        "separate_operator_retest_review_exercised",
        "before_after_evidence_exercised",
        "persistent_failure_detection_exercised",
        "regression_detection_exercised",
        "bounded_repair_results_exercised",
        "tamper_stale_drift_and_materialization_replay_boundary_rejection_exercised",
        "retest_review_single_use_receipt_exercised",
    ):
        require(report.get(key) is True)
    for key in (
        "production_source_read",
        "production_source_modified",
        "source_modified",
        "runtime_mutated",
        "raw_source_exposed",
        "raw_patch_exposed",
        "raw_test_output_exposed",
        "private_evidence_exposed",
        "private_reasoning_exposed",
        "patch_applied_to_source",
        "repair_applied_to_production",
        "rollback_executed",
        "shell_invoked",
        "registered_tool_invoked",
        "provider_contacted",
        "model_operation_performed",
        "production_runtime_mutated",
        "memory_mutated",
        "automatic_approval_created",
        "automatic_authorization_granted",
        "source_application_authorized",
        "installation_performed",
        "promotion_performed",
        "certification_performed",
        "release_authorized",
        "durable_retest_replay_prevention_available",
    ):
        require(report.get(key) is False)
    require(report.get("forbidden_report_value_count") == 0)
    require(len(str(report.get("structural_digest") or "")) == 64)
    summary = report.get("summary") or {}
    require(summary.get("retained_checkpoint_count") == 3)
    require(summary.get("successful_repair_case_count") == 3)
    require(summary.get("persistent_failure_case_count") == 1)
    require(summary.get("regression_case_count") == 1)
    require(summary.get("repair_review_decision_case_count") == 3)
    require(summary.get("retest_review_decision_case_count") == 3)
    require(summary.get("public_summary_case_count") == 15)
    require(int(summary.get("negative_boundary_case_count") or 0) >= 16)
    require(summary.get("rollback_evidence_case_count") == 5)
    require(summary.get("open_limitation_count") == 7)
    require(summary.get("maximum_retests") == 8)
    require(summary.get("maximum_retest_timeout_seconds") == 30)
    require(summary.get("privacy_forbidden_entry_count") == 0)
    require(summary.get("privacy_content_finding_count") == 0)
    require(len(report.get("limitations") or []) == 7)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "supervised-sandbox-repair-retest-checkpoint",
        source_root=ROOT,
        runtime_root=runtime,
    )
    require(dispatched.get("read_only") is True)
    require(dispatched.get("source_modified") is False)
    require(dispatched.get("runtime_mutated") is False)
    require((dispatched.get("checkpoint_summary") or {}).get("ok") is True)
    require((dispatched.get("checkpoint_summary") or {}).get("registered_contract_version") == "v1183.9")

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "supervised-sandbox-repair-retest-checkpoint"),
    None,
)
require(row is not None)
require((row or {}).get("builder") == "build_supervised_sandbox_repair_retest_checkpoint")
require((row or {}).get("contract_version") == "v1183.9")
require((row or {}).get("read_only") is True)
require((row or {}).get("post_available") is False)
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))

with tempfile.TemporaryDirectory(prefix="eidolon-v1183-9-cli-") as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "supervised-sandbox-repair-retest-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=900,
        check=False,
    )
    require(cli.returncode == 0)
    cli_payload = json.loads(cli.stdout)
    require(cli_payload.get("contract_version") == "v1183.9")
    require(cli_payload.get("ok") is True)
    require(cli_payload.get("read_only") is True)

status, payload = dispatch_api("GET", "/api/cognition/supervised-sandbox-repair-retest-checkpoint")
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1183.9")
require((payload.get("data") or {}).get("ok") is True)
post_status, _ = dispatch_api(
    "POST",
    "/api/cognition/supervised-sandbox-repair-retest-checkpoint",
    body={"confirm": True},
)
require(post_status in (404, 405))

dashboard_path = ROOT / "conscious_agent" / "dashboard_first_use.py"
dashboard = dashboard_path.read_text(encoding="utf-8")
require("supervised-sandbox-repair-retest-checkpoint-panel" in dashboard)
require("/api/cognition/supervised-sandbox-repair-retest-checkpoint" in dashboard)
require("refreshSupervisedSandboxRepairRetestCheckpoint" in dashboard)
require("refreshSupervisedSandboxRetestingCheckpoint" in dashboard)
require("refreshSupervisedSandboxRepairRetestCheckpoint();" in dashboard)
require("refreshSupervisedSandboxRetestingCheckpoint();" in dashboard)
require("checkpoint remains v1183.9" not in dashboard)
require("Next bounded unit: v1184.0-v1184.2" in dashboard)
require(re.search(r"async function refreshSupervisedSandboxRetestingCheckpoint\(\)\{\{.*?/api/cognition/supervised-sandbox-retesting-checkpoint.*?\n\}\}", dashboard, re.S) is not None)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1183.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1183.8"' in metadata)
require("v1183.9 Supervised Sandbox Repair and Retest Checkpoint" in metadata)
require("v1184.0-v1184.2 Complete Supervised Project-Development Loop Foundations" in metadata)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1183.9 Supervised Sandbox Repair and Retest Checkpoint" in readme)
require("Current source: v1183.9" in readme)
require("v1184.0-v1184.2" in readme)
require("Current source: v1183.9" in next_steps)
require("Complete supervised project-development loop" in next_steps)
require("v1183.9" in roadmap and "v1184.0-v1184.2" in roadmap and "v1200" in roadmap)
require("v1183.9 Supervised Sandbox Repair and Retest Checkpoint" in history)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1183.9-supervised-sandbox-repair-retest-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1183_9_supervised_sandbox_repair_retest_checkpoint_tests.py") == 1)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1183.9-supervised-sandbox-repair-retest-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "production_source_modified": False,
    "repair_applied_to_production": False,
    "rollback_executed": False,
    "authority_expanded": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
