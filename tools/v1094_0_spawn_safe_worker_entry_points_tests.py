from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

RESULTS: list[dict[str, object]] = []


def check(name: str, fn) -> None:
    try:
        fn()
        RESULTS.append({"name": name, "ok": True})
    except Exception as exc:
        RESULTS.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def wait_terminal(operation_id: str, process, timeout: float = 15.0):
    from process_ownership import inspect_process_operation
    process.join(timeout)
    require(not process.is_alive(), "spawn worker did not exit")
    deadline = time.monotonic() + 3
    state = inspect_process_operation(operation_id)
    while state.get("state") not in {"completed", "failed", "cancelled", "interrupted", "uncertain"} and time.monotonic() < deadline:
        time.sleep(0.03)
        state = inspect_process_operation(operation_id)
    return state


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1094-0-") as td:
        runtime = Path(td) / "runtime"
        lock_root = Path(td) / "locks"
        os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = str(runtime)
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = str(lock_root)
        os.environ["EIDOLON_TEST_UNDECLARED_SECRET"] = "must-not-cross"

        from process_worker_entrypoints import (
            process_worker_inventory,
            start_bounded_command_worker,
            validate_process_worker_config,
        )
        from process_ownership import inspect_process_operation, output_dir

        def inventory_contract():
            report = process_worker_inventory()
            require(report["worker_count"] >= 3, "worker inventory incomplete")
            require(report["content_free"] and not report["command_returned"] and not report["environment_returned"], "inventory leaked private state")
            require(any(row["id"] == "bounded_command_spawn" for row in report["rows"]), "spawn worker missing")

        def explicit_serializable_config():
            valid = validate_process_worker_config({"command": [sys.executable, "-c", "print('ok')"], "cwd": str(ROOT), "environment": {}})
            require(valid["command"][0] == sys.executable, "command normalization failed")
            try:
                validate_process_worker_config({"command": [sys.executable], "cwd": str(ROOT), "environment": {"X": object()}})
            except ValueError:
                return
            raise AssertionError("nonserializable inherited state accepted")

        def real_spawn_and_file_output():
            operation_id = f"spawn_{uuid.uuid4().hex}"
            launched = start_bounded_command_worker(
                operation_id=operation_id,
                acceptance_key="accept-1",
                operation_kind="verification",
                may_mutate=False,
                config={"command": [sys.executable, "-c", "print('spawn-ok')"], "cwd": str(ROOT), "environment": {}, "timeout_seconds": 10},
            )
            require(launched["worker_started"], "spawn worker did not start")
            state = wait_terminal(operation_id, launched["worker_handle"])
            require(state["state"] == "completed", f"worker state {state}")
            text = (output_dir(operation_id) / "stdout.txt").read_text(encoding="utf-8")
            require("spawn-ok" in text, "file-backed output missing")

        def environment_filtering():
            operation_id = f"env_{uuid.uuid4().hex}"
            code = "import os; print(os.getenv('EIDOLON_TEST_UNDECLARED_SECRET','absent'))"
            launched = start_bounded_command_worker(
                operation_id=operation_id,
                acceptance_key="accept-env",
                operation_kind="verification",
                may_mutate=False,
                config={"command": [sys.executable, "-c", code], "cwd": str(ROOT), "environment": {}, "timeout_seconds": 10},
            )
            state = wait_terminal(operation_id, launched["worker_handle"])
            require(state["state"] == "completed", "environment worker failed")
            text = (output_dir(operation_id) / "stdout.txt").read_text(encoding="utf-8").strip()
            require(text == "absent", "undeclared parent secret inherited")

        def duplicate_acceptance_does_not_spawn():
            operation_id = f"duplicate_{uuid.uuid4().hex}"
            config = {"command": [sys.executable, "-c", "import time; time.sleep(.2)"], "cwd": str(ROOT), "environment": {}, "timeout_seconds": 10}
            first = start_bounded_command_worker(operation_id=operation_id, acceptance_key="same", operation_kind="verification", may_mutate=False, config=config)
            second = start_bounded_command_worker(operation_id=operation_id, acceptance_key="same", operation_kind="verification", may_mutate=False, config=config)
            require(first["worker_started"], "first worker not started")
            require(second.get("duplicate") and not second.get("worker_started"), "duplicate spawned")
            wait_terminal(operation_id, first["worker_handle"])

        def runtime_is_external_and_private():
            operation_id = f"private_{uuid.uuid4().hex}"
            launched = start_bounded_command_worker(
                operation_id=operation_id, acceptance_key="private", operation_kind="verification", may_mutate=False,
                config={"command": [sys.executable, "-c", "print('x')"], "cwd": str(ROOT), "environment": {}, "timeout_seconds": 10},
            )
            wait_terminal(operation_id, launched["worker_handle"])
            require(runtime in output_dir(operation_id).parents, "process output not external")
            public = inspect_process_operation(operation_id)
            serialized = json.dumps(public)
            require(str(runtime) not in serialized and "owner_pid" not in serialized and "acceptance_key" not in serialized, "public state leaked private ownership")

        def module_level_spawn_target():
            source = (AGENT / "process_worker_entrypoints.py").read_text(encoding="utf-8")
            tree = ast.parse(source)
            names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            require("run_bounded_command_worker" in names, "spawn target is not module-level")
            require(not any(isinstance(node, ast.Lambda) for node in ast.walk(tree)), "lambda process target found")
            require('get_context("spawn")' in source, "spawn context missing")

        def dashboard_and_release_contract():
            dashboard = (AGENT / "dashboard.py").read_text(encoding="utf-8")
            require('/api/process-worker-inventory' in dashboard, "dashboard inventory route missing")
            metadata = (AGENT / "release_metadata.py").read_text(encoding="utf-8")
            require('RUNTIME_VERSION = "1094.' in metadata, "runtime version not in v1094 arc")

        for name, fn in (
            ("content-free worker inventory", inventory_contract),
            ("explicit serializable worker configuration", explicit_serializable_config),
            ("real spawn worker and file-backed output", real_spawn_and_file_output),
            ("filtered environment inheritance", environment_filtering),
            ("duplicate acceptance does not spawn", duplicate_acceptance_does_not_spawn),
            ("external private process runtime", runtime_is_external_and_private),
            ("module-level spawn target", module_level_spawn_target),
            ("dashboard and release contract", dashboard_and_release_contract),
        ):
            check(name, fn)

    passed = sum(1 for row in RESULTS if row["ok"])
    report = {"version": "1094.0", "status": "pass" if passed == len(RESULTS) else "fail", "passed": passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
