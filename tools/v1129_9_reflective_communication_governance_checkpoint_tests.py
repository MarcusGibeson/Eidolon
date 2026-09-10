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

from conscious_agent.reflective_communication_governance_checkpoint import (
    build_reflective_communication_governance_checkpoint,
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
    report = build_reflective_communication_governance_checkpoint(
        runtime, source_root=ROOT
    )

    require(report["contract_version"] == "v1129.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1129.2")
    require(report["deliberation"]["contract_version"] == "v1129.5")
    require(report["integration"]["contract_version"] == "v1129.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "message_text_exposed",
                "proposed_message_text_exposed",
                "reflection_text_exposed",
                "conclusion_text_exposed",
                "evidence_text_exposed",
                "prompt_exposed",
                "provider_payload_exposed",
                "memory_text_exposed",
                "motivation_text_exposed",
                "goal_text_exposed",
                "identity_text_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "provider_contacted",
                "model_contacted",
                "message_generated",
                "message_sent",
                "notification_created",
                "initiative_created",
                "conversation_proposal_created",
                "approval_created",
                "approval_granted",
                "authorization_created",
                "authorization_granted",
                "external_action_executed",
                "installation_modified",
                "promotion_performed",
                "release_promoted",
                "certification_performed",
                "release_certified",
                "policy_applied",
                "proposal_applied",
                "schedule_mutated",
                "browsing_performed",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["eligibility_signal_created_by_checkpoint"]
        and not report["communication_candidate_created_by_checkpoint"]
        and not report["deliberation_session_created_by_checkpoint"]
        and not report["arbitration_outcome_created_by_checkpoint"]
        and not report["communication_outcome_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "reflective-communication-governance-checkpoint",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1129.9"
    )

    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api(
        "GET", "/api/cognition/reflective-communication-governance-checkpoint"
    )
    require(
        status == 200
        and (payload.get("data") or {}).get("contract_version") == "v1129.9"
    )
    post_status, _ = dispatch_api(
        "POST",
        "/api/cognition/reflective-communication-governance-checkpoint",
        body={},
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "reflective-communication-governance-checkpoint-panel" in dashboard
        and "/api/cognition/reflective-communication-governance-checkpoint"
        in dashboard
        and "loadReflectiveCommunicationGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    require(
        bool(match)
        and tuple(map(int, match.groups())) >= (1129, 9)
        and "v1129.9 Real Reflective Communication Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "eligibility_signal_count",
            "candidate_count",
            "deliberation_session_count",
            "arbitration_outcome_count",
            "communication_outcome_count",
            "reliability_review_count",
            "delayed_follow_up_count",
            "deliberate_silence_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1129.9"}))
