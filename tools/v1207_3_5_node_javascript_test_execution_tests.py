from __future__ import annotations

import json
import os
import time
from pathlib import Path

from v1207_test_support import ROOT, campaign, cleanup, runtime, source_signature

import sys
sys.path.insert(0, str(ROOT / "conscious_agent"))
import node_javascript_test_adapter as adapter
from node_javascript_test_adapter import run_or_resume_node_javascript_tests

START = time.monotonic()
CHECKS: list[bool] = []


def require(value, detail=None):
    CHECKS.append(bool(value))
    if not value:
        raise AssertionError(detail)


before = source_signature()

# A strict package selector is normalized to the exact discovered test file.
rt = runtime("execution-selector")
try:
    proposal, implementation = campaign(rt, mode="selected_script", session_id="execution-selector")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["passed"] is True, result)
    require(result["package_test_script_present"] is True)
    require(result["package_test_script_used"] is True)
    require(bool(result["package_test_script_digest"]))
    require(result["test_file_count"] == 1)
    require(result["command_results"][-1]["phase"] == "tests")
    require(bool(result["command_results"][-1]["selection_digest"]))
finally:
    cleanup(rt)

# Generated tests cannot write outside their private scratch directory.
rt = runtime("execution-filesystem-write")
try:
    proposal, implementation = campaign(rt, mode="filesystem_write", session_id="execution-filesystem-write")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["passed"] is False)
    require(result["outcome_class"] == "tests_failed")
    require(result["sandbox_backend"] == "node-preload-capability-guard")
    require(result["os_isolation_provided"] is False)
    require(result["security_boundary"] == "language_runtime_policy_not_os_container")
    require(not list(rt.rglob("forbidden-node.txt")))
finally:
    cleanup(rt)

# Test timeout kills the process group and records bounded evidence.
rt = runtime("execution-timeout")
old_timeout = adapter.TEST_TIMEOUT_SECONDS
try:
    adapter.TEST_TIMEOUT_SECONDS = 1
    proposal, implementation = campaign(rt, mode="timeout", session_id="execution-timeout")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["passed"] is False)
    require(result["outcome_class"] == "test_timeout", result)
    require(result["command_results"][-1]["exit_class"] == "timeout")
    require(result["command_results"][-1]["cleanup_confirmed"] is True)
    require(result["cleanup_confirmed"] is True)
finally:
    adapter.TEST_TIMEOUT_SECONDS = old_timeout
    cleanup(rt)

# Excessive raw output is killed and represented only by a digest and byte count.
rt = runtime("execution-output")
try:
    proposal, implementation = campaign(rt, mode="output", session_id="execution-output")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["passed"] is False)
    require(result["outcome_class"] == "test_output_limit", result)
    test_result = result["command_results"][-1]
    require(test_result["exit_class"] == "output_limit")
    require(test_result["output_limit_exceeded"] is True)
    require(test_result["output_bytes"] == adapter.MAX_OUTPUT_BYTES + 1)
    require(bool(test_result["output_digest"]))
    require("x" * 100 not in json.dumps(result))
finally:
    cleanup(rt)

# Dynamic non-literal import is rejected before Node executes tests.
rt = runtime("execution-dynamic")
try:
    proposal, implementation = campaign(rt, mode="dynamic_import", session_id="execution-dynamic")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["status"] == "node_javascript_capability_contract_rejected")
    require(result["node_executed"] is False)
    require(result["network_allowed"] is False)
finally:
    cleanup(rt)

# Missing Node is a checkpointable failure, not a crash or package-install attempt.
rt = runtime("execution-node-missing")
old_candidates = adapter._node_candidates
try:
    adapter._node_candidates = lambda _explicit=None: [("explicit", str(rt / "missing-node"))]
    proposal, implementation = campaign(rt, session_id="execution-node-missing")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(result["status"] == "node_runtime_unavailable")
    require(result["outcome_class"] == "node_unavailable")
    require(result["launch_attempt_count"] == 1)
    require(len(result["launch_failure_digests"]) == 1)
    require(result["node_source_class"] == "none")
    require(result["dependencies_installed"] is False)
finally:
    adapter._node_candidates = old_candidates
    cleanup(rt)

# A bounded fake runner can pass discovery but fail syntax checking predictably.
rt = runtime("execution-syntax")
old_run = adapter._run_bounded_command
try:
    def fake_run(argv, **kwargs):
        if "--version" in argv:
            return {"passed": True, "exit_class": "zero", "output_digest": "0" * 64, "output_bytes": 0, "output_limit_exceeded": False, "cleanup_confirmed": True, "duration_ms": 1}
        if "--check" in argv:
            return {"passed": False, "exit_class": "nonzero", "output_digest": "1" * 64, "output_bytes": 0, "output_limit_exceeded": False, "cleanup_confirmed": True, "duration_ms": 1}
        return old_run(argv, **kwargs)
    adapter._run_bounded_command = fake_run
    proposal, implementation = campaign(rt, session_id="execution-syntax")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
        node_executable=sys.executable,
    )
    require(result["passed"] is False)
    require(result["outcome_class"] == "syntax_failed")
    require(result["node_source_class"] == "explicit")
    require(result["command_count"] == 1)
    require(result["command_results"][0]["exit_class"] == "nonzero")
finally:
    adapter._run_bounded_command = old_run
    cleanup(rt)

require(source_signature() == before)
print(json.dumps({
    "ok": True,
    "version": "1207.5",
    "suite": "node-javascript-project-test-discovery-execution",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "source_immutable": True,
    "network_allowed": False,
    "dependencies_installed": False,
    "shell_executed": False,
    "repair_authorized": False,
}, sort_keys=True))
