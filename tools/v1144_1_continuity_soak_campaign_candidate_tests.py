from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.continuity_soak_campaign_candidates import (
    ContinuitySoakCampaignCandidateStore,
)
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
    for kind in ("cognition", "conversation", "inquiry", "development"):
        workload_ids.append(
            workload_store.register(
                f"workload-{kind}",
                workload_id=f"workload-{kind}",
                workload_kind=kind,
                owner_id=f"owner-{kind}",
                cpu_budget_ms=100,
                memory_budget_mb=128,
                latency_budget_ms=500,
                token_budget=256,
            )["eligibility_id"]
        )

    eligibility = ContinuitySoakEligibilityStore(runtime).register(
        "eligibility",
        soak_scope_id="cognitive-alpha-continuity",
        baseline_checkpoint_digest="a" * 64,
        runtime_profile_digest="b" * 64,
        provider_profile_digest="c" * 64,
        workload_eligibility_ids=workload_ids,
        scenario_ids=sorted(SOAK_SCENARIOS),
        duration_days=3,
        observation_interval_minutes=30,
    )

    store = ContinuitySoakCampaignCandidateStore(runtime)
    result = store.register(
        "campaign",
        eligibility_id=eligibility["eligibility_id"],
        campaign_action="prepare",
        campaign_group_id="campaign-group-1",
        observation_profile_id="observation-profile-1",
        recovery_profile_id="recovery-profile-1",
        scenario_sequence=sorted(SOAK_SCENARIOS),
        planned_sleep_cycles=2,
        planned_restart_count=2,
        planned_interruption_count=2,
        planned_provider_outage_count=2,
        max_provider_outage_minutes=30,
        stale_work_threshold_minutes=60,
    )
    require(result["state"] == "requires_operator_review")

    row = store.snapshot()["candidates"][0]
    require(row["eligibility_id"] == eligibility["eligibility_id"] and row["duration_days"] == 3)
    require(row["scenario_sequence"] == sorted(SOAK_SCENARIOS))
    require(
        not row["operator_confirmation_recorded"]
        and not row["launch_authorized"]
        and not row["soak_started"]
        and not row["fault_injection_started"]
    )

    duplicate = store.register(
        "campaign-duplicate",
        eligibility_id=eligibility["eligibility_id"],
        campaign_action="prepare",
        campaign_group_id="campaign-group-1",
        observation_profile_id="observation-profile-1",
        recovery_profile_id="recovery-profile-1",
        scenario_sequence=sorted(SOAK_SCENARIOS),
        planned_sleep_cycles=2,
        planned_restart_count=2,
        planned_interruption_count=2,
        planned_provider_outage_count=2,
        max_provider_outage_minutes=30,
        stale_work_threshold_minutes=60,
    )
    require(duplicate["status"] == "duplicate_suppressed")

    inspection = store.inspection_summary()
    require(
        inspection["contract_version"] == "v1144.1"
        and not inspection["launch_authorized"]
        and not inspection["launch_token_issued"]
        and not any(inspection["authority_boundary"].values())
    )
    require(
        not inspection["raw_content_exposed"]
        and not inspection["provider_payload_exposed"]
        and not inspection["hidden_reasoning_exposed"]
    )

print(json.dumps({"passed": passed, "total": 7, "suite": "v1144.1"}))
