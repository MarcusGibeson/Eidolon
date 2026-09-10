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

from conscious_agent.real_reflective_cognition_checkpoint import (
    build_real_reflective_cognition_checkpoint,
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
    before = {
        path.relative_to(ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    report = build_real_reflective_cognition_checkpoint(runtime, source_root=ROOT)
    after = {
        path.relative_to(ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }

    require(report["contract_version"] == "v1125.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["check_count"] == 18 and report["passed"] == report["total"] == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["runtime_external"] and not report["runtime_mutated"])
    require(before == after and not report["source_modified"])
    require(report["reflective_session_intake"]["contract_version"] == "v1125.2")
    require(report["reflective_execution_continuity"]["contract_version"] == "v1125.5")
    require(report["reflection_integration_reliability"]["contract_version"] == "v1125.8")
    require(
        report["epistemic_status"] == "candidate_artificial_consciousness_not_proven"
        and not report["consciousness_claimed"]
    )
    require(
        not report["reflection_started_by_checkpoint"]
        and not report["reflection_subject_created_by_checkpoint"]
    )
    require(
        not any(
            report[key]
            for key in (
                "raw_messages_exposed",
                "raw_content_exposed",
                "prompts_exposed",
                "provider_payloads_exposed",
                "evidence_text_exposed",
                "conclusions_exposed",
                "hidden_reasoning_exposed",
                "private_content_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "belief_updated",
                "goal_updated",
                "self_model_updated",
                "intention_created",
                "initiative_created",
                "message_sent",
                "notification_created",
                "provider_contacted",
                "browsing_performed",
                "schedule_mutated",
                "policy_applied",
                "proposal_applied",
                "approval_granted",
                "authorization_granted",
                "external_action_executed",
                "release_approved",
                "release_promoted",
                "release_certified",
            )
        )
    )

    environment = dict(os.environ)
    environment["EIDOLON_DATA_DIR"] = str(temporary / "cli-runtime")
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "real-reflective-cognition-checkpoint",
            "--json",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(
        cli.returncode == 0
        and json.loads(cli.stdout)["contract_version"] == "v1125.9"
    )

    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api(
        "GET", "/api/cognition/real-reflective-cognition-checkpoint"
    )
    require(
        status == 200
        and (payload.get("data") or {}).get("contract_version") == "v1125.9"
    )
    post_status, _ = dispatch_api(
        "POST", "/api/cognition/real-reflective-cognition-checkpoint", body={}
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "real-reflective-cognition-checkpoint-panel" in dashboard
        and "/api/cognition/real-reflective-cognition-checkpoint" in dashboard
        and "loadRealReflectiveCognitionCheckpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    require(
        bool(match)
        and tuple(map(int, match.groups())) >= (1125, 9)
        and "v1125.9 Real Reflective Cognition Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )

print(json.dumps({"passed": passed, "total": 18, "suite": "v1125.9"}))
