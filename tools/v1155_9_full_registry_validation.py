from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from conscious_agent.checkpoint_registry import inspect_checkpoint_registry


def _validate(row: dict[str, Any]) -> dict[str, Any]:
    from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
    checkpoint_id = str(row.get("checkpoint_id") or "")
    with tempfile.TemporaryDirectory(prefix="eidolon-v1155-9-registry-") as td:
        runtime = Path(td) / "runtime"
        old = os.environ.get("EIDOLON_DATA_DIR")
        os.environ["EIDOLON_DATA_DIR"] = str(runtime)
        try:
            inputs = {"bootstrap": {}} if "bootstrap" in (row.get("required_inputs") or []) else {}
            result = dispatch_registered_checkpoint(
                checkpoint_id,
                source_root=ROOT,
                runtime_root=runtime,
                checkpoint_inputs=inputs,
            )
            ok = (
                result.get("read_only") is True
                and result.get("source_modified") is False
                and result.get("runtime_mutated") is False
                and result.get("provider_contacted") is False
                and result.get("raw_checkpoint_included") is False
                and (result.get("checkpoint_summary") or {}).get("invocation_completed") is True
            )
            return {"checkpoint_id": checkpoint_id, "ok": ok, "result": None if ok else result}
        except Exception as error:
            return {"checkpoint_id": checkpoint_id, "ok": False, "error": f"{type(error).__name__}: {error}"}
        finally:
            if old is None:
                os.environ.pop("EIDOLON_DATA_DIR", None)
            else:
                os.environ["EIDOLON_DATA_DIR"] = old


def main() -> int:
    registry = inspect_checkpoint_registry(source_root=ROOT)
    rows = list(registry.get("checkpoints", []))
    results: list[dict[str, Any]] = []
    workers = max(1, min(8, os.cpu_count() or 1))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_validate, row) for row in rows]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: row["checkpoint_id"])
    failures = [row for row in results if not row.get("ok")]
    summary = {
        "registered": registry.get("checkpoint_count", 0),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "failures": failures,
        "duplicate_checkpoint_ids": registry.get("duplicate_checkpoint_ids", []),
        "duplicate_builder_targets": registry.get("duplicate_builder_targets", []),
        "worker_count": workers,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
