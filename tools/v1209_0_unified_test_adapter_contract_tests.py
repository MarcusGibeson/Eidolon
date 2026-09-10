from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))

from unified_test_adapter_contract import AUTHORITY_FLAGS, list_test_adapters

START = time.monotonic()
CHECKS: list[bool] = []


def require(value: bool, detail=None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


def source_signature() -> str:
    digest = hashlib.sha256()
    ignored = {".git", "data", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for path in sorted(ROOT.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file() or any(part in ignored for part in path.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


before = source_signature()
registry = list_test_adapters()
require(registry["status"] == "test_adapter_registry_ready", registry)
require(registry["adapter_count"] == 3, registry)
required = {
    "adapter_identity", "supported_project_kinds", "readiness", "dependencies",
    "execution_boundaries", "selected_tests", "outcome", "cleanup", "authority", "privacy",
}
for adapter in registry["adapters"]:
    require(required.issubset(adapter), adapter)
    require(adapter["readiness"]["runtime_checked"] is False, adapter)
    require(adapter["selected_tests"] == {
        "state": "not_selected", "count": 0, "selection_digest": None, "test_contents_included": False,
    }, adapter)
    require(adapter["outcome"]["state"] == "not_executed", adapter)
    require(adapter["cleanup"]["state"] == "not_required", adapter)
    require(adapter["execution_boundaries"]["specialized_executor_preserved"] is True, adapter)
    require(all(adapter["authority"][flag] is False for flag in AUTHORITY_FLAGS), adapter)
    require(all(value is False for value in adapter["privacy"].values()), adapter)
require(registry["tests_executed"] is False and registry["runtime_records_written"] is False, registry)
require(source_signature() == before, "source changed while describing adapter contracts")
print(json.dumps({
    "ok": True, "suite": "v1209.0-unified-test-adapter-contract", "version": "1209.0",
    "checks": len(CHECKS), "passed": sum(CHECKS), "source_immutable": True,
    "tests_executed_by_contract": False, "dependencies_installed": False,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
