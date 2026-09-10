from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

from conscious_agent.conversational_action_portal_v1104 import (
    build_action_proposal_card,
    build_operator_tool_catalog,
    classify_conversation_action,
)
from conscious_agent.developer_alpha_runtime import (
    PLANNED_FILES,
    create_development_proposal,
    developer_alpha_status,
    execute_development_proposal,
    load_development_proposal,
    public_development_proposal,
)
from conscious_agent.natural_language_action_routing import build_natural_language_action_projection

checks: list[bool] = []


def require(value: object) -> None:
    checks.append(bool(value))
    assert value


def source_signature() -> str:
    digest = hashlib.sha256()
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        excluded = {".git", ".venv", "data", "__pycache__"}
        if path.is_file() and not excluded.intersection(relative.parts):
            digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


request = "Make me a web page with a calculator built into it"
before = source_signature()
legacy = classify_conversation_action(request)
modern = build_natural_language_action_projection(request)
card = build_action_proposal_card(request)
catalog = build_operator_tool_catalog()
require(legacy["classification"] == "action")
require(legacy["tool_id"] == "software_development")
require(legacy["intent"] == "supervised_software_development_campaign_request")
require(modern["intent"]["category"] == "action_request")
require(modern["grounding"]["capability_id"] == "software_development")
require(card["tool_id"] == "software_development")
require(card["approval_required"] is True)
require(catalog["tool_count"] == 13)
require(any(row["tool_id"] == "software_development" for row in catalog["tools"]))

with tempfile.TemporaryDirectory(prefix="eidolon-v1200-alpha-") as temporary:
    runtime = Path(temporary) / "runtime"
    proposal = create_development_proposal(request, runtime_root=runtime, persist=True)
    require(proposal["status"] == "ready_for_operator_review")
    require(proposal["approval_granted"] is False)
    require(proposal["planned_files"] == list(PLANNED_FILES))
    require(load_development_proposal(proposal["proposal_id"], runtime_root=runtime)["proposal_digest"] == proposal["proposal_digest"])
    public = public_development_proposal(proposal)
    require("request" not in public)
    require(public["request_digest"] == proposal["request_digest"])

    blocked = execute_development_proposal(proposal["proposal_id"], operator_approved=False, runtime_root=runtime)
    require(blocked["status"] == "awaiting_approval")
    require(not (runtime / "developer_alpha" / "workspaces").exists())

    completed = execute_development_proposal(proposal["proposal_id"], operator_approved=True, runtime_root=runtime)
    require(completed["ok"] is True)
    require(completed["status"] == "completed")
    require(completed["validation"]["passed"] == completed["validation"]["total"])
    require(completed["validation"]["node"]["ok"] is True)
    require(set(completed["workspace_manifest"]) == set(PLANNED_FILES))
    require(completed["stages_completed"] == [
        "inspect", "specify", "plan", "operator_review", "implement_in_sandbox", "test",
        "diagnose_or_repair", "present_result", "bounded_learning",
    ])
    require(completed["source_modified"] is False)
    require(completed["runtime_workspace_modified"] is True)
    require(completed["approval_consumed_once"] is True)
    require(completed["authority_granted"] is False)
    workspace = Path(completed["workspace"])
    require(workspace.is_relative_to(runtime.resolve()))
    require(not workspace.is_relative_to(ROOT.resolve()))
    require(all((workspace / name).is_file() for name in PLANNED_FILES))
    generated_html = (workspace / "index.html").read_text(encoding="utf-8")
    generated_script = (workspace / "calculator.js").read_text(encoding="utf-8")
    require('<script defer src="calculator.js"></script>' in generated_html)
    require("module.exports = { calculate }" in generated_script)
    require("window.__eidolonCalculatorReady = true" in generated_script)

    replay = execute_development_proposal(proposal["proposal_id"], operator_approved=True, runtime_root=runtime)
    require(replay["idempotent_replay"] is True)
    require(replay["receipt_digest"] == completed["receipt_digest"])
    status = developer_alpha_status(runtime_root=runtime)
    require(status["proposal_count"] == 1)
    require(status["completed_count"] == 1)

    unsupported = create_development_proposal("Build a native accounting suite", runtime_root=runtime, persist=False)
    require(unsupported["status"] == "unsupported_alpha_request")
    require(unsupported["planned_files"] == [])

    cli_runtime = Path(temporary) / "cli-runtime"
    env = {**os.environ, "EIDOLON_DATA_DIR": str(cli_runtime), "PYTHONDONTWRITEBYTECODE": "1"}
    proposed = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "developer-alpha", "propose", request, "--json"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    require(proposed.returncode == 0)
    cli_proposal = json.loads(proposed.stdout)
    denied = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "developer-alpha", "execute", "--proposal-id", cli_proposal["proposal_id"], "--json"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    require(denied.returncode != 0)
    require(json.loads(denied.stdout)["status"] == "awaiting_approval")
    approved = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "developer-alpha", "execute", "--proposal-id", cli_proposal["proposal_id"], "--approve", "--json"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
    )
    require(approved.returncode == 0)
    require(json.loads(approved.stdout)["status"] == "completed")

require(source_signature() == before)
verify = (ROOT / "tools" / "release_verify.py").read_text(encoding="utf-8")
require(verify.count("v1200_0_cognitive_beta_autonomous_developer_alpha_tests.py") == 1)

print(json.dumps({
    "ok": all(checks),
    "suite": "v1200.0-cognitive-beta-autonomous-developer-alpha",
    "passed": sum(checks),
    "total": len(checks),
    "calculator_benchmark_completed": True,
    "operator_approval_required": True,
    "source_modified": False,
    "authority_expanded": False,
}, sort_keys=True))
