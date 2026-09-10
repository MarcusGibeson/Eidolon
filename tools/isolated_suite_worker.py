from __future__ import annotations

"""Keep an isolated suite process tree alive until its result is handed off.

The parent verifier launches this worker in a new process group. The worker
launches the suite inside that group, writes a file-backed completion record,
and remains alive. The parent then terminates the worker group, which also
removes descendants that outlived the suite's direct process.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1] / "conscious_agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def _write_atomic(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--timeout", type=float, required=True)
    parser.add_argument("--handoff-grace", type=float, default=15.0)
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--operation-id", default="")
    parser.add_argument("--generation", type=int, default=0)
    args = parser.parse_args()

    command = json.loads(args.command_json)
    if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
        raise SystemExit("command-json must contain a nonempty string list")

    operation_id = str(args.operation_id or "").strip()
    generation = int(args.generation or 0)
    owner_nonce = ""
    if operation_id:
        from process_ownership import activate_process_operation
        activated = activate_process_operation(operation_id, generation)
        if not activated.get("ok"):
            _write_atomic(Path(args.result), {
                "return_code": -1, "timed_out": False, "elapsed_seconds": 0.0,
                "worker_pid": os.getpid(), "ownership_status": activated.get("status"),
            })
            return 2
        owner_nonce = str(activated.get("owner_nonce") or "")

    started = time.perf_counter()
    stdout_path = Path(args.stdout)
    stderr_path = Path(args.stderr)
    result_path = Path(args.result)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=args.cwd,
            stdout=stdout_file,
            stderr=stderr_file,
            env=os.environ.copy(),
        )
        if operation_id:
            from process_ownership import register_process_child
            group_id = process.pid if os.name == "nt" else os.getpgrp()
            registered = register_process_child(
                operation_id, generation, owner_nonce, process.pid,
                child_process_group_id=group_id,
            )
            if not registered.get("ok"):
                try:
                    process.terminate()
                except OSError:
                    pass
        deadline = time.monotonic() + max(0.1, args.timeout)
        timed_out = False
        cancelled = False
        while process.poll() is None:
            if operation_id:
                from process_ownership import process_operation_cancellation_requested
                if process_operation_cancellation_requested(operation_id, generation):
                    cancelled = True
                    break
            if time.monotonic() >= deadline:
                timed_out = True
                break
            time.sleep(0.05)
        return_code = process.returncode if process.returncode is not None else -1
        stdout_file.flush()
        stderr_file.flush()

    terminal_state = "cancelled" if cancelled else ("failed" if timed_out or return_code != 0 else "completed")
    if operation_id:
        from process_ownership import finalize_process_operation, write_process_result
        write_process_result(
            operation_id, generation=generation, owner_nonce=owner_nonce, state=terminal_state,
            return_code=return_code, timed_out=timed_out, applied=False,
        )
        finalize_process_operation(operation_id, generation, owner_nonce, state=terminal_state)

    _write_atomic(
        result_path,
        {
            "return_code": return_code,
            "timed_out": timed_out,
            "cancelled": cancelled,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "suite_pid": process.pid,
            "worker_pid": os.getpid(),
            "operation_id": operation_id,
            "generation": generation,
        },
    )

    # Keep the root PID alive so the parent can terminate the complete process
    # tree on Windows even when the suite's direct process has already exited.
    time.sleep(max(1.0, min(float(args.handoff_grace), 60.0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
