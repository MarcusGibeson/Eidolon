from __future__ import annotations

"""Generation-bound in-process caches for v1252.7 persistent runtime projections."""

import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Hashable

try:
    from persistent_state_index import persistent_state_generation
except ImportError:
    from persistent_state_index import persistent_state_generation

CONTRACT_VERSION = "v1252.7"
_CACHE_LOCK = threading.RLock()
_MAX_ENTRIES = 256
_DEFAULT_TTL_SECONDS = 30.0
_CACHE: OrderedDict[tuple[str, str, int, Hashable], tuple[float, Any]] = OrderedDict()
_STATS = {"hits": 0, "misses": 0, "invalidations": 0, "evictions": 0}


def _copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy(item) for item in value)
    return value


def cached_projection(
    path: str | Path,
    domain: str,
    key: Hashable,
    builder: Callable[[], Any],
    *,
    ttl_seconds: float = _DEFAULT_TTL_SECONDS,
) -> Any:
    """Return a defensive copy of a projection tied to the current index generation."""
    generation = persistent_state_generation(path, domain)
    cache_key = (str(Path(path).expanduser().resolve()), str(domain), generation, key)
    now = time.monotonic()
    with _CACHE_LOCK:
        row = _CACHE.get(cache_key)
        if row and now - row[0] <= max(0.0, float(ttl_seconds)):
            _STATS["hits"] += 1
            _CACHE.move_to_end(cache_key)
            return _copy(row[1])
        _STATS["misses"] += 1
    value = builder()
    with _CACHE_LOCK:
        # Drop obsolete generations for the same path/domain while preserving unrelated domains.
        obsolete = [
            candidate for candidate in _CACHE
            if candidate[0] == cache_key[0] and candidate[1] == cache_key[1] and candidate[2] != generation
        ]
        for candidate in obsolete:
            _CACHE.pop(candidate, None)
            _STATS["invalidations"] += 1
        _CACHE[cache_key] = (now, _copy(value))
        _CACHE.move_to_end(cache_key)
        while len(_CACHE) > _MAX_ENTRIES:
            _CACHE.popitem(last=False)
            _STATS["evictions"] += 1
    return _copy(value)


def clear_persistent_projection_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()
        _STATS.update({"hits": 0, "misses": 0, "invalidations": 0, "evictions": 0})


def persistent_projection_cache_status() -> dict[str, Any]:
    with _CACHE_LOCK:
        return {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "entries": len(_CACHE),
            "max_entries": _MAX_ENTRIES,
            "ttl_seconds": _DEFAULT_TTL_SECONDS,
            **dict(_STATS),
            "generation_bound": True,
            "defensive_copy": True,
            "authority_granted": False,
        }
