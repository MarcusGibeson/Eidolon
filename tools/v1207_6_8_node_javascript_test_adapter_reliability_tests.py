from __future__ import annotations

import concurrent.futures
import json
import os
import time

from v1207_test_support import ROOT, campaign, cleanup, runtime, source_signature

import sys
sys.path.insert(0, str(ROOT / "conscious_agent"))
import node_javascript_test_adapter as adapter
from grounded_development_planning import load_grounded_plan
from ordinary_chat_development_campaign import _read_json
from node_javascript_test_adapter import (
    _node_candidates,
    _operation_path,
    _record_valid,
    _result_path,
    _write_operation,
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

# Candidate discovery is bounded and source-classed on every supported platform.
old_system = adapter.platform.system
old_which = adapter.shutil.which
old_env = dict(os.environ)
try:
    adapter.shutil.which = lambda name: f"/path/{name}" if name == "node" else None
    adapter.platform.system = lambda: "Linux"
    linux = _node_candidates("/explicit/node")
    require(linux[0] == ("explicit", "/explicit/node"))
    require(any(source == "path" for source, _ in linux))
    require(len(linux) <= adapter.MAX_NODE_LAUNCH_ATTEMPTS)
    adapter.platform.system = lambda: "Darwin"
    mac = _node_candidates(None)
    require(any("homebrew" in value or "/usr/local/bin/node" in value for _, value in mac))
    adapter.platform.system = lambda: "Windows"
    os.environ["PROGRAMFILES"] = r"C:\FixtureProgramFiles"
    windows = _node_candidates(None)
    require(any(source == "platform_default" and value.endswith("node.exe") for source, value in windows))
    os.environ["EIDOLON_NODE_EXECUTABLE"] = r"C:\FixtureNode\node.exe"
    explicit_env = _node_candidates(None)
    require(explicit_env[0][0] == "environment")
finally:
    adapter.platform.system = old_system
    adapter.shutil.which = old_which
    os.environ.clear(); os.environ.update(old_env)

# Twelve concurrent adapter calls execute one bounded command sequence.
rt = runtime("reliability-race")
old_run = adapter._run_bounded_command
try:
    proposal, implementation = campaign(rt, session_id="reliability-race")
    calls = []
    def counted(*args, **kwargs):
        calls.append(tuple(args[0]))
        return old_run(*args, **kwargs)
    adapter._run_bounded_command = counted
    def worker(_index):
        return run_or_resume_node_javascript_tests(
            proposal["proposal_id"], expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
        )
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        rows = list(pool.map(worker, range(12)))
    require(len({row.get("node_javascript_test_digest") for row in rows}) == 1, rows)
    require(sum(row.get("operation_status") == "created" for row in rows) == 1)
    require(sum(row.get("operation_status") == "resumed" for row in rows) == 11)
    require(len(calls) == 5, calls)
finally:
    adapter._run_bounded_command = old_run
    cleanup(rt)

# A live prepared operation blocks duplicate execution.
rt = runtime("reliability-live")
try:
    proposal, implementation = campaign(rt, session_id="reliability-live")
    plan = load_grounded_plan(proposal["proposal_id"], 1, runtime_root=rt)
    _write_operation(_operation_path(proposal["proposal_id"], 1, rt), {
        "schema_version": adapter.SCHEMA_VERSION, "contract_version": adapter.CONTRACT_VERSION,
        "phase": "prepared", "proposal_id": proposal["proposal_id"], "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"], "planning_digest": plan["planning_digest"],
        "generation_digest": implementation["generation_digest"], "workspace_digest": implementation["workspace_digest"],
        "attempt_count": 1, "recovery_count": 0, "updated_at_epoch": time.time(),
        "network_allowed": False, "dependencies_installed": False, "shell_executed": False,
        "selected_project_modified": False, "source_modified": False, "repair_authorized": False,
        "apply_authorized": False, "release_authorized": False, "authority_granted": False,
    })
    blocked = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(blocked["status"] == "node_javascript_operation_in_progress")
    require(not _result_path(proposal["proposal_id"], 1, rt).exists())
finally:
    cleanup(rt)

