from __future__ import annotations

import copy
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
    "python_project", proposal_id="proposal-reliable", expected_revision=1,
    expected_revision_digest="a" * 64, expected_workspace_digest="b" * 64,
    approval_receipt_digest="c" * 64, execution_authorized=True,
)

calls = 0


def safe_loader(adapter_id):
    def execute(proposal_id, **kwargs):
        global calls
        calls += 1
        return {
            "ok": True, "status": "python_test_adapter_failed", "passed": False,
            "python_executed": True, "python_test_adapter_digest": "d" * 64,
            "test_file_count": 1, "test_selection_digest": "e" * 64,
            "cleanup_confirmed": True, "operation_status": "resumed",
            "approval_receipt_digest": "c" * 64,
            "authority_granted": False, "repair_authorized": False, "apply_authorized": False,
            "rollback_authorized": False, "release_authorized": False,
            "selected_project_modified": False, "source_modified": False,
            "implementation_applied": False, "network_allowed": False, "dependencies_installed": False,
        }
    return execute, lambda record: dict(record)


failed = run_or_resume_selected_test_adapter(request, adapter_loader=safe_loader)
require(failed["status"] == "test_adapter_execution_completed", failed)
require(failed["outcome"]["state"] == "failed" and failed["outcome"]["passed"] is False, failed)
require(failed["operation_status"] == "resumed", failed)

tampered = copy.deepcopy(request)
tampered["expected_workspace_digest"] = "f" * 64
blocked = run_or_resume_selected_test_adapter(tampered, adapter_loader=safe_loader)
require(blocked["status"] == "test_adapter_execution_request_invalid", blocked)
require(calls == 1, calls)

unapproved = prepare_test_adapter_execution(
    "python_project", proposal_id="proposal-reliable", expected_revision=1,
    expected_revision_digest="a" * 64, expected_workspace_digest="b" * 64,
    approval_receipt_digest="c" * 64, execution_authorized=False,
)
blocked = run_or_resume_selected_test_adapter(unapproved, adapter_loader=safe_loader)
require(blocked["status"] == "test_adapter_execution_request_invalid", blocked)
require(calls == 1, calls)


def raising_loader(adapter_id):
    def execute(proposal_id, **kwargs):
        raise RuntimeError("private path C:/secret and credential value")
    return execute, dict


internal = run_or_resume_selected_test_adapter(request, adapter_loader=raising_loader)
require(internal["status"] == "test_adapter_execution_internal_error", internal)
require("secret" not in json.dumps(internal), internal)


def violating_loader(adapter_id):
    def execute(proposal_id, **kwargs):
        return {"ok": True, "status": "passed", "passed": True, "python_executed": True,
                "python_test_adapter_digest": "a" * 64, "selected_project_modified": True}
    return execute, lambda record: dict(record)


violation = run_or_resume_selected_test_adapter(request, adapter_loader=violating_loader)
require(violation["status"] == "test_adapter_authority_boundary_violation", violation)
require("public_specialized_evidence" not in violation, violation)


def mismatched_approval_loader(adapter_id):
    def execute(proposal_id, **kwargs):
        return {"ok": True, "status": "python_test_adapter_passed", "passed": True,
                "python_executed": True, "python_test_adapter_digest": "b" * 64,
                "approval_receipt_digest": "f" * 64, "cleanup_confirmed": True}
    return execute, lambda record: dict(record)


approval_mismatch = run_or_resume_selected_test_adapter(request, adapter_loader=mismatched_approval_loader)
require(approval_mismatch["status"] == "test_adapter_approval_binding_mismatch", approval_mismatch)
require("public_specialized_evidence" not in approval_mismatch, approval_mismatch)

encoded = json.dumps([failed, blocked, internal, violation, approval_mismatch], sort_keys=True)
for forbidden in ("C:/secret", "credential value", "test body", "provider prompt"):
    require(forbidden not in encoded, encoded)
require(all(value is False for value in failed["privacy"].values()), failed)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
for stage in (
    "v1209.3-test-adapter-execution-request",
    "v1209.4-test-adapter-dispatch",
    "v1209.5-test-adapter-lifecycle-reliability",
):
    require(release.count(f'"{stage}"') == 2, (stage, release.count(f'"{stage}"')))

print(json.dumps({
    "ok": True, "suite": "v1209.5-test-adapter-lifecycle-reliability", "version": "1209.5",
    "checks": len(CHECKS), "passed": sum(CHECKS), "tampered_requests_executed": False,
    "exceptions_content_free": True, "authority_boundary_enforced": True,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
