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

    from conscious_agent.bounded_inquiry_checkpoint import build_bounded_inquiry_checkpoint

    report = build_bounded_inquiry_checkpoint(runtime_root, source_root=ROOT)
    require(report["contract_version"] == "v1113.9" and report["runtime_mutated"] is False)
    require(report["ok"] and all(row["status"] == "pass" for row in report["checks"]))
    require(set(report["summary"]) == {"active_inquiry_continuity", "inquiry_evidence_governance", "inquiry_resolution_continuity"})
    require(report["epistemic_status"] == "candidate_artificial_consciousness_not_proven" and not report["consciousness_claimed"])
    require(not report["research_proposal_created"] and not report["belief_changed"])
    require(not report["approval_granted"] and not report["authorization_granted"] and not report["external_action_executed"])
    require(not report["external_browsing_performed"] and not report["provider_contacted"] and not report["user_prompted"] and not report["message_sent"])
    require(not report["raw_messages_exposed"] and not report["prompts_exposed"] and not report["provider_payloads_exposed"] and not report["evidence_text_exposed"] and not report["hidden_reasoning_exposed"])

    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api("GET", "/api/cognition/bounded-inquiry-checkpoint")
    require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1113.9")
    post_status, _ = dispatch_api("POST", "/api/cognition/bounded-inquiry-checkpoint", body={})
    require(post_status != 200)

    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "bounded-inquiry-checkpoint", "--json"],
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1113.9")

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require("bounded-inquiry-checkpoint-panel" in dashboard and "/api/cognition/bounded-inquiry-checkpoint" in dashboard)
    require(report["runtime_external"] and report["desktop_verification_status"] == "pending")

print(json.dumps({"passed": passed, "total": 13, "suite": "v1113.9"}))
