from __future__ import annotations

"""Content-free repeated startup evidence for ordinary Windows review.

The soak reuses one external runtime across bounded dashboard process launches.
It never sends a message, performs generation, installs a model, or claims native
Windows certification when executed on another platform.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
import time
from typing import Any

from dashboard_startup import measure_first_use_sequence

WINDOWS_STARTUP_SOAK_SCHEMA_VERSION = "1"
MIN_SOAK_RUNS = 2
MAX_SOAK_RUNS = 20
DEFAULT_SOAK_RUNS = 5


def normalize_soak_runs(value: int | str | None) -> int:
    try:
        runs = int(value or DEFAULT_SOAK_RUNS)
    except (TypeError, ValueError) as error:
        raise ValueError("Startup soak runs must be an integer.") from error
    if runs < MIN_SOAK_RUNS or runs > MAX_SOAK_RUNS:
        raise ValueError(f"Startup soak runs must be between {MIN_SOAK_RUNS} and {MAX_SOAK_RUNS}.")
    return runs


def _runtime_inventory(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return round(ordered[index], 6)


def run_windows_startup_soak(
    project_root: str | Path,
    *,
    runs: int = DEFAULT_SOAK_RUNS,
    timeout_seconds: float = 45.0,
    include_provider_probe: bool = False,
    runtime_root: str | Path | None = None,
    platform_name: str | None = None,
) -> dict[str, Any]:
    """Run bounded repeated starts and return content-free evidence."""

    run_count = normalize_soak_runs(runs)
    root = Path(project_root).resolve()
    owns_runtime = runtime_root is None
    runtime = Path(runtime_root).resolve() if runtime_root is not None else Path(tempfile.mkdtemp(prefix="eidolon-windows-startup-soak-"))
    runtime.mkdir(parents=True, exist_ok=True)
    detected_system = str(platform.system()).strip() or "Unknown"
    system = str(platform_name or detected_system).strip() or detected_system
    native_windows = detected_system.lower() == "windows" and os.name == "nt"
    started = time.perf_counter()
    before = _runtime_inventory(runtime)
    rows: list[dict[str, Any]] = []
    try:
        for index in range(run_count):
            launch_mode = "cold" if index == 0 else "warm"
            result = measure_first_use_sequence(
                root,
                runtime_root=runtime,
                seed_runtime=index == 0,
                timeout_seconds=timeout_seconds,
                include_provider_probe=include_provider_probe,
            )
            rows.append({
                "run": index + 1,
                "launch_mode": launch_mode,
                "ok": bool(result.get("ok")),
                "tcp_ready_seconds": result.get("tcp_ready_seconds"),
                "health_seconds": result.get("first_health_response_seconds"),
                "chat_interactive_seconds": result.get("chat_input_interactive_seconds"),
                "conversation_restoration_completed": bool(result.get("active_conversation_restoration_completed")),
                "conversation_surface_available": bool(result.get("conversation_surface_available")),
                "continuity_digest": str(result.get("continuity_digest") or "")[:64],
                "provider_status": str(result.get("provider_status") or "not_checked")[:60],
                "health_below_target": bool(result.get("cold_health_below_target")),
                "input_below_target": bool(result.get("chat_interactive_below_target")),
                "accepted_message_replayed": False,
                "provider_request_repeated": False,
            })
        after = _runtime_inventory(runtime)
        digests = [row["continuity_digest"] for row in rows if row["continuity_digest"]]
        health = [float(row["health_seconds"]) for row in rows if isinstance(row.get("health_seconds"), (int, float))]
        interactive = [float(row["chat_interactive_seconds"]) for row in rows if isinstance(row.get("chat_interactive_seconds"), (int, float))]
        all_required_ok = all(row["ok"] for row in rows)
        continuity_stable = len(digests) == run_count and len(set(digests)) == 1
        health_budget_pass = len(health) == run_count and all(value < 15.0 for value in health)
        chat_interactive_target_met = len(interactive) == run_count and all(value < 5.0 for value in interactive)
        required_pass = bool(all_required_ok and continuity_stable and health_budget_pass)
        return {
            "schema_version": WINDOWS_STARTUP_SOAK_SCHEMA_VERSION,
            "ok": required_pass,
            "status": "pass" if required_pass else "fail",
            "performance_status": "target_met" if chat_interactive_target_met else "target_miss",
            "platform": system,
            "native_windows": native_windows,
            "native_windows_certified": False,
            "classification": "native_windows_evidence" if native_windows else "cross_platform_compatibility_evidence",
            "python_version": platform.python_version(),
            "python_311_or_newer": tuple(int(part) for part in platform.python_version_tuple()[:2]) >= (3, 11),
            "run_count": run_count,
            "runs": rows,
            "continuity_stable": continuity_stable,
            "health_budget_pass": health_budget_pass,
            "chat_interactive_budget_pass": chat_interactive_target_met,
            "chat_interactive_target_required": False,
            "maximum_health_seconds": round(max(health), 6) if health else None,
            "p95_health_seconds": _percentile(health, 0.95),
            "maximum_chat_interactive_seconds": round(max(interactive), 6) if interactive else None,
            "p95_chat_interactive_seconds": _percentile(interactive, 0.95),
            "runtime_file_count_before": len(before),
            "runtime_file_count_after": len(after),
            "source_mutation_checked_by_caller": True,
            "accepted_message_replayed": False,
            "provider_request_repeated": False,
            "provider_probe_enabled": bool(include_provider_probe),
            "models_changed": False,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "content_free": True,
            "private_values_included": False,
        }
    finally:
        if owns_runtime:
            shutil.rmtree(runtime, ignore_errors=True)


def safe_soak_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)
