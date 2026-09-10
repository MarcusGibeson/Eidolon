from __future__ import annotations

"""Regressions for v2503.2 verifier hot-path optimization.

These tests prove concurrency/configuration contracts without performing live
network requests or changing release authority.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for entry in (str(AGENT), str(ROOT / "tools")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import import_compatibility_regression as import_regression  # noqa: E402
import verification_compile  # noqa: E402
import verification_evidence  # noqa: E402


def run_tests() -> dict[str, object]:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    original_run_case = import_regression._run_case
    lock = threading.Lock()
    state = {"active": 0, "max_active": 0}

    def fake_run_case(case: dict[str, object], **_: object) -> dict[str, object]:
        with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        try:
            time.sleep(0.03)
            return {
                "label": case["label"],
                "kind": case["kind"],
                "surface": case.get("surface"),
                "run_index": 1,
                "ok": True,
            }
        finally:
            with lock:
                state["active"] -= 1

    try:
        import_regression._run_case = fake_run_case
        report = import_regression.build_import_report(max_workers=4)
    finally:
        import_regression._run_case = original_run_case

    checks["import-matrix-runs-concurrently"] = state["max_active"] >= 2
    checks["import-matrix-preserves-declared-order"] = [row["label"] for row in report["results"]] == [case["label"] for case in import_regression.IMPORT_CASES]
    checks["import-matrix-keeps-all-isolated-cases"] = report.get("check_count") == len(import_regression.IMPORT_CASES) and report.get("passed_count") == len(import_regression.IMPORT_CASES)
    checks["import-worker-count-recorded"] = report.get("execution_mode") == "parallel_isolated_processes" and report.get("max_workers") == 4
    details["import_matrix"] = {"max_active": state["max_active"], "max_workers": report.get("max_workers")}

    command_one = verification_compile.build_compile_command(workers=1)
    command_two = verification_compile.build_compile_command(workers=2)
    checks["compile-worker-one-is-explicit"] = command_one[command_one.index("-j") + 1] == "1"
    checks["compile-worker-two-is-explicit"] = command_two[command_two.index("-j") + 1] == "2"

    old_compile_env = os.environ.get("EIDOLON_COMPILE_WORKERS")
    old_import_env = os.environ.get("EIDOLON_IMPORT_WORKERS")
    try:
        os.environ["EIDOLON_COMPILE_WORKERS"] = "1"
        os.environ["EIDOLON_IMPORT_WORKERS"] = "2"
        checks["compile-worker-env-is-honored"] = verification_compile.build_compile_command()[verification_compile.build_compile_command().index("-j") + 1] == "1"
        original_run_case = import_regression._run_case
        import_regression._run_case = lambda case, **_: {"label": case["label"], "kind": case["kind"], "surface": case.get("surface"), "run_index": 1, "ok": True}
        try:
            env_report = import_regression.build_import_report()
        finally:
            import_regression._run_case = original_run_case
        checks["import-worker-env-is-honored"] = env_report.get("max_workers") == 2
    finally:
        if old_compile_env is None:
            os.environ.pop("EIDOLON_COMPILE_WORKERS", None)
        else:
            os.environ["EIDOLON_COMPILE_WORKERS"] = old_compile_env
        if old_import_env is None:
            os.environ.pop("EIDOLON_IMPORT_WORKERS", None)
        else:
            os.environ["EIDOLON_IMPORT_WORKERS"] = old_import_env

    original_snapshot = verification_evidence.source_snapshot_digest
    try:
        verification_evidence.source_snapshot_digest = lambda _root: (_ for _ in ()).throw(AssertionError("unexpected rescan"))
        validation = verification_evidence.validate_evidence_bundle(
            {"source_snapshot_sha256": "a" * 64},
            expected_root=ROOT,
            expected_producer="fixture",
            expected_invocation_nonce="fixture",
            expected_source_snapshot="a" * 64,
            attestation_key="fixture",
            current_source_snapshot="a" * 64,
        )
    finally:
        verification_evidence.source_snapshot_digest = original_snapshot
    checks["precomputed-current-source-digest-avoids-rescan"] = validation.get("checks", {}).get("source-current") is True

    release_verify_text = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
    checks["quick-core-throttles-inner-compile"] = '"env_overrides": {"EIDOLON_COMPILE_WORKERS": "1"}' in release_verify_text
    checks["quick-core-throttles-inner-imports"] = '"env_overrides": {"EIDOLON_IMPORT_WORKERS": "2"}' in release_verify_text

    ok = all(checks.values())
    return {
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "check_count": len(checks),
        "passed_count": sum(1 for value in checks.values() if value),
        "checks": checks,
        "details": details,
        "runtime_mutated": False,
        "authority_expanded": False,
        "network_request_count": 0,
        "provider_request_count": 0,
    }


def main() -> int:
    report = run_tests()
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, passed in report["checks"].items():
            print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        print(f"Status: {report['status']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
