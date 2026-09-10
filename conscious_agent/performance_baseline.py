from __future__ import annotations

"""Content-free same-host performance baseline support for v1253.9.1.

Baselines are explicit runtime evidence, never source/package data and never
release authority. Host identity is deliberately coarse: no hostname, username,
paths, serial numbers, MAC addresses, or other unique machine identifiers.
"""

import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Mapping

from paths import DATA_DIR

CONTRACT_VERSION = "v1253.9.1"
BASELINE_SCHEMA = "eidolon.performance-baseline.v1"


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def coarse_host_profile() -> dict[str, Any]:
    profile = {
        "platform_system": platform.system() or os.name,
        "machine_family": platform.machine() or "unknown",
        "python_implementation": platform.python_implementation(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "pointer_bits": 64 if sys.maxsize > 2**32 else 32,
        "content_free": True,
    }
    profile["profile_digest"] = _digest(profile)
    return profile


def _path(data_dir: str | Path | None = None) -> Path:
    root = Path(data_dir).resolve() if data_dir is not None else DATA_DIR
    return root / "performance" / "accepted_same_host_baseline.json"


def load_same_host_baseline(*, data_dir: str | Path | None = None) -> dict[str, Any] | None:
    path = _path(data_dir)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("schema") != BASELINE_SCHEMA:
        return None
    if (value.get("host_profile") or {}).get("profile_digest") != coarse_host_profile()["profile_digest"]:
        return None
    return value


def accept_same_host_baseline(metrics: Mapping[str, Any], *, source_version: str, data_dir: str | Path | None = None) -> dict[str, Any]:
    allowed: dict[str, Any] = {}
    for name, row in metrics.items():
        if not isinstance(row, Mapping):
            continue
        allowed[str(name)] = {
            key: row.get(key) for key in ("count", "median", "p95", "minimum", "maximum")
            if isinstance(row.get(key), (int, float))
        }
    record = {
        "schema": BASELINE_SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "source_version": str(source_version),
        "host_profile": coarse_host_profile(),
        "metrics": allowed,
        "content_free": True,
        "release_authorized": False,
        "independent_authority_granted": False,
    }
    record["record_digest"] = _digest(record)
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)
    return record


__all__ = ["CONTRACT_VERSION", "BASELINE_SCHEMA", "coarse_host_profile", "load_same_host_baseline", "accept_same_host_baseline"]
