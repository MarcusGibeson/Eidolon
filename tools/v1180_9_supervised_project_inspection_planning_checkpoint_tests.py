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
from conscious_agent.supervised_project_inspection_planning_checkpoint import (
    build_supervised_project_inspection_planning_checkpoint,
)

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))


with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory) / "runtime"
    report = build_supervised_project_inspection_planning_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(report["ok"] and report["passed"] == report["total"])
    require(report["total"] >= 150)
    require(report["read_only"] and report["post_available"] is False)
    require(report["content_free"] and report["authority_preserved"])
    require(report["operator_promotion_required"])
    require(report["desktop_verification_deferred_until_v1200"])
    for key in (
        "supervised_project_inspection_planning_checkpoint_completed",
        "explicit_root_inspection_exercised",
        "scope_privacy_boundaries_exercised",
        "deficiency_review_exercised",
        "specification_candidates_exercised",
        "implementation_test_planning_exercised",
        "tamper_and_replay_rejection_exercised",
        "bounded_limits_exercised",
    ):
        require(report[key])
    for key in (
        "private_project_registry_discovered", "raw_source_exposed", "raw_evidence_exposed",
        "raw_patch_created", "specification_automatically_confirmed", "patch_created",
        "patch_applied", "tests_executed", "shell_invoked", "automatic_approval_created",
        "automatic_authorization_granted", "execution_invoked", "registered_tool_invoked",
        "provider_contacted", "model_operation_performed", "source_edit_performed",
        "production_runtime_mutated", "memory_mutated", "installation_performed",
        "promotion_performed", "certification_performed", "source_modified", "runtime_mutated",
    ):
        require(report[key] is False)
    require(report["forbidden_report_value_count"] == 0)
    require(len(report["structural_digest"]) == 64)
    summary = report["summary"]
    require(summary["retained_checkpoint_count"] == 1)
    require(summary["inspected_file_case_count"] == 5)
    require(summary["deficiency_candidate_case_count"] == 4)
    require(summary["review_decision_case_count"] == 4)
    require(summary["confirmed_deficiency_case_count"] == 2)
    require(summary["specification_case_count"] == 2)
    require(summary["implementation_plan_case_count"] == 2)
    require(summary["scope_boundary_case_count"] == 5)
    require(summary["tamper_rejection_case_count"] >= 6)
    require(summary["maximum_files"] == 512)
    require(summary["maximum_file_bytes"] == 512_000)
    require(summary["maximum_total_bytes"] == 8_000_000)
    require(summary["maximum_public_files"] == 128)
    require(summary["maximum_candidates"] == 64)
    require(summary["maximum_review_rows"] == 64)
    require(summary["maximum_specifications"] == 32)
    require(summary["maximum_plan_rows"] == 32)
    require(summary["privacy_forbidden_entry_count"] == 0)
    require(summary["privacy_content_finding_count"] == 0)
    require(not runtime.exists())

    dispatched = dispatch_registered_checkpoint(
        "supervised-project-inspection-planning-checkpoint", source_root=ROOT, runtime_root=runtime,
    )
    require(dispatched["read_only"])
    require(not dispatched["source_modified"] and not dispatched["runtime_mutated"])
    require(dispatched["checkpoint_summary"]["ok"])

registry = inspect_checkpoint_registry(source_root=ROOT)
row = next((item for item in registry["checkpoints"] if item["checkpoint_id"] == "supervised-project-inspection-planning-checkpoint"), None)
require(row is not None)
require(row["builder"] == "build_supervised_project_inspection_planning_checkpoint")
require(row["contract_version"] == "v1180.9")
require(not registry["duplicate_checkpoint_ids"] and not registry["duplicate_builder_targets"])

with tempfile.TemporaryDirectory() as directory:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["EIDOLON_DATA_DIR"] = str(Path(directory) / "runtime")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPYCACHEPREFIX"] = str(Path(directory) / "pycache")
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "supervised-project-inspection-planning-checkpoint"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=600,
    )
    require(cli.returncode == 0)
    require(json.loads(cli.stdout)["contract_version"] == "v1180.9")

from conscious_agent.api_server import dispatch_api
status, payload = dispatch_api("GET", "/api/cognition/supervised-project-inspection-planning-checkpoint")
require(status == 200)
require((payload.get("data") or {}).get("contract_version") == "v1180.9")
post_status, _ = dispatch_api(
    "POST", "/api/cognition/supervised-project-inspection-planning-checkpoint", body={"confirm": True},
)
require(post_status in (404, 405))

dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
require("supervised-project-inspection-planning-checkpoint-panel" in dashboard)
require("/api/cognition/supervised-project-inspection-planning-checkpoint" in dashboard)
require("refreshSupervisedProjectInspectionPlanningCheckpoint" in dashboard)
require("Desktop review deferred to v1200" in dashboard)
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
require(bool(working_match) and tuple(map(int, working_match.groups())) >= (1180, 9))
require(bool(previous_match) and tuple(map(int, previous_match.groups())) >= (1180, 8))
require("v1180.9" in metadata or tuple(map(int, working_match.groups())) > (1180, 9))
next_steps = (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8")
history = (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
roadmap = (ROOT / "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
require("v1180.9" in next_steps and "v1181.0-v1181.2" in next_steps and "v1200" in next_steps)
require("v1180.9 Supervised Project Inspection and Planning" in history)
require(("Current source: v1180.9" in roadmap or "Current source: v1181.2" in roadmap or "Current source: v1181.5" in roadmap or "Current source: v1181.8" in roadmap) and "v1180-v1184" in roadmap and "v1200" in roadmap)
require("v1180.9 Supervised Project Inspection and Planning" in readme)

release_verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(release_verify.count("v1180.9-supervised-project-inspection-planning-read-only-checkpoint") == 1)
require(release_verify.count("tools/v1180_9_supervised_project_inspection_planning_checkpoint_tests.py") == 1)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1180.9-supervised-project-inspection-planning-read-only-checkpoint",
    "passed": sum(checks),
    "total": len(checks),
    "read_only": True,
    "patch_created": False,
    "tests_executed": False,
    "execution_invoked": False,
}, sort_keys=True))
if not all(checks):
    print([index + 1 for index, value in enumerate(checks) if not value])
    raise SystemExit(1)
