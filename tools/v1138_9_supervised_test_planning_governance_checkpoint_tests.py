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

from conscious_agent.supervised_test_plan_governance_checkpoint import (
    build_supervised_test_plan_governance_checkpoint,
)

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime" / "cognition"
    report = build_supervised_test_plan_governance_checkpoint(
        runtime, source_root=ROOT
    )

    require(report["contract_version"] == "v1138.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1138.2")
    require(report["deliberation"]["contract_version"] == "v1138.5")
    require(report["integration"]["contract_version"] == "v1138.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "raw_source_exposed",
                "source_content_exposed",
                "failure_log_exposed",
                "conversation_exposed",
                "prompt_exposed",
                "provider_payload_exposed",
                "evidence_text_exposed",
                "proposal_text_exposed",
                "specification_text_exposed",
                "test_plan_text_exposed",
                "test_code_exposed",
                "private_project_record_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "browser_contacted",
                "browsing_performed",
                "provider_contacted",
                "model_contacted",
                "message_generated",
                "message_sent",
                "notification_created",
                "goal_mutated",
                "plan_mutated",
                "initiative_mutated",
                "proposal_created",
                "development_proposal_created",
                "specification_created",
                "test_plan_created",
                "test_code_created",
                "fixture_created",
                "sandbox_created",
                "tests_executed",
                "approval_created",
                "authorization_created",
                "external_action_executed",
                "source_modified_by_checkpoint",
                "installation_modified",
                "promotion_performed",
                "certification_performed",
                "filesystem_modified",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["test_plan_eligibility_created_by_checkpoint"]
        and not report["test_plan_candidate_created_by_checkpoint"]
        and not report["deliberation_session_created_by_checkpoint"]
        and not report["arbitration_outcome_created_by_checkpoint"]
        and not report["outcome_lineage_created_by_checkpoint"]
        and not report["reliability_review_created_by_checkpoint"]
        and not report["test_plan_created_by_checkpoint"]
        and not report["test_code_created_by_checkpoint"]
        and not report["fixture_created_by_checkpoint"]
        and not report["sandbox_change_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "supervised-test-planning-governance-checkpoint",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1138.9"
    )

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api(
            "GET", "/api/cognition/supervised-test-planning-governance-checkpoint"
        )
        require(
            status == 200
            and (payload.get("data") or {}).get("contract_version") == "v1138.9"
        )
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/supervised-test-planning-governance-checkpoint",
            body={},
        )
        require(post_status in (404, 405))
    finally:
        if old_data_dir is None:
            os.environ.pop("EIDOLON_DATA_DIR", None)
        else:
            os.environ["EIDOLON_DATA_DIR"] = old_data_dir

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "supervised-test-planning-governance-checkpoint-panel" in dashboard
        and "/api/cognition/supervised-test-planning-governance-checkpoint"
        in dashboard
        and "loadSupervisedTestPlanningGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(
        encoding="utf-8"
    )
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(
        r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata
    )
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1138, 9)
        and previous >= (1137, 9)
        and previous <= working
        and "v1138.9 Supervised Test Planning Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_record_count",
            "candidate_count",
            "deliberation_session_count",
            "arbitration_outcome_count",
            "outcome_lineage_count",
            "reliability_review_count",
            "supported_or_probable_count",
            "deliberate_no_test_plan_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1138.9"}))
