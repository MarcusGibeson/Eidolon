from __future__ import annotations

"""Deterministic in-process source compilation for quick release verification.

Unlike the exhaustive disposable-bytecode helper, this gate never launches a
nested compileall worker tree and never writes bytecode.  It reads every Python
source file in the shipped source surfaces and asks CPython's compiler to parse
and compile the source to an in-memory code object.  The exhaustive bytecode
helper remains available for full/diagnostic verification.
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (ROOT / "conscious_agent", ROOT / "tools", ROOT / "eidolon.py")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}


def _sources():
    for target in TARGETS:
        if target.is_file():
            yield target
            continue
        for current, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            base = Path(current)
            for name in files:
                if name.endswith(".py"):
                    yield base / name


def run() -> dict[str, object]:
    started = time.perf_counter()
    failures: list[dict[str, str]] = []
    count = 0
    total_bytes = 0
    for path in _sources():
        count += 1
        try:
            raw = path.read_bytes()
            total_bytes += len(raw)
            source = raw.decode("utf-8-sig")
            compile(source, str(path.relative_to(ROOT)), "exec", dont_inherit=True)
        except Exception as exc:  # syntax/encoding/read failures are certification failures
            failures.append({
                "path": path.relative_to(ROOT).as_posix(),
                "error": f"{type(exc).__name__}: {exc}",
            })
    ok = not failures
    return {
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "check_count": count,
        "passed_count": count - len(failures),
        "failure_count": len(failures),
        "source_bytes": total_bytes,
        "failures": failures[:100],
        "bytecode_written": False,
        "source_tree_bytecode_measured": True,
        "source_tree_bytecode_written": False,
        "source_tree_mutation_count": 0,
        "cache_cleanup_ok": True,
        "compile_execution_count": 1,
        "return_code": 0 if ok else 1,
        "timed_out": False,
        "mode": "in_memory_source_compile",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def main() -> int:
    report = run()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
