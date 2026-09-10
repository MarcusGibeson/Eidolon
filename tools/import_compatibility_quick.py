from __future__ import annotations

"""Deterministic certifying import-parity probe for release verification.

The exhaustive historical import harness remains available separately.  This
probe covers the supported package/direct import surfaces with bounded,
sequential child interpreters and no nested worker orchestration.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"

CASES: tuple[tuple[str, list[str], str], ...] = (
    ("release-metadata-package", [sys.executable, "-c", "import conscious_agent.release_metadata; print('OK_RELEASE_PACKAGE')"], "OK_RELEASE_PACKAGE"),
    ("release-metadata-direct", [sys.executable, "-c", f"import sys; sys.path.insert(0,{str(AGENT)!r}); import release_metadata; print('OK_RELEASE_DIRECT')"], "OK_RELEASE_DIRECT"),
    ("api-package", [sys.executable, "-c", "import conscious_agent.api_server; print('OK_API_PACKAGE')"], "OK_API_PACKAGE"),
    ("api-direct", [sys.executable, "-c", f"import sys; sys.path.insert(0,{str(AGENT)!r}); import api_server; print('OK_API_DIRECT')"], "OK_API_DIRECT"),
    ("registry-package", [sys.executable, "-c", "import conscious_agent.registry_navigation_smoke_consolidation; print('OK_REGISTRY_PACKAGE')"], "OK_REGISTRY_PACKAGE"),
    ("registry-direct", [sys.executable, "-c", f"import sys; sys.path.insert(0,{str(AGENT)!r}); import registry_navigation_smoke_consolidation; print('OK_REGISTRY_DIRECT')"], "OK_REGISTRY_DIRECT"),
    ("inventory-package", [sys.executable, "-c", "import conscious_agent.version_metadata_inventory; print('OK_INVENTORY_PACKAGE')"], "OK_INVENTORY_PACKAGE"),
    ("inventory-direct", [sys.executable, "-c", f"import sys; sys.path.insert(0,{str(AGENT)!r}); import version_metadata_inventory; print('OK_INVENTORY_DIRECT')"], "OK_INVENTORY_DIRECT"),
)


def run_case(label: str, command: list[str], sentinel: str, *, timeout: int = 20) -> dict[str, Any]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="eidolon-import-quick-") as td:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["EIDOLON_DATA_DIR"] = str(Path(td) / "data")
        Path(env["EIDOLON_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
        try:
            cp = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
            timed_out = False
            rc = cp.returncode
            stdout = cp.stdout or ""
            stderr = cp.stderr or ""
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            rc = -1
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    sentinel_ok = sentinel in stdout
    ok = not timed_out and rc == 0 and sentinel_ok
    return {
        "label": label,
        "ok": ok,
        "return_code": rc,
        "timed_out": timed_out,
        "sentinel_ok": sentinel_ok,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "stderr_tail": "\n".join(stderr.splitlines()[-8:]),
    }


def build_report() -> dict[str, Any]:
    results = [run_case(*case) for case in CASES]
    passed = sum(1 for row in results if row["ok"])
    return {
        "mode": "imports",
        "status": "pass" if passed == len(results) else "blocked",
        "ok": passed == len(results),
        "check_count": len(results),
        "passed_count": passed,
        "results": results,
        "execution_mode": "sequential_bounded_subprocesses",
        "nested_worker_orchestration": False,
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
