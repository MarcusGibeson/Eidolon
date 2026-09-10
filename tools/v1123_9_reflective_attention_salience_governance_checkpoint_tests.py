from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from conscious_agent.reflective_attention_salience_governance_checkpoint import (
    build_reflective_attention_salience_governance_checkpoint,
)

passed = 0


def require(condition: object) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    temporary = Path(td)
    runtime = temporary / "runtime"
    before = {
        path.relative_to(ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    report = build_reflective_attention_salience_governance_checkpoint(
        runtime, source_root=ROOT
    )
    after = {
        path.relative_to(ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }

    require(report["contract_version"] == "v1123.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["check_count"] == 18 and len(report["checks"]) == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["runtime_external"] and not report["runtime_mutated"])
    require(before == after and not report["source_modified"])
    require(report["reflective_attention_salience_intake"]["contract_version"] == "v1123.2")
    require(report["reflective_attention_deliberation"]["contract_version"] == "v1123.5")
    require(report["reflective_attention_continuity_review"]["contract_version"] == "v1123.8")
    require(report["epistemic_status"] == "candidate_artificial_consciousness_not_proven" and not report["consciousness_claimed"])
    require(
        not any(
            report[key]
            for key in (
                "raw_messages_exposed",
                "raw_content_exposed",
                "prompts_exposed",
                "provider_payloads_exposed",
                "evidence_text_exposed",
                "motivational_text_exposed",
                "identity_text_exposed",
                "objective_text_exposed",
                "hidden_reasoning_exposed",
                "private_content_exposed",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "attention_selected",
                "reflection_created",
                "intention_created",
                "initiative_created",
                "message_sent",
                "notification_created",
                "provider_contacted",
                "browsing_performed",
                "schedule_mutated",
                "policy_applied",
            )
        )
    )
    require(
        not any(
            report[key]
            for key in (
                "proposal_created",
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
            "reflective-attention-salience-governance-checkpoint",
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
        and json.loads(cli.stdout)["contract_version"] == "v1123.9"
    )

    os.environ["EIDOLON_DATA_DIR"] = str(temporary / "api-runtime")
    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api(
        "GET", "/api/cognition/reflective-attention-salience-governance-checkpoint"
    )
    require(
        status == 200
        and (payload.get("data") or {}).get("contract_version") == "v1123.9"
    )
    post_status, _ = dispatch_api(
        "POST",
        "/api/cognition/reflective-attention-salience-governance-checkpoint",
        body={},
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "reflective-attention-salience-governance-checkpoint-panel" in dashboard
        and "/api/cognition/reflective-attention-salience-governance-checkpoint"
        in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(
        encoding="utf-8"
    )
    import re
    match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    require(
        bool(match)
        and tuple(map(int, match.groups())) >= (1123, 9)
        and "v1123.9 Reflective Attention and Salience Governance Checkpoint"
        in (ROOT / "README_RELEASE_HISTORY.md").read_text(encoding="utf-8")
    )

print(json.dumps({"passed": passed, "total": 18, "suite": "v1123.9"}))
