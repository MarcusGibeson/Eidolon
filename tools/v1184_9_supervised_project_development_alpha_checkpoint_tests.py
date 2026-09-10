from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(prefix="eidolon-v1184-9-external-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(_TEST_RUNTIME_ROOT)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.api_server import dispatch_api
from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.supervised_project_development_alpha_checkpoint import (
    build_supervised_project_development_alpha_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory(prefix="eidolon-v1184-9-tests-") as directory:
    runtime = Path(directory) / "runtime"
    report = build_supervised_project_development_alpha_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report.get("ok") is True)
    require(report.get("passed") == report.get("total"))
    require(int(report.get("total") or 0) >= 300)
    require(report.get("contract_version") == "v1184.9")
    require(report.get("checkpoint_id") == "supervised-project-development-alpha:v1184.9")
    require(report.get("read_only") is True)
    require(report.get("post_available") is False)
    require(report.get("content_free") is True)
    require(report.get("authority_preserved") is True)
    require(report.get("operator_review_required") is True)
    require(report.get("operator_promotion_required") is True)
    require(report.get("desktop_verification_deferred_until_v1200") is True)
    for key in (
        "supervised_project_development_alpha_checkpoint_completed",
        "retained_project_development_foundations_checkpoint_completed",
        "retained_project_outcome_learning_checkpoint_completed",
        "retained_project_reliability_recovery_checkpoint_completed",
        "inspection_through_retest_lineage_exercised",
        "operator_result_presentation_exercised",
        "accepted_rejected_failed_repaired_outcomes_exercised",
        "accountable_outcome_learning_exercised",
        "historical_truth_preservation_exercised",
        "stale_source_and_drift_rejection_exercised",
        "interruption_recovery_states_exercised",
        "rollback_evidence_verification_exercised",
        "privacy_hardening_exercised",
        "tamper_and_lineage_boundary_rejection_exercised",
        "source_runtime_immutability_exercised",
    ):
        require(report.get(key) is True)
    for key in (
        "production_source_read", "production_source_modified", "source_modified",
        "sandbox_modified", "runtime_mutated", "raw_source_exposed", "raw_patch_exposed",
        "raw_test_output_exposed", "private_evidence_exposed", "private_reasoning_exposed",
        "inspection_executed", "planning_executed", "implementation_executed",
        "tests_executed", "repair_executed", "retest_executed", "rollback_executed",
        "shell_invoked", "registered_tool_invoked", "provider_contacted",
        "model_operation_performed", "production_runtime_mutated", "memory_mutated",
        "automatic_approval_created", "automatic_authorization_granted",
        "source_application_authorized", "installation_performed", "promotion_performed",
        "certification_performed", "release_authorized", "autonomous_action_authorized",
    ):
        require(report.get(key) is False)
    require(report.get("forbidden_report_value_count") == 0)
    require(len(str(report.get("structural_digest") or "")) == 64)
    require(report.get("source_tree_digest_before") == report.get("source_tree_digest_after"))
    require(report.get("runtime_tree_digest_before") == report.get("runtime_tree_digest_after"))
    summary = report.get("summary") or {}
    require(summary.get("retained_checkpoint_count") == 3)
    require(summary.get("governed_stage_count") == 9)
    require(summary.get("complete_lineage_case_count") == 4)
    require(summary.get("outcome_case_count") == 4)
    require(summary.get("learning_case_count") == 4)
    require(summary.get("reliability_ready_case_count") == 8)
    require(summary.get("interruption_state_case_count") == 4)
    require(int(summary.get("negative_boundary_case_count") or 0) >= 12)
    require(summary.get("rollback_evidence_case_count") == 6)
    require(summary.get("public_summary_case_count") == 9)
    require(summary.get("privacy_forbidden_entry_count") == 0)
    require(summary.get("privacy_content_finding_count") == 0)
    require(summary.get("open_limitation_count") == 7)
    require(len(report.get("limitations") or []) == 7)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "supervised-project-development-alpha-checkpoint",
        source_root=ROOT,
        runtime_root=runtime,
    )
    require(dispatched.get("read_only") is True)
    require(dispatched.get("source_modified") is False)
    require(dispatched.get("runtime_mutated") is False)
    checkpoint_summary = dispatched.get("checkpoint_summary") or {}
    require(checkpoint_summary.get("ok") is True)
    require(checkpoint_summary.get("registered_contract_version") == "v1184.9")
    require(checkpoint_summary.get("reported_contract_version") == "v1184.9")
    require(checkpoint_summary.get("post_available") is False)

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next(
    (item for item in registry.get("checkpoints", []) if item.get("checkpoint_id") == "supervised-project-development-alpha-checkpoint"),
    None,
)
require(row is not None)
require((row or {}).get("builder") == "build_supervised_project_development_alpha_checkpoint")
require((row or {}).get("contract_version") == "v1184.9")
require((row or {}).get("read_only") is True)
require((row or {}).get("post_available") is False)
require(not registry.get("duplicate_checkpoint_ids"))
require(not registry.get("duplicate_builder_targets"))

