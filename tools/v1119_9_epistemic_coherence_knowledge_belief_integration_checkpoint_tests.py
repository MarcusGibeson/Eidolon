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

from conscious_agent.api_server import dispatch_api
from conscious_agent.epistemic_coherence_knowledge_belief_integration_checkpoint import (
    build_epistemic_coherence_knowledge_belief_integration_checkpoint,
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
    report = build_epistemic_coherence_knowledge_belief_integration_checkpoint(
        runtime,
        source_root=ROOT,
    )
    source_after = {
        path.relative_to(ROOT).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in ROOT.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }

    require(report["contract_version"] == "v1119.9")
    require(report["ok"] and report["status"] == "ready_for_desktop_verification")
    require(report["check_count"] == 18 and len(report["checks"]) == 18)
    require(all(row["status"] == "pass" for row in report["checks"]))
    require(report["runtime_external"] is True and report["runtime_mutated"] is False)
    require(source_before == source_after and report["source_modified"] is False)
    require(report["epistemic_coherence_intake"]["contract_version"] == "v1119.2")
    require(report["epistemic_coherence_deliberation"]["contract_version"] == "v1119.5")
    require(report["knowledge_belief_integration"]["contract_version"] == "v1119.8")
    require(not any(report[key] for key in (
        "raw_messages_exposed", "raw_content_exposed", "prompts_exposed",
        "provider_payloads_exposed", "evidence_text_exposed", "knowledge_text_exposed",
        "belief_text_exposed", "self_model_text_exposed", "hidden_reasoning_exposed",
        "private_content_exposed",
    )))
    require(not any(report[key] for key in (
        "records_repaired", "records_merged", "evidence_mutated", "knowledge_mutated",
        "belief_mutated", "identity_claim_mutated", "self_model_mutated",
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
            "epistemic-coherence-knowledge-belief-integration-checkpoint",
            "--json",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1119.9")

    os.environ["EIDOLON_DATA_DIR"] = str(Path(td) / "api-runtime")
    status, payload = dispatch_api(
        "GET", "/api/cognition/epistemic-coherence-knowledge-belief-integration-checkpoint"
    )
    require(status == 200 and (payload.get("data") or {})["contract_version"] == "v1119.9")
    post_status, _ = dispatch_api(
        "POST",
        "/api/cognition/epistemic-coherence-knowledge-belief-integration-checkpoint",
        body={},
    )
    require(post_status in (404, 405))

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(
        encoding="utf-8"
    )
    require(
        "epistemic-coherence-knowledge-belief-integration-checkpoint-panel" in dashboard
        and "/api/cognition/epistemic-coherence-knowledge-belief-integration-checkpoint" in dashboard
    )

    metadata = (ROOT / "conscious_agent" / "release_metadata.py").read_text(encoding="utf-8")
    import re
    working_match = re.search(r'WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    previous_match = re.search(r'PREVIOUS_WORKING_SOURCE_VERSION = "(\d+)\.(\d+)"', metadata)
    working = tuple(map(int, working_match.groups())) if working_match else (0, 0)
    previous = tuple(map(int, previous_match.groups())) if previous_match else (0, 0)
    require(
        working >= (1119, 9)
        and previous >= (1118, 9)
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
    require("v1119.9" in docs and "v1120" in docs)

print(json.dumps({"passed": passed, "total": 18, "suite": "v1119.9"}))
