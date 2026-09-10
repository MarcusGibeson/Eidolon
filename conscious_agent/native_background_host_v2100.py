from __future__ import annotations

"""Native host bridge for the operator-enabled Era 6 ticket scheduler.

The dashboard already owns a bounded cognitive-service thread. This bridge lets
that thread prepare content-free scheduler tickets at a minute-granularity,
exactly-once cadence. It never executes a ticket, contacts a provider, sends a
message, mutates source, or starts another process.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from background_cognition_scheduler_v2000 import public_scheduler_state, read_scheduler_state
from era6_attention_initiative import prepare_era6_background_cycle

CONTRACT_VERSION = "v2100.9"

_DENIED = {
    "background_work_executed": False,
    "provider_contacted": False,
    "message_sent": False,
    "process_started": False,
    "source_modified": False,
    "installation_authorized": False,
    "promotion_authorized": False,
    "authority_expanded": False,
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def sample_native_resource_measurements() -> dict[str, Any]:
    """Return bounded host load evidence when optional psutil is available."""
    try:
        import psutil  # type: ignore
    except ImportError:
        result = {
            "ok": False,
            "status": "native_resource_sampler_unavailable",
            "measurements": {},
            "content_free": True,
        }
    else:
        cpu = max(0.0, min(100.0, float(psutil.cpu_percent(interval=0.05))))
        memory = max(0.0, min(100.0, float(psutil.virtual_memory().percent)))
        measurements = {
            "cpu_percent": round(cpu, 3),
            "memory_percent": round(memory, 3),
            "foreground_high_load": cpu >= 85.0,
        }
        result = {
            "ok": True,
            "status": "native_resource_measurements_sampled",
            "measurements": measurements,
            "content_free": True,
        }
    result["measurement_digest"] = _digest(result)
    return result


def run_native_background_host_tick(
    *,
    runtime_root: str | Path | None = None,
    now_epoch: float | None = None,
    resource_measurements: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Prepare one idempotent Era 6 background cycle when explicitly enabled."""
    scheduler = public_scheduler_state(read_scheduler_state(runtime_root=runtime_root))
    if not scheduler.get("enabled"):
        return {
            "ok": True,
            "status": "native_background_scheduler_disabled",
            "scheduler_revision": scheduler.get("revision"),
            "resource_evidence_status": "not_sampled",
            **_DENIED,
        }

    current = datetime.fromtimestamp(now_epoch, tz=timezone.utc) if now_epoch is not None else datetime.now(timezone.utc)
    cycle_id = f"native-era6-{current.strftime('%Y%m%dT%H%M')}"
    sampled = (
        {
            "ok": True,
            "status": "caller_resource_measurements",
            "measurements": dict(resource_measurements),
            "content_free": True,
            "measurement_digest": _digest(dict(resource_measurements)),
        }
        if resource_measurements is not None
        else sample_native_resource_measurements()
    )
    cycle = prepare_era6_background_cycle(
        cycle_id=cycle_id,
        runtime_root=runtime_root,
        resource_measurements=sampled.get("measurements") if isinstance(sampled.get("measurements"), Mapping) else {},
    )
    result = {
        "ok": bool(cycle.get("ok")),
        "status": "native_background_tick_prepared" if cycle.get("ok") else "native_background_tick_blocked",
        "cycle_id": cycle_id,
        "cycle_digest": str(cycle.get("cycle_digest") or ""),
        "focus_status": str(cycle.get("focus_status") or ""),
        "scheduler_status": str(cycle.get("scheduler_status") or ""),
        "tickets_prepared": int(cycle.get("tickets_prepared") or 0),
        "resource_mode": str(cycle.get("resource_mode") or ""),
        "resource_evidence_status": str(sampled.get("status") or ""),
        "resource_measurement_digest": str(sampled.get("measurement_digest") or ""),
        "content_free": True,
        **_DENIED,
    }
    result["host_tick_digest"] = _digest(result)
    return result


__all__ = ["CONTRACT_VERSION", "sample_native_resource_measurements", "run_native_background_host_tick"]
