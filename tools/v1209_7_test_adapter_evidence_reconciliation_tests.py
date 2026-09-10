from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))

from unified_test_adapter_contract import prepare_test_adapter_execution, run_or_resume_selected_test_adapter

START = time.monotonic()
CHECKS: list[bool] = []


def require(value: bool, detail=None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


request = prepare_test_adapter_execution(
    "python_project", proposal_id="proposal-evidence", expected_revision=2,
    expected_revision_digest="a" * 64, expected_workspace_digest="b" * 64,
    approval_receipt_digest="c" * 64, execution_authorized=True,
)


def run(execute_result, projection=None):
    def loader(adapter_id):
        def execute(proposal_id, **kwargs):
            return execute_result
        return execute, (projection or (lambda row: dict(row)))
    return run_or_resume_selected_test_adapter(request, adapter_loader=loader)


for malformed, reason in (
    ([], "specialized_result_not_mapping"),
    ({"ok": True}, "specialized_public_evidence_invalid"),
    ({"ok": True, "status": "passed", "passed": True, "python_executed": False}, "specialized_public_evidence_invalid"),
    ({"ok": True, "status": "passed", "passed": True, "python_executed": True,
      "python_test_adapter_digest": "x" * 64}, "specialized_public_evidence_invalid"),
    ({"ok": True, "status": "passed", "passed": True, "python_executed": True,
      "python_test_adapter_digest": "d" * 64, "test_selection_digest": "short"}, "specialized_public_evidence_invalid"),
    ({"ok": True, "status": "passed", "passed": True, "python_executed": True,
      "python_test_adapter_digest": "d" * 64, "cleanup_confirmed": "yes"}, "specialized_public_evidence_invalid"),
    ({"ok": True, "status": "passed", "passed": True, "python_executed": True,
      "python_test_adapter_digest": "d" * 64, "private_output": "C:/secret"}, "specialized_public_evidence_invalid"),
    ({"ok": True, "status": "passed", "passed": True, "python_executed": True,
      "python_test_adapter_digest": "d" * 64,
      "command_results": [{"raw_output": "secret test output"}]}, "specialized_public_evidence_invalid"),
):
    result = run(malformed)
    require(result["status"] == "test_adapter_evidence_invalid", result)
    require(result["reason"] == reason, result)
    require("public_specialized_evidence" not in result, result)

non_mapping_projection = run(
    {"ok": True, "status": "passed", "python_executed": True, "python_test_adapter_digest": "d" * 64},
    projection=lambda row: [row],
)
require(non_mapping_projection["status"] == "test_adapter_evidence_invalid", non_mapping_projection)

cleanup = run({
    "ok": True, "status": "python_test_adapter_passed", "passed": True,
    "python_executed": True, "python_test_adapter_digest": "d" * 64,
    "cleanup_confirmed": False,
})
require(cleanup["status"] == "test_adapter_cleanup_incomplete", cleanup)
require(cleanup["cleanup"]["state"] == "failed", cleanup)
require(cleanup["reliability"]["failure_class"] == "cleanup_incomplete", cleanup)
require(cleanup["reliability"]["retry_disposition"] == "cleanup_review_required", cleanup)

rejected = run({"ok": False, "status": "python_runtime_unavailable"})
require(rejected["status"] == "test_adapter_execution_rejected", rejected)
require(rejected["outcome"]["state"] == "not_executed", rejected)
require(rejected["reliability"]["failure_class"] == "specialized_adapter_rejected", rejected)

encoded = json.dumps([non_mapping_projection, cleanup, rejected], sort_keys=True)
require("C:/secret" not in encoded, encoded)
require(all(value is False for value in rejected["privacy"].values()), rejected)

print(json.dumps({
    "ok": True, "suite": "v1209.7-test-adapter-evidence-reconciliation", "version": "1209.7",
    "checks": len(CHECKS), "passed": sum(CHECKS), "malformed_evidence_exposed": False,
    "cleanup_failure_explicit": True, "specialized_rejection_distinct": True,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
