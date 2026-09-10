from __future__ import annotations

"""Import compatibility and complete-report performance regressions.

Every import surface runs in its own interpreter and emits a unique sentinel.
Complete reports are a separate mode with an evidence graph, so inventory and
corrective stages execute once and the consolidated report consumes them.
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for entry in (str(AGENT), str(ROOT / "tools")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from verification_evidence import (
    ENV_ATTESTATION_KEY,
    ENV_EVIDENCE_FILE,
    ENV_EVIDENCE_PURPOSE,
    ENV_EXPECTED_PRODUCER,
    ENV_INVOCATION_NONCE,
    ENV_SOURCE_SNAPSHOT,
    build_evidence_bundle,
    build_stage_receipt,
    expected_stage_commands,
    isoformat_utc,
    new_attestation_key,
    new_invocation_nonce,
    source_snapshot_digest,
    write_evidence_bundle,
)

PACKAGE_SENTINEL = "EIDOLON_PACKAGE_IMPORT_OK"
SCRIPT_SENTINEL = "EIDOLON_DIRECT_IMPORT_OK"
API_SENTINEL = "EIDOLON_API_IMPORT_OK"
REGISTRY_SENTINEL = "EIDOLON_REGISTRY_IMPORT_OK"
INVENTORY_SENTINEL = "EIDOLON_INVENTORY_IMPORT_OK"
API_HELP_SENTINEL = "EIDOLON_API_CLI_HELP_OK"
TREE_SNAPSHOT_EXCLUDED_DIRS = {".git", ".venv", "venv"}


def _physical_tree_snapshot(root: Path) -> dict[str, str]:
    """Hash the complete extracted tree while excluding tooling infrastructure."""
    snapshot: dict[str, str] = {}
    for current, directories, names in os.walk(root):
        directories[:] = [name for name in directories if name not in TREE_SNAPSHOT_EXCLUDED_DIRS]
        current_path = Path(current)
        if current_path != root:
            relative_dir = current_path.relative_to(root).as_posix()
            snapshot[f"{relative_dir}/"] = "directory"
        for name in names:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def _package_import_code(module: str, sentinel: str) -> str:
    return f"import {module}; print({sentinel!r})"


def _direct_import_code(module: str, sentinel: str) -> str:
    return f"import sys; sys.path.insert(0, {str(AGENT)!r}); import {module}; print({sentinel!r})"


IMPORT_CASES: tuple[dict[str, Any], ...] = (
    {
        "label": "package-namespace-import",
        "kind": "package_import",
        "surface": "package",
        "command": (sys.executable, "-c", _package_import_code("conscious_agent.release_metadata", PACKAGE_SENTINEL)),
        "timeout": 45,
        "sentinel": PACKAGE_SENTINEL,
    },
    {
        "label": "historical-direct-script-namespace-import",
        "kind": "direct_script_import",
        "surface": "direct-script",
        "command": (sys.executable, "-c", _direct_import_code("release_metadata", SCRIPT_SENTINEL)),
        "timeout": 45,
        "sentinel": SCRIPT_SENTINEL,
    },
    {
        "label": "api-package-import",
        "kind": "api_import",
        "surface": "api/package",
        "command": (sys.executable, "-c", _package_import_code("conscious_agent.api_server", API_SENTINEL)),
        "timeout": 45,
        "sentinel": API_SENTINEL,
    },
    {
        "label": "api-direct-script-import",
        "kind": "api_import",
        "surface": "api/direct-script",
        "command": (sys.executable, "-c", _direct_import_code("api_server", API_SENTINEL)),
        "timeout": 45,
        "sentinel": API_SENTINEL,
    },
    {
        "label": "registry-package-import",
        "kind": "registry_import",
        "surface": "registry/package",
        "command": (sys.executable, "-c", _package_import_code("conscious_agent.registry_navigation_smoke_consolidation", REGISTRY_SENTINEL)),
        "timeout": 45,
        "sentinel": REGISTRY_SENTINEL,
    },
    {
        "label": "registry-direct-script-import",
        "kind": "registry_import",
        "surface": "registry/direct-script",
        "command": (sys.executable, "-c", _direct_import_code("registry_navigation_smoke_consolidation", REGISTRY_SENTINEL)),
        "timeout": 45,
        "sentinel": REGISTRY_SENTINEL,
    },
    {
        "label": "inventory-package-import",
        "kind": "inventory_import",
        "surface": "inventory/package",
        "command": (sys.executable, "-c", _package_import_code("conscious_agent.version_metadata_inventory", INVENTORY_SENTINEL)),
        "timeout": 45,
        "sentinel": INVENTORY_SENTINEL,
    },
    {
        "label": "inventory-direct-script-import",
        "kind": "inventory_import",
        "surface": "inventory/direct-script",
        "command": (sys.executable, "-c", _direct_import_code("version_metadata_inventory", INVENTORY_SENTINEL)),
        "timeout": 45,
        "sentinel": INVENTORY_SENTINEL,
    },
    {
        "label": "api-package-cli-help",
        "kind": "cli_entry_point",
        "surface": "api/package-cli",
        "command": (sys.executable, "-m", "conscious_agent.api_server", "--help"),
        "timeout": 45,
        "sentinel": API_HELP_SENTINEL,
    },
    {
        "label": "api-script-cli-help",
        "kind": "cli_entry_point",
        "surface": "api/script-cli",
        "command": (sys.executable, "conscious_agent/api_server.py", "--help"),
        "timeout": 45,
        "sentinel": API_HELP_SENTINEL,
    },
)

REPORT_CASES: tuple[dict[str, Any], ...] = (
    {
        "label": "inventory-complete-report",
        "kind": "report_performance",
        "surface": "inventory",
        "command": (sys.executable, "-m", "conscious_agent.version_metadata_inventory", "--json"),
        "timeout": 90,
        "performance_budget_seconds": 30,
    },
    {
        "label": "corrective-complete-report",
        "kind": "report_dependency",
        "surface": "corrective",
        "command": (sys.executable, "tools/pre_v1078_9_corrective_tests.py", "--json"),
        "timeout": 300,
        "performance_budget_seconds": 180,
    },
    {
        "label": "registry-complete-report",
        "kind": "report_performance",
        "surface": "registry",
        "command": (sys.executable, "-m", "conscious_agent.registry_navigation_smoke_consolidation", "--json"),
        "timeout": 600,
        "performance_budget_seconds": 300,
    },
)


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10, check=False)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _run_case(
    case: dict[str, Any],
    *,
    run_index: int = 1,
    command_override: tuple[str, ...] | None = None,
    retain_payload: bool = False,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    command = tuple(str(part) for part in (command_override or case["command"]))
    timeout = int(case["timeout"])
    started_at = isoformat_utc()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="eidolon-import-regression-") as temp_dir:
        stdout_path = Path(temp_dir) / "stdout.log"
        stderr_path = Path(temp_dir) / "stderr.log"
        runtime_data_path = Path(temp_dir) / "runtime-data"
        runtime_data_path.mkdir()
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        kwargs: dict[str, Any] = {} if os.name == "nt" else {"start_new_session": True}
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            process = subprocess.Popen(
                list(command),
                cwd=ROOT,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                env={
                    **os.environ,
                    "PYTHONUNBUFFERED": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "EIDOLON_DATA_DIR": str(runtime_data_path),
                    **(env_overrides or {}),
                },
                creationflags=creationflags,
                **kwargs,
            )
            try:
                return_code = process.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate(process)
                return_code = process.returncode if process.returncode is not None else -1
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")

    elapsed = round(time.perf_counter() - started, 3)
    finished_at = isoformat_utc()
    sentinel = case.get("sentinel")
    sentinel_ok = True if not sentinel else str(sentinel).lower() in stdout.lower()
    parsed_payload: dict[str, Any] | None = None
    parse_error: str | None = None
    report_case = case["kind"] in {"report_performance", "report_dependency"}
    if report_case and not timed_out:
        try:
            candidate = json.loads(stdout)
            if not isinstance(candidate, dict):
                raise TypeError("JSON report must be an object")
            parsed_payload = candidate
        except (json.JSONDecodeError, TypeError) as exc:
            parse_error = f"{type(exc).__name__}: {exc}"

    parse_ok = not report_case or parsed_payload is not None
    functional_ok = parsed_payload.get("ok") is True if parsed_payload is not None else (sentinel_ok if not report_case else False)
    exit_ok = not timed_out and return_code == 0
    performance_budget = case.get("performance_budget_seconds")
    performance_ok = True if performance_budget is None else elapsed <= float(performance_budget)
    ok = exit_ok and parse_ok and functional_ok and performance_ok
    result = {
        "label": case["label"],
        "kind": case["kind"],
        "surface": case.get("surface"),
        "run_index": run_index,
        "command": list(command),
        "ok": ok,
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": elapsed,
        "started_at": started_at,
        "finished_at": finished_at,
        "timeout_seconds": timeout,
        "performance_budget_seconds": performance_budget,
        "performance_budget_ok": performance_ok,
        "performance_status": "pass" if performance_ok else "blocked",
        "sentinel": sentinel,
        "sentinel_ok": sentinel_ok,
        "functional_ok": functional_ok,
        "functional_status": "pass" if functional_ok else "blocked",
        "exit_ok": exit_ok,
        "exit_status": "timeout" if timed_out else ("pass" if exit_ok else "blocked"),
        "parse_ok": parse_ok,
        "parse_status": "not_applicable" if not report_case else ("pass" if parse_ok else "blocked"),
        "parsed_report_status": parsed_payload.get("status") if parsed_payload else None,
        "failed_report_rows": [
            {
                "name": row.get("name"),
                "status": row.get("status"),
                "summary": row.get("summary"),
                "details": row.get("details"),
            }
            for row in (parsed_payload or {}).get("rows", [])
            if isinstance(row, dict) and row.get("ok") is not True
        ],
        "verification_evidence": (parsed_payload or {}).get("verification_evidence"),
        "expensive_stage_ownership": (parsed_payload or {}).get("expensive_stage_ownership"),
        "parse_error": parse_error,
        "error": f"timeout after {timeout}s" if timed_out else None,
        "stdout_tail": "\n".join(stdout.splitlines()[-12:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-12:]),
    }
    if retain_payload:
        result["_parsed_payload"] = parsed_payload
    return result


def _summary(mode: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    public_results = [{key: value for key, value in row.items() if not key.startswith("_")} for row in results]
    return {
        "mode": mode,
        "status": "pass" if all(row["ok"] for row in results) else "blocked",
        "ok": all(row["ok"] for row in results),
        "check_count": len(results),
        "passed_count": sum(1 for row in results if row["ok"]),
        "results": public_results,
        "expensive_reports_used_for_import_resolution": False,
        "independent_status_dimensions": ["functional", "exit", "parse", "performance"],
    }


def build_import_report(*, max_workers: int | None = None) -> dict[str, Any]:
    """Run isolated import surfaces concurrently without sharing interpreters.

    Every case still owns a dedicated child Python process and disposable runtime
    directory.  Concurrency removes only the unnecessary parent-side
    serialization; result ordering remains the declared IMPORT_CASES ordering so
    receipts and diagnostics stay deterministic.
    """
    resolved_workers = max_workers if max_workers is not None else int(os.environ.get("EIDOLON_IMPORT_WORKERS", "6"))
    max_workers = max(1, min(int(resolved_workers), len(IMPORT_CASES)))
    indexed_results: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_case, case): index
            for index, case in enumerate(IMPORT_CASES)
        }
        for future in as_completed(futures):
            indexed_results[futures[future]] = future.result()
    results = [indexed_results[index] for index in range(len(IMPORT_CASES))]
    report = _summary("imports", results)
    report["execution_mode"] = "parallel_isolated_processes"
    report["max_workers"] = max_workers
    return report


def _report_case(label: str) -> dict[str, Any]:
    return next(case for case in REPORT_CASES if case["label"] == label)


def build_report_performance_report(*, repeat: int = 1) -> dict[str, Any]:
    physical_tree_before = _physical_tree_snapshot(ROOT)
    results: list[dict[str, Any]] = []
    for run_index in range(1, repeat + 1):
        producer = f"import_compatibility_regression:reports:{run_index}"
        invocation_nonce = new_invocation_nonce()
        attestation_key = new_attestation_key()
        command_map = expected_stage_commands(ROOT, purpose="report-performance")
        source_before_inventory = source_snapshot_digest(ROOT)
        inventory = _run_case(
            _report_case("inventory-complete-report"),
            run_index=run_index,
            command_override=tuple(command_map["version-inventory"][0]),
            retain_payload=True,
        )
        source_after_inventory = source_snapshot_digest(ROOT)
        corrective = _run_case(
            _report_case("corrective-complete-report"),
            run_index=run_index,
            command_override=tuple(command_map["corrective-suite"][0]),
            retain_payload=True,
        )
        source_after_corrective = source_snapshot_digest(ROOT)
        results.extend((inventory, corrective))
        with tempfile.TemporaryDirectory(prefix="eidolon-report-evidence-") as temp_dir:
            evidence_path = Path(temp_dir) / "verification-evidence.json"
            stage_inputs = {
                "version-inventory": (inventory, source_before_inventory, source_after_inventory),
                "corrective-suite": (corrective, source_after_inventory, source_after_corrective),
            }
            receipts = {
                name: build_stage_receipt(
                    name,
                    producer=producer,
                    invocation_nonce=invocation_nonce,
                    source_snapshot_before=source_before,
                    source_snapshot_after=source_after,
                    commands=[result["command"]],
                    report=result.get("_parsed_payload") or {},
                    started_at=str(result["started_at"]),
                    finished_at=str(result["finished_at"]),
                    elapsed_seconds=float(result["elapsed_seconds"]),
                    return_code=int(result["return_code"]),
                    timed_out=bool(result["timed_out"]),
                    subprocess_execution_count=1,
                    attestation_key=attestation_key,
                )
                for name, (result, source_before, source_after) in stage_inputs.items()
            }
            bundle = build_evidence_bundle(
                ROOT,
                producer=producer,
                invocation_nonce=invocation_nonce,
                source_snapshot_sha256=source_before_inventory,
                attestation_key=attestation_key,
                stages=receipts,
                purpose="report-performance",
            )
            write_evidence_bundle(evidence_path, bundle)
            registry_case = _report_case("registry-complete-report")
            registry_command = (*registry_case["command"], "--evidence-file", str(evidence_path))
            registry = _run_case(
                registry_case,
                run_index=run_index,
                command_override=registry_command,
                env_overrides={
                    ENV_EVIDENCE_FILE: str(evidence_path),
                    ENV_ATTESTATION_KEY: attestation_key,
                    ENV_INVOCATION_NONCE: invocation_nonce,
                    ENV_EXPECTED_PRODUCER: producer,
                    ENV_SOURCE_SNAPSHOT: source_before_inventory,
                    ENV_EVIDENCE_PURPOSE: "report-performance",
                },
            )
            results.append(registry)
    report = _summary("reports", results)
    report["repeat"] = repeat
    report["stage_execution_counts"] = {
        label: sum(1 for row in results if row["label"] == label)
        for label in ("inventory-complete-report", "corrective-complete-report", "registry-complete-report")
    }
    physical_tree_after = _physical_tree_snapshot(ROOT)
    before_paths = set(physical_tree_before)
    after_paths = set(physical_tree_after)
    modified = sorted(
        path for path in before_paths & after_paths
        if physical_tree_before[path] != physical_tree_after[path]
    )
    tree_delta = {
        "added": sorted(after_paths - before_paths),
        "removed": sorted(before_paths - after_paths),
        "modified": modified,
    }
    tree_unchanged = not any(tree_delta.values())
    report["source_tree_immutability"] = {"unchanged": tree_unchanged, **tree_delta}
    if not tree_unchanged:
        report["ok"] = False
        report["status"] = "blocked"
    return report


def build_report(*, mode: str = "imports", repeat: int = 1, import_workers: int | None = None) -> dict[str, Any]:
    if mode == "imports":
        return build_import_report(max_workers=import_workers)
    if mode == "reports":
        return build_report_performance_report(repeat=repeat)
    import_report = build_import_report(max_workers=import_workers)
    performance_report = build_report_performance_report(repeat=repeat)
    results = [*import_report["results"], *performance_report["results"]]
    report = _summary("all", results)
    report["imports"] = import_report
    report["reports"] = performance_report
    report["repeat"] = repeat
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify isolated import surfaces separately from complete report performance.")
    parser.add_argument("--mode", choices=("imports", "reports", "all"), default="imports")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--workers", type=int, default=None, help="parallel isolated import workers (defaults to EIDOLON_IMPORT_WORKERS or 6)")
    args = parser.parse_args()
    if args.repeat < 1 or args.repeat > 3:
        parser.error("--repeat must be between 1 and 3")
    if args.workers is not None and (args.workers < 1 or args.workers > len(IMPORT_CASES)):
        parser.error(f"--workers must be between 1 and {len(IMPORT_CASES)}")
    report = build_report(mode=args.mode, repeat=args.repeat, import_workers=args.workers)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for row in report["results"]:
            print(
                f"[{'PASS' if row['ok'] else 'FAIL'}] {row['label']} run={row['run_index']} "
                f"({row['elapsed_seconds']}s, functional={row['functional_status']}, exit={row['exit_status']}, "
                f"parse={row['parse_status']}, performance={row['performance_status']})"
            )
        print(f"Status: {report['status']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