# A stale prepared operation is recovered exactly once.
rt = runtime("reliability-stale")
try:
    proposal, implementation = campaign(rt, session_id="reliability-stale")
    plan = load_grounded_plan(proposal["proposal_id"], 1, runtime_root=rt)
    _write_operation(_operation_path(proposal["proposal_id"], 1, rt), {
        "schema_version": adapter.SCHEMA_VERSION, "contract_version": adapter.CONTRACT_VERSION,
        "phase": "prepared", "proposal_id": proposal["proposal_id"], "proposal_revision": 1,
        "proposal_revision_digest": proposal["revision_digest"], "planning_digest": plan["planning_digest"],
        "generation_digest": implementation["generation_digest"], "workspace_digest": implementation["workspace_digest"],
        "attempt_count": 1, "recovery_count": 0,
        "updated_at_epoch": time.time() - adapter.OPERATION_STALE_SECONDS - 5,
        "network_allowed": False, "dependencies_installed": False, "shell_executed": False,
        "selected_project_modified": False, "source_modified": False, "repair_authorized": False,
        "apply_authorized": False, "release_authorized": False, "authority_granted": False,
    })
    recovered = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(recovered["passed"] is True)
    require(recovered["operation_recovery_count"] == 1)
    operation = _read_json(_operation_path(proposal["proposal_id"], 1, rt))
    require(operation["phase"] == "sealed")
    require(operation["recovery_count"] == 1)
    require(operation["attempt_count"] == 2)
finally:
    cleanup(rt)

# Tampered journals and sealed-without-result states block.
for name, mode, expected in (
    ("reliability-tamper", "tamper", "node_javascript_operation_invalid"),
    ("reliability-missing", "sealed", "node_javascript_result_missing"),
):
    rt = runtime(name)
    try:
        proposal, implementation = campaign(rt, session_id=name)
        plan = load_grounded_plan(proposal["proposal_id"], 1, runtime_root=rt)
        operation = _write_operation(_operation_path(proposal["proposal_id"], 1, rt), {
            "schema_version": adapter.SCHEMA_VERSION, "contract_version": adapter.CONTRACT_VERSION,
            "phase": "prepared", "proposal_id": proposal["proposal_id"], "proposal_revision": 1,
            "proposal_revision_digest": proposal["revision_digest"], "planning_digest": plan["planning_digest"],
            "generation_digest": implementation["generation_digest"], "workspace_digest": implementation["workspace_digest"],
            "attempt_count": 1, "recovery_count": 0, "updated_at_epoch": time.time() - 100,
            "network_allowed": False, "dependencies_installed": False, "shell_executed": False,
            "selected_project_modified": False, "source_modified": False, "repair_authorized": False,
            "apply_authorized": False, "release_authorized": False, "authority_granted": False,
        })
        if mode == "tamper":
            operation["phase"] = "sealed"
            _operation_path(proposal["proposal_id"], 1, rt).write_text(json.dumps(operation), encoding="utf-8")
        else:
            _write_operation(_operation_path(proposal["proposal_id"], 1, rt), {
                **{k: v for k, v in operation.items() if k != "operation_digest"},
                "phase": "sealed", "result_digest": "f" * 64,
            })
        result = run_or_resume_node_javascript_tests(
            proposal["proposal_id"], expected_revision=1,
            expected_revision_digest=proposal["revision_digest"],
            expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
        )
        require(result["status"] == expected, result)
    finally:
        cleanup(rt)

# Tampered results never self-heal on resume.
rt = runtime("reliability-result-tamper")
try:
    proposal, implementation = campaign(rt, session_id="reliability-result-tamper")
    result = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    raw = json.loads(_result_path(proposal["proposal_id"], 1, rt).read_text())
    raw["passed"] = False
    _result_path(proposal["proposal_id"], 1, rt).write_text(json.dumps(raw), encoding="utf-8")
    blocked = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest=implementation["workspace_digest"], runtime_root=rt,
    )
    require(blocked["status"] == "node_javascript_test_record_invalid")
    require(_record_valid(raw) is False)
finally:
    cleanup(rt)

# Stale workspace bindings reject before Node execution.
rt = runtime("reliability-stale-workspace")
try:
    proposal, implementation = campaign(rt, session_id="reliability-stale-workspace")
    blocked = run_or_resume_node_javascript_tests(
        proposal["proposal_id"], expected_revision=1,
        expected_revision_digest=proposal["revision_digest"],
        expected_workspace_digest="0" * 64, runtime_root=rt,
    )
    require(blocked["status"] == "stale_workspace_revision")
finally:
    cleanup(rt)

require(source_signature() == before)
print(json.dumps({
    "ok": True,
    "version": "1207.8",
    "suite": "node-javascript-test-adapter-reliability-cross-platform",
    "checks": len(CHECKS),
    "passed": sum(CHECKS),
    "elapsed_seconds": round(time.monotonic() - START, 4),
    "source_immutable": True,
    "network_allowed": False,
    "dependencies_installed": False,
    "shell_executed": False,
    "repair_authorized": False,
}, sort_keys=True))
