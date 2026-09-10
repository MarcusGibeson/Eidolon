from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1101-0-runtime-")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

import dashboard_startup
import first_use_runtime
import release_metadata


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def test_python_311_or_newer_contract() -> None:
    require(sys.version_info >= (3, 11), sys.version)


def test_content_free_phase_receipt() -> None:
    payload = first_use_runtime.build_first_use_bootstrap()
    receipt = first_use_runtime.build_content_free_timing_receipt(payload)
    require(receipt["content_free"] is True, receipt)
    require(receipt["private_values_included"] is False, receipt)
    require(not first_use_runtime.timing_receipt_contains_private_fields(receipt), receipt)
    names = [row["name"] for row in receipt["phases"]]
    require(names == [
        "active_project_restoration",
        "conversation_restoration",
        "conversation_ownership_restoration",
        "provider_availability_restoration",
    ], names)


def test_timing_receipt_drops_private_runtime_values() -> None:
    payload = first_use_runtime.build_first_use_bootstrap()
    payload["draft"]["content"] = "PRIVATE DRAFT"
    payload["active_project"]["name"] = "PRIVATE PROJECT"
    receipt_text = json.dumps(first_use_runtime.build_content_free_timing_receipt(payload))
    require("PRIVATE DRAFT" not in receipt_text, receipt_text)
    require("PRIVATE PROJECT" not in receipt_text, receipt_text)


def test_actual_cold_sequence_meets_required_budgets() -> None:
    report = dashboard_startup.measure_first_use_sequence(
        ROOT, timeout_seconds=35, include_provider_probe=False,
    )
    require(report["ok"] is True, report)
    require(report["cold_health_below_target"] is True, report)
    require(report["first_health_response_seconds"] < 15.0, report)
    require(
        report["chat_interactive_below_target"]
        is (report["chat_input_interactive_seconds"] < report["target_chat_interactive_seconds"]),
        report,
    )
    require(report["content_free"] is True and report["private_values_included"] is False, report)
    require(report["active_conversation_restoration_completed"] is True, report)
    require(report["conversation_surface_available"] is True, report)


def test_cold_warm_and_fresh_external_runtime_are_measured() -> None:
    report = dashboard_startup.measure_cold_warm_and_fresh_first_use(
        ROOT, timeout_seconds=35, include_provider_probe=False,
    )
    require(report["ok"] is True, report)
    for key in ("cold", "warm", "fresh_external_runtime"):
        row = report[key]
        require(row["ok"] is True, (key, row))
        require(row["first_health_response_seconds"] < 15.0, (key, row))
        require(
            row["chat_interactive_below_target"]
            is (row["chat_input_interactive_seconds"] < row["target_chat_interactive_seconds"]),
            (key, row),
        )
        require(row["accepted_message_replayed"] is False, (key, row))
        require(row["provider_request_repeated"] is False, (key, row))
        require(row["active_conversation_restoration_completed"] is True, (key, row))


def test_version_reaches_bundle_candidate() -> None:
    version = tuple(int(part) for part in release_metadata.WORKING_SOURCE_VERSION.split("."))
    require(version >= (1101, 2), release_metadata.WORKING_SOURCE_VERSION)


TESTS = [(name.removeprefix("test_"), fn) for name, fn in list(globals().items()) if name.startswith("test_")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.parse_args()
    checks = []
    passed = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as error:
            checks.append({"name": name, "status": "fail", "message": f"{type(error).__name__}: {error}"})
        else:
            passed += 1
            checks.append({"name": name, "status": "pass", "message": ""})
    value = {"suite": "v1101.0-cold-start-budget-truth", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(value, indent=2))
    return 0 if value["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
