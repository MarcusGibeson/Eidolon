from __future__ import annotations

"""Disposable bytecode compilation for Eidolon verification.

Compilation must not populate ``__pycache__`` directories inside an extracted
source tree.  This helper writes every ``.pyc`` into a temporary cache root,
checks free space before starting, and removes the cache on every exit path.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
COMPILE_TARGETS: tuple[str, ...] = ("conscious_agent", "tools", "eidolon.py")
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_COMPILE_WORKERS = 2
MINIMUM_CACHE_HEADROOM_BYTES = 512 * 1024 * 1024
SOURCE_SIZE_MULTIPLIER = 8
INFRASTRUCTURE_DIR_NAMES = {".git", ".venv", "venv"}


def build_compile_command(*, workers: int | None = None) -> list[str]:
    """Return a bounded command whose length is independent of extraction depth."""
    resolved_workers = workers if workers is not None else int(os.environ.get("EIDOLON_COMPILE_WORKERS", str(DEFAULT_COMPILE_WORKERS)))
    resolved_workers = max(1, int(resolved_workers))
    return [sys.executable, "-m", "compileall", "-q", "-f", "-j", str(resolved_workers), *COMPILE_TARGETS]


def _source_python_bytes(root: Path) -> int:
    total = 0
    for target in COMPILE_TARGETS:
        path = root / target
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
        elif path.is_dir():
            for source in path.rglob("*.py"):
                try:
                    if source.is_file():
                        total += source.stat().st_size
                except OSError:
                    continue
    return total


def required_cache_bytes(root: Path) -> int:
    """Return conservative disposable-cache headroom for this source tree."""
    return max(MINIMUM_CACHE_HEADROOM_BYTES, _source_python_bytes(root) * SOURCE_SIZE_MULTIPLIER)


def _bytecode_snapshot(root: Path) -> dict[str, Any]:
    files: dict[str, str] = {}
    cache_dirs: list[str] = []
    errors: list[dict[str, str]] = []
    for current, directories, names in os.walk(root):
        directories[:] = [name for name in directories if name not in INFRASTRUCTURE_DIR_NAMES]
        current_path = Path(current)
        if current_path.name == "__pycache__":
            cache_dirs.append(current_path.relative_to(root).as_posix())
        for name in names:
            if not name.endswith(".pyc"):
                continue
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            try:
                files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError as exc:
                errors.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})
    return {"files": files, "cache_dirs": sorted(cache_dirs), "errors": errors}


def _bytecode_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_files = dict(before.get("files") or {})
    after_files = dict(after.get("files") or {})
    before_dirs = set(before.get("cache_dirs") or [])
    after_dirs = set(after.get("cache_dirs") or [])
    added = sorted(after_files.keys() - before_files.keys())
    deleted = sorted(before_files.keys() - after_files.keys())
    modified = sorted(
        path for path in before_files.keys() & after_files.keys()
        if before_files[path] != after_files[path]
    )
    added_dirs = sorted(after_dirs - before_dirs)
    deleted_dirs = sorted(before_dirs - after_dirs)
    errors = [*(before.get("errors") or []), *(after.get("errors") or [])]
    return {
        "before_file_count": len(before_files),
        "after_file_count": len(after_files),
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "added_cache_dirs": added_dirs,
        "deleted_cache_dirs": deleted_dirs,
        "errors": errors,
        "mutation_count": len(added) + len(modified) + len(deleted) + len(added_dirs) + len(deleted_dirs),
        "write_count": len(added) + len(modified) + len(added_dirs),
    }


def run_disposable_compile(
    root: str | Path = ROOT,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    temp_parent: str | Path | None = None,
    disk_usage: Callable[[str | os.PathLike[str]], shutil._ntuple_diskusage] = shutil.disk_usage,
    workers: int | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    project_root = Path(root).resolve()
    cache_parent = Path(temp_parent or tempfile.gettempdir()).resolve()
    required = required_cache_bytes(project_root)
    bytecode_before = _bytecode_snapshot(project_root)

    try:
        free_before = int(disk_usage(cache_parent).free)
    except OSError as exc:
        return {
            "status": "blocked",
            "ok": False,
            "reason": f"free-space preflight failed: {type(exc).__name__}: {exc}",
            "project_root": str(project_root),
            "cache_parent": str(cache_parent),
            "required_free_bytes": required,
            "source_tree_bytecode_measured": True,
            "source_tree_bytecode_written": False,
            "source_tree_mutation_count": 0,
            "compile_execution_count": 0,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }

    if free_before < required:
        return {
            "status": "blocked",
            "ok": False,
            "reason": "insufficient free disk for disposable Python bytecode cache",
            "project_root": str(project_root),
            "cache_parent": str(cache_parent),
            "free_bytes": free_before,
            "required_free_bytes": required,
            "source_tree_bytecode_measured": True,
            "source_tree_bytecode_written": False,
            "source_tree_mutation_count": 0,
            "compile_execution_count": 0,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }

    command = build_compile_command(workers=workers)
    stdout = ""
    stderr = ""
    return_code: int | None = None
    timed_out = False
    cache_root_text: str | None = None
    cleanup_ok = False
    cache_file_count = 0
    compile_execution_count = 0

    try:
        with tempfile.TemporaryDirectory(prefix="eidolon-pycache-", dir=cache_parent) as temp_dir:
            cache_root = Path(temp_dir)
            cache_root_text = str(cache_root)
            env = dict(os.environ)
            env["PYTHONPYCACHEPREFIX"] = str(cache_root)
            # compileall is explicitly responsible for bytecode in this child.
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            try:
                compile_execution_count += 1
                completed = subprocess.run(
                    command,
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
                return_code = completed.returncode
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
                stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
            cache_file_count = sum(1 for path in cache_root.rglob("*.pyc") if path.is_file())
        cleanup_ok = cache_root_text is not None and not Path(cache_root_text).exists()
    except OSError as exc:
        stderr = f"{type(exc).__name__}: {exc}"
        cleanup_ok = cache_root_text is None or not Path(cache_root_text).exists()

    bytecode_after = _bytecode_snapshot(project_root)
    bytecode_delta = _bytecode_delta(bytecode_before, bytecode_after)
    source_tree_bytecode_written = bytecode_delta["write_count"] > 0
    source_tree_mutation_count = int(bytecode_delta["mutation_count"])
    ok = (
        not timed_out
        and return_code == 0
        and cleanup_ok
        and not bytecode_delta["errors"]
        and source_tree_mutation_count == 0
    )
    reason: str | None = None
    if timed_out:
        reason = f"compileall exceeded {timeout}s"
    elif return_code not in (0, None):
        reason = f"compileall exited with code {return_code}"
    elif return_code is None:
        reason = stderr or "compileall did not start"
    elif not cleanup_ok:
        reason = "disposable bytecode cache was not removed"
    elif bytecode_delta["errors"]:
        reason = "source-tree bytecode measurement failed"
    elif source_tree_mutation_count:
        reason = "compilation changed source-tree bytecode or cache directories"

    return {
        "status": "pass" if ok else "blocked",
        "ok": ok,
        "reason": reason,
        "command": command,
        "compile_targets": list(COMPILE_TARGETS),
        "project_root": str(project_root),
        "cache_parent": str(cache_parent),
        "cache_root": cache_root_text,
        "cache_cleanup_ok": cleanup_ok,
        "cache_file_count": cache_file_count,
        "source_tree_bytecode_measured": True,
        "source_tree_bytecode_written": source_tree_bytecode_written,
        "source_tree_mutation_count": source_tree_mutation_count,
        "source_tree_bytecode_delta": bytecode_delta,
        "compile_execution_count": compile_execution_count,
        "free_bytes_before": free_before,
        "required_free_bytes": required,
        "return_code": return_code,
        "timed_out": timed_out,
        "stdout_tail": "\n".join(stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-20:]),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Eidolon into a disposable bytecode cache.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--workers", type=int, default=None, help="compile workers (defaults to EIDOLON_COMPILE_WORKERS or 2)")
    args = parser.parse_args()
    if args.workers is not None and args.workers < 1:
        parser.error("--workers must be at least 1")
    report = run_disposable_compile(args.root, timeout=args.timeout, workers=args.workers)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Disposable compilation: {report['status']}")
        if report.get("reason"):
            print(report["reason"])
        print(f"Elapsed: {report.get('elapsed_seconds')}s")
        print(f"Cache cleanup: {report.get('cache_cleanup_ok')}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
