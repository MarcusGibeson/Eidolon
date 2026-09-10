from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))

from unified_test_adapter_contract import prepare_test_adapter_execution

START = time.monotonic()
CHECKS: list[bool] = []


def require(value: bool, detail=None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


def prepare(kind="python_project", **changes):
    values = {
        "proposal_id": "proposal-1209",
        "expected_revision": 2,
        "expected_revision_digest": "a" * 64,
        "expected_workspace_digest": "b" * 64,
        "approval_receipt_digest": "c" * 64,
        "execution_authorized": True,
    }
    values.update(changes)
    return prepare_test_adapter_execution(kind, **values)


for kind, adapter_id in (
    ("new_small_web_project", "browser_runtime"),
    ("javascript_tool_project", "node_javascript"),
    ("python_project", "python"),
):
    extra = {"expected_preview_digest": "d" * 64} if adapter_id == "browser_runtime" else {}
    row = prepare(kind, **extra)
    require(row["status"] == "test_adapter_execution_prepared", row)
    require(row["selected_adapter_id"] == adapter_id, row)
    require(row["authority"]["execution_authorized"] is True, row)
    require(row["tests_executed"] is False and row["runtime_records_written"] is False, row)
    require(bool(row["selection_digest"] and row["execution_request_digest"]), row)

blocked = prepare("python_project", execution_authorized=False)
require(blocked["status"] == "test_adapter_execution_approval_required", blocked)
require(all(value is False for value in blocked["authority"].values()), blocked)
require(blocked["tests_executed"] is False, blocked)

for change, reason in (
    ({"proposal_id": ""}, "proposal_id_missing"),
    ({"expected_revision": 0}, "expected_revision_invalid"),
    ({"expected_revision_digest": ""}, "expected_revision_digest_missing"),
    ({"expected_workspace_digest": ""}, "expected_workspace_digest_missing"),
    ({"approval_receipt_digest": ""}, "approval_receipt_digest_missing"),
):
    invalid = prepare(**change)
    require(invalid["status"] == "test_adapter_execution_request_invalid", invalid)
    require(invalid["reason"] == reason, invalid)

browser_without_preview = prepare("new_small_web_project")
require(browser_without_preview["reason"] == "expected_preview_digest_missing", browser_without_preview)
ambiguous = prepare("javascript_or_web_project")
require(ambiguous["status"] == "test_adapter_ambiguous", ambiguous)
unsupported = prepare("mobile_application")
require(unsupported["status"] == "test_adapter_unsupported", unsupported)

encoded = json.dumps([blocked, browser_without_preview, ambiguous, unsupported], sort_keys=True)
for forbidden in ("private path", "test body", "provider prompt", "credential value", "runtime output"):
    require(forbidden not in encoded, encoded)

print(json.dumps({
    "ok": True, "suite": "v1209.3-test-adapter-execution-request", "version": "1209.3",
    "checks": len(CHECKS), "passed": sum(CHECKS), "tests_executed": False,
    "separate_execution_authorization_required": True, "runtime_records_written": False,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
