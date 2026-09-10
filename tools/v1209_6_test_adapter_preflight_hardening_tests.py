from __future__ import annotations

import json
import sys
import time
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))

from ordinary_chat_development_campaign import _digest
from unified_test_adapter_contract import prepare_test_adapter_execution, run_or_resume_selected_test_adapter

START = time.monotonic()
CHECKS: list[bool] = []


def require(value: bool, detail=None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


def prepare(kind="python_project", **changes):
    values = {
        "proposal_id": "proposal-preflight",
        "expected_revision": 4,
        "expected_revision_digest": "a" * 64,
        "expected_workspace_digest": "b" * 64,
        "approval_receipt_digest": "c" * 64,
        "execution_authorized": True,
    }
    values.update(changes)
    return prepare_test_adapter_execution(kind, **values)


for field, reason in (
    ("expected_revision_digest", "expected_revision_digest_invalid"),
    ("expected_workspace_digest", "expected_workspace_digest_invalid"),
    ("approval_receipt_digest", "approval_receipt_digest_invalid"),
):
    for invalid in ("f" * 63, "g" * 64, 7):
        result = prepare(**{field: invalid})
        require(result["status"] == "test_adapter_execution_request_invalid", result)
        require(result["reason"] == reason, result)

bad_preview = prepare("new_small_web_project", expected_preview_digest="z" * 64)
require(bad_preview["reason"] == "expected_preview_digest_invalid", bad_preview)

for malformed in (None, [], "request"):
    result = run_or_resume_selected_test_adapter(malformed)  # type: ignore[arg-type]
    require(result["status"] == "test_adapter_execution_request_invalid", result)
    require(result["reliability"]["failure_class"] == "request_invalid", result)

request = prepare("javascript_tool_project")
tampered = dict(request)
tampered["authority"] = "execution"
tampered["execution_request_digest"] = _digest({key: value for key, value in tampered.items() if key != "execution_request_digest"})
blocked = run_or_resume_selected_test_adapter(tampered)
require(blocked["status"] == "test_adapter_execution_request_invalid", blocked)

seen: list[dict] = []


def loader(adapter_id):
    def execute(proposal_id, **kwargs):
        seen.append(kwargs)
        return {
            "ok": True, "status": "node_javascript_test_adapter_passed", "passed": True,
            "node_executed": True, "node_javascript_test_digest": "d" * 64,
            "test_file_count": 1, "test_selection_digest": "e" * 64,
            "cleanup_confirmed": True, "operation_status": "created",
            "approval_receipt_digest": "c" * 64,
        }
    return execute, lambda row: dict(row)


runtime_root = PureWindowsPath("C:/Eidolon Runtime/records")
executable = r"C:\Program Files\nodejs\node.exe"
completed = run_or_resume_selected_test_adapter(
    request, runtime_root=runtime_root, executable=executable, adapter_loader=loader,
)
require(completed["status"] == "test_adapter_execution_completed", completed)
require(completed["reliability"]["runtime_root_supplied"] is True, completed)
require(completed["reliability"]["executable_override_supplied"] is True, completed)
require(completed["reliability"]["path_values_exposed"] is False, completed)
require(seen[0]["runtime_root"] == runtime_root and seen[0]["node_executable"] == executable, seen)
encoded = json.dumps(completed, sort_keys=True)
require("Eidolon Runtime" not in encoded and "Program Files" not in encoded, encoded)
require("_runtime_root_supplied" not in completed and "_executable_override_supplied" not in completed, completed)

print(json.dumps({
    "ok": True, "suite": "v1209.6-test-adapter-preflight-hardening", "version": "1209.6",
    "checks": len(CHECKS), "passed": sum(CHECKS), "strict_digest_binding": True,
    "windows_path_values_exposed": False, "malformed_requests_blocked": True,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
