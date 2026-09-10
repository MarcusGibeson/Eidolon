from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.continuity_soak_eligibility import (
    ContinuitySoakEligibilityStore,
    SOAK_SCENARIOS,
)
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as temporary_directory:
    runtime = Path(temporary_directory) / "runtime" / "cognition"
    workload_store = WorkloadBudgetEligibilityStore(runtime)
    workload_ids = []
    for index, kind in enumerate(("cognition", "conversation", "inquiry", "development"), start=1):
        result = workload_store.register(
            f"workload-{index}",
            workload_id=f"workload-{kind}",
            workload_kind=kind,
            owner_id=f"owner-{kind}",
            cpu_budget_ms=100,
            memory_budget_mb=128,
            latency_budget_ms=500,
            token_budget=256,
        )
        workload_ids.append(result["eligibility_id"])

    store = ContinuitySoakEligibilityStore(runtime)
    result = store.register(
        "soak-eligibility",
        soak_scope_id="cognitive-alpha-continuity",
        baseline_checkpoint_digest="a" * 64,
        runtime_profile_digest="b" * 64,
        provider_profile_digest="c" * 64,
        workload_eligibility_ids=workload_ids,
        scenario_ids=sorted(SOAK_SCENARIOS),
        duration_days=3,
        observation_interval_minutes=30,
    )
    require(result["state"] == "eligible")

    record = store.snapshot()["records"][0]
    require(record["scenario_ids"] == sorted(SOAK_SCENARIOS) and record["duration_days"] == 3)
    require(record["workload_kinds"] == ["cognition", "conversation", "development", "inquiry"])
    require(record["minimum_observation_count"] == 144 and not record["soak_started"])

    duplicate = store.register(
        "soak-eligibility-duplicate",
        soak_scope_id="cognitive-alpha-continuity",
        baseline_checkpoint_digest="a" * 64,
        runtime_profile_digest="b" * 64,
        provider_profile_digest="c" * 64,
        workload_eligibility_ids=workload_ids,
        scenario_ids=sorted(SOAK_SCENARIOS),
        duration_days=3,
        observation_interval_minutes=30,
    )
    require(duplicate["status"] == "duplicate_suppressed")

    missing = store.register(
        "soak-eligibility-missing",
        soak_scope_id="missing-scenarios",
        baseline_checkpoint_digest="a" * 64,
        runtime_profile_digest="b" * 64,
        provider_profile_digest="c" * 64,
        workload_eligibility_ids=workload_ids,
        scenario_ids=["restart", "recovery"],
        duration_days=3,
        observation_interval_minutes=30,
    )
    require(missing["state"] == "awaiting_scenario_coverage")

    inspection = store.inspection_summary()
    require(
        inspection["contract_version"] == "v1144.0"
        and not inspection["soak_started"]
        and not inspection["fault_injection_started"]
        and not any(inspection["authority_boundary"].values())
    )
    require(
        not inspection["raw_content_exposed"]
        and not inspection["provider_payload_exposed"]
        and not inspection["hidden_reasoning_exposed"]
    )

print(json.dumps({"passed": passed, "total": 8, "suite": "v1144.0"}))
