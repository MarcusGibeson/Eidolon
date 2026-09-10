from __future__ import annotations

import json
import multiprocessing as mp
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check(name: str, fn) -> None:
    try:
        fn(); RESULTS.append({"name": name, "ok": True})
    except Exception as exc:
        RESULTS.append({"name": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})


def _persist_then_die(operation_id: str, generation: int, runtime: str, locks: str) -> None:
    os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = runtime
    os.environ["EIDOLON_METADATA_LOCK_DIR"] = locks
    if str(AGENT) not in sys.path:
        sys.path.insert(0, str(AGENT))
    from process_ownership import activate_process_operation, write_process_result
    active = activate_process_operation(operation_id, generation)
    if active.get("ok"):
        write_process_result(operation_id, generation=generation, owner_nonce=str(active["owner_nonce"]), state="completed", return_code=0)
    os._exit(0)


def wait_child(operation_id: str, timeout: float = 15.0):
    from process_ownership import inspect_process_operation
    deadline = time.monotonic() + timeout
    state = inspect_process_operation(operation_id)
    while not state.get("child_active") and time.monotonic() < deadline:
        time.sleep(.03); state = inspect_process_operation(operation_id)
    return state


def start_orphan(operation_id: str, *, may_mutate: bool):
    from process_worker_entrypoints import start_bounded_command_worker
    launched = start_bounded_command_worker(
        operation_id=operation_id, acceptance_key="orphan", operation_kind="project_work" if may_mutate else "verification", may_mutate=may_mutate,
        config={"command": [sys.executable, "-c", "import time; time.sleep(60)"], "cwd": str(ROOT), "environment": {}, "timeout_seconds": 120},
    )
    require(launched.get("worker_started"), "worker not started")
    require(wait_child(operation_id).get("child_active"), "child not registered")
    worker = launched["worker_handle"]
    worker.terminate(); worker.join(10)
    require(not worker.is_alive(), "worker did not die")
    return launched


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1094-2-") as td:
        runtime = str(Path(td) / "runtime")
        locks = str(Path(td) / "locks")
        os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = runtime
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = locks
        from json_storage import write_json_atomic
        from process_ownership import (
            accept_process_operation,
            inspect_process_operation,
            ownership_path,
        )
        from process_recovery import (
            build_process_recovery_state,
            cleanup_process_recovery_operation,
            reconcile_process_operation,
            reconcile_process_recovery_operation,
        )

        def read_only_orphan_recovery():
            operation_id = f"read_{uuid.uuid4().hex}"
            start_orphan(operation_id, may_mutate=False)
            state = reconcile_process_operation(operation_id)
            require(state["status"] == "orphan_running" and not state["replay_allowed"], f"orphan not detected {state}")
            recovered = reconcile_process_recovery_operation(operation_id, operator_confirmed=True)
            require(recovered["status"] == "interrupted" and recovered["safe_retry"] and recovered.get("orphan_terminated"), f"read orphan not safely interrupted {recovered}")

        def mutating_orphan_is_uncertain():
            operation_id = f"mutate_{uuid.uuid4().hex}"
            start_orphan(operation_id, may_mutate=True)
            recovered = reconcile_process_recovery_operation(operation_id, operator_confirmed=True)
            require(recovered["status"] == "uncertain" and not recovered["safe_retry"] and not recovered["replay_allowed"], f"mutating orphan replay boundary broken {recovered}")

        def generation_bound_result_reconciles():
            operation_id = f"result_{uuid.uuid4().hex}"
            accepted = accept_process_operation(operation_id, operation_kind="verification", may_mutate=False, acceptance_key="result")
            ctx = mp.get_context("spawn")
            process = ctx.Process(target=_persist_then_die, args=(operation_id, accepted["generation"], runtime, locks))
            process.start(); process.join(10); require(process.exitcode == 0, "result helper failed")
            recovered = reconcile_process_operation(operation_id)
            require(recovered["status"] == "completed" and recovered["result_bound"] and not recovered["replay_allowed"], f"exact result not reconciled {recovered}")

        def child_pid_reuse_is_not_terminated():
            operation_id = f"reuse_{uuid.uuid4().hex}"
            accepted = accept_process_operation(operation_id, operation_kind="verification", may_mutate=False, acceptance_key="reuse")
            path = ownership_path(operation_id)
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw.update({
                "state": "running", "owner_pid": 99999999, "owner_start_identity": "dead-owner", "owner_nonce": uuid.uuid4().hex,
                "child_pid": os.getpid(), "child_start_identity": "wrong-start-identity", "child_process_group_id": 0,
            })
            write_json_atomic(path, raw, expected_type=dict, sort_keys=True)
            recovered = reconcile_process_recovery_operation(operation_id, operator_confirmed=True)
            require(recovered["status"] == "interrupted", f"PID reuse state incorrect {recovered}")
            require(os.getpid() > 0, "current test process was terminated")

        def cleanup_requires_literal_confirmation():
            operation_id = f"cleanup_{uuid.uuid4().hex}"
            accepted = accept_process_operation(operation_id, operation_kind="verification", may_mutate=False, acceptance_key="cleanup")
            path = ownership_path(operation_id); raw = json.loads(path.read_text(encoding="utf-8")); raw["state"] = "interrupted"; write_json_atomic(path, raw, expected_type=dict, sort_keys=True)
            denied = cleanup_process_recovery_operation(operation_id, operator_confirmed="true")
            require(denied["status"] == "confirmation_required" and path.exists(), "truthy string confirmation accepted")
            cleaned = cleanup_process_recovery_operation(operation_id, operator_confirmed=True)
            require(cleaned["ok"] and not path.exists(), "terminal cleanup failed")

        def aggregate_is_content_free():
            report = build_process_recovery_state(); encoded = json.dumps(report)
            require(report["content_free"] and not report["payload_returned"] and not report["private_process_details_returned"], "aggregate not content-free")
            for token in ("owner_pid", "owner_nonce", "child_pid", str(Path(runtime))):
                require(token not in encoded, f"aggregate leaked {token}")

        def dashboard_recovery_routes():
            source = (AGENT / "dashboard.py").read_text(encoding="utf-8")
            require('/api/process-recovery-state' in source and '/api/process-recovery/reconcile' in source, "dashboard recovery routes missing")
            require('body.get("operator_confirmed") is True' in source, "literal confirmation missing")

        def retained_boundaries_present():
            worker = (ROOT / "tools" / "isolated_suite_worker.py").read_text(encoding="utf-8")
            source = (AGENT / "process_recovery.py").read_text(encoding="utf-8")
            require("replay_allowed" in source and "child_process_group_id" in source, "replay or exact-tree boundary missing")
            require("process_operation_cancellation_requested" in worker and "write_process_result" in worker, "isolated worker recovery integration missing")

        def release_contract():
            metadata = (AGENT / "release_metadata.py").read_text(encoding="utf-8")
            require('RUNTIME_VERSION = "1094.' in metadata, "runtime not in v1094 arc")
            require('NEXT_RECOMMENDED_ARC' in metadata, "next arc missing")

        for name, fn in (
            ("read-only orphan recovery", read_only_orphan_recovery),
            ("mutating orphan remains uncertain", mutating_orphan_is_uncertain),
            ("generation-bound result reconciliation", generation_bound_result_reconciles),
            ("child PID reuse protection", child_pid_reuse_is_not_terminated),
            ("literal terminal cleanup confirmation", cleanup_requires_literal_confirmation),
            ("content-free aggregate recovery state", aggregate_is_content_free),
            ("dashboard recovery routes", dashboard_recovery_routes),
            ("retained process boundaries", retained_boundaries_present),
            ("release and next-arc contract", release_contract),
        ):
            check(name, fn)

    passed = sum(1 for row in RESULTS if row["ok"])
    report = {"version": "1094.2", "status": "pass" if passed == len(RESULTS) else "fail", "passed": passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
