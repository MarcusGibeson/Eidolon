from __future__ import annotations

import json
import time

from v1207_test_support import ROOT, campaign, cleanup, runtime, source_signature

import sys
sys.path.insert(0, str(ROOT / "conscious_agent"))
from node_javascript_test_adapter import (
    _operation_path,
    _result_path,
    public_node_javascript_test_result,
    run_or_resume_node_javascript_tests,
)

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


before = source_signature()

# Passing project-owned tests use one normalized node --test command after syntax checks.
rt = runtime("foundations-pass")
try:
    calls: list[int] = []
    proposal, implementation = campaign(rt, calls=calls, session_id="foundations-pass")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["ok"] is True)
    require(result["passed"] is True, result)
    require(result["status"] == "node_javascript_test_adapter_passed")
    require(result["outcome_class"] == "passed")
    require(result["node_executed"] is True)
    require(result["syntax_file_count"] == 3)
    require(result["test_file_count"] == 1)
    require(result["command_count"] == 4)
    require(result["passed_command_count"] == 4)
    require(result["failed_command_count"] == 0)
    require(result["package_test_script_present"] is True)
    require(result["package_test_script_used"] is True)
    require(result["cleanup_confirmed"] is True)
    require(result["network_allowed"] is False)
    require(result["dependencies_installed"] is False)
    require(result["shell_executed"] is False)
    require(result["selected_project_modified"] is False)
    require(result["repair_authorized"] is False)
    require(result["release_authorized"] is False)
    require(_result_path(proposal["proposal_id"], 1, rt).is_file())
    require(_operation_path(proposal["proposal_id"], 1, rt).is_file())
    resumed = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(resumed["operation_status"] == "resumed")
    require(resumed["node_javascript_test_digest"] == result["node_javascript_test_digest"])
    require(len(calls) == 1)
    public = public_node_javascript_test_result(result)
    encoded = json.dumps(public, sort_keys=True)
    require(public["private_path_exposed"] is False)
    require(public["private_content_exposed"] is False)
    require(public["raw_output_exposed"] is False)
    require(public["node_executable_path_exposed"] is False)
    require(public["package_script_text_exposed"] is False)
    require(str(rt) not in encoded)
    require("tests/tool.test.js" not in encoded)
    require("counts" not in encoded)
    require("node --test" not in encoded)
finally:
    cleanup(rt)

# Failing tests are evidence, never repair authority.
rt = runtime("foundations-fail")
try:
    proposal, implementation = campaign(rt, mode="fail", session_id="foundations-fail")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["ok"] is True)
    require(result["passed"] is False)
    require(result["status"] == "node_javascript_test_adapter_failed")
    require(result["outcome_class"] == "tests_failed")
    require(result["failed_command_count"] == 1)
    require(result["repair_authorized"] is False)
    require(result["apply_authorized"] is False)
finally:
    cleanup(rt)

# Network-capable project code is rejected before command execution.
rt = runtime("foundations-network")
try:
    proposal, implementation = campaign(rt, mode="network", session_id="foundations-network")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["ok"] is True)
    require(result["passed"] is False)
    require(result["status"] == "node_javascript_capability_contract_rejected")
    require(result["outcome_class"] == "contract_rejected")
    require(result["node_executed"] is False)
    require(bool(result["rejected_path_digest"]))
    require(result["network_allowed"] is False)
finally:
    cleanup(rt)

# Package scripts are parsed, never passed to a shell.
rt = runtime("foundations-script")
try:
    proposal, implementation = campaign(rt, mode="unsupported_script", session_id="foundations-script")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["ok"] is True)
    require(result["passed"] is False)
    require(result["status"] == "node_test_script_unsupported")
    require(result["node_executed"] is False)
    require(result["shell_executed"] is False)
finally:
    cleanup(rt)

require(source_signature() == before)
print(json.dumps({
    "ok": True,
    "version": "1207.2",
    "suite": "node-javascript-test-adapter-foundations",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "source_immutable": True,
    "network_allowed": False,
    "dependencies_installed": False,
    "shell_executed": False,
    "repair_authorized": False,
    "release_authorized": False,
}, sort_keys=True))
