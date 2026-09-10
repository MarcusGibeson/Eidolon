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

    from conscious_agent.epistemic_maintenance_belief_revision_governance_checkpoint import (
        build_epistemic_maintenance_belief_revision_governance_checkpoint,
    )

    before = {
        path.relative_to(runtime_root).as_posix(): path.read_bytes()
        for path in runtime_root.rglob("*")
        if path.is_file()
    }
    report = build_epistemic_maintenance_belief_revision_governance_checkpoint(
        runtime_root,
        source_root=ROOT,
    )
    after = {
        path.relative_to(runtime_root).as_posix(): path.read_bytes()
        for path in runtime_root.rglob("*")
        if path.is_file()
    }

    require(report["contract_version"] == "v1118.9" and report["runtime_mutated"] is False and before == after)
    require(report["ok"] and len(report["checks"]) == 18 and all(row["status"] == "pass" for row in report["checks"]))
    require(set(report["summary"]) == {"belief_reconsideration_intake", "belief_revision_deliberation", "belief_continuity_review"})
    require(next(row for row in report["checks"] if row["id"] == "evidence_change_signal_lineage")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "bounded_revision_deliberation")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "unresolved_and_deliberate_no_revision")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "historical_supersession_without_deletion")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "false_instability_suppression")["status"] == "pass")
    require(next(row for row in report["checks"] if row["id"] == "operator_reviewed_policy_proposal_boundary")["status"] == "pass")
    require(report["epistemic_status"] == "candidate_artificial_consciousness_not_proven" and not report["consciousness_claimed"])
    require(not any(report[key] for key in ("belief_revised", "belief_mutated", "attention_selected", "intention_formed", "decision_committed", "proposal_created", "proposal_applied", "approval_granted", "authorization_granted", "external_action_executed", "release_approved", "release_promoted", "release_certified")))
    require(not any(report[key] for key in ("raw_messages_exposed", "raw_content_exposed", "prompts_exposed", "provider_payloads_exposed", "evidence_text_exposed", "hidden_reasoning_exposed", "private_content_exposed")))

    from conscious_agent.api_server import dispatch_api

    status, payload = dispatch_api("GET", "/api/cognition/epistemic-maintenance-belief-revision-governance-checkpoint")
    require(status == 200 and (payload.get("data") or {}).get("contract_version") == "v1118.9")
    post_status, _ = dispatch_api("POST", "/api/cognition/epistemic-maintenance-belief-revision-governance-checkpoint", body={})
    require(post_status != 200)

    cli = subprocess.run(
        [sys.executable, str(ROOT / "eidolon.py"), "epistemic-maintenance-belief-revision-governance-checkpoint", "--json"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=dict(os.environ),
        timeout=60,
    )
    require(cli.returncode == 0 and json.loads(cli.stdout)["contract_version"] == "v1118.9")

    dashboard = (ROOT / "conscious_agent" / "dashboard_first_use.py").read_text(encoding="utf-8")
    require("epistemic-maintenance-belief-revision-governance-checkpoint-panel" in dashboard and "/api/cognition/epistemic-maintenance-belief-revision-governance-checkpoint" in dashboard)
    require(report["runtime_external"] and report["desktop_verification_status"] == "pending")
    require(report["check_count"] == 18 and report["source_modified"] is False)

print(json.dumps({"passed": passed, "total": 18, "suite": "v1118.9"}))
