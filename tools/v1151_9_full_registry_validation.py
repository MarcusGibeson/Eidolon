from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from conscious_agent.architecture_checkpoint_dispatch import dispatch_registered_checkpoint
from conscious_agent.checkpoint_registry import checkpoint_descriptors

BOOTSTRAP = {
    "chat_interactive": True,
    "administrative_services_loaded": False,
    "runtime_guidance": {"runtime_external": True},
    "recovery": {},
    "provider": {"status": "unknown"},
    "progress": {"phases": [
        {"name": "conversation_restoration", "status": "ready"},
        {"name": "conversation_ownership_restoration", "status": "ready"},
    ]},
    "accepted_turn_replayed": False,
    "provider_contacted": False,
    "runtime_mutation_performed": False,
}


def run_slice(start: int, stop: int | None, runtime_root: Path) -> dict:
    descriptors = list(checkpoint_descriptors(source_root=ROOT))
    selected = descriptors[start:stop]
    rows = []
    for descriptor in selected:
        checkpoint_id = descriptor["checkpoint_id"]
        inputs = {"bootstrap": BOOTSTRAP} if "bootstrap" in descriptor.get("required_inputs", []) else None
        try:
            result = dispatch_registered_checkpoint(
                checkpoint_id,
                source_root=ROOT,
                runtime_root=runtime_root,
                checkpoint_inputs=inputs,
            )
            summary = result.get("checkpoint_summary") or {}
            ok = bool(
                summary.get("invocation_supported")
                and summary.get("invocation_completed")
                and result.get("read_only")
                and not result.get("source_modified")
                and not result.get("runtime_mutated")
                and not result.get("provider_contacted")
                and not result.get("raw_checkpoint_included")
            )
            rows.append({
                "checkpoint_id": checkpoint_id,
                "ok": ok,
                "status": summary.get("status"),
                "error_type": summary.get("error_type"),
            })
        except Exception as error:
            rows.append({
                "checkpoint_id": checkpoint_id,
                "ok": False,
                "status": "validation_exception",
                "error_type": type(error).__name__,
            })
    passed = sum(1 for row in rows if row["ok"])
    return {
        "suite": "v1151.9-full-registry-validation",
        "registry_count": len(descriptors),
        "slice_start": start,
        "slice_stop": start + len(selected),
        "selected": len(selected),
        "passed": passed,
        "failed": len(selected) - passed,
        "ok": passed == len(selected),
        "failures": [row for row in rows if not row["ok"]],
        "read_only": True,
        "content_free": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Invoke a bounded slice of the v1151.9 consolidated checkpoint registry read-only.")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--runtime-root")
    args = parser.parse_args()
    if args.runtime_root:
        runtime = Path(args.runtime_root).expanduser().resolve()
        runtime.mkdir(parents=True, exist_ok=True)
        report = run_slice(max(0, args.start), args.stop, runtime)
    else:
        with tempfile.TemporaryDirectory() as td:
            report = run_slice(max(0, args.start), args.stop, Path(td) / "runtime")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
