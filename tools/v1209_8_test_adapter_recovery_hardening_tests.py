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
    "python_project", proposal_id="proposal-recovery", expected_revision=7,
    expected_revision_digest="a" * 64, expected_workspace_digest="b" * 64,
    approval_receipt_digest="c" * 64, execution_authorized=True,
)

calls = 0


def recovering_loader(adapter_id):
    def execute(proposal_id, **kwargs):
        global calls
        calls += 1
        if calls == 1:
            return {"ok": False, "status": "python_test_operation_in_progress"}
        return {
            "ok": True, "status": "python_test_adapter_passed", "passed": True,
            "python_executed": True, "python_test_adapter_digest": "d" * 64,
            "test_file_count": 2, "test_selection_digest": "e" * 64,
            "cleanup_confirmed": True, "operation_status": "resumed",
            "approval_receipt_digest": "c" * 64,
        }
    return execute, lambda row: dict(row)


first = run_or_resume_selected_test_adapter(request, runtime_root=Path("runtime-a"), adapter_loader=recovering_loader)
second = run_or_resume_selected_test_adapter(request, runtime_root=Path("runtime-a"), adapter_loader=recovering_loader)
require(first["status"] == "test_adapter_execution_rejected", first)
require(first["reliability"]["retry_disposition"] == "same_request_may_resume", first)
require(second["status"] == "test_adapter_execution_completed", second)
require(second["operation_status"] == "resumed", second)
require(second["reliability"]["retry_disposition"] == "not_needed", second)
require(first["dispatch_attempt_digest"] == second["dispatch_attempt_digest"], (first, second))
require(first["execution_request_digest"] == second["execution_request_digest"], (first, second))
require(calls == 2, calls)


def failure_loader(adapter_id):
    def execute(proposal_id, **kwargs):
        return {
            "ok": True, "status": "python_test_adapter_failed", "passed": False,
            "python_executed": True, "python_test_adapter_digest": "f" * 64,
            "cleanup_confirmed": True, "operation_status": "resumed",
        }
    return execute, lambda row: dict(row)


failed = run_or_resume_selected_test_adapter(request, runtime_root=Path("runtime-b"), adapter_loader=failure_loader)
require(failed["status"] == "test_adapter_execution_completed", failed)
require(failed["outcome"]["state"] == "failed", failed)
require(failed["reliability"]["failure_class"] == "test_failure", failed)
require(failed["reliability"]["retry_disposition"] == "not_needed", failed)
require(failed["dispatch_attempt_digest"] == second["dispatch_attempt_digest"], (failed, second))


def raising_loader(adapter_id):
    def execute(proposal_id, **kwargs):
        raise OSError("private runtime path and provider output")
    return execute, dict


internal = run_or_resume_selected_test_adapter(request, runtime_root=Path("runtime-c"), adapter_loader=raising_loader)
require(internal["status"] == "test_adapter_execution_internal_error", internal)
require(internal["reliability"]["retry_disposition"] == "same_request_may_resume", internal)
require(internal["dispatch_attempt_digest"] == second["dispatch_attempt_digest"], (internal, second))
require("private runtime path" not in json.dumps(internal, sort_keys=True), internal)

for result in (first, second, failed, internal):
    require(result["reliability"]["same_request_digest_required"] is True, result)
    require(result["reliability"]["specialized_resume_authoritative"] is True, result)
    require(result["reliability"]["path_values_exposed"] is False, result)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
for stage in (
    "v1209.6-test-adapter-preflight-hardening",
    "v1209.7-test-adapter-evidence-reconciliation",
    "v1209.8-test-adapter-recovery-hardening",
):
    require(release.count(f'"{stage}"') == 2, (stage, release.count(f'"{stage}"')))

print(json.dumps({
    "ok": True, "suite": "v1209.8-test-adapter-recovery-hardening", "version": "1209.8",
    "checks": len(CHECKS), "passed": sum(CHECKS), "same_request_resume_preserved": True,
    "test_failure_distinct_from_dispatch_failure": True, "exception_content_free": True,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
