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

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.supervised_sandbox_testing_repair_checkpoint import build_supervised_sandbox_testing_repair_checkpoint

checks: list[bool] = []

def require(value: object) -> None:
    checks.append(bool(value))

with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_supervised_sandbox_testing_repair_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 120)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    for key in (
        "supervised_sandbox_testing_repair_checkpoint_completed",
        "retained_supervised_implementation_checkpoint_completed",
        "sandbox_test_review_exercised", "sandbox_test_execution_exercised",
        "pass_failure_timeout_blocked_evidence_exercised",
        "conservative_diagnosis_exercised", "operator_diagnosis_review_exercised",
        "repair_retest_planning_exercised", "tamper_and_boundary_rejection_exercised",
    ):
        require(report[key])
    for key in (
        "production_source_read", "production_source_modified", "raw_source_exposed",
        "raw_test_output_exposed", "raw_patch_exposed", "patch_created",
        "patch_applied_to_source", "repair_performed", "tests_rerun", "shell_invoked",
        "automatic_approval_created", "automatic_authorization_granted",
        "repair_authorized", "retest_authorized", "source_application_authorized",
        "execution_invoked", "registered_tool_invoked", "provider_contacted",
        "model_operation_performed", "source_edit_performed", "production_runtime_mutated",
        "memory_mutated", "installation_performed", "promotion_performed",
        "certification_performed", "release_authorized", "source_modified", "runtime_mutated",
    ):
        require(report[key] is False)
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    summary = report["summary"]
    require(summary["retained_checkpoint_count"] == 1)
    require(summary["sandbox_test_review_case_count"] == 3)
    require(summary["sandbox_execution_case_count"] == 2)
    require(summary["evidence_outcome_case_count"] == 4)
    require(summary["diagnosis_case_count"] == 4)
    require(summary["repair_review_decision_case_count"] == 3)
    require(summary["repair_plan_case_count"] == 3)
    require(summary["negative_boundary_case_count"] >= 10)
    require(summary["maximum_tests"] == 8)
    require(summary["maximum_timeout_seconds"] == 30)
    require(summary["maximum_test_results"] == 8)
    require(summary["maximum_diagnoses"] == 8)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "supervised-sandbox-testing-repair-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched["read_only"])
    require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
    require(dispatched["checkpoint_summary"]["ok"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry["checkpoints"] if item["checkpoint_id"] == "supervised-sandbox-testing-repair-checkpoint"), None)
require(row is not None)
require(row["builder"] == "build_supervised_sandbox_testing_repair_checkpoint")
require(row["contract_version"] == "v1182.9")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "supervised-sandbox-testing-repair-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=900,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1182.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api("GET", "/api/cognition/supervised-sandbox-testing-repair-checkpoint")
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1182.9")
post_status, _ = dispatch_api(
    "POST", "/api/cognition/supervised-sandbox-testing-repair-checkpoint", body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("supervised-sandbox-testing-repair-checkpoint-panel" in dashboard)
require("/api/cognition/supervised-sandbox-testing-repair-checkpoint" in dashboard)
require("refreshSupervisedSandboxTestingRepairCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(bool(working_match) and tuple(map(int, working_match.groups())) >= (1182, 9))
require(bool(previous_match) and tuple(map(int, previous_match.groups())) >= (1182, 8))
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
require("v1182.9" in next_steps and "v1183.0-v1183.2" in next_steps and "v1200" in next_steps)
require("v1182.9 Supervised Sandbox Testing and Repair" in history)
require("Current source: v1182.9" in roadmap and "v1180-v1184" in roadmap and "v1200" in roadmap)
require("v1182.9 Supervised Sandbox Testing and Repair" in readme)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1182.9-supervised-sandbox-testing-repair-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1182_9_supervised_sandbox_testing_repair_checkpoint_tests.py") == 1)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1182.9-supervised-sandbox-testing-repair-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "production_source_modified": False,
    "repair_performed": False,
    "tests_rerun": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
