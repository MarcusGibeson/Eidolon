from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2400-windows-data-")

from cooperative_development_v2300 import inspect_work_coordination, register_work
from outcome_learning_governance_v2300 import inspect_learning_state, record_verified_outcome
from preference_adaptation_v2300 import build_adaptation_projection, inspect_preferences, record_preference


checks: list[str] = []


def require(value: object, name: str) -> None:
    checks.append(name)
    assert value, name


require(os.name == "nt", "native_windows_host")

learning_root = Path(tempfile.mkdtemp(prefix="eidolon-v2400-thread-learning-"))


def add_outcome(index: int) -> dict[str, object]:
    return record_verified_outcome(
        outcome_id=f"thread-outcome-{index}", task_type="thread-race", result="success",
        evidence_digest=f"{index + 1:064x}", event_id=f"thread-outcome-event-{index}",
        runtime_root=learning_root,
    )


with ThreadPoolExecutor(max_workers=4) as executor:
    outcome_results = list(executor.map(add_outcome, range(4)))
require(all(result.get("ok") for result in outcome_results), "concurrent_outcome_writes_complete")
learning_state = inspect_learning_state(runtime_root=learning_root)
require(learning_state.get("revision") == 4 and learning_state.get("outcome_count") == 4, "concurrent_outcome_writes_converge")

preference_root = Path(tempfile.mkdtemp(prefix="eidolon-v2400-thread-preference-"))
domains = ("tone", "detail", "timing", "ui")


def add_preference(index: int) -> dict[str, object]:
    return record_preference(
        preference_id=f"thread-preference-{index}", domain=domains[index], value=f"value-{index}",
        kind="explicit", evidence_digests=[f"{index + 10:064x}"],
        event_id=f"thread-preference-event-{index}", runtime_root=preference_root,
    )


with ThreadPoolExecutor(max_workers=4) as executor:
    preference_results = list(executor.map(add_preference, range(4)))
require(all(result.get("ok") for result in preference_results), "concurrent_preference_writes_complete")
preference_state = inspect_preferences(runtime_root=preference_root)
require(preference_state.get("revision") == 4 and preference_state.get("record_count") == 4, "concurrent_preference_writes_converge")
require(not build_adaptation_projection(runtime_root=preference_root, now=math.inf).get("ok"), "nonfinite_native_time_fails_closed")

work_root = Path(tempfile.mkdtemp(prefix="eidolon-v2400-thread-work-"))


def add_work(index: int) -> dict[str, object]:
    return register_work(
        work_id=f"thread-work-{index}", owner_kind="eidolon",
        base_manifest_digest="a" * 64, intent_digest=f"{index + 20:064x}",
        touched_paths=[f"conscious_agent/thread_{index}.py"],
        event_id=f"thread-work-event-{index}", runtime_root=work_root,
    )


with ThreadPoolExecutor(max_workers=4) as executor:
    work_results = list(executor.map(add_work, range(4)))
require(all(result.get("ok") for result in work_results), "concurrent_work_writes_complete")
work_state = inspect_work_coordination(runtime_root=work_root)
require(work_state.get("revision") == 4 and work_state.get("work_item_count") == 4, "concurrent_work_writes_converge")
require(work_state.get("retained_operation_owner") == "ownership_concurrency", "native_coordination_remains_advisory")

print(json.dumps({
    "suite": "v2400.9-era9-windows-native",
    "ok": True,
    "passed": len(checks),
    "failed": 0,
    "checks": checks,
}, sort_keys=True))
