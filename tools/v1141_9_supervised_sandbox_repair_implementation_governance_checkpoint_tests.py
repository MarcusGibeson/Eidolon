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

from conscious_agent.supervised_sandbox_repair_implementation_governance_checkpoint import (
    build_supervised_sandbox_repair_implementation_governance_checkpoint,
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
    report = build_supervised_sandbox_repair_implementation_governance_checkpoint(
        runtime, source_root=ROOT
    )

    require(report["contract_version"] == "v1141.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1141.2")
    require(report["execution"]["contract_version"] == "v1141.5")
    require(report["integration"]["contract_version"] == "v1141.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "raw_source_exposed",
                "source_content_exposed",
                "patch_text_exposed",
                "commands_exposed",
                "test_instructions_exposed",
                "logs_exposed",
                "conversation_exposed",
                "prompt_exposed",
                "provider_payload_exposed",
                "private_project_record_exposed",
                "private_path_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "browser_contacted",
                "provider_contacted",
                "model_contacted",
                "message_sent",
                "notification_created",
                "goal_mutated",
                "plan_mutated",
                "initiative_mutated",
                "proposal_created",
                "approval_created",
                "authorization_created",
                "installation_modified",
                "installation_performed",
                "promotion_performed",
                "certification_performed",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["eligibility_created_by_checkpoint"]
        and not report["work_order_created_by_checkpoint"]
        and not report["claim_created_by_checkpoint"]
        and not report["sandbox_created_by_checkpoint"]
        and not report["workspace_materialized_by_checkpoint"]
        and not report["candidate_change_created_by_checkpoint"]
        and not report["command_executed_by_checkpoint"]
        and not report["test_executed_by_checkpoint"]
        and not report["rollback_executed_by_checkpoint"]
        and not report["structural_receipt_created_by_checkpoint"]
        and not report["continuity_record_created_by_checkpoint"]
        and not report["reliability_review_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "supervised-sandbox-repair-implementation-governance-checkpoint",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1141.9"
    )

    old_data_dir = os.environ.get("EIDOLON_DATA_DIR")
    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    try:
        from conscious_agent.api_server import dispatch_api

        status, payload = dispatch_api(
            "GET",
            "/api/cognition/supervised-sandbox-repair-implementation-governance-checkpoint",
        )
        require(
            status == 200
            and (payload.get("data") or {}).get("contract_version") == "v1141.9"
        )
        post_status, _ = dispatch_api(
            "POST",
            "/api/cognition/supervised-sandbox-repair-implementation-governance-checkpoint",
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
        "supervised-sandbox-repair-implementation-governance-checkpoint-panel"
        in dashboard
        and "/api/cognition/supervised-sandbox-repair-implementation-governance-checkpoint"
        in dashboard
        and "loadSupervisedSandboxRepairImplementationGovernanceCheckpoint"
        in dashboard
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
        working >= (1141, 9)
        and (working != (1141, 9) or previous == (1141, 8))
        and "v1141.9 Supervised Sandbox Repair Implementation Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_record_count",
            "work_order_count",
            "ready_for_materialization_count",
            "materialization_count",
            "execution_count",
            "reconciliation_count",
            "reliability_review_count",
            "operator_candidate_evidence_ready_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1141.9"}))
