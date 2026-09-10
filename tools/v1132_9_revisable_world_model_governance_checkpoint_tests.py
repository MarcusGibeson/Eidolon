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

from conscious_agent.revisable_world_model_governance_checkpoint import (
    build_revisable_world_model_governance_checkpoint,
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
    report = build_revisable_world_model_governance_checkpoint(
        runtime, source_root=ROOT
    )

    require(report["contract_version"] == "v1132.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1132.2")
    require(report["deliberation"]["contract_version"] == "v1132.5")
    require(report["integration"]["contract_version"] == "v1132.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "evidence_text_exposed",
                "belief_text_exposed",
                "memory_text_exposed",
                "goal_text_exposed",
                "identity_text_exposed",
                "prompt_exposed",
                "provider_payload_exposed",
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
                "initiative_created",
                "initiative_mutated",
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
                "filesystem_modified",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["world_model_signal_created_by_checkpoint"]
        and not report["world_model_candidate_created_by_checkpoint"]
        and not report["deliberation_session_created_by_checkpoint"]
        and not report["arbitration_outcome_created_by_checkpoint"]
        and not report["world_model_outcome_created_by_checkpoint"]
        and not report["world_model_revision_applied_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "revisable-world-model-governance-checkpoint",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1132.9"
    )

    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api(
        "GET", "/api/cognition/revisable-world-model-governance-checkpoint"
    )
    require(
        status == 200
        and (payload.get("data") or {}).get("contract_version") == "v1132.9"
    )
    post_status, _ = dispatch_api(
        "POST",
        "/api/cognition/revisable-world-model-governance-checkpoint",
        body={},
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "revisable-world-model-governance-checkpoint-panel" in dashboard
        and "/api/cognition/revisable-world-model-governance-checkpoint" in dashboard
        and "loadRevisableWorldModelGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    require(
        bool(match)
        and tuple(map(int, match.groups())) >= (1132, 9)
        and "v1132.9 Revisable World Model Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "world_model_signal_count",
            "candidate_count",
            "deliberation_session_count",
            "arbitration_outcome_count",
            "world_model_outcome_count",
            "reliability_review_count",
            "accepted_or_review_recommended_count",
            "deliberate_non_acceptance_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1132.9"}))
