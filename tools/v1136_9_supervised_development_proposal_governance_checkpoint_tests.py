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

from conscious_agent.supervised_development_proposal_governance_checkpoint import (
    build_supervised_development_proposal_governance_checkpoint,
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
    report = build_supervised_development_proposal_governance_checkpoint(
        runtime, source_root=ROOT
    )

    require(report["contract_version"] == "v1136.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1136.2")
    require(report["deliberation"]["contract_version"] == "v1136.5")
    require(report["integration"]["contract_version"] == "v1136.8")
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
        and not report["proposal_eligibility_created_by_checkpoint"]
        and not report["proposal_candidate_created_by_checkpoint"]
        and not report["deliberation_session_created_by_checkpoint"]
        and not report["arbitration_outcome_created_by_checkpoint"]
        and not report["outcome_lineage_created_by_checkpoint"]
        and not report["reliability_review_created_by_checkpoint"]
        and not report["development_proposal_created_by_checkpoint"]
        and not report["specification_created_by_checkpoint"]
        and not report["test_plan_created_by_checkpoint"]
        and not report["sandbox_change_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "supervised-development-proposal-governance-checkpoint",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1136.9"
    )

    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api(
        "GET", "/api/cognition/supervised-development-proposal-governance-checkpoint"
    )
    require(
        status == 200
        and (payload.get("data") or {}).get("contract_version") == "v1136.9"
    )
    post_status, _ = dispatch_api(
        "POST",
        "/api/cognition/supervised-development-proposal-governance-checkpoint",
        body={},
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "supervised-development-proposal-governance-checkpoint-panel" in dashboard
        and "/api/cognition/supervised-development-proposal-governance-checkpoint"
        in dashboard
        and "loadSupervisedDevelopmentProposalGovernanceCheckpoint" in dashboard
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
        working >= (1136, 9)
        and previous >= (1135, 9)
        and previous <= working
        and "v1136.9 Supervised Development Proposal Governance Checkpoint"
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
            "deliberate_no_proposal_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1136.9"}))
