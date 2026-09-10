from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v1101-6-runtime-")

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
sys.path.insert(0, str(AGENT))

import windows_startup_soak


def require(value: object, message: object) -> None:
    if not value:
        raise AssertionError(message)


def _source_snapshot() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(ROOT.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def test_soak_run_count_is_bounded() -> None:
    require(windows_startup_soak.normalize_soak_runs(2) == 2, "minimum")
    require(windows_startup_soak.normalize_soak_runs(20) == 20, "maximum")
    for value in (1, 21, "not-a-number"):
        try:
            windows_startup_soak.normalize_soak_runs(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid run count accepted: {value}")


def test_real_repeated_startup_soak_is_content_free_and_stable() -> None:
    runtime = Path(tempfile.mkdtemp(prefix="eidolon-v1101-6-shared-"))
    report = windows_startup_soak.run_windows_startup_soak(
        ROOT,
        runs=2,
        timeout_seconds=35,
        include_provider_probe=False,
        runtime_root=runtime,
    )
    require(report["ok"] is True, report)
    require(report["run_count"] == 2 and len(report["runs"]) == 2, report)
    require(report["continuity_stable"] is True, report)
    require(report["health_budget_pass"] is True, report)
    measured_target = all(float(row["chat_interactive_seconds"]) < 5.0 for row in report["runs"])
    require(report["chat_interactive_budget_pass"] is measured_target, report)
    require(report["chat_interactive_target_required"] is False, report)
    require(report["performance_status"] == ("target_met" if measured_target else "target_miss"), report)
    require(report["accepted_message_replayed"] is False and report["provider_request_repeated"] is False, report)


def test_soak_does_not_mutate_source() -> None:
    before = _source_snapshot()
    windows_startup_soak.run_windows_startup_soak(ROOT, runs=2, timeout_seconds=35, include_provider_probe=False)
    after = _source_snapshot()
    require(before == after, {"before_count": len(before), "after_count": len(after)})


def test_non_windows_host_never_claims_native_windows_certification() -> None:
    report = windows_startup_soak.run_windows_startup_soak(
        ROOT,
        runs=2,
        timeout_seconds=35,
        include_provider_probe=False,
        platform_name="Windows",
    )
    expected_native = platform.system().lower() == "windows" and os.name == "nt"
    require(report["native_windows"] is expected_native, report)
    require(report["native_windows_certified"] is False, report)
    if not expected_native:
        require(report["classification"] == "cross_platform_compatibility_evidence", report)


def test_soak_report_contains_no_paths_or_private_payloads() -> None:
    fake = {
        "ok": True,
        "tcp_ready_seconds": 0.2,
        "first_health_response_seconds": 0.3,
        "chat_input_interactive_seconds": 0.4,
        "active_conversation_restoration_completed": True,
        "conversation_surface_available": True,
        "continuity_digest": "a" * 64,
        "provider_status": "not_checked",
        "cold_health_below_target": True,
        "chat_interactive_below_target": True,
    }
    original = windows_startup_soak.measure_first_use_sequence
    windows_startup_soak.measure_first_use_sequence = lambda *_args, **_kwargs: dict(fake)
    try:
        report = windows_startup_soak.run_windows_startup_soak(ROOT, runs=2, runtime_root=tempfile.mkdtemp())
    finally:
        windows_startup_soak.measure_first_use_sequence = original
    encoded = json.dumps(report).lower()
    for token in ("source_root", "runtime_root", "active_runtime_root", "prompt_text", "response_text", "draft_content", "provider_payload"):
        require(token not in encoded, token)
    require(report["content_free"] is True and report["private_values_included"] is False, report)


def test_cli_and_focused_registration_exist_once() -> None:
    cli = (ROOT / "tools" / "windows_startup_soak.py").read_text(encoding="utf-8")
    verifier = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
    require("run_windows_startup_soak" in cli and "--runs" in cli, "soak cli")
    require(verifier.count('"tools/v1101_6_windows_startup_soak_tests.py"') == 1, "focused registration")


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
    report = {"suite": "v1101.6-windows-startup-soak", "ok": passed == len(TESTS), "passed": passed, "total": len(TESTS), "checks": checks}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
