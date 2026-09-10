from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.continuity_soak_campaign_candidates import ContinuitySoakCampaignCandidateStore
from conscious_agent.continuity_soak_eligibility import ContinuitySoakEligibilityStore, SOAK_SCENARIOS
from conscious_agent.multi_day_continuity_soak_intake_checkpoint import build_multi_day_continuity_soak_intake_checkpoint
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as temporary_directory:
    temporary = Path(temporary_directory)
    runtime = temporary / "runtime" / "cognition"
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
    ContinuitySoakCampaignCandidateStore(runtime).register(
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

    report = build_multi_day_continuity_soak_intake_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1144.2")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 20)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["eligibility"]["contract_version"] == "v1144.0")
    require(report["campaigns"]["contract_version"] == "v1144.1")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "workload_payload_exposed",
                "provider_payload_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "campaign_started",
                "fault_injection_started",
                "provider_contacted",
                "process_restarted",
                "work_interrupted",
                "work_resumed",
                "message_sent",
                "source_mutated",
                "approval_created",
                "authorization_created",
                "installation_performed",
                "promotion_performed",
                "certification_performed",
            )
        )
    )
    require(
        not report["eligibility_created_by_checkpoint"]
        and not report["campaign_created_by_checkpoint"]
        and not report["consciousness_proven"]
        and report["desktop_verification_pending"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "multi-day-continuity-soak-intake-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1144.2")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/multi-day-continuity-soak-intake-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1144.2")
        post_status, _ = dispatch_api(
            "POST", "/api/cognition/multi-day-continuity-soak-intake-checkpoint", body={}
        )
        require(post_status in (404, 405))
    finally:
        if old_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data_dir

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require(
        "multi-day-continuity-soak-intake-checkpoint-panel" in dashboard
        and "/api/cognition/multi-day-continuity-soak-intake-checkpoint" in dashboard
        and "loadMultiDayContinuitySoakIntakeCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1144, 2)
        and (working != (1144, 2) or previous == (1143, 9))
        and "v1144.2 Multi-Day Continuity Soak Intake Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_record_count",
            "campaign_candidate_count",
            "recognized_scenario_count",
            "recognized_workload_count",
        }
    )
    require(report["summary"]["recognized_scenario_count"] == 6)

print(json.dumps({"passed": passed, "total": 17, "suite": "v1144.2"}))
