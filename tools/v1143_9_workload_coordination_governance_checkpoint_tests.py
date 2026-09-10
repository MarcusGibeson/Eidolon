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

from conscious_agent.workload_budget_eligibility import WorkloadBudgetEligibilityStore
from conscious_agent.workload_coordination_candidates import WorkloadCoordinationCandidateStore
from conscious_agent.workload_live_arbitration import WorkloadLiveArbitrationStore
from conscious_agent.workload_coordination_continuity import WorkloadCoordinationContinuityStore
from conscious_agent.workload_coordination_reliability_review import WorkloadCoordinationReliabilityReviewStore
from conscious_agent.workload_coordination_visible_evidence import WorkloadCoordinationVisibleEvidenceStore
from conscious_agent.workload_coordination_governance_checkpoint import build_workload_coordination_governance_checkpoint

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"
    eligibility = WorkloadBudgetEligibilityStore(runtime).register(
        "eligibility",
        workload_id="workload-1",
        workload_kind="cognition",
        owner_id="cognition-service",
        cpu_budget_ms=100,
        memory_budget_mb=128,
        latency_budget_ms=500,
        token_budget=256,
        priority=50,
    )
    candidate = WorkloadCoordinationCandidateStore(runtime).register(
        "candidate",
        eligibility_id=eligibility["eligibility_id"],
        coordination_action="admit",
        coordination_group_id="group-1",
        fairness_class_id="interactive",
    )
    arbitration = WorkloadLiveArbitrationStore(runtime).arbitrate(
        "arbitration",
        candidate_id=candidate["candidate_id"],
        available_cpu_ms=100,
        available_memory_mb=128,
        available_latency_ms=500,
        available_tokens=256,
    )
    continuity = WorkloadCoordinationContinuityStore(runtime).register(
        "continuity",
        arbitration_id=arbitration["arbitration_id"],
        continuity_key="continuity-key",
        action="complete",
    )
    review = WorkloadCoordinationReliabilityReviewStore(runtime).register(
        "review",
        arbitration_id=arbitration["arbitration_id"],
        continuity_id=continuity["continuity_id"],
        observed_latency_ms=100,
    )
    WorkloadCoordinationVisibleEvidenceStore(runtime).register(
        "evidence",
        review_id=review["review_id"],
    )

    report = build_workload_coordination_governance_checkpoint(runtime, source_root=ROOT)
    require(report["contract_version"] == "v1143.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 20)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1143.2")
    require(report["execution"]["contract_version"] == "v1143.5")
    require(report["reliability"]["contract_version"] == "v1143.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "workload_payload_exposed",
                "conversation_exposed",
                "prompt_exposed",
                "reasoning_text_exposed",
                "source_content_exposed",
                "command_log_exposed",
                "provider_payload_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "schedule_mutated",
                "scheduler_mutated",
                "underlying_work_executed",
                "preemption_executed",
                "provider_contacted",
                "message_sent",
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
        and not report["candidate_created_by_checkpoint"]
        and not report["arbitration_created_by_checkpoint"]
        and not report["continuity_created_by_checkpoint"]
        and not report["reliability_review_created_by_checkpoint"]
        and not report["visible_evidence_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "workload-coordination-governance-checkpoint"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1143.9")

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api("GET", "/api/cognition/workload-coordination-governance-checkpoint")
        require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1143.9")
        post_status, _ = dispatch_api("POST", "/api/cognition/workload-coordination-governance-checkpoint", body={})
        require(post_status in (404, 405))
    finally:
        if old_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data_dir

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require(
        "workload-coordination-governance-checkpoint-panel" in dashboard
        and "/api/cognition/workload-coordination-governance-checkpoint" in dashboard
        and "loadWorkloadCoordinationGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1143, 9)
        and (working != (1143, 9) or previous == (1143, 8))
        and "v1143.9 Workload Coordination Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_record_count",
            "coordination_candidate_count",
            "arbitration_record_count",
            "continuity_record_count",
            "reliability_review_count",
            "visible_evidence_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1143.9"}))
