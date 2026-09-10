from __future__ import annotations

"""Content-free, read-only dashboard cold-start status for v1253.5."""

import sys
import time
from typing import Any

from release_authority import WORKING_SOURCE_VERSION

CONTRACT_VERSION = "v1253.5"
_IMPORTED_AT = time.perf_counter()


def build_fast_runtime_status() -> dict[str, Any]:
    """Return status without importing api_server or mutation domains."""
    from dashboard_performance import prewarm_status
    return {
        "ok": True,
        "data": {
            "runtime": {
                "source_version": WORKING_SOURCE_VERSION,
                "dashboard_uptime_seconds": round(max(0.0, time.perf_counter() - _IMPORTED_AT), 3),
                "api_server_loaded": "api_server" in sys.modules,
                "cold_start_status": True,
            },
            "api_prewarm": prewarm_status(),
            "counts": {},
        },
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "content_free": True,
        "provider_contacted": False,
        "runtime_mutation_performed": False,
        "project_mutation_authorized": False,
        "release_authorized": False,
    }


__all__ = ["CONTRACT_VERSION", "build_fast_runtime_status"]
