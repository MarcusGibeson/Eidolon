from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "conscious_agent"))

from ordinary_chat_development_campaign import _digest
from unified_test_adapter_contract import list_test_adapters, select_test_adapter

START = time.monotonic()
CHECKS: list[bool] = []


def require(value: bool, detail=None) -> None:
    if not value:
        raise AssertionError(detail)
    CHECKS.append(True)


expected = {
    "new_small_web_project": "browser_runtime",
    "static_web_project": "browser_runtime",
    "empty_project": "browser_runtime",
    "new_javascript_tool_project": "node_javascript",
    "javascript_tool_project": "node_javascript",
    "new_python_cli_project": "python",
    "python_cli_project": "python",
    "python_project": "python",
}
for kind, adapter_id in expected.items():
    result = select_test_adapter(kind)
    require(result["status"] == "test_adapter_selected", result)
    require(result["selected_adapter_id"] == adapter_id, result)
    require(result["execution_requires_separate_authorization"] is True, result)
    require(all(value is False for value in result["authority"].values()), result)

unsupported = select_test_adapter("mobile_application")
require(unsupported["status"] == "test_adapter_unsupported", unsupported)

ambiguous = select_test_adapter("javascript_or_web_project")
require(ambiguous["status"] == "test_adapter_ambiguous", ambiguous)
require(ambiguous["candidate_adapter_ids"] == ["browser_runtime", "node_javascript"], ambiguous)
resolved = select_test_adapter("javascript_or_web_project", requested_adapter_id="node_javascript")
require(resolved["status"] == "test_adapter_selected" and resolved["selected_adapter_id"] == "node_javascript", resolved)

rows = copy.deepcopy(list_test_adapters()["adapters"])
python_row = next(row for row in rows if row["adapter_identity"]["adapter_id"] == "python")
python_row["readiness"] = {
    **python_row["readiness"], "state": "unavailable", "reason": "configured_runtime_unavailable",
}
python_row["adapter_contract_digest"] = _digest({key: value for key, value in python_row.items() if key != "adapter_contract_digest"})
unavailable_registry = list_test_adapters(rows)
unavailable = select_test_adapter("python_project", registry=unavailable_registry)
require(unavailable["status"] == "test_adapter_unavailable", unavailable)
require(unavailable["reason"] == "configured_runtime_unavailable", unavailable)

bad_rows = copy.deepcopy(list_test_adapters()["adapters"])
bad_rows[0]["readiness"]["state"] = "mystery"
configuration_error = select_test_adapter("new_small_web_project", registry={
    **list_test_adapters(), "adapters": bad_rows,
})
require(configuration_error["status"] == "test_adapter_configuration_error", configuration_error)
unknown_request = select_test_adapter("python_project", requested_adapter_id="missing")
require(unknown_request["status"] == "test_adapter_configuration_error", unknown_request)
missing_kind = select_test_adapter("")
require(missing_kind["status"] == "test_adapter_configuration_error", missing_kind)

public_json = json.dumps([unsupported, ambiguous, unavailable, configuration_error], sort_keys=True)
for forbidden in ("private path", "test body", "provider prompt", "credential", "runtime output"):
    require(forbidden not in public_json, public_json)

release = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
for stage in (
    "v1209.0-unified-test-adapter-contract",
    "v1209.1-test-adapter-registry",
    "v1209.2-test-adapter-selection",
):
    require(release.count(f'"{stage}"') == 2, (stage, release.count(f'"{stage}"')))

print(json.dumps({
    "ok": True, "suite": "v1209.2-test-adapter-selection", "version": "1209.2",
    "checks": len(CHECKS), "passed": sum(CHECKS), "supported_states": 5,
    "tests_executed_by_selection": False, "operator_review_required": True,
    "elapsed_seconds": round(time.monotonic() - START, 4),
}, sort_keys=True), flush=True)
