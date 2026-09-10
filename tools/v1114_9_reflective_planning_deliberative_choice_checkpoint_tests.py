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

    from conscious_agent.reflective_planning_deliberative_choice_checkpoint import (
        build_reflective_planning_deliberative_choice_checkpoint,
    )

    before = {p.relative_to(runtime_root).as_posix(): p.read_bytes() for p in runtime_root.rglob("*") if p.is_file()}
    report = build_reflective_planning_deliberative_choice_checkpoint(runtime_root, source_root=ROOT)
    after = {p.relative_to(runtime_root).as_posix(): p.read_bytes() for p in runtime_root.rglob("*") if p.is_file()}

    require(report["contract_version"] == "v1114.9" and report["runtime_mutated"] is False and before == after)
    require(report["ok"] and all(row["status"] == "pass" for row in report["checks"]))
    require(set(report["summary"]) == {"deliberative_option_continuity", "decision_commitment_lifecycle", "deliberative_decision_follow_through"})
    require(next(row for row in report["checks"] if row["id"] == "bounded_option_comparison")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "commitment_lifecycle_continuity")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "decision_to_intention_restraint")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "outcome_and_reconsideration_restraint")["status"] == "pass")
    require(report["epistemic_status"] == "candidate_artificial_consciousness_not_proven" and not report["consciousness_claimed"])
    require(not any(report[key] for key in ("decision_committed", "intention_candidate_created", "intention_formed", "proposal_created", "approval_granted", "authorization_granted", "external_action_executed")))
    require(not any(report[key] for key in ("raw_messages_exposed", "prompts_exposed", "provider_payloads_exposed", "evidence_text_exposed", "hidden_reasoning_exposed", "private_content_exposed")))

    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api("GET", "/api/cognition/reflective-planning-deliberative-choice-checkpoint")
    require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1114.9")
    post_status, _ = dispatch_api("POST", "/api/cognition/reflective-planning-deliberative-choice-checkpoint", body={})
    require(post_status != 200)

    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "reflective-planning-deliberative-choice-checkpoint", "--json"],
        capture_output=True,
        text=True,
        env=dict(os.environ),
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1114.9")

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require("reflective-planning-deliberative-choice-checkpoint-panel" in dashboard and "/api/cognition/reflective-planning-deliberative-choice-checkpoint" in dashboard)
    require(report["runtime_external"] and report["desktop_verification_status"] == "pending")

print(json.dumps({"passed": passed, "total": 15, "suite": "v1114.9"}))
