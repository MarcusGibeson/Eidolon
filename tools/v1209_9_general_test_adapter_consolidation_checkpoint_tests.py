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
os.environ.setdefault("EIDOLON_DATA_DIR", tempfile.mkdtemp(prefix="eidolon-v1209-9-data-"))

from conscious_agent.checkpoint_registry import inspect_checkpoint_registry
from conscious_agent.dashboard_first_use import render_first_use_shell
from conscious_agent.general_test_adapter_consolidation_checkpoint import (
    CONTRACT_VERSION,
    build_general_test_adapter_consolidation_checkpoint,
)

CHECKS: list[bool] = []


def require(value: object, detail: object | None = None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


with tempfile.TemporaryDirectory(prefix="eidolon-v1209-9-") as temporary:
    runtime = Path(temporary) / "must-not-be-created"
    report = build_general_test_adapter_consolidation_checkpoint(source_root=ROOT, runtime_root=runtime)
    require(not runtime.exists())

for key, expected in (
    ("ok", True),
    ("contract_version", "v1209.9"),
    ("retained_contract_version", "v1209.8"),
    ("read_only", True),
    ("post_available", False),
    ("content_free", True),
    ("synthetic_contract_evaluation", True),
    ("specialized_executor_invoked", False),
    ("project_tests_executed", False),
    ("runtime_probed", False),
    ("runtime_data_read", False),
    ("runtime_mutated", False),
    ("runtime_records_written", False),
    ("source_modified", False),
    ("project_modified", False),
    ("provider_contacted", False),
    ("dependencies_installed", False),
    ("automatic_diagnosis", False),
    ("automatic_repair", False),
    ("approval_created", False),
    ("approval_consumed", False),
    ("apply_authorized", False),
    ("promotion_authorized", False),
    ("release_authorized", False),
    ("model_management_authorized", False),
    ("authority_granted", False),
    ("global_profile_pass_claimed", False),
):
    require(report.get(key) == expected, (key, report.get(key)))
require(report["passed"] == report["total"])
require(report["total"] >= 100, report["total"])
require(report["source_signature_before"] == report["source_signature_after"])
require(len(report["structural_digest"]) == 64)
require(len(report["limitations"]) == 5)

summary = report["summary"]
for key, expected in (
    ("adapter_count", 3),
    ("concrete_project_kind_count", 8),
    ("explicit_state_count", 5),
    ("synthetic_dispatch_count", 3),
    ("dispatch_error_class_count", 7),
    ("registry_deterministic", True),
    ("selection_non_executing", True),
    ("execution_separately_authorized", True),
    ("specialized_executor_preserved", True),
    ("runtime_records_external", True),
    ("privacy_preserved", True),
    ("authority_preserved", True),
    ("checkpoint_registry_discovered", True),
):
    require(summary.get(key) == expected, (key, summary.get(key)))
require(summary["adapter_ids"] == ["browser_runtime", "node_javascript", "python"])
require(summary["concrete_project_routing"]["new_small_web_project"] == "browser_runtime")
require(summary["concrete_project_routing"]["javascript_tool_project"] == "node_javascript")
require(summary["concrete_project_routing"]["python_project"] == "python")

registry = inspect_checkpoint_registry(source_root=ROOT)
descriptor = next(
    (row for row in registry["checkpoints"] if row["checkpoint_id"] == "general-test-adapter-consolidation-checkpoint"),
    None,
)
require(descriptor is not None)
require((descriptor or {}).get("contract_version") == CONTRACT_VERSION)
require((descriptor or {}).get("builder") == "build_general_test_adapter_consolidation_checkpoint")
require((descriptor or {}).get("read_only") is True)
require((descriptor or {}).get("post_available") is False)
require((descriptor or {}).get("required_input_count") == 0)
require(not registry["duplicate_checkpoint_ids"])
require(not registry["duplicate_builder_targets"])

process = subprocess.run(
    [sys.executable, str(ROOT / "eidolon.py"), "general-test-adapter-consolidation-checkpoint"],
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=120,
    env={
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "EIDOLON_DATA_DIR": tempfile.mkdtemp(prefix="eidolon-v1209-9-cli-"),
    },
)
require(process.returncode == 0, process.stderr)
cli_report = json.loads(process.stdout.strip().splitlines()[-1])
require(cli_report["ok"] is True)
require(cli_report["contract_version"] == "v1209.9")
require(cli_report["summary"]["adapter_count"] == 3)
require(cli_report["global_profile_pass_claimed"] is False)

api_source = (ROOT / "conscious_agent" / "api_server.py").read_text(encoding="utf-8")
route = 'parts == ["cognition", "general-test-adapter-consolidation-checkpoint"]'
require(api_source.count(route) == 1, api_source.count(route))
require("build_general_test_adapter_consolidation_checkpoint()" in api_source)
require("POST /api/cognition/general-test-adapter-consolidation-checkpoint" not in api_source)

html = render_first_use_shell()
require("general-test-adapter-consolidation-checkpoint-panel" in html)
require("general-test-adapter-consolidation-checkpoint-state" in html)
require("general-test-adapter-consolidation-checkpoint-summary" in html)
require("/api/cognition/general-test-adapter-consolidation-checkpoint" in html)
require("no project tests executed" in html.lower())

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
stage = "v1209.9-general-test-adapter-consolidation-checkpoint"
require(release.count(f'"{stage}"') == 2, release.count(f'"{stage}"'))
metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
require('WORKING_SOURCE_VERSION = "1209.9"' in metadata)
require('PREVIOUS_WORKING_SOURCE_VERSION = "1209.8"' in metadata)
require("General Test Adapter Consolidation Checkpoint" in (ROOT / "README_NEXT_STEPS.md").read_text(encoding="utf-8"))
require("v1209.9" in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8"))
require(not (ROOT / "data" / "development_campaigns").exists())

print(json.dumps({
    "ok": True,
    "suite": "v1209.9-general-test-adapter-consolidation-checkpoint",
    "version": "1209.9",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "source_immutable": True,
    "runtime_mutated": False,
    "project_tests_executed": False,
    "specialized_executor_invoked": False,
    "operator_review_required": True,
    "repair_authorized": False,
    "release_authorized": False,
}, sort_keys=True), flush=True)
