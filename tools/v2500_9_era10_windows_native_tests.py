from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "conscious_agent"))
sys.dont_write_bytecode = True
os.environ["EIDOLON_DATA_DIR"] = tempfile.mkdtemp(prefix="eidolon-v2500-windows-data-")

from autonomous_developer_beta_v2400 import (
    build_goal_to_candidate_contract,
    build_stage_evidence,
    inspect_goal_to_candidate,
    record_stage_receipt,
    start_goal_to_candidate,
)
from unattended_operation_v2400 import (
    build_health_trend,
    build_unattended_policy,
    record_health_sample,
    run_accelerated_soak_fixture,
)


checks: list[str] = []


def require(value: object, name: str) -> None:
    checks.append(name)
    assert value, name


require(os.name == "nt", "native_windows_host")

runtime = Path(tempfile.mkdtemp(prefix="eidolon-v2500-windows-runtime-"))
policy = build_unattended_policy(policy_id="windows_gate", source_digest="a" * 64, allowed_activities=["health_inspection"])
health_results = [
    record_health_sample(
        runtime_root=runtime,
        event_id=f"health-{index}",
        policy_digest=policy["policy_digest"],
        source_digest="a" * 64,
        sample={"queue_depth": index, "latency_ms": index * 2, "cpu_percent": 10 + index},
    )
    for index in range(16)
]
require(all(row.get("status") == "health_sample_recorded" for row in health_results), "windows_health_writes_complete")
trend = build_health_trend(runtime_root=runtime)
require(trend.get("ok") and trend.get("sample_count") == 16, "windows_health_writes_converge")
require(trend["averages"]["queue_depth"] == 7.5 and trend["averages"]["latency_ms"] == 15.0, "windows_health_averages_correct")

contract = build_goal_to_candidate_contract(
    goal_id="windows_goal",
    goal_digest="a" * 64,
    baseline_source_digest="b" * 64,
    scope_digest="c" * 64,
)
start_results = [
    start_goal_to_candidate(runtime_root=runtime, event_id="windows-start", contract=contract)
    for _ in range(8)
]
statuses = [str(row.get("status")) for row in start_results]
require(statuses.count("developer_beta_started") == 1 and statuses.count("developer_beta_start_replayed") == 7, "developer_start_exactly_once_replay")
start_digest = next(str(row.get("state_digest")) for row in start_results if row.get("state_digest"))

stage_evidence = build_stage_evidence(stage="requirements", artifact_digest="1" * 64)
stage_results = [
    record_stage_receipt(
        runtime_root=runtime,
        goal_id="windows_goal",
        event_id="windows-stage",
        expected_state_digest=start_digest,
        stage="requirements",
        evidence_digest=stage_evidence["evidence_digest"],
        evidence_payload=stage_evidence,
    )
    for _ in range(8)
]
stage_statuses = [str(row.get("status")) for row in stage_results]
require(stage_statuses.count("developer_beta_stage_recorded") == 1 and stage_statuses.count("developer_beta_stage_replayed") == 7, "developer_stage_exactly_once_replay")

restart = inspect_goal_to_candidate(runtime_root=runtime, goal_id="windows_goal")
require(restart.get("ok") and restart.get("stage") == "architecture" and restart.get("completed_stage_count") == 1, "developer_persisted_state_restores")

policy = build_unattended_policy(policy_id="soak", source_digest="a" * 64, allowed_activities=["health_inspection", "queue_inspection"])
events = []
for index in range(5000):
    pressure = index % 29 == 0
    outage = index % 41 == 0
    events.append({
        "cpu_percent": 92 if pressure else 20,
        "memory_percent": 30,
        "queue_depth": 2,
        "failure_streak": 0,
        "provider_available": not outage,
    })
soak = run_accelerated_soak_fixture(policy=policy, source_digest="a" * 64, events=events)
require(soak.get("ok") and soak.get("event_count") == 5000 and soak.get("blocked_count") == 0, "accelerated_unattended_soak_completes")
require(soak.get("paused_count", 0) > 0 and soak.get("provider_degraded_count", 0) > 0 and soak.get("automatic_recovery_count", 0) > 0, "accelerated_soak_exercises_pause_degrade_recovery")
require(not soak.get("wall_clock_soak_completed") and not soak.get("sleep_resume_native_evidence_collected"), "accelerated_soak_does_not_fabricate_wall_clock_evidence")

print(json.dumps({"suite": "v2500.9-era10-windows-native", "ok": True, "passed": len(checks), "failed": 0, "checks": checks}, sort_keys=True))
