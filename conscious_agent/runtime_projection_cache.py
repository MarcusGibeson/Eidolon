from __future__ import annotations

"""Tiny read-only projection cache for dashboard polling.

The cache is deliberately short-lived. It never caches POST results, approvals,
or execution decisions. A coarse external-runtime directory signature invalidates
read-only status projections after atomic state-file replacement.
"""

from copy import deepcopy
from pathlib import Path
import threading
import time
from typing import Any, Callable

from paths import DATA_DIR

CONTRACT_VERSION = "v1251.7"
_CACHE_LOCK = threading.RLock()
_CACHE: dict[str, tuple[float, tuple[tuple[str, int, int], ...], Any]] = {}
_INFLIGHT: dict[str, threading.Event] = {}
DEFAULT_TTL_SECONDS = 0.75
SHARED_BUILD_WAIT_SECONDS = 60.0
_MISS = object()


def _runtime_signature() -> tuple[tuple[str, int, int], ...]:
    roots = [DATA_DIR]
    if DATA_DIR.exists():
        try:
            roots.extend(path for path in DATA_DIR.iterdir() if path.is_dir())
        except OSError:
            pass
    rows: list[tuple[str, int, int]] = []
    for path in roots:
        try:
            stat = path.stat()
        except OSError:
            continue
        rows.append((path.name, int(stat.st_mtime_ns), int(stat.st_size)))
    return tuple(sorted(rows))


def _cached_value(token: str, signature: tuple[tuple[str, int, int], ...], ttl_seconds: float) -> Any:
    with _CACHE_LOCK:
        cached = _CACHE.get(token)
        if cached and time.monotonic() - cached[0] <= max(0.0, float(ttl_seconds)) and cached[1] == signature:
            return deepcopy(cached[2])
    return _MISS


def cached_read_only_projection(key: str, builder: Callable[[], Any], *, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> Any:
    """Serve one projection per key, sharing a build already under way.

    Polling surfaces ask for these projections far faster than an expensive one
    can be produced. Building per caller meant several full rebuilds running at
    once, each taking the same coarse state locks, so the projection got slower
    the more often it was requested and request threads piled up behind it.
    """
    token = str(key or "").strip()
    if not token:
        return builder()
    requested_at = time.monotonic()
    value = _cached_value(token, _runtime_signature(), ttl_seconds)
    if value is not _MISS:
        return value

    with _CACHE_LOCK:
        in_flight = _INFLIGHT.get(token)
        owned = in_flight is None
        if owned:
            in_flight = threading.Event()
            _INFLIGHT[token] = in_flight

    if not owned:
        in_flight.wait(SHARED_BUILD_WAIT_SECONDS)
        with _CACHE_LOCK:
            cached = _CACHE.get(token)
            # Accept a result finished after this caller asked: it is at least as
            # current as a build started here would have been. The directory
            # signature is not used, because it churns on every unrelated write.
            if cached and cached[0] >= requested_at:
                return deepcopy(cached[2])
        return builder()

    try:
        value = builder()
        with _CACHE_LOCK:
            _CACHE[token] = (time.monotonic(), _runtime_signature(), deepcopy(value))
    finally:
        with _CACHE_LOCK:
            _INFLIGHT.pop(token, None)
        in_flight.set()
    return deepcopy(value)


def prune_projection_cache(*, now: float | None = None) -> int:
    """Drop expired cache rows without invoking any projection builder."""
    current = time.monotonic() if now is None else float(now)
    removed = 0
    with _CACHE_LOCK:
        for key, row in list(_CACHE.items()):
            if current - float(row[0]) > DEFAULT_TTL_SECONDS:
                _CACHE.pop(key, None)
                removed += 1
    return removed


def clear_projection_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def cache_status() -> dict[str, Any]:
    with _CACHE_LOCK:
        return {
            "contract_version": CONTRACT_VERSION,
            "entry_count": len(_CACHE),
            "keys": sorted(_CACHE),
            "in_flight_build_count": len(_INFLIGHT),
            "ttl_seconds": DEFAULT_TTL_SECONDS,
            "read_only": True,
            "content_free": True,
            "approval_granted": False,
            "tool_execution_authorized": False,
            "project_mutation_authorized": False,
            "release_authorized": False,
        }


__all__ = ["CONTRACT_VERSION", "DEFAULT_TTL_SECONDS", "cached_read_only_projection", "prune_projection_cache", "clear_projection_cache", "cache_status"]
