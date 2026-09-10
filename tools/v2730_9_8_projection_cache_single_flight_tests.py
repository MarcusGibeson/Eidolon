from __future__ import annotations

"""Concurrent callers must share one projection build, not start their own.

The builder ran outside the cache lock, so every caller that missed the cache
began a full rebuild. The dashboard status projection takes tens of seconds and
is polled every few seconds, so several complete rebuilds ran at once, each
taking the same coarse state locks. Request threads then piled up behind them
and the projection got slower the more often it was asked for.

The directory signature also changes on any unrelated write, so a caller waiting
on a shared build accepts a result finished after it asked rather than requiring
a signature match it would almost never get.
"""

import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "conscious_agent"
for value in (str(ROOT), str(AGENT)):
    if value not in sys.path:
        sys.path.insert(0, value)
sys.dont_write_bytecode = True
RUNTIME = Path(tempfile.mkdtemp(prefix="eidolon-v2730-9-8-runtime-"))
os.environ["EIDOLON_DATA_DIR"] = str(RUNTIME)

from runtime_projection_cache import (
    cache_status,
    cached_read_only_projection,
    clear_projection_cache,
)


CHECKS: list[str] = []


def require(condition: object, name: str) -> None:
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


class SlowBuilder:
    def __init__(self, seconds: float = 0.8) -> None:
        self.seconds = seconds
        self.calls = 0
        self._lock = threading.Lock()

    def __call__(self) -> dict:
        with self._lock:
            self.calls += 1
            ordinal = self.calls
        time.sleep(self.seconds)
        return {"build": ordinal}


def run_concurrently(count: int, builder, key: str, ttl: float = 0.75) -> list:
    results: list = [None] * count
    def worker(index: int) -> None:
        results[index] = cached_read_only_projection(key, builder, ttl_seconds=ttl)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    # Writes during the build change the directory signature, exactly as a live
    # conversation turn would.
    def churn() -> None:
        for i in range(6):
            (RUNTIME / f"churn-{i}.json").write_text("{}", encoding="utf-8")
            time.sleep(0.05)
    for thread in threads:
        thread.start()
    threading.Thread(target=churn, daemon=True).start()
    for thread in threads:
        thread.join(timeout=90)
    require(all(not t.is_alive() for t in threads), "no_caller_is_left_waiting_forever")
    CHECKS.pop()
    return results


# 1. Eight concurrent callers, one build.
clear_projection_cache()
builder = SlowBuilder(0.8)
started = time.monotonic()
results = run_concurrently(8, builder, "api_status")
elapsed = time.monotonic() - started
require(builder.calls == 1, f"eight_concurrent_callers_trigger_one_build (saw {builder.calls})")
require(all(r == {"build": 1} for r in results), "every_caller_receives_the_shared_result")
require(elapsed < 8 * 0.8, "callers_wait_on_the_shared_build_rather_than_serialising")
require(cache_status()["in_flight_build_count"] == 0, "no_build_is_left_marked_in_flight")

# 2. A later, separate request still rebuilds - this is a cache, not a freeze.
time.sleep(0.9)
(RUNTIME / "after.json").write_text("{}", encoding="utf-8")
second = cached_read_only_projection("api_status", builder, ttl_seconds=0.75)
require(builder.calls == 2, "a_later_request_still_gets_a_fresh_build")
require(second == {"build": 2}, "the_later_caller_receives_the_new_result")

# 3. A hit inside the TTL with a stable signature does not rebuild.
immediate = cached_read_only_projection("api_status", builder, ttl_seconds=30.0)
require(builder.calls == 2, "an_unexpired_projection_is_served_from_cache")
require(immediate == {"build": 2}, "the_cached_value_is_returned_intact")

# 4. Distinct keys never share a build.
clear_projection_cache()
other = SlowBuilder(0.3)
run_concurrently(3, other, "other_key")
require(other.calls == 1, "a_second_key_builds_independently")

# 5. A failing builder releases its slot instead of stranding every waiter.
clear_projection_cache()
failures = {"count": 0}
release = threading.Event()

def failing_builder():
    failures["count"] += 1
    release.wait(5.0)
    raise RuntimeError("builder failed")

errors: list = []
def failing_worker():
    try:
        cached_read_only_projection("failing", failing_builder, ttl_seconds=0.75)
    except Exception as error:
        errors.append(type(error).__name__)

owner = threading.Thread(target=failing_worker)
owner.start()
time.sleep(0.3)
release.set()
owner.join(timeout=30)
require(not owner.is_alive(), "a_failing_build_does_not_hang_its_caller")
require(errors == ["RuntimeError"], "a_builder_failure_reaches_the_caller")
require(cache_status()["in_flight_build_count"] == 0, "a_failed_build_releases_its_in_flight_slot")

# The key must be buildable again afterwards.
recovered = cached_read_only_projection("failing", lambda: {"ok": True}, ttl_seconds=0.75)
require(recovered == {"ok": True}, "a_key_is_buildable_again_after_a_failure")

# 6. Mutating a returned projection cannot corrupt the cached copy.
clear_projection_cache()
shared_builder = SlowBuilder(0.05)
first = cached_read_only_projection("isolation", shared_builder, ttl_seconds=30.0)
first["build"] = "mutated"
again = cached_read_only_projection("isolation", shared_builder, ttl_seconds=30.0)
require(again == {"build": 1}, "callers_cannot_mutate_the_cached_projection")

print(json.dumps({"suite": "v2730.9.8-projection-cache-single-flight", "passed": len(CHECKS), "total": len(CHECKS), "ok": True, "checks": CHECKS}))
