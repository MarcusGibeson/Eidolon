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

from conscious_agent.api_server import dispatch_api
from conscious_agent.self_model_integrity_identity_claim_governance_checkpoint import (
    build_self_model_integrity_identity_claim_governance_checkpoint,
)

passed = 0


def require(condition: bool) -> None:
    global passed
    if not condition:
        raise AssertionError(f"check {passed + 1} failed")
    passed += 1


with tempfile.TemporaryDirectory() as td:
    runtime = Path(td) / "runtime"
    source_before = {
        path.relative_to(ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    report = build_self_model_integrity_identity_claim_governance_checkpoint(
        runtime,
        source_root=ROOT,
    )
    source_after = {
        path.relative_to(ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }

    require(report["contract_version"] == "v1120.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["check_count"] == 18 and len(report["checks"]) == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["runtime_external"] is True and report["runtime_mutated"] is False)
    require(source_before == source_after and report["source_modified"] is False)
    require(report["self_model_integrity_intake"]["contract_version"] == "v1120.2")
    require(report["self_model_revision_deliberation"]["contract_version"] == "v1120.5")
    require(report["self_model_continuity_review"]["contract_version"] == "v1120.8")
    require(not any(report[key] for key in (
        "raw_messages_exposed", "raw_content_exposed", "prompts_exposed",
        "provider_payloads_exposed", "claim_text_exposed", "identity_text_exposed",
        "self_model_text_exposed", "hidden_reasoning_exposed", "private_content_exposed",
    )))
    require(not any(report[key] for key in (
        "identity_revised", "identity_claim_mutated", "self_model_revised",
        "self_model_mutated", "temporary_state_promoted", "persistent_trait_created",
        "records_deleted", "policy_applied",
    )))
    require(not any(report[key] for key in (
        "attention_selected", "intention_formed", "decision_committed", "proposal_created",
        "proposal_applied", "approval_granted", "authorization_granted",
        "external_action_executed", "release_approved", "release_promoted", "release_certified",
    )))

    env = dict(os.environ)
    env["EIDOLON_DATA_DIR"] = str(Path(td) / "cli-runtime")
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "eidolon.py"),
            "self-model-integrity-identity-claim-governance-checkpoint",
            "--json",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1120.9")

    os.environ["EIDOLON_DATA_DIR"] = str(Path(td) / "api-runtime")
    status, payload = dispatch_api(
        "GET", "/api/cognition/self-model-integrity-identity-claim-governance-checkpoint"
    )
    require(status == 200 and (payload.get("data") or {})["contract_version"] == "v1120.9")
    post_status, _ = dispatch_api(
        "POST",
        "/api/cognition/self-model-integrity-identity-claim-governance-checkpoint",
        body={},
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "self-model-integrity-identity-claim-governance-checkpoint-panel" in dashboard
        and "/api/cognition/self-model-integrity-identity-claim-governance-checkpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1120, 9)
        and previous >= (1120, 8)
        and previous <= working
        and 'METADATA_SCHEMA_VERSION = "1"' in metadata
    )

    docs = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in (
            "README.md",
            "README_NEXT_STEPS.md",
            "README_RELEASE_HISTORY.md",
            "archive/docs/legacy_dependencies/roadmaps/README_V1100_ROADMAP.md",
        )
    )
    require("v1120.9" in docs and "v1121" in docs)

print(json.dumps({"passed": passed, "total": 18, "suite": "v1120.9"}))
