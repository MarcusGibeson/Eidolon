import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.continuity_soak_campaign_candidates import ContinuitySoakCampaignCandidateStore
from conscious_agent.continuity_soak_eligibility import ContinuitySoakEligibilityStore, SOAK_SCENARIOS
from conscious_agent.continuity_soak_live_execution import ContinuitySoakLiveExecutionStore
from conscious_agent.continuity_soak_recovery_receipts import ContinuitySoakRecoveryReceiptStore
from conscious_agent.continuity_soak_reliability_review import ContinuitySoakReliabilityReviewStore
from conscious_agent.continuity_soak_visible_evidence import ContinuitySoakVisibleEvidenceStore
from conscious_agent.multi_day_continuity_soak_governance_checkpoint import (
    build_multi_day_continuity_soak_governance_checkpoint,
)
from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"

    workloads = WorkloadBudgetEligibilityStore(runtime)
    workload_ids = [
        workloads.register(
            f"workload-{kind}",
            workload_id=f"workload-{kind}",
            workload_kind=kind,
            owner_id=f"owner-{kind}",
            cpu_budget_ms=100,
            memory_budget_mb=128,
            latency_budget_ms=500,
            token_budget=256,
        )["eligibility_id"]
        for kind in ("cognition", "conversation", "inquiry", "development")
    ]

    eligibility = ContinuitySoakEligibilityStore(runtime).register(
        "eligibility",
        soak_scope_id="continuity-scope",
        baseline_checkpoint_digest="a" * 64,
        runtime_profile_digest="b" * 64,
        provider_profile_digest="c" * 64,
        workload_eligibility_ids=workload_ids,
        scenario_ids=sorted(SOAK_SCENARIOS),
        duration_days=3,
        observation_interval_minutes=30,
    )
    campaign = ContinuitySoakCampaignCandidateStore(runtime).register(
        "campaign",
        eligibility_id=eligibility["eligibility_id"],
        campaign_action="prepare",
        campaign_group_id="campaign-group",
        observation_profile_id="observation-profile",
        recovery_profile_id="recovery-profile",
        scenario_sequence=sorted(SOAK_SCENARIOS),
        planned_sleep_cycles=2,
        planned_restart_count=2,
        planned_interruption_count=2,
        planned_provider_outage_count=2,
        max_provider_outage_minutes=30,
        stale_work_threshold_minutes=60,
    )
    execution = ContinuitySoakLiveExecutionStore(runtime).register(
        "execution",
        campaign_id=campaign["campaign_id"],
        operator_confirmation_id="operator-confirmation",
        launch_token_id="launch-token",
        worker_claim_id="worker-claim",
        action="observe",
        scenario_id="restart",
        observation_index=1,
        elapsed_minutes=30,
    )
    receipt = ContinuitySoakRecoveryReceiptStore(runtime).register(
        "receipt",
        execution_id=execution["execution_id"],
        scenario_id="restart",
        restart_epoch=1,
        worker_claim_id="worker-claim",
        recovery_attempted=True,
        recovery_succeeded=True,
        latency_ms=100,
    )
    review = ContinuitySoakReliabilityReviewStore(runtime).register(
        "review",
        receipt_id=receipt["receipt_id"],
        expected_scenario_count=6,
        observed_scenario_count=6,
        baseline_latency_ms=100,
        observed_latency_ms=100,
    )
    ContinuitySoakVisibleEvidenceStore(runtime).register(
        "evidence",
        review_id=review["review_id"],
    )

    report = build_multi_day_continuity_soak_governance_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1144.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 20)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1144.2")
    require(report["execution"]["contract_version"] == "v1144.5")
    require(report["reliability"]["contract_version"] == "v1144.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "workload_payload_exposed",
                "provider_payload_exposed",
                "command_log_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "campaign_started_by_checkpoint",
                "fault_injection_started_by_checkpoint",
                "provider_contacted",
                "process_restarted",
                "work_interrupted",
                "work_resumed",
                "recovery_action_executed",
                "approval_created",
                "authorization_created",
                "installation_performed",
                "promotion_performed",
                "certification_performed",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["eligibility_created_by_checkpoint"]
        and not report["campaign_created_by_checkpoint"]
        and not report["execution_created_by_checkpoint"]
        and not report["receipt_created_by_checkpoint"]
        and not report["reliability_review_created_by_checkpoint"]
        and not report["visible_evidence_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "multi-day-continuity-soak-governance-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1144.9")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/multi-day-continuity-soak-governance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1144.9")
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/multi-day-continuity-soak-governance-checkpoint",
            body={},
        )
        require(post_status in (404, 405))
    finally:
        if old_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data_dir

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require(
        "multi-day-continuity-soak-governance-checkpoint-panel" in dashboard
        and "/api/cognition/multi-day-continuity-soak-governance-checkpoint" in dashboard
        and "loadMultiDayContinuitySoakGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1144, 9)
        and (working != (1144, 9) or previous == (1144, 8))
        and "v1144.9 Multi-Day Continuity Soak Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_record_count",
            "campaign_candidate_count",
            "execution_record_count",
            "recovery_receipt_count",
            "reliability_review_count",
            "visible_evidence_count",
            "recognized_scenario_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1144.9"}))
