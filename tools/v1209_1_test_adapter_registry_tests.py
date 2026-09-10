from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))

from unified_test_adapter_contract import list_test_adapters, registry_digest, validate_registry

START = time.monotonic()
CHECKS: list[bool] = []


def require(value: bool, detail=None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


first = list_test_adapters()
second = list_test_adapters()
require(first == second, (first, second))
require(first["registry_digest"] == registry_digest(), first)
require(validate_registry(first), first)
ids = [row["adapter_identity"]["adapter_id"] for row in first["adapters"]]
require(ids == ["browser_runtime", "node_javascript", "python"], ids)
require(len(ids) == len(set(ids)), ids)
require(first["inspection_only"] is True, first)
require(not first["providers_contacted"] and not first["dependencies_installed"] and not first["projects_modified"], first)
for row in first["adapters"]:
    dependency_ids = [item["dependency_id"] for item in row["dependencies"]]
    require(dependency_ids and len(dependency_ids) == len(set(dependency_ids)), row)
    require(all(item["availability"] == "deferred_until_authorized_execution" for item in row["dependencies"]), row)

duplicate = [dict(row) for row in first["adapters"]]
duplicate[1] = dict(duplicate[1])
duplicate[1]["adapter_identity"] = dict(duplicate[0]["adapter_identity"])
invalid = list_test_adapters(duplicate)
require(invalid["status"] == "test_adapter_configuration_error", invalid)
require(invalid["configuration_error"] in {"duplicate_adapter_identity", "adapter_contract_digest_invalid"}, invalid)
print(json.dumps({
    "ok": True, "suite": "v1209.1-test-adapter-registry", "version": "1209.1",
    "checks": len(CHECKS), "passed": sum(CHECKS), "registry_deterministic": True,
    "runtime_probed": False, "dependencies_installed": False,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
