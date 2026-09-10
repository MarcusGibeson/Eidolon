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

from conscious_agent.reflection_supported_revision_governance_checkpoint import (
    build_reflection_supported_revision_governance_checkpoint,
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
    report = build_reflection_supported_revision_governance_checkpoint(
        runtime, source_root=ROOT
    )

    require(report["contract_version"] == "v1128.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["passed"] == report["total"] == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(not report["runtime_mutated"] and not report["source_modified"])
    require(report["intake"]["contract_version"] == "v1128.2")
    require(report["deliberation"]["contract_version"] == "v1128.5")
    require(report["integration"]["contract_version"] == "v1128.8")
    require(
        not any(
            report[key]
            for key in (
                "raw_content_exposed",
                "conclusion_text_exposed",
                "evidence_text_exposed",
                "hidden_reasoning_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "belief_revised",
                "motivation_revised",
                "goal_revised",
                "self_model_revised",
                "revision_applied",
                "target_revised",
                "provider_contacted",
                "reflection_created",
                "message_sent",
                "notification_created",
                "initiative_created",
                "approval_granted",
                "authorization_granted",
                "external_action_executed",
                "installation_modified",
                "release_promoted",
                "release_certified",
            )
        )
    )
    require(
        not report["consciousness_proven"]
        and not report["revision_signal_created_by_checkpoint"]
        and not report["revision_candidate_created_by_checkpoint"]
        and not report["revision_session_created_by_checkpoint"]
        and not report["revision_outcome_created_by_checkpoint"]
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "reflection-supported-revision-governance-checkpoint",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1128.9"
    )

    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api(
        "GET", "/api/cognition/reflection-supported-revision-governance-checkpoint"
    )
    require(
        status == 200
        and (payload.get("data") or {}).get("contract_version") == "v1128.9"
    )
    post_status, _ = dispatch_api(
        "POST",
        "/api/cognition/reflection-supported-revision-governance-checkpoint",
        body={},
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "reflection-supported-revision-governance-checkpoint-panel" in dashboard
        and "/api/cognition/reflection-supported-revision-governance-checkpoint"
        in dashboard
        and "loadReflectionSupportedRevisionGovernanceCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    require(
        bool(match)
        and tuple(map(int, match.groups())) >= (1128, 9)
        and "v1128.9 Reflection-Supported Revision Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )
    require(
        set(report["summary"])
        == {
            "signal_count",
            "candidate_count",
            "session_count",
            "arbitration_outcome_count",
            "revision_outcome_count",
            "reliability_review_count",
        }
    )
    require(report["desktop_verification_pending"])

print(json.dumps({"passed": passed, "total": 18, "suite": "v1128.9"}))
