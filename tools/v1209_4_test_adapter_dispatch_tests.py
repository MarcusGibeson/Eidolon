from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.path.insert(0, str(ROOT / "tools"))

from unified_test_adapter_contract import prepare_test_adapter_execution, run_or_resume_selected_test_adapter

START = time.monotonic()
CHECKS: list[bool] = []


def require(value: bool, detail=None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


def request(kind, **extra):
    return prepare_test_adapter_execution(
        kind, proposal_id="proposal-dispatch", expected_revision=3,
        expected_revision_digest="a" * 64, expected_workspace_digest="b" * 64,
        approval_receipt_digest="c" * 64, execution_authorized=True, **extra,
    )


calls: list[tuple[str, str, dict]] = []


def loader(adapter_id):
    digest_field, executed_field = {
        "browser_runtime": ("browser_runtime_test_digest", "browser_executed"),
        "node_javascript": ("node_javascript_test_digest", "node_executed"),
        "python": ("python_test_adapter_digest", "python_executed"),
    }[adapter_id]

    evidence_character = {"browser_runtime": "b", "node_javascript": "d", "python": "e"}[adapter_id]

    def execute(proposal_id, **kwargs):
        calls.append((adapter_id, proposal_id, kwargs))
        return {
            "ok": True, "status": f"{adapter_id}_passed", "passed": True,
            executed_field: True, digest_field: evidence_character * 64,
            "test_file_count": 2, "test_selection_digest": "d" * 64,
            "cleanup_confirmed": True, "operation_status": "created",
            "authority_granted": False, "repair_authorized": False, "apply_authorized": False,
            "rollback_authorized": False, "release_authorized": False,
            "selected_project_modified": False, "source_modified": False,
            "implementation_applied": False, "network_allowed": False,
            "dependencies_installed": False,
        }

    def project(record):
        return dict(record)

    return execute, project


rows = (
    ("new_small_web_project", "browser_runtime", {"expected_preview_digest": "e" * 64}),
    ("javascript_tool_project", "node_javascript", {}),
    ("python_project", "python", {}),
)
for kind, adapter_id, extra in rows:
    result = run_or_resume_selected_test_adapter(request(kind, **extra), runtime_root="external-runtime", adapter_loader=loader)
    require(result["status"] == "test_adapter_execution_completed", result)
    require(result["selected_adapter_id"] == adapter_id, result)
    require(result["tests_executed"] is True and result["outcome"]["passed"] is True, result)
    expected_digest = {"browser_runtime": "b", "node_javascript": "d", "python": "e"}[adapter_id] * 64
    require(result["outcome"]["evidence_digest"] == expected_digest, result)
    require(result["cleanup"]["cleanup_confirmed"] is True, result)
    require(result["selected_tests"]["count"] == 2, result)
    require(result["runtime_records_external"] is True and result["specialized_executor_preserved"] is True, result)
    require(result["authority"]["execution_authorized"] is True, result)
    require(all(not result["authority"][key] for key in (
        "authority_granted", "install_authorized", "repair_authorized", "apply_authorized",
        "promotion_authorized", "release_authorized", "model_management_authorized",
    )), result)

require([row[0] for row in calls] == ["browser_runtime", "node_javascript", "python"], calls)
require("expected_preview_digest" in calls[0][2], calls[0])
require("expected_preview_digest" not in calls[1][2] and "expected_preview_digest" not in calls[2][2], calls)
require(all(row[1] == "proposal-dispatch" for row in calls), calls)

# Exercise the ordinary specialized entrypoints through the unified dispatcher.
from v1207_test_support import campaign as javascript_campaign, cleanup as javascript_cleanup, runtime as javascript_runtime
from v1208_test_support import campaign as python_campaign, cleanup as python_cleanup, runtime as python_runtime

js_runtime = javascript_runtime("unified-dispatch")
try:
    proposal, implementation = javascript_campaign(js_runtime, session_id="v1209-real-node")
    real_request = prepare_test_adapter_execution(
        "javascript_tool_project", proposal_id=proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"],
        approval_receipt_digest=implementation["approval_receipt_digest"], execution_authorized=True,
    )
    real_node = run_or_resume_selected_test_adapter(real_request, runtime_root=js_runtime)
    require(real_node["status"] == "test_adapter_execution_completed", real_node)
    require(real_node["tests_executed"] is True and real_node["outcome"]["passed"] is True, real_node)
    require(real_node["outcome"]["specialized_status"] == "node_javascript_test_adapter_passed", real_node)
finally:
    javascript_cleanup(js_runtime)

py_runtime = python_runtime("unified-dispatch")
try:
    proposal, implementation = python_campaign(py_runtime, session_id="v1209-real-python")
    real_request = prepare_test_adapter_execution(
        "python_project", proposal_id=proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"],
        approval_receipt_digest=implementation["approval_receipt_digest"], execution_authorized=True,
    )
    real_python = run_or_resume_selected_test_adapter(real_request, runtime_root=py_runtime)
    require(real_python["status"] == "test_adapter_execution_completed", real_python)
    require(real_python["tests_executed"] is True and real_python["outcome"]["passed"] is True, real_python)
    require(real_python["outcome"]["specialized_status"] == "python_test_adapter_passed", real_python)
finally:
    python_cleanup(py_runtime)

print(json.dumps({
    "ok": True, "suite": "v1209.4-test-adapter-dispatch", "version": "1209.4",
    "checks": len(CHECKS), "passed": sum(CHECKS), "specialized_adapters_delegated": 3,
    "real_specialized_entrypoints_executed": 2,
    "specialized_executor_preserved": True, "dependencies_installed": False,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
