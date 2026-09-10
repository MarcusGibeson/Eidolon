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


def _live_owner(operation_id: str, generation: int, runtime: str, locks: str, ready, release) -> None:
    os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = runtime
    os.environ["EIDOLON_METADATA_LOCK_DIR"] = locks
    if str(AGENT) not in sys.path:
        sys.path.insert(0, str(AGENT))
    from process_ownership import activate_process_operation, finalize_process_operation, write_process_result
    active = activate_process_operation(operation_id, generation)
    ready.put(active)
    release.get(timeout=15)
    if active.get("ok"):
        nonce = str(active.get("owner_nonce") or "")
        write_process_result(operation_id, generation=generation, owner_nonce=nonce, state="completed")
        finalize_process_operation(operation_id, generation, nonce, state="completed")


def wait_state(operation_id: str, expected: set[str], timeout: float = 15.0):
    from process_ownership import inspect_process_operation
    deadline = time.monotonic() + timeout
    state = inspect_process_operation(operation_id)
    while state.get("state") not in expected and time.monotonic() < deadline:
        time.sleep(.03); state = inspect_process_operation(operation_id)
    return state


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eidolon-v1094-1-") as td:
        runtime = str(Path(td) / "runtime")
        locks = str(Path(td) / "locks")
        os.environ["EIDOLON_PROCESS_RUNTIME_ROOT"] = runtime
        os.environ["EIDOLON_METADATA_LOCK_DIR"] = locks
        from json_storage import write_json_atomic
        from process_ownership import (
            accept_process_operation,
            activate_process_operation,
            inspect_process_operation,
            ownership_path,
            process_start_identity,
        )
        from process_worker_entrypoints import cancel_bounded_command_worker, start_bounded_command_worker

        def private_identity_public_redaction():
            operation_id = f"private_{uuid.uuid4().hex}"
            accepted = accept_process_operation(operation_id, operation_kind="verification", may_mutate=False, acceptance_key="a")
            require(accepted["ok"], "accept failed")
            raw = json.loads(ownership_path(operation_id).read_text(encoding="utf-8"))
            require(raw["launcher_pid"] == os.getpid() and raw["launcher_start_identity"], "private start identity missing")
            public = inspect_process_operation(operation_id)
            encoded = json.dumps(public)
            require("launcher_pid" not in encoded and "acceptance_key" not in encoded and "owner_nonce" not in encoded, "public state leaked identity")

        def slow_live_owner_preserved():
            operation_id = f"live_{uuid.uuid4().hex}"
            accepted = accept_process_operation(operation_id, operation_kind="verification", may_mutate=False, acceptance_key="b")
            ctx = mp.get_context("spawn"); ready = ctx.Queue(); release = ctx.Queue()
            process = ctx.Process(target=_live_owner, args=(operation_id, accepted["generation"], runtime, locks, ready, release))
            process.start(); active = ready.get(timeout=10)
            require(active.get("ok"), f"child did not activate: {active}")
            second = activate_process_operation(operation_id, accepted["generation"])
            require(second.get("status") == "live_owner_preserved", f"live owner replaced: {second}")
            mismatch = activate_process_operation(operation_id, accepted["generation"] + 1)
            require(mismatch.get("status") == "generation_mismatch", "generation mismatch accepted")
            release.put(True); process.join(10); require(process.exitcode == 0, "live owner helper failed")

        def pid_reuse_fails_closed():
            operation_id = f"reuse_{uuid.uuid4().hex}"
            accepted = accept_process_operation(operation_id, operation_kind="verification", may_mutate=False, acceptance_key="c")
            path = ownership_path(operation_id)
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw.update({"state": "running", "owner_pid": os.getpid(), "owner_start_identity": "forged-wrong-start", "owner_nonce": uuid.uuid4().hex})
            write_json_atomic(path, raw, expected_type=dict, sort_keys=True)
            public = inspect_process_operation(operation_id)
            require(public["owner_dead"] and not public["owner_active"], f"PID reuse not rejected: {public}")

        def exact_cancellation():
            operation_id = f"cancel_{uuid.uuid4().hex}"
            launched = start_bounded_command_worker(
                operation_id=operation_id, acceptance_key="cancel", operation_kind="verification", may_mutate=False,
                config={"command": [sys.executable, "-c", "import time; time.sleep(30)"], "cwd": str(ROOT), "environment": {}, "timeout_seconds": 60},
            )
            state = wait_state(operation_id, {"running", "cancellation_requested"})
            require(state.get("owner_active"), "worker owner never became active")
            response = cancel_bounded_command_worker(operation_id, operator_confirmed=True)
            require(response.get("ok"), "cancellation not requested")
            launched["worker_handle"].join(15)
            final = wait_state(operation_id, {"cancelled", "failed"})
            require(final["state"] == "cancelled", f"unexpected cancellation result {final}")

        def duplicate_mutation_executes_once():
            operation_id = f"once_{uuid.uuid4().hex}"
            side_effect = Path(td) / "once.txt"
            code = f"from pathlib import Path; p=Path({str(side_effect)!r}); p.parent.mkdir(parents=True,exist_ok=True); p.open('a').write('x\\n')"
            config = {"command": [sys.executable, "-c", code], "cwd": str(ROOT), "environment": {}, "timeout_seconds": 10}
            first = start_bounded_command_worker(operation_id=operation_id, acceptance_key="exact", operation_kind="project_work", may_mutate=True, config=config)
            second = start_bounded_command_worker(operation_id=operation_id, acceptance_key="exact", operation_kind="project_work", may_mutate=True, config=config)
            require(first["worker_started"] and second.get("duplicate") and not second.get("worker_started"), "exactly-once acceptance failed")
            first["worker_handle"].join(15)
            require(side_effect.read_text(encoding="utf-8").splitlines() == ["x"], "mutating command executed more than once")

        def malformed_existing_record_fails_closed():
            operation_id = f"bad_{uuid.uuid4().hex}"
            path = ownership_path(operation_id); path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{bad", encoding="utf-8")
            result = accept_process_operation(operation_id, operation_kind="verification", may_mutate=False, acceptance_key="z")
            require(result.get("status") == "invalid_existing_ownership" and not result.get("ok"), "malformed ownership overwritten")
            require(path.read_text(encoding="utf-8") == "{bad", "malformed record mutated")

        def coordination_boundary_remains_separate():
            ownership = ownership_path("separate")
            metadata_lock = Path(locks)
            require(Path(runtime) in ownership.parents, "ownership outside private process root")
            require(metadata_lock not in ownership.parents, "process ownership replaced metadata lock boundary")

        def isolated_worker_contract():
            source = (ROOT / "tools" / "isolated_suite_worker.py").read_text(encoding="utf-8")
            verifier = (ROOT / "tools" / "post_review_development_verify.py").read_text(encoding="utf-8")
            for token in ("--operation-id", "activate_process_operation", "register_process_child", "write_process_result"):
                require(token in source, f"isolated worker missing {token}")
            require("accept_process_operation" in verifier and "EIDOLON_PROCESS_RUNTIME_ROOT" in verifier, "verifier not using ownership contract")

        for name, fn in (
            ("private identity and public redaction", private_identity_public_redaction),
            ("slow live owner preserved", slow_live_owner_preserved),
            ("PID reuse fails closed", pid_reuse_fails_closed),
            ("exact operation cancellation", exact_cancellation),
            ("duplicate mutating execution prevented", duplicate_mutation_executes_once),
            ("malformed ownership fails closed", malformed_existing_record_fails_closed),
            ("metadata coordination remains separate", coordination_boundary_remains_separate),
            ("isolated verifier ownership integration", isolated_worker_contract),
        ):
            check(name, fn)

    passed = sum(1 for row in RESULTS if row["ok"])
    report = {"version": "1094.1", "status": "pass" if passed == len(RESULTS) else "fail", "passed": passed, "total": len(RESULTS), "checks": RESULTS}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