with tempfile.TemporaryDirectory(prefix="eidolon-v1184-9-cli-") as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "supervised-project-development-alpha-checkpoint"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=900,
        check=False,
    )
    require(cli.returncode == 0)
    cli_payload = json.loads(cli.stdout)
    require(cli_payload.get("contract_version") == "v1184.9")
    require(cli_payload.get("ok") is True)
    require(cli_payload.get("read_only") is True)
    require(cli_payload.get("post_available") is False)

status, payload = dispatch_api("GET", "/api/cognition/supervised-project-development-alpha-checkpoint")
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1184.9")
require((payload.get("data") or {}).get("ok") is True)
post_status, _ = dispatch_api(
    "POST",
    "/api/cognition/supervised-project-development-alpha-checkpoint",
    body={"confirm": True},
)
require(post_status in (404, 405))

source_dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("supervised-project-development-alpha-checkpoint-panel" in source_dashboard)
require("/api/cognition/supervised-project-development-alpha-checkpoint" in source_dashboard)
require("refreshSupervisedProjectDevelopmentAlphaCheckpoint" in source_dashboard)
require("refreshSupervisedProjectDevelopmentAlphaCheckpoint();" in source_dashboard)
require("Next bounded unit: v1185.0-v1185.2" in source_dashboard)
require(re.search(r"async function refreshSupervisedProjectDevelopmentAlphaCheckpoint\(\)\{\{.*?/api/cognition/supervised-project-development-alpha-checkpoint.*?\n\}\}", source_dashboard, re.S) is not None)
html = render_first_use_shell()
require("supervised-project-development-alpha-checkpoint-panel" in html)
require("/api/cognition/supervised-project-development-alpha-checkpoint" in html)
script_match = re.search(r"<script>(.*?)</script>", html, re.S)
require(script_match is not None)
if script_match is not None:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1184-9-js-") as directory:
        js = Path(directory) / "dashboard.js"
        js.write_text(script_match.group(1), encoding="utf-8")
        node = subprocess.run(["node", "--check", str(js)], text=True, capture_output=True, timeout=60, check=False)
        require(node.returncode == 0)

metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1184.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1184.8"' in metadata)
require("v1184.9 Supervised Project Development Alpha Checkpoint" in metadata)
require("v1185.0-v1185.2 Persistent Development Campaign Foundations" in metadata)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
require("v1184.9 Supervised Project Development Alpha Checkpoint" in readme)
require("Current source: v1184.9" in readme)
require("v1185.0-v1185.2" in readme)
require("Current source: v1184.9" in next_steps)
require("Persistent Development Campaign Foundations" in next_steps)
require("v1184.9" in roadmap and "v1185.0-v1185.2" in roadmap and "v1200" in roadmap)
require("v1184.9 Supervised Project Development Alpha Checkpoint" in history)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1184.9-supervised-project-development-alpha-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1184_9_supervised_project_development_alpha_checkpoint_tests.py") == 1)
require(release_verify.count("v1184.0-v1184.2-supervised-project-development-foundations") == 1)
require(release_verify.count("tools/v1184_2_supervised_project_development_foundations_tests.py") == 1)

shutil.rmtree(_TEST_RUNTIME_ROOT, ignore_errors=True)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1184.9-supervised-project-development-alpha-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "production_source_modified": False,
    "rollback_executed": False,
    "authority_expanded": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
