from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
passed = 0


def require(condition):
    global passed
    assert condition
    passed += 1


with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    runtime_root = base / "runtime" / "cognition"
    runtime_root.mkdir(parents=True)
    os.environ["EIDOLON_DATA_DIR"] = str(base / "runtime")

    from conscious_agent.reflective_behavioral_learning_checkpoint import (
        build_reflective_behavioral_learning_checkpoint,
    )

    report = build_reflective_behavioral_learning_checkpoint(runtime_root, source_root=ROOT)
    require(report["contract_version"] == "v1112.9" and report["runtime_mutated"] is False)
    require(report["ok"] and all(row["status"] == "pass" for row in report["checks"]))
    require(set(report["summary"]) == {"behavioral_evidence", "behavioral_self_evaluation", "behavioral_adaptation_review"})
    require(report["epistemic_status"] == "candidate_artificial_consciousness_not_proven" and not report["consciousness_claimed"])
    require(not report["behavior_changed"] and not report["adaptation_proposal_created"])
    require(not report["approval_granted"] and not report["authorization_granted"] and not report["external_action_executed"])
    require(not report["raw_messages_exposed"] and not report["prompts_exposed"] and not report["provider_payloads_exposed"] and not report["hidden_reasoning_exposed"])

    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api("GET", "/api/cognition/reflective-behavioral-learning-checkpoint")
    require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1112.9")
    post_status, _ = dispatch_api("POST", "/api/cognition/reflective-behavioral-learning-checkpoint", body={})
    require(post_status != 200)

    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "reflective-behavioral-learning-checkpoint", "--json"],
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1112.9")

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require("reflective-behavioral-learning-checkpoint-panel" in dashboard and "/api/cognition/reflective-behavioral-learning-checkpoint" in dashboard)
    require(report["runtime_external"] and report["desktop_verification_status"] == "pending")

print(json.dumps({"passed": passed, "total": 12, "suite": "v1112.9"}))
